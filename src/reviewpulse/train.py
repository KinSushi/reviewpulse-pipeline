"""Rôle
    Entraîner, mesurer, enregistrer le modèle de classification de sentiment et, si les critères sont remplis, promouvoir la version.

Place dans la chaîne
    - Après le module `transform` (zone propre) et exécuté par le DAG hebdomadaire.
    - Produit le modèle enregistré dans le registre MLflow, qui alimente ensuite les modules `score` et `api`.

Fonctionnement
    1. Le jeu de test (20 % stratifié) est tiré **uniquement** des avis dont `sample_source == config.SAMPLE_NATURAL`.
    2. L’entraînement utilise le reste des avis naturels **plus** toutes les lignes `sample_source == config.SAMPLE_NEGATIVE_BOOST`.
    3. Un seuil de décision est recherché par validation croisée stratifiée à 5 plis sur les avis naturels d’entraînement ; à chaque pli, les avis de boost sont ajoutés à l’entraînement mais ne sont jamais évalués.
    4. Le modèle final (pipeline TF‑IDF + régression logistique) est entraîné sur l’ensemble des données d’entraînement et l’attribut `decision_threshold_` y est fixé.
    5. Les métriques (`f1_macro`, `recall_negative`, `precision_negative`, `roc_auc`, etc.) sont calculées sur le jeu de test naturel au seuil retenu.
    6. Le modèle, les métriques et l’artefact `top_terms.json` sont loggés dans MLflow.  
       L’alias `challenger` pointe sur la version entraînée ; l’alias `champion` est mis à jour **si** `f1_macro >= config.F1_MACRO_MIN` (0,75) **et** supérieur au F1 du champion actuel.

Choix de conception
    - Pipeline TF‑IDF (char_wb, n‑grammes 2‑5) + `LogisticRegression(C=4.0, class_weight="balanced", max_iter=2000, random_state=config.RANDOM_STATE)` (ADR 0006).  
    - Utilisation du flux négatif complémentaire uniquement pour l’entraînement et du seuil appris via CV (ADR 0007).  
    - Barrière de promotion et gestion des alias `challenger` / `champion` (ADR 0008).  
    - Pas d'input_example à l'enregistrement, seulement la signature : avec un input_example, MLflow valide l'exemple par son chemin générique, qui passe un tableau au vectoriseur et échoue (« 'int' object has no attribute 'lower' », constaté le 16/09/2026).  
    - Enregistrement des artefacts via `mlflow.log_dict` avec emplacement absolu `config.ARTIFACT_DIR` (ADR 0010).

Preuves
    - F1 macro = 0,807 et AUC = 0,948 sur le jeu de test naturel (mesure documentée).  
    - Un ré‑entraînement identique reproduit les mêmes métriques et ne déclenche pas de promotion, confirmant la règle « strictement supérieur » (ADR 0008).

Tests associés
    - `test_train_score.py`
    - `test_boost.py`
    - `test_decision.py`
    - `test_artifacts_location.py`
    - `test_fresh_dirs.py`
"""

import logging
import json
from pathlib import Path

import pandas as pd
import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import (
    f1_score,
    recall_score,
    precision_score,
    roc_auc_score,
)

# Import du module décision unique, source de vérité pour le calcul des probabilités
# et la conversion en labels. Cela garantit la cohérence entre train, score et API.
from reviewpulse import decision, config

logger = logging.getLogger(__name__)


