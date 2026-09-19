"""tests/test_verifier_briques.py
Batterie de tests unitaires pour le module ``tools.verifier_briques``.
"""

from __future__ import annotations

import sys
import pathlib
import pytest

# Ajout du répertoire ``tools`` au chemin d'importation
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import verifier_briques as vb


def _creer_arborescence(
    racine: pathlib.Path,
    exigences: str,
    briques: str,
    registre: str,
) -> None:
    """Crée les fichiers ``docs/08_exigences_par_bloc.md``,
    ``docs/18_briques_exigees.md`` et ``docs/16_registre_suivi.md`` avec le
    contenu fourni."""
    docs = racine / "docs"
    docs.mkdir(parents=True, exist_ok=True)

    (docs / "08_exigences_par_bloc.md").write_text(exigences, encoding="utf-8")
    (docs / "18_briques_exigees.md").write_text(briques, encoding="utf-8")
    (docs / "16_registre_suivi.md").write_text(registre, encoding="utf-8")


def test_cas_conforme_ne_signale_rien(tmp_path: pathlib.Path):
    """Le cas conforme ne signale aucune anomalie."""
    exigences = "**Kafka**\n**Airflow**"
    briques = """## Briques techniques
| Brique | Exigée par | État | Preuve |
|---|---|---|---|
| Airflow | X | présente | |
| Kafka | X | absente | R17 |
## Termes non techniques
"""
    registre = """| R17 | suivi |
|---|---|
"""
    _creer_arborescence(tmp_path, exigences, briques, registre)

    result = vb.verifier(tmp_path)
    assert result["non_classes"] == [], f"non_classes inattendu : {result['non_classes']}"
    assert result["sans_sujet"] == [], f"sans_sujet inattendu : {result['sans_sujet']}"
    assert result["sujets_inconnus"] == [], f"sujets_inconnus inattendu : {result['sujets_inconnus']}"


def test_terme_non_classe_est_signale(tmp_path: pathlib.Path):
    """Un terme en gras absent du tableau et des non‑techniques est signalé."""
    exigences = "**MongoDB**"
    briques = """## Briques techniques
| Brique | Exigée par | État | Preuve |
|---|---|---|---|
## Termes non techniques
"""
    registre = ""
    _creer_arborescence(tmp_path, exigences, briques, registre)

    result = vb.verifier(tmp_path)
    assert result["non_classes"] == ["MongoDB"], f"non_classes attendu ['MongoDB'] : {result['non_classes']}"


def test_brique_absente_sans_sujet_est_signalee(tmp_path: pathlib.Path):
    """Une brique absente sans référence Rnn doit apparaître dans ``sans_sujet``."""
    exigences = ""
    briques = """## Briques techniques
| Brique | Exigée par | État | Preuve |
|---|---|---|---|
| BriqueX | Y | absente | |
## Termes non techniques
"""
    registre = ""
    _creer_arborescence(tmp_path, exigences, briques, registre)

    result = vb.verifier(tmp_path)
    assert result["sans_sujet"] == ["BriqueX"], f"sans_sujet attendu ['BriqueX'] : {result['sans_sujet']}"


def test_sujet_inconnu_est_signale(tmp_path: pathlib.Path):
    """Une référence à un sujet non présent dans le registre est signalée."""
    exigences = ""
    briques = """## Briques techniques
| Brique | Exigée par | État | Preuve |
|---|---|---|---|
| BriqueY | Z | absente | R99 |
## Termes non techniques
"""
    registre = """| R01 | ok |
|---|---|
"""
    _creer_arborescence(tmp_path, exigences, briques, registre)

    result = vb.verifier(tmp_path)
    assert result["sujets_inconnus"] == ["R99"], f"sujets_inconnus attendu ['R99'] : {result['sujets_inconnus']}"


def test_ligne_vide_entre_titre_et_tableau(tmp_path: pathlib.Path):
    """Une ligne vide entre le titre et le tableau ne doit pas empêcher la lecture."""
    exigences = ""
    briques = """## Briques techniques

| Brique | Exigée par | État | Preuve |
|---|---|---|---|
| Airflow | X | présente | |
## Termes non techniques
"""
    registre = ""
    _creer_arborescence(tmp_path, exigences, briques, registre)

    # La fonction doit retourner le dictionnaire des briques sans lever d'exception
    result = vb.verifier(tmp_path)
    assert "Airflow" in result["briques"], f"Airflow devrait être présent dans les briques : {result['briques']}"


def test_terme_contenant_une_virgule(tmp_path: pathlib.Path):
    """Un terme non technique contenant une virgule doit être lu en entier."""
    exigences = ""
    briques = """## Briques techniques
| Brique | Exigée par | État | Preuve |
|---|---|---|---|
## Termes non techniques
`Sources primaires, lues le 16/09/2026`
"""
    registre = ""
    _creer_arborescence(tmp_path, exigences, briques, registre)

    result = vb.verifier(tmp_path)
    attendu = {"Sources primaires, lues le 16/09/2026"}
    assert result["non_techniques"] == attendu, f"non_techniques attendu {attendu} : {result['non_techniques']}"


def test_sujets_lus_dans_le_tableau_du_registre(tmp_path: pathlib.Path):
    """Les identifiants Rnn doivent être extraits de la première cellule du tableau."""
    exigences = ""
    briques = """## Briques techniques
| Brique | Exigée par | État | Preuve |
|---|---|---|---|
## Termes non techniques
"""
    registre = """| R42 | description |
| R43 | autre |
|---|---|
"""
    _creer_arborescence(tmp_path, exigences, briques, registre)

    sujets = vb.sujets_du_registre(tmp_path)
    assert sorted(sujets) == ["R42", "R43"], f"sujets attendus ['R42','R43'] : {sujets}"


def test_etat_invalide_leve_une_erreur(tmp_path: pathlib.Path):
    """Un état inconnu dans le tableau doit lever ``ValueError``."""
    exigences = ""
    briques = """## Briques techniques
| Brique | Exigée par | État | Preuve |
|---|---|---|---|
| BriqueZ | A | inconnu | |
## Termes non techniques
"""
    registre = ""
    _creer_arborescence(tmp_path, exigences, briques, registre)

    with pytest.raises(ValueError):
        vb.briques_classees(tmp_path)


def test_etat_accentue_est_accepte(tmp_path: pathlib.Path):
    """Les états avec accent doivent être acceptés et normalisés."""
    exigences = ""
    briques = """## Briques techniques
| Brique | Exigée par | État | Preuve |
|---|---|---|---|
| B1 | X | présente | |
| B2 | Y | partielle | |
| B3 | Z | absente | |
## Termes non techniques
"""
    registre = ""
    _creer_arborescence(tmp_path, exigences, briques, registre)

    briques_dict, _ = vb.briques_classees(tmp_path)
    assert briques_dict["B1"]["etat"] == "presente", f"État normalisé attendu 'presente' : {briques_dict['B1']['etat']}"
    assert briques_dict["B2"]["etat"] == "partielle", f"État normalisé attendu 'partielle' : {briques_dict['B2']['etat']}"
    assert briques_dict["B3"]["etat"] == "absente", f"État normalisé attendu 'absente' : {briques_dict['B3']['etat']}"
