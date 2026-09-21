# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""tests/test_mention_droit_auteur.py
Vérification de la cohérence des mentions légales entre le paquet, l'API et l'outil.
"""

from __future__ import annotations

import pathlib
from fastapi.testclient import TestClient

import reviewpulse
from reviewpulse import api


def test_le_paquet_expose_auteur_et_mention():
    """Le paquet expose un auteur contenant 'Sovralys LLC' et un copyright valide."""
    assert "Sovralys LLC" in reviewpulse.__author__, "L'auteur doit contenir 'Sovralys LLC'"
    assert reviewpulse.__copyright__.startswith("Copyright "), "Le copyright doit commencer par 'Copyright '"
    # Vérification du caractère U+00A9 (©) juste après "Copyright "
    assert reviewpulse.__copyright__[9] == "\u00a9", "Le caractère de droit d'auteur (U+00A9) est attendu après 'Copyright '"
    assert "2026" in reviewpulse.__copyright__, "L'année 2026 doit figurer dans le copyright"
    assert reviewpulse.__copyright__.endswith(reviewpulse.__author__), "Le copyright doit se terminer par le nom de l'auteur"


def test_la_documentation_de_l_api_porte_la_mention():
    """L'OpenAPI de l'application réplique exactement les métadonnées du paquet."""
    client = TestClient(api.app)
    response = client.get("/openapi.json")
    assert response.status_code == 200, "L'accès à openapi.json doit réussir sans charger le modèle"
    
    data = response.json()
    info = data.get("info", {})
    
    assert info.get("description") == reviewpulse.__copyright__, "La description OpenAPI doit correspondre au copyright du paquet"
    contact = info.get("contact", {})
    assert contact.get("name") == reviewpulse.__author__, "Le nom de contact OpenAPI doit correspondre à l'auteur du paquet"


def test_temoin_la_mention_de_l_outil_et_celle_du_paquet_sont_la_meme():
    """TÉMOIN : La mention dans l'outil shell doit être strictement identique à celle du paquet."""
    base_dir = pathlib.Path(__file__).resolve().parents[1]
    script_path = base_dir / "tools" / "copyright.sh"
    
    if not script_path.exists():
        raise FileNotFoundError(f"Le fichier témoin {script_path} est introuvable")
    
    with script_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # La deuxième ligne (index 1) est attendue comme : "# <mention>"
    if len(lines) < 2:
        raise AssertionError("Le script copyright.sh doit contenir au moins deux lignes")
    
    seconde_ligne = lines[1]
    if not seconde_ligne.startswith("# "):
        raise AssertionError(f"La deuxième ligne de {script_path} doit commencer par '# '")
    
    mention_outil = seconde_ligne[2:].rstrip("\n\r")
    
    assert mention_outil == reviewpulse.__copyright__, (
        f"Divergence détectée : l'outil contient '{mention_outil}' "
        f"alors que le paquet déclare '{reviewpulse.__copyright__}'"
    )
