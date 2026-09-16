"""reviewpulse.transform
=======================

**Rôle**
    Produire la zone propre, pseudonymisée et typée, uniquement si les contrôles qualité passent.

**Place dans la chaîne**
    Après ``reviewpulse.ingest`` et avant ``reviewpulse.train`` et ``reviewpulse.score``.

**Fonctionnement**
    1. Lecture récursive de tous les fichiers ``*.jsonl`` dans ``config.RAW_DIR`` ; le flux est déduit de la partition ``sample=`` du chemin, la valeur par défaut étant ``config.SAMPLE_NATURAL``.
    2. Dédoublonnage avec priorité au flux naturel puis, à égalité, à la mise à jour la plus récente.
    3. Suppression des balises BBCode et des lignes dont le texte devient vide.
    4. Conversion des champs aux types déclarés dans ``config.CLEAN_COLUMNS`` ; calcul des colonnes dérivées (hash, durée de jeu, longueur du texte, etc.).
    5. Pseudonymisation du ``steamid`` via HMAC‑SHA256 avec le sel fourni par ``config.salt()`` ; suppression des colonnes interdites listées dans ``config.FORBIDDEN_CLEAN_COLUMNS``.
    6. Contrôle qualité bloquant via ``reviewpulse.quality.assert_quality``.
    7. Écriture atomique du DataFrame propre au format Parquet.
    8. Purge des partitions brutes plus anciennes que ``config.RAW_RETENTION_DAYS`` (30 jours).

**Choix de conception**
    - Utilisation de pandas (ADR 0003).
    - Pseudonymisation HMAC salée, sel obligatoire (ADR 0004).
    - Contrôles qualité exécutés avant l’écriture (ADR 0005).

**Preuves**
    - 16/09/2026 : exécution sans sel entraîne l’arrêt du pipeline et aucune modification de la zone propre.

**Tests associés**
    - ``test_transform_quality.py``
    - ``test_fresh_dirs.py``
    - ``test_boost.py``
"""

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
    """Extrait les informations de partition depuis le chemin du fichier.

    Args:
        file_path: Chemin complet du fichier *.jsonl*.

    Returns:
        Tuple contenant ``app_id`` (int), ``language`` (str) et ``sample_source`` (str).

    Raises:
        RuntimeError: Si ``app_id`` ou ``language`` ne peuvent être extraits.

    Pourquoi :
        Centralise la logique d’extraction pour garantir la même interprétation dans :func:`load_raw` et faciliter les tests.
    """
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
    """Lit les fichiers *.jsonl* bruts et ajoute les colonnes de partition.

    Args:
        raw_dir: Répertoire contenant les fichiers bruts. Si ``None``,
            utilise ``config.RAW_DIR``.

    Returns:
        DataFrame contenant toutes les lignes valides avec les colonnes
        ``app_id``, ``language_partition`` et ``sample_source`` ajoutées.
        Retourne un DataFrame vide si aucun enregistrement n’est trouvé.
    """
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
    """Supprime les balises BBCode, réduit les espaces multiples et strip.

    Args:
        text: Chaîne brute contenant éventuellement du BBCode.

    Returns:
        Texte nettoyé.
    """
    text = _RE_BBCODE.sub("", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean(raw: pd.DataFrame, salt: bytes) -> pd.DataFrame:
    """Transforme le DataFrame brut en DataFrame propre conforme à ``CLEAN_COLUMNS``.

    Args:
        raw: DataFrame issu de :func:`load_raw`.
        salt: Sel utilisé pour le hachage HMAC du ``steamid``.

    Returns:
        DataFrame propre, typé et ordonné selon ``config.CLEAN_COLUMNS``.

    Raises:
        RuntimeError: Si une colonne interdite apparaît après le nettoyage.

    Pourquoi :
        Centralise toutes les étapes de normalisation, dédoublonnage et dérivation de nouvelles colonnes afin de garantir la conformité aux exigences de qualité.
    """
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
    """Écriture atomique du DataFrame propre au format Parquet.

    Args:
        df: DataFrame conforme à ``CLEAN_COLUMNS``.
        path: Chemin de destination. Si ``None``, utilise ``config.CLEAN_FILE``.

    Returns:
        Chemin final du fichier écrit.
    """
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
    """Supprime les partitions de données brutes plus anciennes que la période de rétention.

    Args:
        raw_dir: Répertoire racine contenant les partitions ``dt=``.
            Par défaut ``config.RAW_DIR``.
        retention_days: Nombre de jours à conserver. Par défaut
            ``config.RAW_RETENTION_DAYS``.
        today: Date de référence pour le calcul du seuil. Permet l’injection
            en tests ; sinon ``datetime.date.today()``.

    Returns:
        Nombre total de fichiers supprimés.
    """
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
    """Pipeline complet : chargement → nettoyage → contrôle qualité → écriture → purge.

    Returns:
        Code de sortie du pipeline (0 = succès, 1 = échec).

    Pourquoi :
        Fournit un point d’entrée unique exploitable par Airflow et les tests d’intégration.
    """
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
