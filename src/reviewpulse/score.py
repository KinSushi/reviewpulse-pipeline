"""reviewpulse.score
===================

Rôle
----
Charge le modèle champion, calcule les scores sur la zone propre et génère le résumé quotidien.

Place dans la chaîne
--------------------
- Exécuté après l’étape *train* (ou directement après *transform* dans le DAG quotidien).  
- Les fichiers produits ``config.SCORED_FILE`` et ``config.SUMMARY_FILE`` sont consommés par le tableau de bord et le point d’accès ``/insights`` de l’API.

Fonctionnement
--------------
1. ``load_champion`` charge le modèle enregistré sous l’alias ``config.ALIAS_CHAMPION`` via MLflow et récupère sa version.
2. ``score`` vérifie la présence de la colonne ``review_text``, obtient le seuil depuis le modèle via ``decision.model_threshold``, calcule la probabilité de la classe négative avec ``decision.negative_proba``, génère les étiquettes avec ``decision.predict_labels`` et ajoute les métadonnées ``decision_threshold``, ``model_version`` et ``scored_at`` (timestamp UTC).
3. ``summarize`` filtre les lignes dont ``sample_source`` vaut ``config.SAMPLE_NATURAL`` (si la colonne existe), crée une colonne ``date`` à partir de ``created_at`` et agrège par ``app_id``, ``language`` et ``date`` pour obtenir le nombre d’avis et les parts négatives prédites et réelles.
4. ``_atomic_write`` écrit un DataFrame au format Parquet de façon atomique.
5. ``main`` orchestre les étapes ci‑dessus et renvoie ``0`` en cas de succès, ``1`` sinon.

Choix de conception
--------------------
- Le seuil est lu sur le modèle (il voyage avec le modèle) – conformément à l’ADR 0007.  
- Le résumé ne porte que sur les avis du flux naturel, afin d’éviter une inflation de la part négative due au flux complémentaire – également décrit dans l’ADR 0007.  
- Le champ ``scored_at`` utilise ``pd.Timestamp.now(tz="UTC")`` : en pandas 2.2, Timestamp.utcnow() est déjà daté UTC et tz_localize levait une erreur (constaté le 16/09/2026).

Preuves
-------
Sur la stack déployée, le rapport entre la part négative prédite et la part négative réelle est compris entre **0,79** et **1,21** selon le jeu et la langue (mesure du 16/09/2026) – ADR 0007.

Tests associés
--------------
- ``test_train_score.py``  
- ``test_boost.py``  
- ``test_decision.py``  
"""

import os
import logging
import tempfile
from pathlib import Path

import pandas as pd
import mlflow
from mlflow.tracking import MlflowClient

from reviewpulse import config, decision

logger = logging.getLogger(__name__)


def load_champion(tracking_uri: str | None = None) -> tuple[object, str]:
    """
    Charge le modèle désigné comme champion depuis le registre MLflow.

    Args:
        tracking_uri: URI du serveur de suivi MLflow. Si ``None``, la valeur
            ``config.MLFLOW_TRACKING_URI`` est utilisée.

    Returns:
        Tuple contenant le modèle chargé et la version du modèle sous forme de
        chaîne.

    Raises:
        mlflow.exceptions.MlflowException: si le modèle ou l'alias n'existe pas.

    Pourquoi:
        Centraliser le chargement du modèle champion évite la duplication du
        code de configuration MLflow et garantit que la même version est utilisée
        partout dans la chaîne de scoring.
    """
    # Utiliser la configuration par défaut si aucun URI n'est fourni
    if tracking_uri is None:
        tracking_uri = config.MLFLOW_TRACKING_URI
    # Configurer l'URI de suivi pour les appels MLflow suivants
    mlflow.set_tracking_uri(tracking_uri)
    # Construction de l'URI du modèle via l'alias champion
    model_uri = f"models:/{config.MODEL_NAME}@{config.ALIAS_CHAMPION}"
    # Chargement du modèle enregistré
    model = mlflow.sklearn.load_model(model_uri)
    # Client MLflow pour récupérer la version associée à l'alias
    client = MlflowClient(tracking_uri=tracking_uri)
    version = client.get_model_version_by_alias(
        name=config.MODEL_NAME, alias=config.ALIAS_CHAMPION
    ).version
    return model, str(version)


def score(
    df: pd.DataFrame,
    model: object,
    model_version: str,
) -> pd.DataFrame:
    """
    Calcule les scores de probabilité négative, les prédictions et les
    métadonnées associées pour chaque avis du DataFrame fourni.

    Args:
        df: DataFrame contenant au minimum la colonne ``review_text``.
        model: Modèle MLflow chargé (compatible scikit‑learn).
        model_version: Version du modèle sous forme de chaîne, à inscrire dans le
            résultat.

    Returns:
        DataFrame enrichi avec les colonnes ``proba_negative``, ``pred_label``,
        ``decision_threshold``, ``model_version`` et ``scored_at``.

    Raises:
        KeyError: si la colonne ``review_text`` est absente.

    Pourquoi:
        Utiliser les fonctions du module ``decision`` assure que le calcul du
        seuil et la conversion en étiquette sont identiques à ceux utilisés
        lors de l'entraînement et dans l'API.
    """
    if "review_text" not in df.columns:
        raise KeyError("La colonne 'review_text' est requise pour le scoring.")

    # Récupération du seuil de décision centralisé
    threshold = decision.model_threshold(model)

    # Calcul de la probabilité de la classe négative
    proba_negative = decision.negative_proba(model, df["review_text"])

    # Conversion de la probabilité en étiquette selon le seuil
    pred_label = decision.predict_labels(proba_negative, threshold)

    # Copie du DataFrame d'origine pour ne pas le modifier en place
    scored = df.copy()
    scored["proba_negative"] = pd.Series(proba_negative, index=scored.index)
    scored["pred_label"] = pd.Series(pred_label, index=scored.index)
    scored["decision_threshold"] = threshold
    scored["model_version"] = model_version
    # Timestamp UTC naïf, on le localise explicitement
    scored["scored_at"] = pd.Timestamp.now(tz="UTC")
    return scored


