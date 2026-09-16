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
    Charge le modèle désigné comme « champion » dans le registre MLflow.

    Le modèle est récupéré via son alias, puis on extrait la version
    associée afin de la consigner dans les fichiers de scores.
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
    Ajoute les scores de probabilité négative, les prédictions et le seuil de
    décision au DataFrame.

    Pourquoi utiliser le module ``decision`` ?
    ------------------------------------------------
    La convention de décision (calcul de la probabilité de la classe négative,
    récupération du seuil et conversion en étiquette) est centralisée dans
    ``decision.py``.  L’utiliser garantit que le même comportement est partagé
    entre ``train.py``, ``score.py`` et l’API, évitant ainsi les inversions de
    classes constatées en production.
    """
    if "review_text" not in df.columns:
        raise KeyError("La colonne 'review_text' est requise pour le scoring.")

    # Seuil de décision unique, fourni par la fonction utilitaire
    threshold = decision.model_threshold(model)

    # Probabilité de la classe négative (classe 0) via la fonction centrale
    proba_negative = decision.negative_proba(model, df["review_text"])

    # Prédiction conforme à la convention : 0 = négatif si proba >= seuil
    pred_label = decision.predict_labels(proba_negative, threshold)

    scored = df.copy()
    scored["proba_negative"] = pd.Series(proba_negative, index=scored.index)
    scored["pred_label"] = pd.Series(pred_label, index=scored.index)
    scored["decision_threshold"] = threshold
    scored["model_version"] = model_version
    # Timestamp UTC naïf → on le localise explicitement
    scored["scored_at"] = pd.Timestamp.now(tz="UTC")
    return scored


def summarize(scored: pd.DataFrame) -> pd.DataFrame:
    """
    Agrège les scores par application, langue et jour, uniquement sur les lignes
    issues du flux « natural ».

    La fonction conserve le comportement décrit dans le contrat : le filtrage
    sur ``sample_source == config.SAMPLE_NATURAL`` n’est appliqué que si la
    colonne existe, afin de rester compatible avec les jeux de données plus
    anciens.
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

    # Filtrer sur le flux naturel si la colonne existe
    if "sample_source" in scored.columns:
        natural = scored[scored["sample_source"] == config.SAMPLE_NATURAL]
    else:
        natural = scored

    # Extraire la date (UTC) de created_at
    natural = natural.copy()
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
    Charge le modèle champion, applique le scoring sur le jeu de données propre,
    écrit les fichiers ``SCORED_FILE`` et ``SUMMARY_FILE`` puis retourne le code
    de sortie (0 = succès).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        # Charger le modèle champion
        model, version = load_champion()
        logger.info("Modèle champion chargé, version %s", version)

        # Charger les données nettoyées
        df_clean = pd.read_parquet(config.CLEAN_FILE)

        # Appliquer le scoring
        df_scored = score(df_clean, model, version)

        # Écrire le fichier scored
        _atomic_write(df_scored, config.SCORED_FILE)
        logger.info("Fichier scored écrit : %s", config.SCORED_FILE)

        # Résumer et écrire le fichier de synthèse
        df_summary = summarize(df_scored)
        _atomic_write(df_summary, config.SUMMARY_FILE)
        logger.info("Fichier de résumé écrit : %s", config.SUMMARY_FILE)

        return 0
    except Exception as exc:  # pragma: no cover
        logger.exception("Erreur lors du scoring : %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
