"""tests/test_comparaison_modeles.py
Batterie de tests unitaires pour le module ``tools.comparaison_modeles``.
"""

from __future__ import annotations

import sys
import pathlib

import pandas as pd
import pytest
from sklearn.model_selection import StratifiedKFold

# Ajout du repertoire ``tools`` au chemin d'importation
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import comparaison_modeles as cm

from reviewpulse import config, train


@pytest.fixture
def jeu():
    """Fabrique 60 avis naturels courts equilibres et 10 avis negatifs supplementaires."""
    positifs = [
        f"great game love it number {i}" for i in range(30)
    ]
    negatifs = [
        f"terrible broken refund now number {i}" for i in range(30)
    ]
    texts = positifs + negatifs
    labels = [1] * 30 + [0] * 30
    df = pd.DataFrame(
        {
            "review_text": texts,
            "label": labels,
        }
    )
    df.index = pd.RangeIndex(0, 60)

    boost_texts = [f"zzboostzz bad game number {i}" for i in range(10)]
    boost_df = pd.DataFrame(
        {
            "review_text": boost_texts,
            "label": [0] * 10,
        }
    )

    skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    plis = list(skf.split(df["review_text"], df["label"]))

    return {
        "X": df["review_text"].astype("string"),
        "y": df["label"],
        "boost_df": boost_df,
        "plis": plis,
    }


def test_noms_de_candidats_uniques():
    """Les noms rendus par ``candidats()`` sont tous differents et le modele en service y figure."""
    noms = [c.nom for c in cm.candidats()]
    assert len(noms) == len(set(noms)), "Les noms des candidats doivent etre uniques"
    assert "logreg_caracteres" in noms, "Le modele en service doit etre present dans les noms"


def test_chaque_fabrique_rend_un_pipeline_neuf():
    """Deux appels a ``fabrique()`` rendent deux objets differents dont la derniere etape s'appelle ``clf``."""
    liste = [c for c in cm.candidats() if not (c.nom == "xgboost" and cm.xgboost is None)]
    for candidat in liste:
        p1 = candidat.fabrique()
        p2 = candidat.fabrique()
        assert p1 is not p2, f"{candidat.nom} : deux fabriques doivent rendre des objets distincts"
        assert p1.steps[-1][0] == "clf", f"{candidat.nom} : la derniere etape doit s'appeler clf"


def test_temoin_le_candidat_en_service_est_le_pipeline_du_projet():
    """Le candidat en service reproduit exactement le pipeline de ``reviewpulse.train.build_pipeline()``."""
    candidat = next(c for c in cm.candidats() if c.nom == "logreg_caracteres")
    pipeline_outil = candidat.fabrique()
    pipeline_projet = train.build_pipeline()

    for etape in ("tfidf", "clf"):
        assert pipeline_outil.named_steps[etape].get_params() == pipeline_projet.named_steps[etape].get_params(), (
            f"Les parametres de l'etape {etape} du candidat en service "
            "doivent etre ceux de reviewpulse.train.build_pipeline()"
        )


def test_evaluation_rend_des_mesures_bornees(jeu):
    """L'evaluation du candidat en service rend des metriques coherentes et un seuil de la grille."""
    candidat = next(c for c in cm.candidats() if c.nom == "logreg_caracteres")
    res = cm._evaluer_candidat(
        candidat,
        jeu["X"],
        jeu["y"],
        jeu["boost_df"],
        jeu["plis"],
    )

    assert 0.0 <= res["f1_macro"] <= 1.0, "F1 macro doit etre compris entre 0 et 1"
    assert 0.0 <= res["auc"] <= 1.0, "AUC doit etre comprise entre 0 et 1"
    assert 0.0 <= res["recall_negatif"] <= 1.0, "Rappel negatif doit etre compris entre 0 et 1"
    assert 0.0 <= res["precision_negatif"] <= 1.0, "Precision negative doit etre comprise entre 0 et 1"
    assert res["seuil"] in config.THRESHOLD_GRID, "Le seuil retenu doit appartenir a la grille"
    assert len(res["f1_par_pli"]) == 3, "Il doit y avoir exactement trois F1 par pli"


def test_le_flux_complementaire_ne_sert_qu_a_l_entrainement(jeu, monkeypatch):
    """Aucun texte de validation ne contient le mot sentinelle du flux complementaire."""
    texts_valides = []

    vraie_negative_proba = cm.decision.negative_proba

    def espion(pipeline, X):
        """Enregistre les textes recus en validation puis delegue a la vraie fonction."""
        if hasattr(X, "tolist"):
            texts_valides.extend(X.tolist())
        else:
            texts_valides.extend(list(X))
        return vraie_negative_proba(pipeline, X)

    monkeypatch.setattr(cm.decision, "negative_proba", espion)

    candidat = next(c for c in cm.candidats() if c.nom == "logreg_caracteres")
    cm._evaluer_candidat(
        candidat,
        jeu["X"],
        jeu["y"],
        jeu["boost_df"],
        jeu["plis"],
    )

    assert set(texts_valides) == set(jeu["X"].tolist()), (
        "L'ensemble des textes vus en validation doit etre exactement les 60 textes naturels de la fixture"
    )
    assert not any("zzboostzz" in t for t in texts_valides), (
        "Aucun texte de validation ne doit contenir le mot sentinelle du flux complementaire"
    )


def test_xgboost_absent_ne_fait_pas_tomber_l_outil(monkeypatch):
    """L'absence du paquet xgboost ne leve pas d'exception et marque le candidat comme non mesurable."""
    monkeypatch.setattr(cm, "xgboost", None)
    liste = cm.candidats()
    xgboost_candidat = next((c for c in liste if c.nom == "xgboost"), None)
    assert xgboost_candidat is not None, "Le candidat xgboost doit etre liste"
    assert xgboost_candidat.poids_par_echantillon is True, "Le candidat xgboost porte l'indicateur de poids par echantillon"
