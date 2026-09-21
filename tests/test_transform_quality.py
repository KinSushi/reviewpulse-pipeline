# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
import os
import hashlib
import hmac
import json

import pandas as pd
import pytest

from reviewpulse import config
from reviewpulse import transform
from reviewpulse import quality


def test_load_raw_reads_jsonl_and_partitions(data_env, review_factory):
    # Arrange: create raw directory structure and a jsonl file
    raw_dir = config.RAW_DIR

    app_id = 1
    language = "english"
    date_str = "2026-09-16"
    partition_path = raw_dir / f"app_id={app_id}" / f"language={language}" / f"dt={date_str}"
    partition_path.mkdir(parents=True, exist_ok=True)

    review = review_factory(rid="R123", steamid="7656119800000000")
    jsonl_path = partition_path / "batch_test.jsonl"
    jsonl_path.write_text(json.dumps(review, ensure_ascii=False) + "\n", encoding="utf-8")

    # Act
    df = transform.load_raw()

    # Assert
    assert not df.empty
    assert "recommendationid" in df.columns
    assert df["app_id"].iloc[0] == app_id
    assert df["language_partition"].iloc[0] == language
    assert df["recommendationid"].iloc[0] == review["recommendationid"]


def test_clean_deduplication_bbcode_and_empty(monkeypatch):
    # Arrange: raw DataFrame with duplicates, BBCode and empty text after cleaning
    salt = b"test-salt"
    monkeypatch.setattr(config, "SALT", None, raising=False)  # ensure config.salt uses env
    os.environ["REVIEWPULSE_SALT"] = "test-salt"

    raw = pd.DataFrame(
        [
            {
                "recommendationid": "dup1",
                "review": "[b]Great game![/b]",
                "voted_up": True,
                "timestamp_created": 1_800_000_000,
                "timestamp_updated": 1_800_000_100,
                "author": {"steamid": "7656119800000001", "playtime_at_review": 60},
                "votes_up": 5,
                "weighted_vote_score": "0.8",
                "language": "english",
                "app_id": 1,
                "language_partition": "english",
            },
            {
                "recommendationid": "dup1",
                "review": "[b]Great game![/b]",
                "voted_up": True,
                "timestamp_created": 1_800_000_000,
                "timestamp_updated": 1_800_000_200,  # newer
                "author": {"steamid": "7656119800000001", "playtime_at_review": 60},
                "votes_up": 5,
                "weighted_vote_score": "0.8",
                "language": "english",
                "app_id": 1,
                "language_partition": "english",
            },
            {
                "recommendationid": "empty1",
                "review": "[b] [/b]",
                "voted_up": False,
                "timestamp_created": 1_800_000_500,
                "timestamp_updated": 1_800_000_500,
                "author": {"steamid": "7656119800000002"},
                "votes_up": 0,
                "weighted_vote_score": "0.2",
                "language": "english",
                "app_id": 1,
                "language_partition": "english",
            },
        ]
    )

    # Act
    cleaned = transform.clean(raw, salt)

    # Assert deduplication (only one dup1 row, the newer)
    assert cleaned["review_id"].tolist() == ["dup1"]
    # BBCode removed, spaces normalized, empty text rows removed
    assert cleaned.loc[cleaned["review_id"] == "dup1", "review_text"].iloc[0] == "Great game!"
    # The empty1 row becomes empty after BBCode removal -> should be dropped
    assert "empty1" not in cleaned["review_id"].values


def test_author_pseudo_stable(monkeypatch):
    # Arrange: two rows with same steamid
    os.environ["REVIEWPULSE_SALT"] = "stable-salt"
    salt = config.salt()

    raw = pd.DataFrame(
        [
            {
                "recommendationid": "r1",
                "review": "Nice",
                "voted_up": True,
                "timestamp_created": 1_800_000_000,
                "timestamp_updated": 1_800_000_100,
                "author": {"steamid": "7656119800000010", "playtime_at_review": 30},
                "votes_up": 1,
                "weighted_vote_score": "0.6",
                "language": "english",
                "app_id": 1,
                "language_partition": "english",
            },
            {
                "recommendationid": "r2",
                "review": "Bad",
                "voted_up": False,
                "timestamp_created": 1_800_000_200,
                "timestamp_updated": 1_800_000_300,
                "author": {"steamid": "7656119800000010", "playtime_at_review": 45},
                "votes_up": 0,
                "weighted_vote_score": "0.3",
                "language": "english",
                "app_id": 1,
                "language_partition": "english",
            },
        ]
    )

    cleaned = transform.clean(raw, salt)

    pseudo_vals = cleaned["author_pseudo"].unique()
    assert len(pseudo_vals) == 1
    expected = hmac.new(salt, b"7656119800000010", hashlib.sha256).hexdigest()
    assert pseudo_vals[0] == expected
    assert len(pseudo_vals[0]) == 64
    assert all(c in "0123456789abcdef" for c in pseudo_vals[0])


def test_clean_schema_and_forbidden_columns(monkeypatch):
    # Arrange: simple raw entry
    os.environ["REVIEWPULSE_SALT"] = "schema-salt"
    salt = config.salt()

    raw = pd.DataFrame(
        [
            {
                "recommendationid": "r3",
                "review": "Okay game",
                "voted_up": True,
                "timestamp_created": 1_800_001_000,
                "timestamp_updated": 1_800_001_100,
                "author": {"steamid": "7656119800000020", "playtime_at_review": 10},
                "votes_up": 2,
                "weighted_vote_score": "0.7",
                "language": "english",
                "app_id": 1,
                "language_partition": "english",
            }
        ]
    )

    cleaned = transform.clean(raw, salt)

    # Columns match config.CLEAN_COLUMNS keys and order
    assert list(cleaned.columns) == list(config.CLEAN_COLUMNS.keys())
    # Types match
    for col, expected_type in config.CLEAN_COLUMNS.items():
        assert str(cleaned[col].dtype) == expected_type

    # Forbidden columns absent
    for forbidden in config.FORBIDDEN_CLEAN_COLUMNS:
        assert forbidden not in cleaned.columns


def test_missing_salt_raises(monkeypatch):
    # Remove environment variable
    monkeypatch.delenv("REVIEWPULSE_SALT", raising=False)
    with pytest.raises(RuntimeError):
        _ = config.salt()


def test_check_clean_passes_on_labelled_frame(labelled_frame):
    errors = quality.check_clean(labelled_frame)
    assert errors == []


def test_assert_quality_raises_on_errors(labelled_frame):
    df = labelled_frame.copy()

    # Introduce duplicate review_id
    duplicate_row = df.iloc[0].copy()
    df = pd.concat([df, pd.DataFrame([duplicate_row])], ignore_index=True)

    # Introduce invalid label (2)
    df.loc[df.index[0], "label"] = 2

    # Add forbidden column
    df["steamid"] = "7656119800000000"

    with pytest.raises(quality.DataQualityError) as excinfo:
        quality.assert_quality(df)

    msg = str(excinfo.value).lower()
    assert "duplicate" in msg or "review_id" in msg
    assert "label" in msg
    assert "forbidden" in msg or "steamid" in msg
