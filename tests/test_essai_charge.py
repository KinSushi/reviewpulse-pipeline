"""tests/test_essai_charge.py
Batterie de tests unitaires pour le module ``tools.essai_charge``.
"""

from __future__ import annotations

import sys
import pathlib
import urllib.error
import urllib.request
import pytest

# Ajout du répertoire ``tools`` au chemin d'importation
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import essai_charge as ec


class _FakeResponse:
    """Réponse factice compatible avec ``urllib.request.urlopen``."""

    def __init__(self, code: int = 200):
        self._code = code

    def getcode(self) -> int:
        return self._code

    def read(self) -> bytes:
        return b""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_percentiles_sur_serie_connue():
    """Le calcul des percentiles sur la série 1‑100 rend les valeurs attendues."""
    serie = list(range(1, 101))  # déjà triée
    assert ec._calculer_percentile(serie, 50) == 50, "p50 attendu = 50"
    assert ec._calculer_percentile(serie, 90) == 90, "p90 attendu = 90"
    assert ec._calculer_percentile(serie, 99) == 99, "p99 attendu = 99"


def test_percentile_sur_un_seul_element():
    """Une série d’un seul élément rend cet élément quel que soit le percentile."""
    serie = [42]
    for p in (0, 10, 50, 99, 100):
        assert ec._calculer_percentile(serie, p) == 42, f"p{p} attendu = 42"


def test_verifier_service_accepte_200(monkeypatch):
    """Un code 200 ne lève aucune exception."""
    def fake_urlopen(req, timeout=None):
        return _FakeResponse(200)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    # Aucun RuntimeError ne doit être levé
    ec.verifier_service("http://exemple.test", delai=1.0)


def test_verifier_service_refuse_un_code_autre(monkeypatch):
    """Un code autre que 200 déclenche RuntimeError contenant l'URL."""
    def fake_urlopen(req, timeout=None):
        return _FakeResponse(503)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    url = "http://exemple.test"
    with pytest.raises(RuntimeError) as excinfo:
        ec.verifier_service(url, delai=1.0)
    assert url in str(excinfo.value), "Le message d'erreur doit citer l'URL"


def test_verifier_service_refuse_une_panne_reseau(monkeypatch):
    """Une URLError déclenche RuntimeError."""
    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("panne réseau simulée")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError):
        ec.verifier_service("http://exemple.test", delai=1.0)


def test_une_requete_compte_un_succes(monkeypatch):
    """Une réponse 200 doit être rapportée comme succès avec durée positive."""
    def fake_urlopen(req, timeout=None):
        return _FakeResponse(200)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    succes, duree, code = ec.une_requete("http://exemple.test", "texte", delai=1.0)
    assert succes is True, "La requête doit être marquée comme succès"
    assert duree > 0, "La durée doit être strictement positive"
    assert code == 200, "Le code HTTP doit être 200"


def test_une_requete_compte_un_echec_sans_interrompre(monkeypatch):
    """Une exception doit être traduite en échec, durée positive et code None."""
    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("panne simulée")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    succes, duree, code = ec.une_requete("http://exemple.test", "texte", delai=1.0)
    assert succes is False, "La requête doit être marquée comme échec"
    assert duree > 0, "La durée doit être strictement positive même en échec"
    assert code is None, "Le code doit être None en cas d'exception"


def test_mesurer_agrege_les_chiffres(monkeypatch):
    """Avec un faux urlopen toujours à 200, mesurer doit rapporter 0 échec et un débit positif."""
    def fake_urlopen(req, timeout=None):
        return _FakeResponse(200)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = ec.mesurer(
        base_url="http://exemple.test",
        textes=["x"],
        concurrence=4,
        nb_requetes=20,
        delai=1.0,
    )
    assert result["requetes"] == 20, "Nombre total de requêtes attendu = 20"
    assert result["succes"] == 20, "Toutes les requêtes doivent être des succès"
    assert result["echecs"] == 0, "Aucun échec attendu"
    assert result["taux_erreur"] == 0.0, "Le taux d'erreur doit être nul"
    assert result["debit"] > 0, "Le débit doit être strictement positif"
    for key in ("p50", "p90", "p99"):
        assert key in result, f"{key} doit être présent dans le résultat"
        assert result[key] >= 0, f"{key} doit être non‑négatif"


def test_mesurer_compte_les_echecs(monkeypatch):
    """Un urlopen qui lève une exception une fois sur deux doit produire des échecs comptés."""
    calls = {"cpt": 0}

    def fake_urlopen(req, timeout=None):
        calls["cpt"] += 1
        if calls["cpt"] % 2 == 0:
            raise urllib.error.URLError("panne simulée")
        return _FakeResponse(200)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    nb = 10
    result = ec.mesurer(
        base_url="http://exemple.test",
        textes=["x"],
        concurrence=2,
        nb_requetes=nb,
        delai=1.0,
    )
    assert result["echecs"] > 0, "Il doit y avoir au moins un échec"
    expected_taux = result["echecs"] / nb
    assert result["taux_erreur"] == pytest.approx(expected_taux), "Le taux d'erreur doit correspondre au ratio réel"


def test_rapport_mentionne_les_chiffres_et_la_limite():
    """Le rapport Markdown doit contenir débit, p99 et la phrase de limitation."""
    mesure = {
        "requetes": 5,
        "succes": 5,
        "echecs": 0,
        "taux_erreur": 0.0,
        "duree_totale": 1.23,
        "debit": 4.07,
        "p50": 10.0,
        "p90": 20.0,
        "p99": 30.0,
        "moyenne": 15.0,
        "max": 25.0,
    }
    md = ec.rapport_markdown(
        mesure=mesure,
        base_url="http://exemple.test",
        concurrence=2,
        date_utc="2026-09-19T12:00:00Z",
        commit="abcd1234",
    )
    assert "Débit (req/s)" in md, "Le tableau doit contenir la colonne débit"
    assert "30.00" in md, "Le p99 doit être présent avec deux décimales"
    phrase_limite = "Cette mesure a été réalisée sur une seule machine"
    assert phrase_limite in md, "Le rapport doit mentionner la limitation de la mesure"
