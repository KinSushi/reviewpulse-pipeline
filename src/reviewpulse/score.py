# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""reviewpulse.score
===================

Rôle
----
Charge le modèle champion, calcule les scores sur la zone propre, génère le résumé quotidien et persiste les prédictions dans la couche *silver* du lakehouse.

Place dans la chaîne
--------------------
- Exécuté après l’étape *train* (ou directement après *transform* dans le DAG quotidien).  
- Les fichiers produits ``config.SCORED_FILE`` et ``config.SUMMARY_FILE`` sont consommés par le tableau de bord et le point d’accès ``/insights`` de l’API.  
- La table ``config.SILVER_PREDICTIONS_TABLE`` est utilisée par les analyses downstream via Iceberg.

Fonctionnement
--------------
1. ``load_champion`` charge le modèle enregistré sous l’alias ``config.ALIAS_CHAMPION`` via MLflow et récupère sa version.  
2. ``score`` vérifie la présence de la colonne ``review_text``, obtient le seuil depuis le modèle via ``decision.model_threshold``, calcule la probabilité de la classe négative avec ``decision.negative_proba``, génère les étiquettes avec ``decision.predict_labels`` et ajoute les métadonnées ``decision_threshold``, ``model_version`` et ``scored_at`` (timestamp UTC).  
3. ``summarize`` filtre les lignes dont ``sample_source`` vaut ``config.SAMPLE_NATURAL`` (si la colonne existe), crée une colonne ``date`` à partir de ``created_at`` et agrège par ``app_id``, ``language`` et ``date`` pour obtenir le nombre d’avis et les parts négatives prédites et réelles.  
4. ``_atomic_write`` écrit un DataFrame au format Parquet de façon atomique.  
5. ``main`` orchestre les étapes ci‑dessus, écrit les tables ``SCORED_FILE`` et ``SUMMARY_FILE`` puis persiste les prédictions dans Iceberg via ``lakehouse.write_table``.  

Choix de conception
--------------------
- Le seuil est lu sur le modèle (il voyage avec le modèle) – conformément à l’ADR 0007.  
- Le résumé ne porte que sur les avis du flux naturel – également décrit dans l’ADR 0007.  
- L’écriture Iceberg utilise les colonnes listées dans le contrat et convertit les horodatages en ``timestamp[us, tz=UTC]`` via ``lakehouse`` – conformément aux ADR 0013 et 0014.  
- Le champ ``scored_at`` utilise ``pd.Timestamp.now(tz="UTC")`` : en pandas 2.2, ``Timestamp.utcnow()`` est déjà daté UTC et ``tz_localize`` levait une erreur (constaté le 16/09/2026).

Tests associés
--------------
- ``test_train_score.py``  
- ``test_boost.py``  
- ``test_decision.py``  
- ``test_spark_silver.py`` (vérifie la persistance Iceberg)  

Quoi
----
Ce module charge le modèle champion, applique le scoring aux avis de la zone propre, génère un résumé agrégé quotidien et persiste les prédictions dans la couche *silver* du lakehouse.

Pourquoi
--------
Le besoin métier est de fournir chaque jour des scores de sentiment fiables aux tableaux de bord et à l’API ``/insights``. Le module évite le défaut d’incohérence entre le seuil utilisé en production et celui entraîné (ADR 0007) et garantit que le résumé ne mélange pas les avis naturels et les avis complémentaires, préservant ainsi la validité des métriques.

Où
---
- Appelé par le DAG quotidien ``dags/reviewpulse_daily.py`` (étape *score*).  
- Lit le fichier ``config.CLEAN_FILE`` (zone propre).  
- Écrit ``config.SCORED_FILE`` et ``config.SUMMARY_FILE`` dans le répertoire de sortie.  
- Persiste les prédictions dans la table Iceberg ``config.SILVER_PREDICTIONS_TABLE`` via ``lakehouse.write_table``.

Comment
-------
1. Chargement du modèle champion via MLflow.  
2. Vérification de la présence de la colonne ``review_text``.  
3. Extraction du seuil depuis le modèle, calcul des probabilités négatives et des étiquettes.  
4. Enrichissement du DataFrame avec les métadonnées requises.  
5. Filtrage du flux naturel, création d’une colonne date en UTC et agrégation par application, langue et jour.  
6. Écriture atomique des résultats et persistance Iceberg.

Limites connues
---------------
- Le module ne gère pas les cas où le modèle ne possède pas la méthode attendue ``predict`` ; une exception ``MlflowException`` sera levée.  
- Aucun contrôle de cohérence entre le schéma du DataFrame d’entrée et le contrat de la table Iceberg n’est effectué au niveau du code (c’est géré par ``lakehouse``).  
- Le seuil est uniquement lu depuis le modèle ; il n’est pas possible de le surcharger via configuration.

