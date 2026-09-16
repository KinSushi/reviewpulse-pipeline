import os
import json
import time
import logging
import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from reviewpulse import config

logger = logging.getLogger(__name__)


def _sleep(seconds: float, sleep_func: Any = time.sleep) -> None:
    """Helper to allow injection of sleep function."""
    sleep_func(seconds)


def fetch_page(
    session: requests.Session,
    app_id: int,
    language: str,
    cursor: str,
    *,
    review_type: str = "all",
    sleep: Any = time.sleep,
) -> Dict[str, Any]:
    """
    Récupère une page d'avis depuis l'API Steam.

    Le paramètre ``review_type`` est ajouté à la requête (valeur ``all`` par défaut).
    Lève ``RuntimeError`` si le code HTTP n'est pas 200, si le champ
    ``success`` n'est pas égal à 1, ou après épuisement des tentatives
    de retry.
    """
    url = config.STEAM_URL.format(app_id=app_id)
    params = {
        "json": 1,
        "filter": "recent",
        "language": language,
        "purchase_type": "all",
        "num_per_page": config.PAGE_SIZE,
        "cursor": cursor,
        "review_type": review_type,
    }

    attempts = 0
    while True:
        try:
            response = session.get(
                url,
                params=params,
                timeout=config.HTTP_TIMEOUT_S,
            )
        except Exception as exc:
            raise RuntimeError(f"Erreur réseau lors de la requête : {exc}") from exc

        if response.status_code == 200:
            payload = response.json()
            if payload.get("success") != 1:
                raise RuntimeError("L'API Steam a renvoyé success != 1")
            return payload

        if response.status_code in (429,) + tuple(range(500, 600)):
            if attempts >= config.HTTP_MAX_RETRIES:
                raise RuntimeError(
                    f"Échec après {attempts + 1} tentatives, code {response.status_code}"
                )
            backoff = 2 ** attempts
            _sleep(backoff, sleep)
            attempts += 1
            continue

        raise RuntimeError(f"Erreur HTTP inattendue : {response.status_code}")


