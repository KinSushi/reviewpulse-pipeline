"""tests/test_comparaison_modeles.py
Batterie de tests unitaires pour le module ``tools.comparaison_modeles``.
"""

from __future__ import annotations

import sys
import pathlib
from unittest.mock import MagicMock

import pytest
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

# Ajout du repertoire ``tools`` au chemin d'importation
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

# Mock des modules reviewpulse avant import de comparaison_modeles
reviewpulse_mock = MagicMock()
config_mock = MagicMock()
decision_mock = MagicMock()
train_mock = MagicMock()

config_mock.THRESHOLD_GRID = [0.3, 0.4, 0.5, 0.6, 0.7]
config_mock.RANDOM_STATE = 42
config_mock.DEFAULT_DECISION_THRESHOLD = 0.5
config_mock.CLEAN_FILE = pathlib.Path("/fake/clean.parquet")
config_mock.SAMPLE_NATURAL = "natural"
config_mock.SAMPLE_NEGATIVE_BOOST = "boost"

def _mock_negative_proba(pipeline, X):
    """Simule negative_proba en renvoyant une colonne aleatoire."""
    return pd.Series(np.random.rand(len(X)), index=X.index)

def _mock_predict_labels(proba, threshold):
    """Simule predict_labels en seuillant les probabilites."""
    return (proba > threshold).astype(int)

def _mock_build_pipeline():
    """Fabrique un pipeline de reference identique au modele en service."""
    tfidf = TfidfVectorizer(
        analyzer="char",
        ngram_range=(3, 5),
        min_df=2,
        sublinear_tf=True,
        lowercase=True,
    )
    clf = LogisticRegression(
        C=10.0,
        class_weight="balanced",
        max_iter=2000,
        random_state=42,
    )
    return Pipeline([("tfidf", tfidf), ("clf", clf)])

decision_mock.negative_proba = MagicMock(side_effect=_mock_negative_proba)
decision_mock.predict_labels = MagicMock(side_effect=_mock_predict_labels)
train_mock.build_pipeline = MagicMock(side_effect=_mock_build_pipeline)

sys.modules["reviewpulse"] = reviewpulse_mock
sys.modules["reviewpulse.config"] = config_mock
sys.modules["reviewpulse.decision"] = decision_mock
sys.modules["reviewpulse.train"] = train_mock

import comparaison_modeles as cm


@pytest.fixture
def jeu():
    """Fabrique 60 avis naturels et 10 avis boost avec zzboostzz."""
    avis_positifs = [
        f"great game love it number {i}" for i in range(30)
    ]
    avis_negatifs = [
        f"terrible broken refund now number {i}" for i in range(30)
    ]
    reviews = avis_positifs + avis_negatifs
    labels = [1] * 30 + [0] * 30
    X = pd.Series(reviews, name="review_text")
    y = pd.Series(labels, name="label")
    
    boost_reviews = [
        f"zzboostzz awful experience number {i}" for i in range(10)
    ]
    boost_df = pd.DataFrame({
        "review_text": boost_reviews,
        "label": [0] * 10,
    })
    
    skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    plis = list(skf.split(X, y))
    
    return X, y, boost_df, plis


def test_noms_de_candidats_uniques():
    """Les noms rendus par candidats() sont tous differents et le modele en service y figure."""
    candidats_list = cm.candidats()
    noms = [c.nom for c in candidats_list]
    assert len(noms) == len(set(noms)), "Des noms de candidats sont en double"
    assert any("logreg_caracteres" in nom for nom in noms), "Le modele en service doit figurer dans les candidats"


def test_chaque_fabrique_rend_un_pipeline_neuf():
    """Pour chaque candidat mesurable, deux appels a fabrique() rendent deux objets DIFFERENTS."""
    candidats_list = cm.candidats()
    for candidat in candidats_list:
        if candidat.nom == "xgboost" and cm.xgboost is None:
            continue
        pipeline_1 = candidat.fabrique()
        pipeline_2 = candidat.fabrique()
        assert pipeline_1 is not pipeline_2, f"Fabrique de {candidat.nom} ne rend pas un objet neuf"
        etapes = dict(pipeline_1.named_steps)
        assert "clf" in etapes, f"La derniere etape du pipeline {candidat.nom} doit s'appeler clf"


