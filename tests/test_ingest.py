import json
import time

import pytest

from reviewpulse import ingest, config


@pytest.fixture(autouse=True)
def reset_state(monkeypatch, data_env):
    """Ensure a clean state before each test."""
    # Reset manifest file if it exists
    manifest = config.STATE_DIR / f"seen_{12345}_english.txt"
    if manifest.exists():
        manifest.unlink()
    # Ensure no raw files exist
    raw_root = config.RAW_DIR
    if raw_root.exists():
        for p in raw_root.rglob("*"):
            if p.is_file():
                p.unlink()
    yield
    # Cleanup after test
    if manifest.exists():
        manifest.unlink()


def _read_raw_reviews():
    """Return list of review objects read from the single jsonl file created."""
    raw_files = list(config.RAW_DIR.rglob("*.jsonl"))
    assert len(raw_files) == 1, f"expected exactly one raw file, found {len(raw_files)}"
    with raw_files[0].open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def test_first_pass_writes_reviews(data_env, review_factory, fake_session_cls):
    """(1) premier passage écrit 2 avis dans un fichier jsonl dont chaque ligne décodée est égale à l'objet reçu."""
    rev1 = review_factory("r1")
    rev2 = review_factory("r2")
    pages = [
        {
            "success": 1,
            "reviews": [rev1, rev2],
            "cursor": "c1",
        },
        {
            "success": 1,
            "reviews": [],
            "cursor": "c2",
        },
    ]

    session = fake_session_cls(pages)
    count = ingest.ingest_app(
        app_id=12345,
        language="english",
        session=session,
        max_pages=10,
        now=None,
    )
    assert count == 2

    # vérifier le contenu du fichier jsonl
    raw_reviews = _read_raw_reviews()
    assert raw_reviews == [rev1, rev2]

    # le manifeste doit contenir les deux recommendationid
    manifest_path = config.STATE_DIR / "seen_12345_english.txt"
    assert manifest_path.read_text().splitlines() == ["r1", "r2"]


def test_second_pass_idempotent_no_new_file(data_env, review_factory, fake_session_cls):
    """(2) second passage sur les mêmes pages écrit 0 avis et ne crée aucun nouveau fichier."""
    rev1 = review_factory("r1")
    rev2 = review_factory("r2")
    pages = [
        {"success": 1, "reviews": [rev1, rev2], "cursor": "c1"},
        {"success": 1, "reviews": [], "cursor": "c2"},
    ]

    # première ingestion
    session1 = fake_session_cls(pages)
    first_count = ingest.ingest_app(
        app_id=12345,
        language="english",
        session=session1,
        max_pages=10,
        now=None,
    )
    assert first_count == 2
    raw_files_before = list(config.RAW_DIR.rglob("*.jsonl"))
    assert len(raw_files_before) == 1

    # deuxième ingestion avec même session (pages identiques)
    session2 = fake_session_cls(pages)
    second_count = ingest.ingest_app(
        app_id=12345,
        language="english",
        session=session2,
        max_pages=10,
        now=None,
    )
    assert second_count == 0
    raw_files_after = list(config.RAW_DIR.rglob("*.jsonl"))
    # aucun nouveau fichier créé
    assert raw_files_before == raw_files_after


def test_stop_when_cursor_repeats(data_env, review_factory, fake_session_cls):
    """(3) arrêt quand le curseur se répète."""
    rev_a = review_factory("ra")
    rev_b = review_factory("rb")
    pages = [
        {"success": 1, "reviews": [rev_a], "cursor": "c1"},
        {"success": 1, "reviews": [rev_b], "cursor": "c1"},  # même curseur que précédemment
        {"success": 1, "reviews": [review_factory("rc")], "cursor": "c2"},
    ]

    session = fake_session_cls(pages)
    count = ingest.ingest_app(
        app_id=12345,
        language="english",
        session=session,
        max_pages=10,
        now=None,
    )
    # seul le premier lot doit être traité
    assert count == 1
    raw_reviews = _read_raw_reviews()
    assert raw_reviews == [rev_a]

    # le manifeste ne doit contenir que le premier id
    manifest_path = config.STATE_DIR / "seen_12345_english.txt"
    assert manifest_path.read_text().splitlines() == ["ra"]


def test_retry_after_429(monkeypatch, data_env, review_factory, fake_session_cls):
    """(4) nouvelle tentative après un 429 puis succès, avec sleep factice."""
    rev = review_factory("r429")
    pages = [
        {"status_code": 429, "payload": {}},  # première réponse 429
        {"success": 1, "reviews": [rev], "cursor": "c1"},
        {"success": 1, "reviews": [], "cursor": "c2"},
    ]

    class CustomFakeSession(fake_session_cls):
        def __init__(self, pages):
            super().__init__(pages)

        def get(self, url, params=None, timeout=None):
            # pop the next page definition
            page_def = self._pages.pop(0)
            if "status_code" in page_def:
                # simulate HTTP error response
                resp = type(
                    "Resp",
                    (),
                    {
                        "status_code": page_def["status_code"],
                        "json": staticmethod(lambda: page_def["payload"]),
                    },
                )()
                self.calls.append(params or {})
                return resp
            else:
                resp = type(
                    "Resp",
                    (),
                    {
                        "status_code": 200,
                        "json": staticmethod(lambda: page_def),
                    },
                )()
                self.calls.append(params or {})
                return resp

    sleep_calls = []

    def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(time, "sleep", fake_sleep)

    session = CustomFakeSession(pages)
    count = ingest.ingest_app(
        app_id=12345,
        language="english",
        session=session,
        max_pages=10,
        now=None,
        sleep=fake_sleep,
    )
    assert count == 1
    # on doit avoir attendu 1 seconde (premier back‑off)
    assert sleep_calls == [1]

    raw_reviews = _read_raw_reviews()
    assert raw_reviews == [rev]


def test_success_zero_raises(monkeypatch, data_env, fake_session_cls):
    """(5) success=0 lève RuntimeError."""
    pages = [
        {"success": 0, "reviews": [], "cursor": "c0"},
    ]

    session = fake_session_cls(pages)
    with pytest.raises(RuntimeError):
        ingest.ingest_app(
            app_id=12345,
            language="english",
            session=session,
            max_pages=10,
            now=None,
        )
