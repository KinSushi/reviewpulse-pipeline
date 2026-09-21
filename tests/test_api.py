# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
import concurrent.futures
import re
import time

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from reviewpulse import config
from reviewpulse import api as api_module
from reviewpulse import decision

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

# ---------------------------------------------------------------------------
# Fixture et tests pour l'endpoint /explain avec un vrai pipeline sklearn
# ---------------------------------------------------------------------------

@pytest.fixture
def client_pipeline():
    """Construit un petit pipeline réel et le fournit via la dépendance get_model."""
    # Jeux de données très simples (français)
    texts = [
        "Ce produit est terrible, je déteste tout.",
        "J'adore ce jeu, c'est fantastique !",
        "Mauvaise expérience, très décevant.",
        "Excellent service, très satisfait.",
        "Je n'aime pas ce film, c'est nul.",
        "Superbe performance, je recommande.",
        "Pire achat de ma vie.",
        "Magnifique, je suis ravi.",
        "Terrible, rien à voir avec la description.",
        "Parfait, exactement ce que je voulais."
    ]
    labels = [
        decision.LABEL_NEGATIVE,
        decision.LABEL_POSITIVE,
        decision.LABEL_NEGATIVE,
        decision.LABEL_POSITIVE,
        decision.LABEL_NEGATIVE,
        decision.LABEL_POSITIVE,
        decision.LABEL_NEGATIVE,
        decision.LABEL_POSITIVE,
        decision.LABEL_NEGATIVE,
        decision.LABEL_POSITIVE,
    ]

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3))),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
    pipeline.fit(texts, labels)
    # Le pipeline doit exposer l'attribut decision_threshold_ attendu par l'API
    pipeline.decision_threshold_ = 0.5

    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[api_module.get_model] = lambda: (pipeline, "real")
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = original_overrides


