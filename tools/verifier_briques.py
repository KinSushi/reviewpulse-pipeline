"""tools.verifier_briques
========================

Ce module vérifie la cohérence entre les exigences exprimées dans
``docs/08_exigences_par_bloc.md`` et les briques techniques listées dans
``docs/18_briques_exigees.md``.  Il assure que :

* chaque notion mise en gras dans le fichier d’exigences apparaît soit dans le
  tableau des briques techniques, soit dans la liste des termes non techniques,
* chaque brique dont l’état n’est pas « présente » possède un sujet ouvert (identifiant
  ``Rnn``) présent dans le registre ``docs/16_registre_suivi.md``,
* aucun sujet ouvert n’est référencé sans être déclaré dans le registre.

L’outil produit un rapport Markdown détaillé et renvoie un code de sortie
indiquant la présence d’anomalies.
"""

from __future__ import annotations

import argparse
import datetime
import logging
import os
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Dict, Set, Tuple, List

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _normaliser_texte(texte: str) -> str:
    """Supprime les accents et met en minuscules."""
    nfkd = unicodedata.normalize("NFD", texte)
    sans_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sans_accents.lower()


def _obtenir_commit() -> str:
    """Renvoie le hash court du commit Git, la variable d'env ou « inconnu »."""
    env = os.getenv("REVIEWPULSE_COMMIT")
    if env:
        return env
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or "inconnu"
    except Exception:
        return "inconnu"


# --------------------------------------------------------------------------- #
# 1. Extraction des termes en gras
# --------------------------------------------------------------------------- #

def termes_exiges(racine: Path) -> Set[str]:
    """
    Retourne l’ensemble des termes en gras (**…**) du fichier
    ``docs/08_exigences_par_bloc.md``.
    Les espaces de bord sont supprimés.  Les termes contenant un saut de ligne
    ou dépassant 45 caractères sont ignorés.
    """
    chemin = racine / "docs" / "08_exigences_par_bloc.md"
    texte = chemin.read_text(encoding="utf-8")
    # Recherche non gourmande entre deux **, excluant les sauts de ligne
    raw = re.findall(r"\*\*([^*\n]+?)\*\*", texte)
    result: Set[str] = set()
    for terme in raw:
        terme = terme.strip()
        if "\n" in terme:
            continue
        if len(terme) > 45:
            continue
        result.add(terme)
    return result


# --------------------------------------------------------------------------- #
# 2. Lecture du tableau des briques et des termes non techniques
# --------------------------------------------------------------------------- #

