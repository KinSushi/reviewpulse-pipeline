# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
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
    8. Purge des partitions brutes plus anciennes que ``config.RAW_RETENTION_DAYS`` (30 jours).

**Choix de conception**
    - Utilisation de pandas (ADR 0003).
    - Pseudonymisation HMAC salée, sel obligatoire (ADR 0004).
    - Contrôles qualité exécutés avant l'écriture (ADR 0005).

**Preuves**
    - 16/09/2026 : exécution sans sel entraîne l'arrêt du pipeline et aucune modification de la zone propre.

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

    Une phrase de rôle :
        Détermine ``app_id``, ``language`` et ``sample_source`` à partir du chemin
        d'un fichier JSONL de la zone brute.

    Pourquoi :
        Centralise la logique d'extraction pour garantir la même interprétation dans :func:`load_raw` et faciliter les tests.

    Args:
        file_path: Chemin complet du fichier *.jsonl*.

    Returns:
        DataFrame de tous les enregistrements dont le JSON a pu être parsé, avec les colonnes de partition ajoutées. Les lignes au JSON invalide sont ignorées et journalisées.

    Raises:
        RuntimeError: Si ``app_id`` ou ``language`` ne peuvent être extraits.
    """
    app_match = re.search(r"app_id=(\d+)", str(file_path))
    lang_match = re.search(r"language=([a-zA-Z]+)", str(file_path))
    sample_match = _RE_SAMPLE.search(str(file_path))

    if not app_match or not lang_match:
        # Pourquoi : un fichier mal nommé ne doit pas arrêter la collecte ; on journalise et on passe.
        raise RuntimeError(f"Impossible d'extraire les partitions du chemin : {file_path}")

    app_id = int(app_match.group(1))
    language = lang_match.group(1)

    # Pourquoi : la partition sample= n'existe pas sur les anciens chemins du flux naturel ;
    # l'alternative (rejeter le fichier) casserait la compatibilité avec les données déjà collectées.
    sample_source = (
        sample_match.group(1)
        if sample_match
        else config.SAMPLE_NATURAL
    )
    return app_id, language, sample_source


def load_raw(raw_dir: Optional[Path] = None) -> pd.DataFrame:
    """Lit les fichiers *.jsonl* bruts et ajoute les colonnes de partition.

    Une phrase de rôle :
        Charge l'ensemble des enregistrements bruts présents sous ``raw_dir`` et
        y adjoint les métadonnées de partition.

    Pourquoi :
        Isoler la lecture récursive et l'enrichissement par partition permet de
        tester le nettoyage indépendamment de la collecte.

    Args:
        raw_dir: Répertoire contenant les fichiers bruts. Si ``None``,
            utilise ``config.RAW_DIR``.

    Returns:
        DataFrame de tous les enregistrements dont le JSON a pu être parsé, avec les colonnes de partition ajoutées. Les lignes au JSON invalide sont ignorées et journalisées.
        Retourne un DataFrame vide si aucun enregistrement n'est trouvé.
    """
    raw_dir = raw_dir or config.RAW_DIR
    raw_dir = Path(raw_dir)
    records = []

    _logger.info("Chargement des fichiers bruts depuis %s", raw_dir)

    for file_path in raw_dir.rglob("*.jsonl"):
        try:
            app_id, language, sample_source = _extract_partition_info(file_path)
        except RuntimeError as exc:
            # Pourquoi : un fichier mal nommé ne doit pas arrêter la collecte ; on journalise et on passe.
            _logger.error(str(exc))
            continue

        _logger.debug("Lecture de %s (app_id=%d, language=%s, sample=%s)", file_path, app_id, language, sample_source)

        with file_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    # Pourquoi : une ligne corrompue n'invalide pas le lot ; un warning suffit.
                    _logger.warning("Ligne JSON invalide dans %s", file_path)
                    continue
                obj["app_id"] = app_id
                obj["language_partition"] = language
                obj["sample_source"] = sample_source
                records.append(obj)

    _logger.info("%d enregistrements bruts charges depuis %d fichiers", len(records), len(list(raw_dir.rglob("*.jsonl"))))
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def _clean_text(text: str) -> str:
    """Supprime les balises BBCode, réduit les espaces multiples et strip.

    Une phrase de rôle :
        Nettoie une chaîne de texte brute issue de l'API Steam.

    Pourquoi :
        Les avis Steam peuvent contenir du BBCode ; le modèle de texte attend
        une chaîne continue sans balises ni espaces superflus.

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

    Une phrase de rôle :
        Applique l'ensemble des règles de nettoyage, dérivation et
        pseudonymisation pour produire la zone propre.

    Pourquoi :
        Centralise toutes les étapes de normalisation, dédoublonnage et dérivation de nouvelles colonnes afin de garantir la conformité aux exigences de qualité.

    Args:
        raw: DataFrame issu de :func:`load_raw`.
        salt: Sel utilisé pour le hachage HMAC du ``steamid``.

    Returns:
        DataFrame propre, typé et ordonné selon ``config.CLEAN_COLUMNS``.

    Raises:
        RuntimeError: Si une colonne interdite apparaît après le nettoyage.
    """
    if raw.empty:
        _logger.warning("DataFrame brut vide : retour d'un DataFrame propre vide")
        empty_df = pd.DataFrame(columns=config.CLEAN_COLUMNS.keys())
        for col, typ in config.CLEAN_COLUMNS.items():
            empty_df[col] = empty_df[col].astype(typ)
        return empty_df

    df = raw.copy()

    # Pourquoi : copie défensive pour ne pas modifier le DataFrame passé par l'appelant ;
    # l'alternative (mutation en place) compliquerait les tests et les réentraînements.
    if "sample_source" not in df.columns:
        # Pourquoi : certains jeux de tests construisent un DataFrame brut sans la colonne de partition.
        df["sample_source"] = config.SAMPLE_NATURAL

    # review_id
    df["review_id"] = df["recommendationid"]

    # gestion du timestamp_updated
    if "timestamp_updated" not in df.columns:
        # Pourquoi : l'API Steam ne fournit pas toujours ``timestamp_updated`` ;
        # on se replie sur ``timestamp_created`` pour conserver un ordre total.
        df["timestamp_updated"] = df["timestamp_created"]
    df["timestamp_updated"] = (
        pd.to_numeric(df["timestamp_updated"], errors="coerce")
        .fillna(0)
        .astype("int64")
    )

    # Pourquoi : le flux naturel est la source de vérité ; le flux négatif complémentaire
    # ne sert qu'à équilibrer l'entraînement. L'alternative (tirage aléatoire) romprait
    # la traçabilité des avis réels.
    priority_map = {
        config.SAMPLE_NATURAL: 0,
        config.SAMPLE_NEGATIVE_BOOST: 1,
    }
    df["_priority"] = df["sample_source"].map(priority_map).fillna(1).astype("int64")
    # Pourquoi : l'ordre du tri (priorité flux naturel, sinon updated_at DESC) reflète ADR 0005 ; drop_duplicates avec keep="first" garde la première occurrence du groupe, donc la plus prioritaire après tri.
    df = df.sort_values(["_priority", "timestamp_updated"], ascending=[True, False])
    df = df.drop_duplicates(subset="review_id", keep="first")
    df = df.drop(columns=["_priority"])

    # texte nettoyé
    df["review_text"] = df["review"].apply(_clean_text)

    # suppression des lignes où le texte devient vide
    # Pourquoi : un avis sans texte ne peut pas être vectorisé ; on l'écarte en amont de la qualité.
    df = df[df["review_text"] != ""]

    # label
    # Pourquoi : le double cast force dtype=bool puis int64 ; decision.py attend 0/1.
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
        # Pourquoi : si author.steamid est absent, on hache la chaîne vide ; quality.assert_quality détectera la collision sur author_pseudo.
        return hmac.new(salt, steamid.encode(), hashlib.sha256).hexdigest()

    df["author_pseudo"] = df["author"].apply(_hash_steamid)

    # langue : utilise la partition si disponible
    if "language_partition" in df.columns:
        # Pourquoi : la partition est l'autorité de regroupement ; le champ `language` de l'API est libre et peut diverger.
        df["language"] = df["language_partition"]
    elif "language" in df.columns:
        df["language"] = df["language"]
    else:
        # Pourquoi : on conserve la ligne pour permettre à quality.assert_quality de diagnostiquer l'absence de partition plutôt que de masquer le défaut.
        df["language"] = None

    # longueur du texte
    # Pourquoi : uniformité avec CLEAN_COLUMNS ; le schéma prime sur l'optimisation mémoire.
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
            # Pourquoi : RuntimeError ici = erreur de programmation (colonne attendue comme absente apparait) ; quality.DataQualityError concerne les valeurs.
            raise RuntimeError(f"Colonne interdite présente après nettoyage : {forbidden}")

    _logger.info(
        "Zone propre construite : %d lignes, %d colonnes",
        len(clean_df),
        len(clean_df.columns),
    )
    return clean_df


def write_clean(df: pd.DataFrame, path: Optional[Path] = None) -> Path:
    """Écriture atomique du DataFrame propre au format Parquet.

    Une phrase de rôle :
        Persiste le DataFrame propre sur disque de manière atomique.

    Pourquoi :
        L'écriture temporaire suivie d'un ``os.replace`` garantit que les lecteurs
        de la zone propre ne voient jamais un fichier partiellement écrit.

    Args:
        df: DataFrame conforme à ``CLEAN_COLUMNS``.
        path: Chemin de destination. Si ``None``, utilise ``config.CLEAN_FILE``.

    Returns:
        Chemin final du fichier écrit.
    """
    path = path or config.CLEAN_FILE
    path = Path(path)

    # Pourquoi : parents=True crée les dossiers intermédiaires ; exist_ok=True permet les réexécutions idempotentes.
    path.parent.mkdir(parents=True, exist_ok=True)

    # Pourquoi : écriture atomique par fichier temporaire puis remplacement ;
    # l'alternative (écriture directe) exposerait un Parquet incomplet en cas d'arrêt brutal.
    # Pourquoi : with_suffix conserve l'extension .parquet (sinon os.replace renommerait en .tmp et perdrait le type).
    tmp_path = path.with_suffix(".tmp.parquet")
    df.to_parquet(tmp_path, engine="pyarrow")
    os.replace(tmp_path, path)
    _logger.info("Zone propre ecrite a %s", path)
    return path


def purge_raw(
    raw_dir: Optional[Path] = None,
    retention_days: Optional[int] = None,
    today: Optional[datetime.date] = None,
) -> int:
    """Supprime les partitions de données brutes plus anciennes que la période de rétention.

    Une phrase de rôle :
        Efface les partitions brutes ``dt=YYYY-MM-DD`` dépassant la durée de conservation.

    Pourquoi :
        La zone brute grossit chaque jour ; la purge limite l'occupation disque
        tout en conservant l'historique récent pour les réexécutions.

    Args:
        raw_dir: Répertoire racine contenant les partitions ``dt=``.
            Par défaut ``config.RAW_DIR``.
        retention_days: Nombre de jours à conserver. Par défaut
            ``config.RAW_RETENTION_DAYS``.
        today: Date de référence pour le calcul du seuil. Permet l'injection
            en tests ; sinon ``datetime.date.today()``.

    Returns:
        Nombre total de fichiers supprimés.
    """
    raw_dir = raw_dir or config.RAW_DIR
    raw_dir = Path(raw_dir)

    # Pourquoi : absence du dossier = premier lancement ou environnement neuf ; ce n'est pas une erreur.
    if not raw_dir.is_dir():
        return 0

    retention_days = retention_days if retention_days is not None else config.RAW_RETENTION_DAYS
    today = today or datetime.date.today()
    # Pourquoi : on purge par jour calendaire pour rester stable vis-à-vis des fuseaux et des DST.
    cutoff = today - datetime.timedelta(days=retention_days)

    _logger.info("Purge des partitions brutes anterieures a %s dans %s", cutoff, raw_dir)

    removed_files = 0

    for dt_dir in raw_dir.rglob("dt=*"):
        if not dt_dir.is_dir():
            continue
        match = re.search(r"dt=(\d{4}-\d{2}-\d{2})", str(dt_dir))
        if not match:
            continue
        dir_date = datetime.datetime.strptime(match.group(1), "%Y-%m-%d").date()
        # Pourquoi : on conserve la partition du jour exact (<, pas <=) pour qu'une réexécution le même jour ne perde pas sa propre entrée.
        if dir_date < cutoff:
            files = list(dt_dir.rglob("*"))
            removed_files += len(files)
            # Pourquoi : zone brute = données reproductibles depuis l'API ; une suppression est rattrapable par réexécution de ingest.
            shutil.rmtree(dt_dir)
            _logger.info("Partition brute supprimee : %s (%d fichiers)", dt_dir, len(files))

    _logger.info("Purge terminee : %d fichiers supprimes", removed_files)
    return removed_files


def main() -> int:
    """Pipeline complet : chargement → nettoyage → contrôle qualité → écriture → purge.

    Une phrase de rôle :
        Ordonne les étapes de transformation et arrête le pipeline si la qualité n'est pas atteinte.

    Pourquoi :
        Fournit un point d'entrée unique exploitable par Airflow et les tests d'intégration.

    Returns:
        Code de sortie du pipeline (0 = succès, 1 = échec).
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