def _select_experiment(tracking_uri: str) -> None:
    """Sélectionne ou crée l’expérience MLflow selon la règle d’emplacement des artefacts.

    Args:
        tracking_uri: URI de suivi MLflow (ex. « sqlite:///… », « file:… », ou serveur HTTP).

    Pourquoi :
        Garantir que les artefacts sont stockés dans `config.ARTIFACT_DIR` lorsqu’on utilise un backend local, afin que l’API puisse les retrouver.
    """
    # Si le backend est local, on crée l’expérience avec un emplacement d’artefacts dédié.
    if tracking_uri.startswith("sqlite:") or tracking_uri.startswith("file:"):
        if mlflow.get_experiment_by_name(config.MLFLOW_EXPERIMENT) is None:
            # Crée le répertoire d’artefacts s’il n’existe pas.
            Path(config.ARTIFACT_DIR).mkdir(parents=True, exist_ok=True)
            mlflow.create_experiment(
                config.MLFLOW_EXPERIMENT,
                artifact_location=Path(config.ARTIFACT_DIR).resolve().as_uri(),
            )
    # Sélectionne (ou crée) l’expérience pour le reste du run.
    mlflow.set_experiment(config.MLFLOW_EXPERIMENT)


def build_pipeline() -> Pipeline:
    """Construit le pipeline de vectorisation TF‑IDF + régression logistique.

    Returns:
        Pipeline scikit‑learn prêt à être entraîné.

    Pourquoi :
        TF‑IDF sur des n‑grammes de caractères capture les variations orthographiques fréquentes dans les avis courts ; la régression logistique avec `class_weight="balanced"` gère le déséquilibre des classes.
    """
    tfidf = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 5),
        min_df=2,
        max_features=100000,
        sublinear_tf=True,
        lowercase=True,
    )
    clf = LogisticRegression(
        C=4.0,
        class_weight="balanced",
        max_iter=2000,
        random_state=config.RANDOM_STATE,
    )
    return Pipeline([("tfidf", tfidf), ("clf", clf)])


def _top_terms(pipeline: Pipeline, n: int = 20) -> dict:
    """Extrait les n termes les plus négatifs et les n plus positifs.

    Args:
        pipeline: Pipeline entraîné contenant les étapes « tfidf » et « clf ».
        n: Nombre de termes à extraire de chaque côté (défaut = 20).

    Returns:
        Dictionnaire avec les clés « negative » et « positive » contenant les
        listes de termes.

    Pourquoi :
        Fournir un aperçu interprétable des caractéristiques influençant le modèle, utilisé dans le tableau de bord et les artefacts MLflow.
    """
    vectorizer: TfidfVectorizer = pipeline.named_steps["tfidf"]
    clf: LogisticRegression = pipeline.named_steps["clf"]
    coeff = clf.coef_[0]
    terms = vectorizer.get_feature_names_out()
    term_coeff = list(zip(terms, coeff))
    term_coeff.sort(key=lambda x: x[1])  # du plus négatif au plus positif
    negative = [t for t, _ in term_coeff[:n]]
    positive = [t for t, _ in term_coeff[-n:]][::-1]
    return {"negative": negative, "positive": positive}


def _select_decision_threshold(
    pipeline: Pipeline,
    X_train_nat: pd.Series,
    y_train_nat: pd.Series,
    boost_df: pd.DataFrame,
) -> tuple[float, float]:
    """Recherche le seuil optimal sur les données naturelles d'entraînement.

    Le calcul des probabilités négatives utilise la fonction unique
    `decision.negative_proba` afin d'éviter toute duplication de la logique
    (classe 0 ↔ probabilité négative). Les prédictions hors‑seuil sont obtenues
    via `decision.predict_labels`, garantissant la même convention que le
    reste du code base.

    Args:
        pipeline: Pipeline de base (non entraîné) utilisé pour chaque pli.
        X_train_nat: Série des textes d’avis naturels d’entraînement.
        y_train_nat: Série des labels correspondants.
        boost_df: DataFrame contenant les avis de boost négatif.

    Returns:
        Tuple contenant le seuil choisi et le F1 macro moyen obtenu
        sur la validation croisée.

    Pourquoi :
        Centraliser la recherche de seuil afin d’assurer la cohérence avec le module `decision` et d’éviter les dérives de convention.
    """
    skf = StratifiedKFold(
        n_splits=5, shuffle=True, random_state=config.RANDOM_STATE
    )
    oof_proba = pd.Series(index=X_train_nat.index, dtype="float64")

    for train_idx, val_idx in skf.split(X_train_nat, y_train_nat):
        # Entraînement du pli avec les données naturelles + boost
        X_fold_train = pd.concat(
            [X_train_nat.iloc[train_idx], boost_df["review_text"]]
        )
        y_fold_train = pd.concat(
            [y_train_nat.iloc[train_idx], boost_df["label"]]
        )
        pipeline_fold = build_pipeline()
        pipeline_fold.fit(X_fold_train, y_fold_train)

        # Probabilité négative via la fonction centrale
        proba_val = decision.negative_proba(pipeline_fold, X_train_nat.iloc[val_idx])
        oof_proba.iloc[val_idx] = proba_val

    best_thr = config.DEFAULT_DECISION_THRESHOLD
    best_f1 = -1.0
    for thr in config.THRESHOLD_GRID:
        # Prédictions selon le seuil grâce à la fonction unique
        preds = decision.predict_labels(oof_proba, thr)
        f1 = f1_score(y_train_nat, preds, average="macro")
        # En cas d’égalité, on privilégie le seuil le plus proche de 0,5
        if f1 > best_f1 or (abs(f1 - best_f1) < 1e-9 and abs(thr - 0.5) < abs(best_thr - 0.5)):
            best_f1 = f1
            best_thr = thr
    return float(best_thr), float(best_f1)


