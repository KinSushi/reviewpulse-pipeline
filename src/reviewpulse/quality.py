import logging
import re
from pathlib import Path

import pandas as pd

from reviewpulse import config

logger = logging.getLogger(__name__)


class DataQualityError(Exception):
    """Exception levée lorsqu'une ou plusieurs vérifications de qualité échouent."""


def _column_type_mismatch(df: pd.DataFrame) -> list[str]:
    errors = []
    expected_cols = list(config.CLEAN_COLUMNS.keys())
    actual_cols = list(df.columns)

    if actual_cols != expected_cols:
        errors.append(
            f"Colonnes inattendues ou ordre incorrect. Attendu {expected_cols}, trouvé {actual_cols}"
        )
        # Si l'ordre est mauvais, on ne poursuit pas les vérifications de type
        return errors

    for col, expected_type in config.CLEAN_COLUMNS.items():
        actual_type = str(df[col].dtype)
        if actual_type != expected_type:
            errors.append(
                f"Type de colonne '{col}' incorrect : attendu '{expected_type}', trouvé '{actual_type}'"
            )
    return errors


def check_clean(df: pd.DataFrame) -> list[str]:
    """Vérifie la qualité du DataFrame nettoyé.

    Retourne la liste des messages d'erreur ; liste vide si tout est conforme.
    """
    errors: list[str] = []

    # 1. Colonnes et types
    errors.extend(_column_type_mismatch(df))

    # 2. Au moins une ligne
    if df.shape[0] == 0:
        errors.append("Le DataFrame ne contient aucune ligne")

    # 3. review_id non nul et unique
    if "review_id" in df.columns:
        if df["review_id"].isnull().any():
            errors.append("review_id contient des valeurs nulles")
        if not df["review_id"].is_unique:
            errors.append("review_id n'est pas unique")

    # 4. label dans {0, 1}
    if "label" in df.columns:
        invalid_labels = df[~df["label"].isin([0, 1])]
        if not invalid_labels.empty:
            errors.append("label contient des valeurs hors de {0, 1}")

    # 5. language valide
    if "language" in df.columns:
        invalid_lang = df[~df["language"].isin(config.LANGUAGES)]
        if not invalid_lang.empty:
            errors.append(
                f"language contient des valeurs non autorisées : {invalid_lang['language'].unique().tolist()}"
            )

    # 6. sample_source valide (v2)
    if "sample_source" in df.columns:
        invalid_source = df[~df["sample_source"].isin(config.SAMPLE_SOURCES)]
        if not invalid_source.empty:
            errors.append(
                f"sample_source contient des valeurs non autorisées : {invalid_source['sample_source'].unique().tolist()}"
            )
    else:
        # L'absence de la colonne aurait déjà été détectée dans _column_type_mismatch,
        # mais on garde un message explicite au cas où.
        errors.append("Colonne 'sample_source' manquante")

    # 7. text_len >= 1
    if "text_len" in df.columns:
        if (df["text_len"] < 1).any():
            errors.append("text_len contient des valeurs < 1")

    # 8. Colonnes interdites
    forbidden = set(config.FORBIDDEN_CLEAN_COLUMNS)
    present_forbidden = forbidden.intersection(df.columns)
    if present_forbidden:
        errors.append(f"Colonnes interdites présentes : {sorted(present_forbidden)}")

    # 9. author_pseudo format hex 64 caractères
    if "author_pseudo" in df.columns:
        pattern = re.compile(r"^[0-9a-f]{64}$")
        invalid_pseudo = df[~df["author_pseudo"].astype(str).str.match(pattern)]
        if not invalid_pseudo.empty:
            errors.append("author_pseudo ne correspond pas au format hexadécimal 64 caractères")

    # 10. Part de négatifs (calculée uniquement sur les avis naturels) (v2)
    if "label" in df.columns and "sample_source" in df.columns:
        natural_df = df[df["sample_source"] == config.SAMPLE_NATURAL]
        if natural_df.empty:
            errors.append("Aucun avis naturel disponible pour le calcul de la part de négatifs")
        else:
            negative_share = (natural_df["label"] == 0).mean()
            if not (0.005 <= negative_share <= 0.95):
                errors.append(
                    f"Part de négatifs hors limites (0,5 %‑95 %) : {negative_share:.2%}"
                )

    return errors


def assert_quality(df: pd.DataFrame) -> None:
    """Lève DataQualityError si le DataFrame ne satisfait pas les contrôles."""
    failures = check_clean(df)
    if failures:
        message = "Échecs de qualité des données :\n" + "\n".join(failures)
        raise DataQualityError(message)


def main() -> int:
    """Charge le fichier nettoyé, vérifie la qualité et renvoie le code de sortie."""
    clean_path: Path = config.CLEAN_FILE
    try:
        df = pd.read_parquet(clean_path)
    except Exception as exc:
        logger.error("Impossible de lire le fichier nettoyé %s : %s", clean_path, exc)
        return 1

    try:
        assert_quality(df)
    except DataQualityError as e:
        logger.error("Qualité des données non satisfaisante : %s", e)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