def test_explain_success(client_pipeline):
    payload = {"text": "Ce produit est excellent, je l'adore vraiment.", "n": 5}
    resp = client_pipeline.post("/explain", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # version du modèle
    assert data["model_version"] == "real"
    # nombre de contributions locales ≤ n
    assert len(data["terms"]) <= payload["n"]
    # chaque terme rendu doit être présent dans le texte (insensible à la casse)
    for term_obj in data["terms"]:
        term = term_obj["terme"]
        assert re.search(re.escape(term), payload["text"], re.IGNORECASE)
    # contributions triées par valeur absolue décroissante
    contributions = [t["contribution"] for t in data["terms"]]
    abs_contrib = [abs(c) for c in contributions]
    assert abs_contrib == sorted(abs_contrib, reverse=True)


def test_explain_global_terms_signs(client_pipeline):
    payload = {"text": "Mauvaise qualité, très décevant.", "n": 3}
    resp = client_pipeline.post("/explain", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # global_negative et global_positive contiennent exactement 10 termes
    assert len(data["global_negative"]) == 10
    assert len(data["global_positive"]) == 10
    # les coefficients des deux listes sont strictement positifs,
    # et les deux listes de termes sont disjointes
    neg_coeffs = [t["coefficient"] for t in data["global_negative"]]
    pos_coeffs = [t["coefficient"] for t in data["global_positive"]]
    assert all(c > 0 for c in neg_coeffs)
    assert all(c > 0 for c in pos_coeffs)
    # vérifier que les termes sont disjoints
    neg_terms = {t["terme"] for t in data["global_negative"]}
    pos_terms = {t["terme"] for t in data["global_positive"]}
    assert neg_terms.isdisjoint(pos_terms)


def test_explain_empty_text_422(client_pipeline):
    payload = {"text": "", "n": 5}
    resp = client_pipeline.post("/explain", json=payload)
    assert resp.status_code == 422


def test_explain_n_limit(client_pipeline):
    payload = {"text": "Très bon produit, je le recommande vivement.", "n": 2}
    resp = client_pipeline.post("/explain", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # le nombre de termes retournés ne doit pas dépasser n
    assert len(data["terms"]) <= payload["n"]


def test_percentile_temoin_sur_serie_connue():
    """Vérifie les valeurs de référence du calcul de centile sur série 1-100."""
    serie = list(range(1, 101))
    assert api_module._percentile(serie, 50.0) == 50.5, "p50 doit valoir 50.5 (interpolation type 7)"
    assert api_module._percentile(serie, 95.0) == 95.05, "p95 doit valoir 95.05 (interpolation type 7)"
    assert api_module._percentile(serie, 99.0) == 99.01, "p99 doit valoir 99.01 (interpolation type 7)"


def test_percentile_liste_vide_rend_zero():
    """Une liste vide rend 0.0 sans lever d'exception."""
    assert api_module._percentile([], 50.0) == 0.0, "liste vide doit rendre 0.0"
    assert api_module._percentile([], 95.0) == 0.0, "liste vide doit rendre 0.0 pour tout centile"


def test_percentile_un_seul_element():
    """Une série à un élément rend cette valeur pour tous les centiles."""
    assert api_module._percentile([42.0], 50.0) == 42.0, "p50 sur un élément doit rendre cet élément"
    assert api_module._percentile([42.0], 95.0) == 42.0, "p95 sur un élément doit rendre cet élément"
    assert api_module._percentile([42.0], 99.0) == 42.0, "p99 sur un élément doit rendre cet élément"


def test_metrics_repond_sans_modele_charge(client):
    """Le endpoint /metrics répond 200 même sans modèle chargé."""
    # /metrics n'utilise PAS Depends(get_model), contrairement à /health
    # On vérifie que l'endpoint est accessible indépendamment du modèle
    resp = client.get("/metrics")
    assert resp.status_code == 200, "/metrics doit répondre 200 sans dépendre du modèle"


def test_metrics_structure_de_la_reponse(client):
    """La réponse de /metrics porte les clés attendues avec la structure complète."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    # Clés de premier niveau
    assert "endpoints" in data, "réponse doit contenir 'endpoints'"
    assert "total_requests" in data, "réponse doit contenir 'total_requests'"
    assert "samples_retained" in data, "réponse doit contenir 'samples_retained'"
    assert "uptime_seconds" in data, "réponse doit contenir 'uptime_seconds'"
    # Structure de chaque endpoint observé
    for path, metrics in data["endpoints"].items():
        assert "count" in metrics, f"endpoint {path} doit avoir 'count'"
        assert "p50_ms" in metrics, f"endpoint {path} doit avoir 'p50_ms'"
        assert "p95_ms" in metrics, f"endpoint {path} doit avoir 'p95_ms'"
        assert "p99_ms" in metrics, f"endpoint {path} doit avoir 'p99_ms'"
        assert "mean_ms" in metrics, f"endpoint {path} doit avoir 'mean_ms'"
        assert "max_ms" in metrics, f"endpoint {path} doit avoir 'max_ms'"


def test_metrics_compte_les_requetes(client):
    """Après un appel, total_requests et le count de l'endpoint augmentent."""
    resp_before = client.get("/metrics")
    data_before = resp_before.json()
    total_before = data_before["total_requests"]
    health_count_before = data_before["endpoints"]["/health"]["count"]

    # Appel à un endpoint observé
    client.get("/health")

    resp_after = client.get("/metrics")
    data_after = resp_after.json()
    # total_requests a augmenté d'au moins 1 (l'appel à /health)
    assert data_after["total_requests"] > total_before, "total_requests doit augmenter après une requête"
    # le count de /health a augmenté
    assert data_after["endpoints"]["/health"]["count"] > health_count_before, "count de /health doit augmenter"


def test_verrou_un_seul_chargement_sous_concurrence(monkeypatch):
    """Dix appels concurrents à `get_model` ne doivent déclencher qu'un seul chargement."""
    api_module._load_model.cache_clear()

    compteur = {"valeur": 0}
    version_partagee = "v_test_concurrent"

    def faux_load_champion(tracking_uri):
        # Le sommeil est indispensable : sans lui, le premier appel finirait avant que les
        # autres ne commencent, et le test passerait même sans verrou. Il ne prouverait rien.
        compteur["valeur"] += 1
        time.sleep(0.2)
        return FakeModel(), version_partagee

    # La fixture `monkeypatch` défait le remplacement même si une assertion échoue ;
    # un `undo()` écrit à la fin du test ne serait jamais atteint en cas d'échec et
    # fuirait dans les tests voisins.
    monkeypatch.setattr("reviewpulse.score.load_champion", faux_load_champion)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            resultats = [f.result() for f in
                         [executor.submit(api_module.get_model) for _ in range(10)]]

        assert compteur["valeur"] == 1, (
            "Le champion a été chargé %d fois au lieu d'une seule : le verrou de "
            "`get_model` ne dédoublonne plus les appels concurrents." % compteur["valeur"]
        )
        versions = {version for _, version in resultats}
        assert versions == {version_partagee}, (
            "Les dix appels doivent rendre la même version, obtenu : %s" % versions
        )
    finally:
        # Le cache est vidé quoi qu'il arrive : un modèle factice laissé en cache
        # contaminerait les tests suivants.
        api_module._load_model.cache_clear()