def test_temoin_le_candidat_en_service_est_le_pipeline_du_projet():
    """Les parametres tfidf et clf du candidat en service correspondent a build_pipeline()."""
    candidat_en_service = next(c for c in cm.candidats() if c.nom == "logreg_caracteres")
    pipeline_candidat = candidat_en_service.fabrique()
    pipeline_reference = cm.train.build_pipeline()
    
    etapes_candidat = dict(pipeline_candidat.named_steps)
    etapes_reference = dict(pipeline_reference.named_steps)
    
    assert "tfidf" in etapes_candidat, "Le candidat en service doit avoir une etape tfidf"
    assert "clf" in etapes_candidat, "Le candidat en service doit avoir une etape clf"
    
    params_tfidf_candidat = etapes_candidat["tfidf"].get_params()
    params_tfidf_reference = etapes_reference["tfidf"].get_params()
    assert params_tfidf_candidat == params_tfidf_reference, "Parametres tfidf differents du modele en service"
    
    params_clf_candidat = etapes_candidat["clf"].get_params()
    params_clf_reference = etapes_reference["clf"].get_params()
    assert params_clf_candidat == params_clf_reference, "Parametres clf differents du modele en service"


def test_evaluation_rend_des_mesures_bornees(jeu):
    """L'evaluation du candidat en service rend des mesures comprises entre 0 et 1."""
    X, y, boost_df, plis = jeu
    candidat_en_service = next(c for c in cm.candidats() if c.nom == "logreg_caracteres")
    
    resultats = cm._evaluer_candidat(candidat_en_service, X, y, boost_df, plis)
    
    assert 0 <= resultats["f1_macro"] <= 1, f"F1 macro hors bornes : {resultats['f1_macro']}"
    assert 0 <= resultats["auc"] <= 1, f"AUC hors bornes : {resultats['auc']}"
    assert 0 <= resultats["recall_negatif"] <= 1, f"Rappel hors bornes : {resultats['recall_negatif']}"
    assert 0 <= resultats["precision_negatif"] <= 1, f"Precision hors bornes : {resultats['precision_negatif']}"
    assert resultats["seuil"] in cm.config.THRESHOLD_GRID, f"Seuil {resultats['seuil']} hors grille"
    assert len(resultats["f1_par_pli"]) == 3, f"Attendu 3 F1 par pli, obtenu {len(resultats['f1_par_pli'])}"


def test_le_flux_complementaire_ne_sert_qu_a_l_entrainement(jeu, monkeypatch):
    """Aucun texte de validation ne contient zzboostzz et 60 textes valides au total."""
    X, y, boost_df, plis = jeu
    texte_val_recus = []
    original = cm.decision.negative_proba
    
    def espion(pipeline, X_val):
        texte_val_recus.extend(X_val.tolist())
        return original(pipeline, X_val)
    
    monkeypatch.setattr(cm.decision, "negative_proba", espion)
    
    candidat_en_service = next(c for c in cm.candidats() if c.nom == "logreg_caracteres")
    cm._evaluer_candidat(candidat_en_service, X, y, boost_df, plis)
    
    for texte in texte_val_recus:
        assert "zzboostzz" not in texte, f"Texte de validation contient zzboostzz : {texte}"
    
    assert len(texte_val_recus) == 60, f"60 textes de validation attendus, {len(texte_val_recus)} recus"


def test_xgboost_absent_ne_fait_pas_tomber_l_outil(monkeypatch):
    """Avec xgboost=None, candidats() ne leve pas et xgboost est dans la liste."""
    monkeypatch.setattr(cm, "xgboost", None)
    candidats_list = cm.candidats()
    noms = [c.nom for c in candidats_list]
    assert "xgboost" in noms, "Le candidat xgboost doit figurer dans la liste meme si absent"
