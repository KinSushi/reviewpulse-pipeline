# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""Rôle
    Entraîner, mesurer, enregistrer le modèle de classification de sentiment et, si les critères sont remplis, promouvoir la version.

Place dans la chaîne
    - Après le module `transform` (zone propre) et exécuté par le DAG hebdomadaire.
    - Produit le modèle enregistré dans le registre MLflow, qui alimente ensuite les modules `score` et `api`.

Fonctionnement
    1. Le jeu de test (20 % stratifié) est tiré **uniquement** des avis dont `sample_source == config.SAMPLE_NATURAL`.
    2. L'entraînement utilise le reste des avis naturels **plus** toutes les lignes `sample_source == config.SAMPLE_NEGATIVE_BOOST`.
    3. Un seuil de décision est recherché par validation croisée stratifiée à 5 plis sur les avis naturels d'entraînement ; à chaque pli, les avis de boost sont ajoutés à l'entraînement mais ne sont jamais évalués.
    4. Le modèle final (pipeline TF‑IDF + régression logistique) est entraîné sur l'ensemble des données d'entraînement et l'attribut `decision_threshold_` y est fixé.
    5. Les métriques (`f1_macro`, `recall_negative`, `precision_negative`, `roc_auc`, etc.) sont calculées sur le jeu de test naturel au seuil retenu.
    6. Le modèle, les métriques et l'artefact `top_terms.json` sont loggés dans MLflow.  
       L'alias `challenger` pointe sur la version entraînée ; l'alias `champion` est mis à jour **si** `f1_macro >= config.F1_MACRO_MIN` (0,75) **et** supérieur au F1 du champion actuel.

Choix de conception
    - Pipeline TF‑IDF (char_wb, n‑grammes 2‑5) + `LogisticRegression(C=10.0, class_weight="balanced", max_iter=2000, random_state=config.RANDOM_STATE)` (ADR 0006).  
    - Utilisation du flux négatif complémentaire uniquement pour l'entraînement et du seuil appris via CV (ADR 0007).  
    - Barrière de promotion et gestion des alias `challenger` / `champion` (ADR 0008).  
    - Pas d'input_example à l'enregistrement, seulement la signature : avec un input_example, MLflow valide l'exemple par son chemin générique, qui passe un tableau au vectoriseur et échoue (« 'int' object has no attribute 'lower' », constaté le 16/09/2026).  
    - Enregistrement des artefacts via `mlflow.log_dict` avec emplacement absolu `config.ARTIFACT_DIR` (ADR 0010).

Preuves
    - F1 macro = 0,807 et AUC = 0,948 sur le jeu de test naturel (mesure documentée).  
    - Un ré‑entraînement identique reproduit les mêmes métriques et ne déclenche pas de promotion, confirmant la règle « strictement supérieur » (ADR 0008).

Tests associés
    - `test_train_score.py`
    - `test_boost.py`
    - `test_decision.py`
    - `test_artifacts_location.py`
    - `test_fresh_dirs.py`

Décision appliquée ici : ADR 0018 — reproductibilité : empreinte du jeu de données et étiquette `code_commit` dans chaque run.

Quoi
    Module d'entraînement du modèle de classification de sentiment, responsable de la construction du pipeline, de la recherche du seuil de décision, de l'évaluation des métriques et de l'enregistrement dans MLflow avec gestion des alias champion/challenger.

Pourquoi
    Éviter la dérive de convention entre l'entraînement, le scoring et l'API en centralisant la logique de décision (ADR 0009) ; garantir que seul un modèle strictement meilleur que le champion en service soit promu (ADR 0008) ; assurer la reproductibilité des runs via l'empreinte du jeu de données et l'étiquette code_commit (ADR 0018).

Où
    - Appelé par : le DAG hebdomadaire (`dags/reviewpulse_daily.py`) et la fonction `main()` de ce module.
    - Lit : le fichier parquet de la zone propre (`config.CLEAN_FILE`), la configuration (`config`), le module de décision (`decision`).
    - Écrit : le modèle dans le registre MLflow, les métriques dans le run MLflow, l'artefact `top_terms.json` dans `config.ARTIFACT_DIR`.

