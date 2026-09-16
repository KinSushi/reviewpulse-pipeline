import os
import json
import re
import hashlib
import hmac
import logging
import shutil
import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from reviewpulse import config, quality

_logger = logging.getLogger(__name__)

_RE_BBCODE = re.compile(r"\[/?[a-zA-Z*]+(?:=[^\]]*)?\]")
_RE_SAMPLE = re.compile(r"sample=([^/]+)")


def _extract_partition_info(file_path: Path) -> tuple[int, str, str]:
    """Extrait app_id, language et source d'échantillonnage depuis le chemin du fichier."""
    app_match = re.search(r"app_id=(\d+)", str(file_path))
    lang_match = re.search(r"language=([a-zA-Z]+)", str(file_path))
    sample_match = _RE_SAMPLE.search(str(file_path))

    if not app_match or not lang_match:
        raise RuntimeError(f"Impossible d'extraire les partitions du chemin : {file_path}")

    app_id = int(app_match.group(1))
    language = lang_match.group(1)

    # Valeur par défaut « natural » si la partition sample= est absente
    sample_source = (
        sample_match.group(1)
        if sample_match
        else config.SAMPLE_NATURAL
    )
    return app_id, language, sample_source


def load_raw(raw_dir: Optional[Path] = None) -> pd.DataFrame:
    """Lit tous les *.jsonl du répertoire brut et ajoute les colonnes de partition."""
    raw_dir = raw_dir or config.RAW_DIR
    raw_dir = Path(raw_dir)
    records = []

    for file_path in raw_dir.rglob("*.jsonl"):
        try:
            app_id, language, sample_source = _extract_partition_info(file_path)
        except RuntimeError as exc:
            _logger.error(str(exc))
            continue

        with file_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    _logger.warning(f"Ligne JSON invalide dans {file_path}")
                    continue
                obj["app_id"] = app_id
                obj["language_partition"] = language
                obj["sample_source"] = sample_source
                records.append(obj)

    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def _clean_text(text: str) -> str:
    """Supprime les balises BBCode, réduit les espaces et strip."""
    text = _RE_BBCODE.sub("", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean(raw: pd.DataFrame, salt: bytes) -> pd.DataFrame:
    """Transforme le DataFrame brut en DataFrame propre conforme à CLEAN_COLUMNS."""
    if raw.empty:
        empty_df = pd.DataFrame(columns=config.CLEAN_COLUMNS.keys())
        for col, typ in config.CLEAN_COLUMNS.items():
            empty_df[col] = empty_df[col].astype(typ)
        return empty_df

    df = raw.copy()

    # Garantir la présence de la colonne sample_source (valeur par défaut « natural »)
    if "sample_source" not in df.columns:
        df["sample_source"] = config.SAMPLE_NATURAL

    # review_id
    df["review_id"] = df["recommendationid"]

    # gestion du timestamp_updated
    if "timestamp_updated" not in df.columns:
        df["timestamp_updated"] = df["timestamp_created"]
    df["timestamp_updated"] = (
        pd.to_numeric(df["timestamp_updated"], errors="coerce")
        .fillna(0)
        .astype("int64")
    )

    # priorité de dédoublonnage : natural avant negative_boost,
    # puis timestamp_updated décroissant
    priority_map = {
        config.SAMPLE_NATURAL: 0,
        config.SAMPLE_NEGATIVE_BOOST: 1,
    }
    df["_priority"] = df["sample_source"].map(priority_map).fillna(1).astype("int64")
    df = df.sort_values(["_priority", "timestamp_updated"], ascending=[True, False])
    df = df.drop_duplicates(subset="review_id", keep="first")
    df = df.drop(columns=["_priority"])

    # texte nettoyé
    df["review_text"] = df["review"].apply(_clean_text)

    # suppression des lignes où le texte devient vide
    df = df[df["review_text"] != ""]

    # label
    df["label"] = df["voted_up"].astype(bool).astype("int64")

    # dates
    df["created_at"] = pd.to_datetime(df["timestamp_created"], unit="s", utc=True)
    df["updated_at"] = pd.to_datetime(df["timestamp_updated"], unit="s", utc=True)

    # scores et votes
    df["weighted_vote_score"] = df["weighted_vote_score"].astype(float)
    df["votes_up"] = df["votes_up"].astype("int64")

    # playtime
    def _extract_playtime(author):
        if isinstance(author, dict):
            return int(author.get("playtime_at_review", 0))
        return 0

    df["playtime_at_review_min"] = df["author"].apply(_extract_playtime).astype("int64")

    # author_pseudo (hmac sha256)
    def _hash_steamid(author):
        steamid = ""
        if isinstance(author, dict):
            steamid = str(author.get("steamid", ""))
        return hmac.new(salt, steamid.encode(), hashlib.sha256).hexdigest()

    df["author_pseudo"] = df["author"].apply(_hash_steamid)

    # langue : utilise la partition si disponible
    if "language_partition" in df.columns:
        df["language"] = df["language_partition"]
    elif "language" in df.columns:
        df["language"] = df["language"]
    else:
        df["language"] = None

    # longueur du texte
    df["text_len"] = df["review_text"].str.len().astype("int64")

    # sélection et ordre des colonnes selon la spécification
    clean_cols = list(config.CLEAN_COLUMNS.keys())
    clean_df = df[clean_cols].copy()

    # cast aux types déclarés
    for col, typ in config.CLEAN_COLUMNS.items():
        clean_df[col] = clean_df[col].astype(typ)

    # vérification des colonnes interdites
    for forbidden in config.FORBIDDEN_CLEAN_COLUMNS:
        if forbidden in clean_df.columns:
            raise RuntimeError(f"Colonne interdite présente après nettoyage : {forbidden}")

    return clean_df


def write_clean(df: pd.DataFrame, path: Optional[Path] = None) -> Path:
    """Écriture atomique du DataFrame propre au format Parquet."""
    path = path or config.CLEAN_FILE
    path = Path(path)

    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = path.with_suffix(".tmp.parquet")
    df.to_parquet(tmp_path, engine="pyarrow")
    os.replace(tmp_path, path)
    return path


def purge_raw(
    raw_dir: Optional[Path] = None,
    retention_days: Optional[int] = None,
    today: Optional[datetime.date] = None,
) -> int:
    """Supprime les partitions de données brutes plus anciennes que la période de rétention."""
    raw_dir = raw_dir or config.RAW_DIR
    raw_dir = Path(raw_dir)

    if not raw_dir.is_dir():
        return 0

    retention_days = retention_days if retention_days is not None else config.RAW_RETENTION_DAYS
    today = today or datetime.date.today()
    cutoff = today - datetime.timedelta(days=retention_days)

    removed_files = 0

    for dt_dir in raw_dir.rglob("dt=*"):
        if not dt_dir.is_dir():
            continue
        match = re.search(r"dt=(\d{4}-\d{2}-\d{2})", str(dt_dir))
        if not match:
            continue
        dir_date = datetime.datetime.strptime(match.group(1), "%Y-%m-%d").date()
        if dir_date < cutoff:
            files = list(dt_dir.rglob("*"))
            removed_files += len(files)
            shutil.rmtree(dt_dir)

    return removed_files


def main() -> int:
    """Pipeline complet : chargement → nettoyage → contrôle qualité → écriture → purge."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        raw_df = load_raw()
        salt = config.salt()
        clean_df = clean(raw_df, salt)

        quality.assert_quality(clean_df)

        write_clean(clean_df)
        purge_raw()
        return 0
    except quality.DataQualityError as exc:
        _logger.error(str(exc))
        return 1
    except Exception:  # pragma: no cover
        _logger.exception("Erreur inattendue dans le pipeline de transformation")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
