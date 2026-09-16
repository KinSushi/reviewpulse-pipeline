import pandas as pd

from reviewpulse import config, ingest, transform, quality, train, score


def _make_page(review, cursor="*"):
    return {"success": 1, "cursor": cursor, "reviews": [review]}


END_PAGE = {"success": 1, "cursor": "fin", "reviews": []}


def test_ingest_negative_boost_writes_separate_paths_and_manifest(
    data_env,
    review_factory,
    fake_session_cls,
):
    app_id = 123456
    language = "english"
    review = review_factory(1, voted_up=False, text="bad game")
    # Natural ingestion
    session_nat = fake_session_cls([_make_page(review, cursor="cursor1"), END_PAGE])
    new_nat = ingest.ingest_app(
        app_id,
        language,
        session=session_nat,
        sample_source=config.SAMPLE_NATURAL,
    )
    assert new_nat == 1

    # Negative boost ingestion
    session_boost = fake_session_cls([_make_page(review, cursor="cursor2"), END_PAGE])
    new_boost = ingest.ingest_app(
        app_id,
        language,
        session=session_boost,
        sample_source=config.SAMPLE_NEGATIVE_BOOST,
    )
    assert new_boost == 1

    # FakeSession enregistre {url, params, timeout} pour chaque appel.
    assert any((c["params"] or {}).get("review_type") == "negative" for c in session_boost.calls)

    # Chemins attendus
    raw_nat_dir = (
        config.RAW_DIR
        / f"app_id={app_id}"
        / f"language={language}"
    )
    raw_boost_dir = (
        config.RAW_DIR
        / f"sample={config.SAMPLE_NEGATIVE_BOOST}"
        / f"app_id={app_id}"
        / f"language={language}"
    )
    assert any(p.suffix == ".jsonl" for p in raw_nat_dir.rglob("*.jsonl"))
    assert any(p.suffix == ".jsonl" for p in raw_boost_dir.rglob("*.jsonl"))

    # Manifestes séparés
    manifest_nat = config.STATE_DIR / f"seen_{app_id}_{language}.txt"
    manifest_boost = (
        config.STATE_DIR
        / f"seen_{config.SAMPLE_NEGATIVE_BOOST}_{app_id}_{language}.txt"
    )
    assert manifest_nat.read_text().strip() == review["recommendationid"]
    assert manifest_boost.read_text().strip() == review["recommendationid"]


def test_transform_clean_dedup_prioritises_natural(
    data_env,
    review_factory,
    fake_session_cls,
):
    app_id = 111111
    language = "english"
    review = review_factory(42, voted_up=False, text="terrible bug")
    # Ingestion naturelle puis boost
    ingest.ingest_app(
        app_id,
        language,
        session=fake_session_cls([_make_page(review, cursor="c1"), END_PAGE]),
        sample_source=config.SAMPLE_NATURAL,
    )
    ingest.ingest_app(
        app_id,
        language,
        session=fake_session_cls([_make_page(review, cursor="c2"), END_PAGE]),
        sample_source=config.SAMPLE_NEGATIVE_BOOST,
    )

    raw_df = transform.load_raw()
    cleaned = transform.clean(raw_df, config.salt())
    assert len(cleaned) == 1
    assert cleaned["sample_source"].iloc[0] == config.SAMPLE_NATURAL


def test_quality_check_unknown_sample_source(
    data_env,
    labelled_frame,
):
    # Crée un DataFrame valide puis change sample_source
    df = labelled_frame.copy()
    df["sample_source"] = "unknown_source"
    errors = quality.check_clean(df)
    assert any("sample_source" in e for e in errors)


def test_train_and_log_includes_boost_and_decision_threshold(
    data_env,
    labelled_frame,
):
    # Sélectionner 40 lignes négatives pour le boost
    neg_rows = labelled_frame[labelled_frame["label"] == 0].head(40).copy()
    neg_rows["review_id"] = neg_rows["review_id"] + "_b"
    neg_rows["sample_source"] = config.SAMPLE_NEGATIVE_BOOST

    df_all = pd.concat([labelled_frame, neg_rows], ignore_index=True)

    result = train.train_and_log(df_all, tracking_uri=config.MLFLOW_TRACKING_URI)

    assert result["n_boost"] == 40
    # 20 % de 200 lignes naturelles = 40
    assert result["n_test"] == 40
    assert result["decision_threshold"] in config.THRESHOLD_GRID

    # Le modèle champion doit porter le même seuil
    model, version = score.load_champion(tracking_uri=config.MLFLOW_TRACKING_URI)
    assert getattr(model, "decision_threshold_", None) == result["decision_threshold"]


def test_score_summarize_ignores_negative_boost(
    data_env,
):
    # Une ligne naturelle et une ligne boost le même jour
    now = pd.Timestamp("2023-03-15T12:00:00Z")
    df = pd.DataFrame(
        {
            "app_id": [999999, 999999],
            "language": ["english", "english"],
            "created_at": [now, now],
            "review_id": ["r1", "r2"],
            "label": [1, 0],
            "pred_label": [1, 0],
            "sample_source": [config.SAMPLE_NATURAL, config.SAMPLE_NEGATIVE_BOOST],
            "model_version": ["1", "1"],
        }
    )
    summary = score.summarize(df)
    # Seule la ligne naturelle doit être comptée
    assert summary["n_reviews"].iloc[0] == 1
    assert summary["share_negative_true"].iloc[0] == 0.0