def train_and_log(
    df: pd.DataFrame,
    tracking_uri: str | None = None,
    register: bool = True,
) -> dict:
    """Entraîne le modèle, le logge dans MLflow et gère les alias.

    Args:
        df: DataFrame contenant les avis nettoyés (conforme à `config.CLEAN_COLUMNS`).
        tracking_uri: URI de suivi MLflow ; si None, utilise `config.MLFLOW_TRACKING_URI`.
        register: Si True, enregistre le modèle dans le registre MLflow et crée les alias.

    Returns:
        Dictionnaire récapitulatif des métriques, identifiants de run et de version,
        ainsi que du statut de promotion.

    Raises:
        MlflowException: Propagé si une opération MLflow échoue.

    Pourquoi :
        Centraliser tout le flux d’entraînement, de la création d’expérience à la promotion éventuelle, afin de garantir la traçabilité et la reproductibilité.
    """
    if tracking_uri is None:
        tracking_uri = config.MLFLOW_TRACKING_URI

    # Si le backend est SQLite, on s’assure que le répertoire du fichier existe.
    if tracking_uri.startswith("sqlite:///"):
        sqlite_path = tracking_uri[len("sqlite:///") :]
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)

    mlflow.set_tracking_uri(tracking_uri)
    _select_experiment(tracking_uri)

    # Garantir la présence de la colonne sample_source
    if "sample_source" not in df.columns:
        df["sample_source"] = config.SAMPLE_NATURAL

    natural_df = df[df["sample_source"] == config.SAMPLE_NATURAL]
    boost_df = df[df["sample_source"] == config.SAMPLE_NEGATIVE_BOOST]
    n_boost = int(len(boost_df))

    # Split du jeu naturel
    X_nat = natural_df["review_text"].astype("string")
    y_nat = natural_df["label"]
    X_train_nat, X_test_nat, y_train_nat, y_test_nat = train_test_split(
        X_nat,
        y_nat,
        test_size=0.2,
        stratify=y_nat,
        random_state=config.RANDOM_STATE,
    )

    # Sélection du seuil de décision via CV sur les données naturelles d'entraînement
    decision_threshold, f1_cv_mean = _select_decision_threshold(
        build_pipeline(), X_train_nat, y_train_nat, boost_df
    )

    # Entraînement final sur l'ensemble (naturel + boost)
    X_train_full = pd.concat([X_train_nat, boost_df["review_text"]])
    y_train_full = pd.concat([y_train_nat, boost_df["label"]])
    pipeline = build_pipeline()
    pipeline.fit(X_train_full, y_train_full)
    pipeline.decision_threshold_ = decision_threshold

    # Évaluation sur le jeu de test naturel
    proba_test = decision.negative_proba(pipeline, X_test_nat)
    y_pred_test = decision.predict_labels(proba_test, decision_threshold)

    f1_macro = f1_score(y_test_nat, y_pred_test, average="macro")
    recall_negative = recall_score(y_test_nat, y_pred_test, pos_label=0)
    precision_negative = precision_score(y_test_nat, y_pred_test, pos_label=0)
    roc_auc = roc_auc_score((y_test_nat == 0).astype(int), proba_test)

    n_train = int(len(y_train_full))
    n_test = int(len(y_test_nat))
    negative_share = float((y_test_nat == 0).mean())

    # Signature du modèle (sans input_example)
    example_input = X_train_full.head(5).astype(str).tolist()
    signature = infer_signature(
        example_input,
        pipeline.predict_proba(example_input),
    )

    with mlflow.start_run() as run:
        mlflow.log_param("decision_threshold", decision_threshold)
        mlflow.log_param("n_boost", n_boost)

        mlflow.log_metric("f1_macro", f1_macro)
        mlflow.log_metric("recall_negative", recall_negative)
        mlflow.log_metric("precision_negative", precision_negative)
        mlflow.log_metric("roc_auc", roc_auc)
        mlflow.log_metric("n_train", n_train)
        mlflow.log_metric("n_test", n_test)
        mlflow.log_metric("negative_share", negative_share)
        mlflow.log_metric("f1_cv_mean", f1_cv_mean)  # métrique CV ajoutée

        top_terms = _top_terms(pipeline, n=20)
        mlflow.log_dict(top_terms, "artifacts/top_terms.json")

        model_info = mlflow.sklearn.log_model(
            sk_model=pipeline,
            name="model",
            signature=signature,
            registered_model_name=config.MODEL_NAME if register else None,
        )
        run_id = run.info.run_id

        mlflow.set_tag("decision_threshold", decision_threshold)

    client = MlflowClient(tracking_uri=tracking_uri)

    model_version = None
    if register:
        model_version = str(model_info.registered_model_version)
        client.set_registered_model_alias(
            config.MODEL_NAME, config.ALIAS_CHALLENGER, model_version
        )
        # Tag de version sur le modèle enregistré
        client.set_model_version_tag(
            config.MODEL_NAME, model_version, "decision_threshold", str(decision_threshold)
        )

    promoted = False
    champion_f1 = None
    try:
        champion_mv = client.get_model_version_by_alias(
            config.MODEL_NAME, config.ALIAS_CHAMPION
        )
        champion_run = client.get_run(champion_mv.run_id)
        champion_f1 = champion_run.data.metrics.get("f1_macro")
    except MlflowException:
        champion_f1 = None

    # Promotion éventuelle du challenger en champion
    if (
        register
        and f1_macro >= config.F1_MACRO_MIN
        and (champion_f1 is None or f1_macro > champion_f1)
    ):
        if model_version is not None:
            client.set_registered_model_alias(
                config.MODEL_NAME, config.ALIAS_CHAMPION, model_version
            )
            promoted = True

    result = {
        "run_id": run_id,
        "model_version": model_version,
        "promoted": promoted,
        "decision_threshold": decision_threshold,
        "n_boost": n_boost,
        "f1_macro": f1_macro,
        "recall_negative": recall_negative,
        "precision_negative": precision_negative,
        "roc_auc": roc_auc,
        "n_train": n_train,
        "n_test": n_test,
        "negative_share": negative_share,
        "f1_cv_mean": f1_cv_mean,
    }
    return result


def main() -> int:
    """Charge les données nettoyées, entraîne le modèle et affiche les métriques.

    Returns:
        Code de sortie du processus (0 = succès).

    Pourquoi :
        Fournir une interface exécutable conforme aux conventions du projet (journalisation, lecture du fichier `config.CLEAN_FILE`, affichage JSON).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    df = pd.read_parquet(config.CLEAN_FILE)
    metrics = train_and_log(df)
    print(json.dumps(metrics, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
