# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""tests/test_verifier_justifications.py
Batterie de tests unitaires pour les fonctions ``citations`` et ``lire_adrs``
du module ``tools.verifier_justifications``.
"""

from __future__ import annotations

import sys
import pathlib

import pytest

# Ajout du répertoire ``tools`` au chemin d'importation
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import verifier_justifications as vj


def test_citation_simple(tmp_path: pathlib.Path):
    """Un fichier contenant ``ADR 0013`` rend ``{'0013': 1}``."""
    fichier = tmp_path / "code.py"
    fichier.write_text("ADR 0013", encoding="utf-8")
    result = vj.citations(["*.py"], tmp_path)
    assert result == {"0013": 1}, f"Résultat inattendu : {result}"


def test_citation_groupee(tmp_path: pathlib.Path):
    """``ADR 0013, 0014 et 0017`` rend un compte de 1 pour chacun."""
    fichier = tmp_path / "module.txt"
    fichier.write_text("ADR 0013, 0014 et 0017", encoding="utf-8")
    result = vj.citations(["*.txt"], tmp_path)
    attendu = {"0013": 1, "0014": 1, "0017": 1}
    assert result == attendu, f"Résultat attendu {attendu}, obtenu {result}"


def test_citation_plage(tmp_path: pathlib.Path):
    """Test des trois variantes de plage : ``a``, ``à`` et ``-``."""
    fichier = tmp_path / "ranges.md"
    contenu = "\n".join(
        [
            "ADR 0001 a 0004",
            "ADR 0010 à 0013",
            "ADR 0020-0022",
        ]
    )
    fichier.write_text(contenu, encoding="utf-8")
    result = vj.citations(["*.md"], tmp_path)
    attendu = {
        "0001": 1,
        "0002": 1,
        "0003": 1,
        "0004": 1,
        "0010": 1,
        "0011": 1,
        "0012": 1,
        "0013": 1,
        "0020": 1,
        "0021": 1,
        "0022": 1,
    }
    assert result == attendu, f"Plage mal comptée : {result}"


def test_citation_s_arrete_au_premier_intrus(tmp_path: pathlib.Path):
    """``ADR 0004 et la charte`` ne rend que 0004."""
    fichier = tmp_path / "doc.txt"
    fichier.write_text("ADR 0004 et la charte", encoding="utf-8")
    result = vj.citations(["*.txt"], tmp_path)
    assert result == {"0004": 1}, f"Doit s'arrêter au premier intrus, obtenu {result}"


def test_plage_inversee_ignoree(tmp_path: pathlib.Path):
    """``ADR 0020 a 0010`` ne rend rien (plage inversée)."""
    fichier = tmp_path / "inv.txt"
    fichier.write_text("ADR 0020 a 0010", encoding="utf-8")
    result = vj.citations(["*.txt"], tmp_path)
    assert result == {}, f"Plage inversée devrait être ignorée, obtenu {result}"


def test_casse_indifferente(tmp_path: pathlib.Path):
    """La casse ne doit pas affecter la reconnaissance (``adr``)."""
    fichier = tmp_path / "lower.md"
    fichier.write_text("voir l'adr 0007 plus bas", encoding="utf-8")
    result = vj.citations(["*.md"], tmp_path)
    assert result == {"0007": 1}, f"Casse insensible attendue, obtenu {result}"


def test_fichier_illisible_ne_fait_pas_echouer(tmp_path: pathlib.Path):
    """Un motif qui ne désigne aucun fichier rend un dictionnaire vide sans exception."""
    result = vj.citations(["**/nonexistent/*.py"], tmp_path)
    assert result == {}, f"Doit retourner un dict vide, obtenu {result}"


def test_lire_adrs_rejette_un_entete_invalide(tmp_path: pathlib.Path):
    """Un ADR dont l'en‑tête n'est pas valide doit lever ``ValueError``."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    mauvais = adr_dir / "0001-essai.md"
    mauvais.write_text("Ce n'est pas un en‑tête ADR", encoding="utf-8")
    with pytest.raises(ValueError):
        vj.lire_adrs(tmp_path)


def test_lire_adrs_ignore_le_readme(tmp_path: pathlib.Path):
    """Le fichier ``README.md`` doit être ignoré par ``lire_adrs``."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    # ADR valide
    adr = adr_dir / "0002-test.md"
    adr.write_text("# ADR 0002 — Titre de test", encoding="utf-8")
    # README à ignorer
    readme = adr_dir / "README.md"
    readme.write_text("# Documentation", encoding="utf-8")
    adrs = vj.lire_adrs(tmp_path)
    assert isinstance(adrs, list), f"Doit retourner une liste, obtenu {type(adrs)}"
    assert len(adrs) == 1, f"README doit être ignoré, nombre d'ADR trouvé {len(adrs)}"
    assert adrs[0]["numero"] == "0002", f"Numéro attendu '0002', obtenu {adrs[0]['numero']}"