Comment
    Le module sépare les avis naturels (pour le test et la recherche de seuil) des avis de boost négatif (pour l'entraînement uniquement). Une validation croisée stratifiée à 5 plis sur les naturels d'entraînement permet de sélectionner le seuil optimal dans `config.THRESHOLD_GRID`. Le modèle final est entraîné sur l'ensemble complet (naturels + boost) avec le seuil retenu. Les métriques sont calculées sur le test naturel uniquement. L'enregistrement MLflow inclut la signature du modèle (sans input_example), les métriques, les paramètres et l'empreinte du jeu de données. La promotion en champion n'a lieu que si le F1 macro dépasse le seuil minimal et le F1 du champion actuel.

Limites connues
    - Ne garantit pas la détection de dérive des données d'entrée (responsabilité du module `drift`).
    - Ne gère pas le rollback automatique en cas d'échec post-promotion (responsabilité du module `rollback`).
    - L'empreinte du jeu de données nécessite que le fichier source existe sur disque ; sinon le hash est marqué « absent ».
    - La recherche de seuil ne teste que les valeurs dans `config.THRESHOLD_GRID` ; un optimum entre deux valeurs de la grille peut être manqué.
"""

import logging
import json
import os
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
    """Sélectionne ou crée l'expérience MLflow selon la règle d'emplacement des artefacts.

    Rôle : garantir que les artefacts sont stockés dans le répertoire configuré lorsque le backend est local.

    Pourquoi :
        L'API doit pouvoir retrouver les artefacts du modèle ; sans emplacement explicite, un backend SQLite ou file stocke les artefacts dans un répertoire temporaire inaccessible.

    Args:
        tracking_uri: URI de suivi MLflow (ex. « sqlite:///… », « file:… », ou serveur HTTP).

    Returns:
        Aucun retour ; configure l'expérience MLflow globalement.

    Raises:
        Aucun ; les exceptions MLflow sont propagées au caller.
    """
    # Si le backend est local, on crée l'expérience avec un emplacement d'artefacts dédié.
    # Pourquoi : sans artifact_location explicite, MLflow utilise un répertoire temporaire
    # qui n'est pas accessible à l'API en production.
    if tracking_uri.startswith("sqlite:") or tracking_uri.startswith("file:"):
        if mlflow.get_experiment_by_name(config.MLFLOW_EXPERIMENT) is None:
            # Crée le répertoire d'artefacts s'il n'existe pas.
            Path(config.ARTIFACT_DIR).mkdir(parents=True, exist_ok=True)
            mlflow.create_experiment(
                config.MLFLOW_EXPERIMENT,
                artifact_location=Path(config.ARTIFACT_DIR).resolve().as_uri(),
            )
            logger.info(
                "Expérience MLflow créée avec artefacts dans %s",
                config.ARTIFACT_DIR,
            )
        else:
            logger.debug("Expérience MLflow %s déjà existante", config.MLFLOW_EXPERIMENT)
    # Sélectionne (ou crée) l'expérience pour le reste du run.
    mlflow.set_experiment(config.MLFLOW_EXPERIMENT)
    logger.info("Expérience MLflow sélectionnée : %s", config.MLFLOW_EXPERIMENT)


def build_pipeline() -> Pipeline:
    """Construit le pipeline de vectorisation TF‑IDF + régression logistique.

    Rôle : instancier un pipeline reproductible avec les hyperparamètres validés.

    Pourquoi :
        TF‑IDF sur des n‑grammes de caractères capture les variations orthographiques fréquentes dans les avis courts ; la régression logistique avec `class_weight="balanced"` gère le déséquilibre des classes (ADR 0006).

    Returns:
        Pipeline scikit‑learn prêt à être entraîné.

    Raises:
        Aucun ; les exceptions de construction sont propagées au caller.
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
        # C=10.0 remplace C=4.0 le 20/09/2026, sur mesure et non sur intuition :
        # recherche a 12 points, validation croisee a 5 plis, F1 macro 0,7517 contre
        # 0,7437, soit 2,7 erreurs types. Tendance monotone en C, et meme ecart retrouve
        # dans un passage independant. Voir docs/evidence/reglage_hyperparametres.md.
        # La barriere de promotion (ADR 0008) reste juge : elle refusera ce modele s il
        # n est pas strictement meilleur que le champion en service.
        C=10.0,
        class_weight="balanced",
        max_iter=2000,
        random_state=config.RANDOM_STATE,
    )
    return Pipeline([("tfidf", tfidf), ("clf", clf)])


def _top_terms(pipeline: Pipeline, n: int = 20) -> dict:
    """Extrait les n termes les plus négatifs et les n plus positifs.

    Rôle : produire un artefact interprétable pour le tableau de bord et la Model Card.

    Pourquoi :
        Les coefficients de la régression logistique indiquent la contribution de chaque terme à la prédiction ; trier par coefficient permet d'identifier les marqueurs les plus discriminants.

    Args:
        pipeline: Pipeline entraîné contenant les étapes « tfidf » et « clf ».
        n: Nombre de termes à extraire de chaque côté (défaut = 20).

    Returns:
        Dictionnaire avec les clés « negative » et « positive » contenant les
        listes de termes.

    Raises:
        KeyError : si le pipeline ne contient pas les étapes attendues.
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


def _dataset_fingerprint(df: pd.DataFrame, chemin: Path) -> dict:
    """Génère l'empreinte du jeu de données utilisé pour l'entraînement.

    Rôle : tracer la version exacte des données ayant servi à l'entraînement pour la reproductibilité (ADR 0018).

    Pourquoi :
        Sans empreinte, il est impossible de reproduire un run ou de détecter une dérive silencieuse des données d'entraînement.

    Retourne un dictionnaire contenant le condensé SHA‑256 du fichier,
    le nombre de lignes du DataFrame, les bornes de la colonne ``created_at``
    et le comptage des lignes par source d'échantillonnage.

    Les valeurs sont calculées sans charger le fichier complet en mémoire.

    Args:
        df: DataFrame contenant les avis nettoyés.
        chemin: Chemin du fichier parquet source.

    Returns:
        Dictionnaire avec les clés : data_sha256, data_rows, data_first_review,
        data_last_review, data_natural_rows, data_boost_rows.

    Raises:
        Aucun ; les colonnes absentes sont gérées par des valeurs par défaut.
    """
    import hashlib

    # Condensé SHA‑256 du fichier sur disque
    # Comment : lecture par blocs de 8192 octets pour éviter de charger le fichier entier en mémoire.
    sha256 = hashlib.sha256()
    if chemin.exists():
        with chemin.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        data_sha256 = sha256.hexdigest()
        logger.debug("Empreinte SHA-256 calculée pour %s", chemin)
    else:
        # L'empreinte du fichier n'a de sens que lorsque l'entraînement lit la zone propre sur disque.
        data_sha256 = "absent"
        logger.warning("Fichier source %s introuvable ; empreinte marquée 'absent'", chemin)

    # Nombre de lignes du DataFrame
    data_rows = int(len(df))

    # Bornes temporelles de la colonne created_at
    # Pourquoi : permet de vérifier que l'entraînement couvre la période attendue.
    if "created_at" in df.columns and not df.empty:
        first = df["created_at"].min()
        last = df["created_at"].max()
        data_first_review = first.isoformat()
        data_last_review = last.isoformat()
    else:
        data_first_review = ""
        data_last_review = ""
        logger.debug("Colonne created_at absente ou DataFrame vide ; bornes temporelles vides")

    # Comptage par source d'échantillonnage
    # Pourquoi : vérifier que le flux de boost négatif est bien présent en quantité attendue.
    data_natural_rows = int((df["sample_source"] == config.SAMPLE_NATURAL).sum())
    data_boost_rows = int((df["sample_source"] == config.SAMPLE_NEGATIVE_BOOST).sum())

    return {
        "data_sha256": data_sha256,
        "data_rows": data_rows,
        "data_first_review": data_first_review,
        "data_last_review": data_last_review,
        "data_natural_rows": data_natural_rows,
        "data_boost_rows": data_boost_rows,
    }


def _select_decision_threshold(
    pipeline: Pipeline,
    X_train_nat: pd.Series,
    y_train_nat: pd.Series,
    boost_df: pd.DataFrame,
) -> tuple[float, float]:
    """Recherche le seuil optimal sur les données naturelles d'entraînement.

    Rôle : déterminer le seuil de décision qui maximise le F1 macro sur les avis naturels.

    Pourquoi :
        Centraliser la recherche de seuil afin d'assurer la cohérence avec le module `decision` et d'éviter les dérives de convention (ADR 0007, ADR 0009).

    Le calcul des probabilités négatives utilise la fonction unique
    `decision.negative_proba` afin d'éviter toute duplication de la logique
    (classe 0 ↔ probabilité négative). Les prédictions hors‑seuil sont obtenues
    via `decision.predict_labels`, garantissant la même convention que le
    reste du code base.

    Args:
        pipeline: Pipeline de base (non entraîné) utilisé pour chaque pli.
        X_train_nat: Série des textes d'avis naturels d'entraînement.
        y_train_nat: Série des labels correspondants.
        boost_df: DataFrame contenant les avis de boost négatif.

    Returns:
        Tuple contenant le seuil choisi et le F1 macro moyen obtenu
        sur la validation croisée.

    Raises:
        Aucun ; les exceptions de scikit-learn sont propagées au caller.
    """
    # Pourquoi : 5 plis est un compromis entre variance de l'estimation et coût de calcul.
    # shuffle=True avec random_state garantit la reproductibilité (ADR 0018).
    skf = StratifiedKFold(
        n_splits=5, shuffle=True, random_state=config.RANDOM_STATE
    )
    oof_proba = pd.Series(index=X_train_nat.index, dtype="float64")
    logger.info(
        "Recherche de seuil : %d plis, %d avis naturels d'entraînement",
        skf.n_splits,
        len(X_train_nat),
    )

    for train_idx, val_idx in skf.split(X_train_nat, y_train_nat):
        # Entraînement du pli avec les données naturelles + boost
        # Pourquoi : le boost n'est utilisé qu'à l'entraînement, jamais à l'évaluation,
        # pour ne pas biaiser la recherche de seuil (ADR 0007).
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
        # En cas d'égalité, on privilégie le seuil le plus proche de 0,5
        # Pourquoi : en l'absence de différence de performance, un seuil proche de 0,5
        # est plus interprétable et moins sujet aux fluctuations numériques.
        if f1 > best_f1 or (abs(f1 - best_f1) < 1e-9 and abs(thr - 0.5) < abs(best_thr - 0.5)):
            best_f1 = f1
            best_thr = thr
    logger.info(
        "Seuil optimal : %.3f (F1 macro CV : %.4f)",
        best_thr,
        best_f1,
    )
    return float(best_thr), float(best_f1)


def train_and_log(
    df: pd.DataFrame,
    tracking_uri: str | None = None,
    register: bool = True,
) -> dict:
    """Entraîne le modèle, le logge dans MLflow et gère les alias.

    Rôle : orchestrer l'ensemble du flux d'entraînement, de la préparation des données à la promotion éventuelle.

    Pourquoi :
        Centraliser tout le flux d'entraînement, de la création d'expérience à la promotion éventuelle, afin de garantir la traçabilité et la reproductibilité (ADR 0018).

    Args:
        df: DataFrame contenant les avis nettoyés (conforme à `config.CLEAN_COLUMNS`).
        tracking_uri: URI de suivi MLflow ; si None, utilise `config.MLFLOW_TRACKING_URI`.
        register: Si True, enregistre le modèle dans le registre MLflow et crée les alias.

    Returns:
        Dictionnaire récapitulatif des métriques, identifiants de run et de version,
        ainsi que du statut de promotion.

    Raises:
        MlflowException: Propagé si une opération MLflow échoue.
    """
    if tracking_uri is None:
        tracking_uri = config.MLFLOW_TRACKING_URI
    logger.info("URI de tracking MLflow : %s", tracking_uri)

    # Si le backend est SQLite, on s'assure que le répertoire du fichier existe.
    # Pourquoi : MLflow échoue si le répertoire parent du fichier SQLite n'existe pas.
    if tracking_uri.startswith("sqlite:///"):
        sqlite_path = tracking_uri[len("sqlite:///") :]
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Répertoire SQLite vérifié : %s", Path(sqlite_path).parent)

    mlflow.set_tracking_uri(tracking_uri)
    _select_experiment(tracking_uri)

    # Garantir la présence de la colonne sample_source
    # Pourquoi : permet d'exécuter le module sur un DataFrame de test sans cette colonne.
    if "sample_source" not in df.columns:
        df["sample_source"] = config.SAMPLE_NATURAL
        logger.warning("Colonne sample_source absente ; valeur par défaut : %s", config.SAMPLE_NATURAL)

    natural_df = df[df["sample_source"] == config.SAMPLE_NATURAL]
    boost_df = df[df["sample_source"] == config.SAMPLE_NEGATIVE_BOOST]
    n_boost = int(len(boost_df))
    logger.info(
        "Données chargées : %d naturels, %d boost négatif",
        len(natural_df),
        n_boost,
    )

    # Split du jeu naturel
    # Pourquoi : le test est tiré uniquement des naturels pour refléter la distribution réelle en production.
    X_nat = natural_df["review_text"].astype("string")
    y_nat = natural_df["label"]
    X_train_nat, X_test_nat, y_train_nat, y_test_nat = train_test_split(
        X_nat,
        y_nat,
        test_size=0.2,
        stratify=y_nat,
        random_state=config.RANDOM_STATE,
    )
    logger.info(
        "Split effectué : %d train, %d test (20%% stratifié)",
        len(X_train_nat),
        len(X_test_nat),
    )

    # Sélection du seuil de décision via CV sur les données naturelles d'entraînement
    decision_threshold, f1_cv_mean = _select_decision_threshold(
        build_pipeline(), X_train_nat, y_train_nat, boost_df
    )

    # Entraînement final sur l'ensemble (naturel + boost)
    # Pourquoi : le boost améliore la capacité du modèle à détecter les négatifs sans biaiser l'évaluation.
    X_train_full = pd.concat([X_train_nat, boost_df["review_text"]])
    y_train_full = pd.concat([y_train_nat, boost_df["label"]])
    pipeline = build_pipeline()
    pipeline.fit(X_train_full, y_train_full)
    pipeline.decision_threshold_ = decision_threshold
    logger.info("Modèle final entraîné sur %d exemples", len(X_train_full))

    # Évaluation sur le jeu de test naturel
    proba_test = decision.negative_proba(pipeline, X_test_nat)
    y_pred_test = decision.predict_labels(proba_test, decision_threshold)

    f1_macro = f1_score(y_test_nat, y_pred_test, average="macro")
    recall_negative = recall_score(y_test_nat, y_pred_test, pos_label=decision.LABEL_NEGATIVE)
    logger.info("F1 macro (test) : %.4f", f1_macro)
    logger.info("Rappel négatifs (test) : %.4f", recall_negative)

    # Mesure du sur‑apprentissage : calcul du F1 macro sur le jeu d'entraînement
    proba_train = decision.negative_proba(pipeline, X_train_nat)
    y_pred_train = decision.predict_labels(proba_train, decision_threshold)
    f1_macro_train = f1_score(y_train_nat, y_pred_train, average="macro")
    ecart_train_test = f1_macro_train - f1_macro
    precision_negative = precision_score(y_test_nat, y_pred_test, pos_label=decision.LABEL_NEGATIVE)
    roc_auc = roc_auc_score((y_test_nat == decision.LABEL_NEGATIVE).astype(int), proba_test)
    logger.info("Écart F1 train-test : %.4f", ecart_train_test)
    logger.info("ROC AUC : %.4f", roc_auc)

    n_train = int(len(y_train_full))
    n_test = int(len(y_test_nat))
    negative_share = float((y_test_nat == decision.LABEL_NEGATIVE).mean())

    # Signature du modèle (sans input_example)
    # Pourquoi : avec un input_example, MLflow valide l'exemple par son chemin générique,
    # qui passe un tableau au vectoriseur et échoue (« 'int' object has no attribute 'lower' »).
    example_input = X_train_full.head(5).astype(str).tolist()
    signature = infer_signature(
        example_input,
        pipeline.predict_proba(example_input),
    )
    logger.debug("Signature du modèle inférée")

    # Empreinte du jeu de données (zone propre)
    dataset_fingerprint = _dataset_fingerprint(df, config.CLEAN_FILE)

    with mlflow.start_run() as run:
        mlflow.log_param("decision_threshold", decision_threshold)
        mlflow.log_param("n_boost", n_boost)
        logger.info("Run MLflow démarré : %s", run.info.run_id)

        # Enregistrement de l'empreinte du jeu de données
        mlflow.log_param("data_rows", dataset_fingerprint["data_rows"])
        mlflow.log_param("data_natural_rows", dataset_fingerprint["data_natural_rows"])
        mlflow.log_param("data_boost_rows", dataset_fingerprint["data_boost_rows"])
        mlflow.log_param("data_first_review", dataset_fingerprint["data_first_review"])
        mlflow.log_param("data_last_review", dataset_fingerprint["data_last_review"])
        mlflow.set_tag("data_sha256", dataset_fingerprint["data_sha256"])
        # Cette étiquette relie le modèle à la version du code source.
        mlflow.set_tag("code_commit", os.getenv("REVIEWPULSE_COMMIT", "inconnu"))

        mlflow.log_metric("f1_macro", f1_macro)
        mlflow.log_metric("f1_macro_train", f1_macro_train)
        mlflow.log_metric("ecart_train_test", ecart_train_test)
        mlflow.log_metric("recall_negative", recall_negative)
        mlflow.log_metric("precision_negative", precision_negative)
        mlflow.log_metric("roc_auc", roc_auc)
        mlflow.log_metric("n_train", n_train)
        mlflow.log_metric("n_test", n_test)
        mlflow.log_metric("negative_share", negative_share)
        mlflow.log_metric("f1_cv_mean", f1_cv_mean)  # métrique CV ajoutée

        top_terms = _top_terms(pipeline, n=20)
        mlflow.log_dict(top_terms, "artifacts/top_terms.json")
        logger.debug("Artefact top_terms.json enregistré")

        model_info = mlflow.sklearn.log_model(
            sk_model=pipeline,
            name="model",
            signature=signature,
            registered_model_name=config.MODEL_NAME if register else None,
        )
        run_id = run.info.run_id

        mlflow.set_tag("decision_threshold", decision_threshold)
        logger.info("Modèle enregistré dans MLflow")

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
        logger.info("Alias challenger positionné sur la version %s", model_version)

    promoted = False
    champion_f1 = None
    try:
        champion_mv = client.get_model_version_by_alias(
            config.MODEL_NAME, config.ALIAS_CHAMPION
        )
        champion_run = client.get_run(champion_mv.run_id)
        champion_f1 = champion_run.data.metrics.get("f1_macro")
        logger.debug("Champion actuel : version %s, F1 = %s", champion_mv.version, champion_f1)
    except MlflowException:
        champion_f1 = None
        logger.debug("Aucun champion actuel ; première promotion possible")

    # Promotion éventuelle du challenger en champion
    # Pourquoi : la barrière de promotion garantit que seul un modèle strictement meilleur
    # remplace le champion en service (ADR 0008).
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
            logger.info(
                "Modèle promu champion : F1 %.4f >= %.2f et > champion (%s)",
                f1_macro,
                config.F1_MACRO_MIN,
                champion_f1 if champion_f1 is not None else "aucun",
            )
        else:
            logger.warning("Promotion impossible : model_version est None")
    else:
        logger.info(
            "Pas de promotion : F1 %.4f, seuil %.2f, champion F1 %s",
            f1_macro,
            config.F1_MACRO_MIN,
            champion_f1 if champion_f1 is not None else "aucun",
        )

    result = {
        "run_id": run_id,
        "model_version": model_version,
        "promoted": promoted,
        "decision_threshold": decision_threshold,
        "n_boost": n_boost,
        "f1_macro": f1_macro,
        "f1_macro_train": f1_macro_train,
        "ecart_train_test": ecart_train_test,
        "recall_negative": recall_negative,
        "precision_negative": precision_negative,
        "roc_auc": roc_auc,
        "n_train": n_train,
        "n_test": n_test,
        "negative_share": negative_share,
        "f1_cv_mean": f1_cv_mean,
        # Empreinte du jeu de données
        "data_sha256": dataset_fingerprint["data_sha256"],
        "data_rows": dataset_fingerprint["data_rows"],
        "data_first_review": dataset_fingerprint["data_first_review"],
        "data_last_review": dataset_fingerprint["data_last_review"],
        "data_natural_rows": dataset_fingerprint["data_natural_rows"],
        "data_boost_rows": dataset_fingerprint["data_boost_rows"],
    }
    logger.info("Entraînement terminé ; retour des métriques")
    return result


def main() -> int:
    """Charge les données nettoyées, entraîne le modèle et affiche les métriques.

    Rôle : fournir un point d'entrée exécutable pour l'entraînement en ligne de commande.

    Pourquoi :
        Fournir une interface exécutable conforme aux conventions du projet (journalisation, lecture du fichier `config.CLEAN_FILE`, affichage JSON).

    Returns:
        Code de sortie du processus (0 = succès).

    Raises:
        Aucun ; les exceptions sont propagées et terminent le processus avec un code non nul.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info("Démarrage de l'entraînement depuis %s", config.CLEAN_FILE)
    df = pd.read_parquet(config.CLEAN_FILE)
    logger.info("%d lignes chargées depuis %s", len(df), config.CLEAN_FILE)
    metrics = train_and_log(df)
    print(json.dumps(metrics, indent=2, default=str))
    logger.info("Entraînement terminé avec succès")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
