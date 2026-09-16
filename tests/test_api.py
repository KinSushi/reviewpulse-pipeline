import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from reviewpulse import config
from reviewpulse import api as api_module

app = api_module.app


class FakeModel:
    # Attributs requis par l'API et la logique de décision
    classes_ = np.array([0, 1])
    decision_threshold_ = 0.5

    def predict_proba(self, texts):
        probs = []
        for txt in texts:
            if "bug" in txt.lower():
                probs.append([0.9, 0.1])
            else:
                probs.append([0.1, 0.9])
        return np.array(probs)


@pytest.fixture
def client():
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[api_module.get_model] = lambda: (FakeModel(), "7")
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = original_overrides


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["model_version"] == "7"


def test_predict_success(client):
    payload = {"texts": ["This contains a bug in the system.", "I love this game!"]}
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_version"] == "7"
    # Vérification du seuil de décision retourné par l'API
    assert data["decision_threshold"] == 0.5
    preds = data["predictions"]
    assert len(preds) == 2

    # first prediction (bug)
    p0 = preds[0]
    assert p0["text_preview"] == payload["texts"][0][:80]
    assert pytest.approx(p0["proba_negative"], rel=1e-6) == 0.9
    assert p0["label"] == "negative"

    # second prediction (positive)
    p1 = preds[1]
    assert p1["text_preview"] == payload["texts"][1][:80]
    assert pytest.approx(p1["proba_negative"], rel=1e-6) == 0.1
    assert p1["label"] == "positive"


def test_predict_empty_list_422(client):
    resp = client.post("/predict", json={"texts": []})
    assert resp.status_code == 422


def test_predict_too_many_texts_422(client):
    resp = client.post("/predict", json={"texts": ["a"] * 101})
    assert resp.status_code == 422


def test_predict_too_long_text_422(client):
    long_text = "x" * 5001
    resp = client.post("/predict", json={"texts": [long_text]})
    assert resp.status_code == 422


def test_insights_not_found_404(client, data_env):
    # Ensure summary file does not exist
    if config.SUMMARY_FILE.exists():
        config.SUMMARY_FILE.unlink()
    resp = client.get("/insights?app_id=123")
    assert resp.status_code == 404


def test_insights_success_200(client, data_env):
    # Create a minimal summary parquet file
    df = pd.DataFrame(
        [
            {
                "app_id": 1,
                "language": "english",
                "date": pd.Timestamp("2024-01-01"),
                "n_reviews": 10,
                "share_negative_pred": 0.2,
                "share_negative_true": 0.3,
                "model_version": "7",
            }
        ]
    )
    # Ensure directory exists
    config.SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(config.SUMMARY_FILE, engine="pyarrow")

    resp = client.get("/insights?app_id=1")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    row = data[0]
    assert row["app_id"] == 1
    assert row["language"] == "english"
    assert row["date"] == "2024-01-01"
    assert row["n_reviews"] == 10
    assert pytest.approx(row["share_negative_pred"], rel=1e-6) == 0.2
    assert pytest.approx(row["share_negative_true"], rel=1e-6) == 0.3
    assert row["model_version"] == "7"