def ingest_app(
    app_id: int,
    language: str,
    *,
    session: Optional[requests.Session] = None,
    max_pages: Optional[int] = None,
    now: Optional[datetime.datetime] = None,
    sleep: Any = time.sleep,
    raw_dir: Optional[Path] = None,
    state_dir: Optional[Path] = None,
    sample_source: Optional[str] = None,
) -> int:
    """
    Ingestion d'un jeu, d'une langue et d'une source d'échantillonnage.

    Le paramètre ``sample_source`` indique la partition (``natural`` ou
    ``negative_boost``). S'il est ``None``, il est résolu à
    ``config.SAMPLE_NATURAL``. Le type d'avis demandé (``review_type``) est
    dérivé du flux : ``negative`` si ``sample_source`` correspond à
    ``config.SAMPLE_NEGATIVE_BOOST``, sinon ``all``.

    Retourne le nombre d'avis nouveaux écrits.
    """
    raw_dir = raw_dir or config.RAW_DIR
    state_dir = state_dir or config.STATE_DIR
    now = now or datetime.datetime.now(datetime.timezone.utc)

    # Résolution du source d'échantillonnage
    sample_source = sample_source or config.SAMPLE_NATURAL
    is_natural = sample_source == config.SAMPLE_NATURAL

    # Détermination du type d'avis à demander à l'API
    review_type = "negative" if sample_source == config.SAMPLE_NEGATIVE_BOOST else "all"

    # S'assurer que le répertoire d'état existe
    state_dir.mkdir(parents=True, exist_ok=True)

    # Résolution de max_pages
    max_pages = max_pages if max_pages is not None else config.MAX_PAGES

    # Chemin du manifeste selon la source
    if is_natural:
        state_path = state_dir / f"seen_{app_id}_{language}.txt"
    else:
        state_path = state_dir / f"seen_{sample_source}_{app_id}_{language}.txt"

    if state_path.exists():
        seen_ids = set(state_path.read_text(encoding="utf-8").splitlines())
    else:
        seen_ids = set()

    session = session or requests.Session()
    cursor = "*"
    total_new = 0
    page_index = 0
    batch_reviews: list[Dict[str, Any]] = []

    while page_index < max_pages:
        payload = fetch_page(
            session,
            app_id,
            language,
            cursor,
            review_type=review_type,
            sleep=sleep,
        )

        returned_cursor = payload.get("cursor")
        if returned_cursor == cursor:
            break

        reviews = payload.get("reviews", [])
        if not reviews:
            break

        new_reviews = [
            rev for rev in reviews if rev.get("recommendationid") not in seen_ids
        ]

        if not new_reviews:
            break

        batch_reviews.extend(new_reviews)

        new_ids = {rev.get("recommendationid") for rev in new_reviews}
        seen_ids.update(new_ids)
        total_new += len(new_reviews)

        cursor = returned_cursor
        page_index += 1

    if batch_reviews:
        date_str = now.strftime("%Y-%m-%d")
        timestamp_str = now.strftime("%Y%m%dT%H%M%SZ")
        if is_natural:
            batch_dir = (
                Path(raw_dir)
                / f"app_id={app_id}"
                / f"language={language}"
                / f"dt={date_str}"
            )
        else:
            batch_dir = (
                Path(raw_dir)
                / f"sample={sample_source}"
                / f"app_id={app_id}"
                / f"language={language}"
                / f"dt={date_str}"
            )
        batch_dir.mkdir(parents=True, exist_ok=True)

        # Écriture atomique du manifeste
        manifest_tmp = state_path.with_suffix(".tmp")
        with manifest_tmp.open("w", encoding="utf-8") as f:
            for rid in sorted(seen_ids):
                f.write(f"{rid}\n")

        # Écriture atomique du lot brut
        batch_path = batch_dir / f"batch_{timestamp_str}.jsonl"
        batch_tmp = batch_path.with_suffix(".tmp")
        with batch_tmp.open("w", encoding="utf-8") as f:
            for rev in batch_reviews:
                json.dump(rev, f, ensure_ascii=False)
                f.write("\n")
        os.replace(batch_tmp, batch_path)

        # Remplacement atomique du manifeste
        os.replace(manifest_tmp, state_path)

    return total_new


def main() -> int:
    """
    Parcourt toutes les combinaisons APP_IDS × LANGUAGES,
    consomme d'abord le flux naturel puis le flux de boost négatif,
    journalise le nombre total de nouveaux avis.
    Retourne 0.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    total_new = 0
    for app_id in config.APP_IDS:
        for language in config.LANGUAGES:
            # Flux naturel
            try:
                new_natural = ingest_app(
                    app_id,
                    language,
                    sample_source=config.SAMPLE_NATURAL,
                    max_pages=config.MAX_PAGES,
                )
                if new_natural:
                    logger.info(
                        "Nouveaux avis (natural) pour app_id=%s language=%s : %s",
                        app_id,
                        language,
                        new_natural,
                    )
                total_new += new_natural
            except Exception as exc:
                logger.error(
                    "Erreur lors de l'ingestion (natural) app_id=%s language=%s : %s",
                    app_id,
                    language,
                    exc,
                )
                raise

            # Flux boost négatif
            try:
                new_boost = ingest_app(
                    app_id,
                    language,
                    sample_source=config.SAMPLE_NEGATIVE_BOOST,
                    max_pages=config.BOOST_MAX_PAGES,
                )
                if new_boost:
                    logger.info(
                        "Nouveaux avis (negative_boost) pour app_id=%s language=%s : %s",
                        app_id,
                        language,
                        new_boost,
                    )
                total_new += new_boost
            except Exception as exc:
                logger.error(
                    "Erreur lors de l'ingestion (negative_boost) app_id=%s language=%s : %s",
                    app_id,
                    language,
                    exc,
                )
                raise

    logger.info("Total des nouveaux avis ingestés : %s", total_new)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