def briques_classees(racine: Path) -> Tuple[Dict[str, Dict[str, str]], Set[str]]:
    """
    Analyse ``docs/18_briques_exigees.md`` et renvoie :

    * un dictionnaire ``{brique: {"exigee_par":…, "etat":…, "preuve":…}}``,
    * l’ensemble des termes non techniques.

    Lecture ligne à ligne pour éviter que l’expression régulière
    capture trop tôt la fin du tableau des briques techniques.
    Lève ``ValueError`` en français si une des deux sections attendues est
    absente ou si un état n’appartient pas à {« présente », « partielle », « absente »}
    (comparaison sans accents et sans casse).
    """
    chemin = racine / "docs" / "18_briques_exigees.md"
    texte = chemin.read_text(encoding="utf-8")
    lignes = texte.splitlines()

    # ------------------------------------------------------------------- #
    # Extraction de la section « ## Briques techniques »
    # ------------------------------------------------------------------- #
    tableau_lignes: List[str] = []
    in_briques = False
    for ligne in lignes:
        if not in_briques:
            if ligne.lstrip().startswith("## Briques techniques"):
                in_briques = True
                continue
        else:
            if ligne.startswith("|"):
                tableau_lignes.append(ligne.rstrip())
            elif not ligne.strip() and not tableau_lignes:
                # Markdown met une ligne vide entre un titre et son tableau :
                # sortir ici ferait lire un tableau vide (constaté le 19/09/2026).
                continue
            else:
                break

    if not tableau_lignes:
        raise ValueError("Section « ## Briques techniques » manquante dans 18_briques_exigees.md")
    if len(tableau_lignes) < 2:
        raise ValueError("Tableau des briques techniques incomplet.")
    # Ignorer l’en‑tête et le séparateur
    data_lignes = tableau_lignes[2:]

    briques: Dict[str, Dict[str, str]] = {}
    etats_valides = {"presente", "partielle", "absente"}

    for ligne in data_lignes:
        cols = [c.strip() for c in ligne.split("|")[1:-1]]  # première et dernière colonne vides
        if len(cols) != 4:
            continue  # ligne mal formée, on l’ignore
        brique, exigee_par, etat_raw, preuve = cols
        etat_norm = _normaliser_texte(etat_raw)
        if etat_norm not in etats_valides:
            raise ValueError(f"État « {etat_raw} » invalide pour la brique « {brique} ».")
        briques[brique] = {
            "exigee_par": exigee_par,
            "etat": etat_norm,
            "preuve": preuve,
        }

    # ------------------------------------------------------------------- #
    # Extraction de la section « ## Termes non techniques »
    # ------------------------------------------------------------------- #
    termes: Set[str] = set()
    in_termes = False
    for ligne in lignes:
        if not in_termes:
            if ligne.lstrip().startswith("## Termes non techniques"):
                in_termes = True
                continue
        else:
            if ligne.lstrip().startswith("##"):
                break  # fin de la section
            for match in re.finditer(r"`([^`]*)`", ligne):
                # Un terme peut contenir une virgule : « Sources primaires, lues le
                # 16/09/2026 : ». Decouper sur la virgule le coupait en deux et le
                # declarait non classe (constate le 19/09/2026). Les accents graves
                # delimitent le terme, rien d’autre.
                terme = match.group(1).strip()
                if terme:
                    termes.add(terme)

    if not in_termes:
        raise ValueError("Section « ## Termes non techniques » manquante dans 18_briques_exigees.md")

    return briques, termes

def sujets_du_registre(racine: Path) -> Set[str]:
    """
    Retourne l’ensemble des identifiants ``Rnn`` déclarés dans
    ``docs/16_registre_suivi.md``.

    Les sujets vivent dans un tableau Markdown : la ligne commence par une
    barre avant l’identifiant. Une recherche ancrée en début de ligne n’en
    trouvait aucun, et tous les renvois étaient déclarés morts (constaté le
    19/09/2026). On lit donc la première cellule de chaque ligne de tableau.
    """
    chemin = racine / "docs" / "16_registre_suivi.md"
    texte = chemin.read_text(encoding="utf-8")
    sujets: Set[str] = set()
    for ligne in texte.splitlines():
        if not ligne.lstrip().startswith("|"):
            continue
        cellules = ligne.split("|")
        if len(cellules) < 2:
            continue
        premiere = cellules[1].strip()
        if re.fullmatch(r"R\d{2}", premiere):
            sujets.add(premiere)
    return sujets


# --------------------------------------------------------------------------- #
# 4. Vérifications globales
# --------------------------------------------------------------------------- #

def verifier(racine: Path) -> Dict:
    """
    Effectue les contrôles décrits dans la documentation du module.

    Retourne un dictionnaire contenant :

    * ``non_classes``   – termes exigés non répertoriés,
    * ``sans_sujet``    – briques non présentes sans référence de sujet,
    * ``sujets_inconnus`` – références de sujet non présentes dans le registre,
    * ``briques``       – le dictionnaire des briques techniques,
    * ``non_techniques`` – l’ensemble des termes non techniques.
    """
    termes = termes_exiges(racine)
    briques, non_tech = briques_classees(racine)
    sujets_registre = sujets_du_registre(racine)

    # 1. Termes non classés
    brique_noms = set(briques.keys())
    non_classes = sorted(termes - brique_noms - non_tech)

    # 2. Briques sans sujet
    sans_sujet: List[str] = []
    sujets_refs: Set[str] = set()
    for nom, info in briques.items():
        if info["etat"] != "presente":
            # Recherche d'éventuels identifiants Rnn dans la colonne preuve
            refs = set(re.findall(r"R\d{2}\b", info["preuve"]))
            sujets_refs.update(refs)
            if not refs:
                sans_sujet.append(nom)

    # 3. Sujets inconnus (référencés mais absents du registre)
    sujets_inconnus = sorted(sujets_refs - sujets_registre)

    return {
        "non_classes": non_classes,
        "sans_sujet": sorted(sans_sujet),
        "sujets_inconnus": sujets_inconnus,
        "briques": briques,
        "non_techniques": non_tech,
    }