"""

import logging
import os
import tempfile
from pathlib import Path

import pandas as pd
import pyarrow as pa
import mlflow
from mlflow.tracking import MlflowClient

from reviewpulse import config, decision, lakehouse

logger = logging.getLogger(__name__)


def load_champion(tracking_uri: str | None = None) -> tuple[object, str]:
    """
    Charge le modèle désigné comme champion depuis le registre MLflow.

    Pourquoi : charger le modèle champion garantit que le scoring utilise la version la plus récente promue (ADR 0007).

    Args:
        tracking_uri: URI du serveur de suivi MLflow. Si ``None``, la valeur
            ``config.MLFLOW_TRACKING_URI`` est utilisée.

    Returns:
        Tuple contenant le modèle chargé et la version du modèle sous forme de
        chaîne.

    Raises:
        mlflow.exceptions.MlflowException: si le modèle ou l'alias n'existe pas.
    """
    if tracking_uri is None:
        tracking_uri = config.MLFLOW_TRACKING_URI
    mlflow.set_tracking_uri(tracking_uri)
    model_uri = f"models:/{config.MODEL_NAME}@{config.ALIAS_CHAMPION}"
    model = mlflow.sklearn.load_model(model_uri)
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

    Pourquoi : le calcul des scores et l’ajout des métadonnées permettent aux
    tableaux de bord et à l’API d’afficher les parts négatives prédites et de
    tracer l’historique des modèles.

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
    """
    if "review_text" not in df.columns:
        # Pourquoi : la colonne ``review_text`` est indispensable pour le calcul du score.
        logger.warning("Colonne 'review_text' manquante dans le DataFrame d'entrée")
        raise KeyError("La colonne 'review_text' est requise pour le scoring.")

    # Pourquoi : le seuil est lu depuis le modèle pour garantir cohérence avec le modèle (ADR 0007)
    threshold = decision.model_threshold(model)
    # Pourquoi : on calcule la probabilité de la classe négative pour chaque texte
    proba_negative = decision.negative_proba(model, df["review_text"])
    # Pourquoi : les étiquettes sont dérivées en comparant la probabilité au seuil
    pred_label = decision.predict_labels(proba_negative, threshold)

    scored = df.copy()
    scored["proba_negative"] = pd.Series(proba_negative, index=scored.index)
    scored["pred_label"] = pd.Series(pred_label, index=scored.index)
    scored["decision_threshold"] = threshold
    scored["model_version"] = model_version
    scored["scored_at"] = pd.Timestamp.now(tz="UTC")
    return scored


def summarize(scored: pd.DataFrame) -> pd.DataFrame:
    """
    Agrège les scores par application, langue et jour, uniquement sur les lignes
    issues du flux « natural ».

    Pourquoi : le résumé agrégé alimente les tableaux de bord et l’API
    ``/insights`` avec des métriques quotidiennes fiables, en excluant le
    flux complémentaire qui biaiserait les parts négatives.

    Args:
        scored: DataFrame produit par :func:`score`.

    Returns:
        DataFrame agrégé contenant les colonnes ``app_id``, ``language``,
        ``date``, ``n_reviews``, ``share_negative_pred``,
        ``share_negative_true`` et ``model_version``.

    Raises:
        KeyError: si l'une des colonnes requises est absente.
    """
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

    if "sample_source" in scored.columns:
        # Pourquoi : on ne garde que le flux naturel pour éviter gonflement des parts négatives (ADR 0007)
        natural = scored[scored["sample_source"] == config.SAMPLE_NATURAL]
    else:
        natural = scored

    natural = natural.copy()
    # Pourquoi : conversion en UTC puis extraction de la date pour agrégation journalière
    natural["date"] = natural["created_at"].dt.tz_convert("UTC").dt.date

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

    Pourquoi : garantir l'intégrité du fichier même en cas d'interruption du processus.

    Args:
        df: DataFrame à écrire.
        path: Chemin complet du fichier cible.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=path.parent) as tmp:
        tmp_path = Path(tmp.name)
    try:
        df.to_parquet(tmp_path, engine="pyarrow")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def main() -> int:
    """
    Orchestration du scoring quotidien.

    Pourquoi : centraliser le flux complet de chargement du modèle, scoring,
    génération du résumé et persistance afin de garantir une exécution
    atomique et traçable.

    - Charge le modèle champion.
    - Lit le jeu de données propre.
    - Applique le scoring.
    - Écrit les fichiers ``SCORED_FILE`` et ``SUMMARY_FILE`` de façon atomique.
    - Persiste les prédictions dans Iceberg via ``lakehouse.write_table``.
    - Retourne ``0`` en cas de succès, ``1`` sinon.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info("Début du scoring quotidien")
    try:
        model, version = load_champion()
        logger.info("Modèle champion chargé, version %s", version)

        df_clean = pd.read_parquet(config.CLEAN_FILE)
        logger.info("Fichier propre lu : %s, %d lignes", config.CLEAN_FILE, len(df_clean))

        df_scored = score(df_clean, model, version)
        logger.info("Scoring appliqué, %d lignes", len(df_scored))

        _atomic_write(df_scored, config.SCORED_FILE)
        logger.info("Fichier scored écrit : %s", config.SCORED_FILE)

        df_summary = summarize(df_scored)
        logger.info("Résumé généré, %d lignes", len(df_summary))

        _atomic_write(df_summary, config.SUMMARY_FILE)
        logger.info("Fichier de résumé écrit : %s", config.SUMMARY_FILE)

        # Persistance des prédictions dans la table Iceberg « silver.predictions »
        pred_columns = [
            "review_id",
            "app_id",
            "language",
            "sample_source",
            "created_at",
            "label",
            "proba_negative",
            "pred_label",
            "decision_threshold",
            "model_version",
            "scored_at",
        ]
        df_predictions = df_scored[pred_columns].copy()
        # Pourquoi : conversion en table Arrow ; lakehouse gère le cast des timestamps
        arrow_table = pa.Table.from_pandas(df_predictions, preserve_index=False)
        lakehouse.write_table(config.SILVER_PREDICTIONS_TABLE, arrow_table)
        logger.info(
            "Table Iceberg %s écrite avec %d lignes",
            config.SILVER_PREDICTIONS_TABLE,
            len(df_predictions),
        )

        logger.info("Scoring quotidien terminé avec succès")
        return 0
    except Exception as exc:  # pragma: no cover
        logger.exception("Erreur lors du scoring : %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