def summarize(scored: pd.DataFrame) -> pd.DataFrame:
    """
    Agrège les scores par application, langue et jour, uniquement sur les lignes
    issues du flux « natural ».

    Args:
        scored: DataFrame produit par :func:`score`.

    Returns:
        DataFrame agrégé contenant les colonnes ``app_id``, ``language``,
        ``date``, ``n_reviews``, ``share_negative_pred``,
        ``share_negative_true`` et ``model_version``.

    Raises:
        KeyError: si l'une des colonnes requises est absente.

    Pourquoi:
        Le filtrage sur le flux naturel garantit que les métriques de résumé
        restent comparables aux évaluations historiques, même si le jeu de
        données contient d'autres sources.
    """
    # Ensemble des colonnes indispensables au résumé
    required = {
        "app_id",
        "language",
        "created_at",
        "pred_label",
        "label",
        "model_version",
    }
    missing = required - set(scored.columns)
    if missing:
        raise KeyError(f"Colonnes manquantes pour le résumé : {missing}")

    # Filtrer les avis du flux naturel si la colonne existe
    if "sample_source" in scored.columns:
        natural = scored[scored["sample_source"] == config.SAMPLE_NATURAL]
    else:
        natural = scored

    # Extraction de la date (UTC) à partir de ``created_at``
    natural = natural.copy()
    natural["date"] = natural["created_at"].dt.tz_convert("UTC").dt.date

    # Agrégation par application, langue et jour
    agg = (
        natural.groupby(["app_id", "language", "date"], as_index=False)
        .agg(
            n_reviews=("review_id", "size"),
            share_negative_pred=("pred_label", lambda s: (s == 0).mean()),
            share_negative_true=("label", lambda s: (s == 0).mean()),
            model_version=("model_version", "first"),
        )
    )
    agg["share_negative_pred"] = agg["share_negative_pred"].astype("float64")
    agg["share_negative_true"] = agg["share_negative_true"].astype("float64")
    agg["n_reviews"] = agg["n_reviews"].astype("int64")
    return agg


def _atomic_write(df: pd.DataFrame, path: Path) -> None:
    """
    Écriture atomique d'un DataFrame au format Parquet.

    Args:
        df: DataFrame à écrire.
        path: Chemin complet du fichier cible.

    Pourquoi:
        Garantir qu'aucun fichier partiellement écrit n'est laissé en cas
        d'interruption, ce qui est essentiel pour les étapes suivantes de la
        chaîne (API, tableau de bord).
    """
    # S'assurer que le répertoire de destination existe
    path.parent.mkdir(parents=True, exist_ok=True)
    # Création d'un fichier temporaire dans le même répertoire
    with tempfile.NamedTemporaryFile(delete=False, dir=path.parent) as tmp:
        tmp_path = Path(tmp.name)
    try:
        # Sérialisation du DataFrame au format Parquet
        df.to_parquet(tmp_path, engine="pyarrow")
        # Remplacement atomique du fichier cible
        os.replace(tmp_path, path)
    finally:
        # Nettoyage du fichier temporaire en cas d'échec
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def main() -> int:
    """
    Orchestration du scoring quotidien.

    - Charge le modèle champion.
    - Lit le jeu de données propre.
    - Applique le scoring.
    - Écrit les fichiers ``SCORED_FILE`` et ``SUMMARY_FILE`` de façon atomique.
    - Retourne ``0`` en cas de succès, ``1`` sinon.

    Returns:
        Code de sortie du processus (0 = succès, 1 = échec).

    Pourquoi:
        Fournir un point d'entrée unique et testable pour l'étape de scoring,
        conforme aux conventions du projet (logging, gestion d'exceptions,
        code de sortie).
    """
    # Configuration du logger pour la fonction main
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        # Chargement du modèle champion
        model, version = load_champion()
        logger.info("Modèle champion chargé, version %s", version)

        # Lecture du jeu de données propre
        df_clean = pd.read_parquet(config.CLEAN_FILE)

        # Application du scoring
        df_scored = score(df_clean, model, version)

        # Écriture atomique du fichier scored
        _atomic_write(df_scored, config.SCORED_FILE)
        logger.info("Fichier scored écrit : %s", config.SCORED_FILE)

        # Calcul du résumé agrégé
        df_summary = summarize(df_scored)

        # Écriture atomique du fichier de synthèse
        _atomic_write(df_summary, config.SUMMARY_FILE)
        logger.info("Fichier de résumé écrit : %s", config.SUMMARY_FILE)

        return 0
    except Exception as exc:  # pragma: no cover
        logger.exception("Erreur lors du scoring : %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