# --------------------------------------------------------------------------- #
# 5. Génération du rapport Markdown
# --------------------------------------------------------------------------- #

def rapport_markdown(resultat: Dict, date_utc: str, commit: str) -> str:
    """
    Construit le rapport Markdown à partir du dictionnaire retourné par
    :func:`verifier`.

    Le rapport comporte :

    * un compte par état,
    * les trois listes de problèmes,
    * un tableau des briques dont l’état n’est pas « présente », trié par état
      puis par nom.
    """
    lignes: List[str] = []
    lignes.append("# Vérification des briques techniques")
    lignes.append("")
    lignes.append(f"*Date UTC* : {date_utc}")
    lignes.append(f"*Commit* : {commit}")
    lignes.append("")

    # Compte par état
    compte_etat: Dict[str, int] = {"presente": 0, "partielle": 0, "absente": 0}
    for info in resultat["briques"].values():
        compte_etat[info["etat"]] += 1
    lignes.append("## Répartition par état")
    lignes.append("")
    for etat in ["presente", "partielle", "absente"]:
        lignes.append(f"* {etat.capitalize()} : {compte_etat[etat]}")
    lignes.append("")

    # Listes de problèmes
    def _liste_section(titre: str, items: List[str]) -> None:
        lignes.append(f"## {titre}")
        lignes.append("")
        if items:
            for it in items:
                lignes.append(f"- {it}")
        else:
            lignes.append("Aucun problème.")
        lignes.append("")

    _liste_section("Termes exigés non classés", resultat["non_classes"])
    _liste_section("Briques sans sujet ouvert", resultat["sans_sujet"])
    _liste_section("Sujets référencés inconnus", resultat["sujets_inconnus"])

    # Tableau des briques non présentes
    lignes.append("## Briques non présentes")
    lignes.append("")
    lignes.append("| Brique | État | Preuve ou sujet |")
    lignes.append("|---|---|---|")
    # Trier d'abord par état puis par nom
    briques_a_lister = [
        (nom, info) for nom, info in resultat["briques"].items() if info["etat"] != "presente"
    ]
    briques_a_lister.sort(key=lambda x: (x[1]["etat"], x[0]))
    for nom, info in briques_a_lister:
        lignes.append(f"| {nom} | {info['etat']} | {info['preuve']} |")
    lignes.append("")

    return "\n".join(lignes)


# --------------------------------------------------------------------------- #
# 6. Fonction principale
# --------------------------------------------------------------------------- #

def main() -> int:
    """Parse les arguments, exécute la vérification et écrit le rapport."""
    parser = argparse.ArgumentParser(
        description="Vérifie la conformité des exigences et des briques techniques."
    )
    parser.add_argument(
        "--racine",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Répertoire racine du dépôt (défaut le répertoire parent de tools/).",
    )
    parser.add_argument(
        "--rapport",
        type=Path,
        default=Path("docs/evidence/briques.md"),
        help="Chemin du fichier de rapport Markdown (défaut docs/evidence/briques.md).",
    )
    args = parser.parse_args()

    racine: Path = args.racine.resolve()
    resultat = verifier(racine)

    date_utc = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    commit = _obtenir_commit()
    markdown = rapport_markdown(resultat, date_utc, commit)

    # Écriture du rapport
    args.rapport.parent.mkdir(parents=True, exist_ok=True)
    args.rapport.write_text(markdown, encoding="utf-8")

    # Affichage d’un résumé
    print("\n".join([
        f"Non classés : {len(resultat['non_classes'])}",
        f"Sans sujet : {len(resultat['sans_sujet'])}",
        f"Sujets inconnus : {len(resultat['sujets_inconnus'])}",
    ]))

    # Code de sortie : 1 s’il existe au moins un problème
    return 1 if resultat["non_classes"] or resultat["sans_sujet"] or resultat["sujets_inconnus"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
