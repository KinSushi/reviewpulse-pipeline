# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""tools.verifier_justifications
================================

Ce module fournit un outil en ligne de commande permettant de vérifier que
toutes les décisions d'architecture (ADR) sont correctement citées dans le
code, les réponses aux questions du jury et les diapositives de présentation.

Fonctionnalités principales :
* lecture et indexation des fichiers ADR,
* recherche de citations de la forme ``ADR 0004`` ou ``ADR0004`` (insensible à la casse),
* détection des ADR orphelins (non citées) et des références fantômes (citéses mais inexistantes),
* génération d’un rapport Markdown détaillé,
* code de sortie : ``1`` s’il existe au moins un problème, ``0`` sinon.
"""

from __future__ import annotations

import argparse
import datetime
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Lecture des ADR
# --------------------------------------------------------------------------- #
def lire_adrs(racine: Path) -> List[Dict]:
    """
    Parcourt ``docs/adr`` et retourne la liste des ADR.

    Chaque entrée est un dictionnaire ``{"numero": "0004", "titre": "...", "chemin": Path}``,
    triée par numéro croissant.

    Raises:
        ValueError: si un fichier ADR ne commence pas par la ligne attendue.
    """
    adr_dir = racine / "docs" / "adr"
    adrs: List[Dict] = []

    for chemin in sorted(adr_dir.glob("*.md")):
        if chemin.name.lower() == "readme.md":
            continue
        try:
            première_ligne = chemin.read_text(encoding="utf-8").splitlines()[0].strip()
        except Exception as exc:
            logger.warning("Impossible de lire %s : %s", chemin, exc)
            continue

        match = re.match(r"^# ADR (\d{4})\s*—\s*(.+)$", première_ligne)
        if not match:
            raise ValueError(
                f"Le fichier {chemin} ne commence pas par '# ADR NNNN — <titre>'"
            )
        numero, titre = match.group(1), match.group(2)
        adrs.append({"numero": numero, "titre": titre, "chemin": chemin})

    adrs.sort(key=lambda d: d["numero"])
    return adrs


# --------------------------------------------------------------------------- #
# Recherche de citations
# --------------------------------------------------------------------------- #
def citations(motifs: List[str], racine: Path) -> Dict[str, int]:
    """
    Retourne le nombre de citations d'ADR pour chaque numéro trouvé dans les fichiers
    correspondant aux motifs glob fournis.

    Reconnaît trois formes de citation :
    - ``ADR 0013`` : un seul numéro ;
    - ``ADR 0013, 0014 et 0017`` : liste de numéros, séparés par virgules, le mot « et » ou les deux,
      insensible à la casse ;
    - ``ADR 0001 a 0020``, ``ADR 0001 à 0020`` ou ``ADR 0001-0020`` : plage couvrant tous les numéros
      entre la borne basse et la borne haute incluses.

    La lecture s’arrête au premier élément qui n’est ni un nombre à quatre chiffres,
    ni un séparateur autorisé. Une plage dont la borne haute est inférieure à la borne basse
    est ignorée avec un avertissement. Les plages de plus de 50 numéros sont également ignorées
    et journalisées.

    Les fichiers illisibles sont ignorés mais journalisés.
    """
    compteur: Dict[str, int] = {}

    # Expression régulière qui capture tout le texte suivant « ADR » jusqu’au premier
    # caractère non autorisé (ni chiffre à 4 chiffres, ni séparateur). Elle permet de
    # récupérer une chaîne contenant soit un seul numéro, soit une liste, soit une plage.
    adr_pattern = re.compile(
        r"ADR\s*([0-9]{4}(?:\s*(?:,|et|,?\s*et\s*)\s*[0-9]{4})*(?:\s*(?:a|à|-)\s*[0-9]{4})?)",
        re.IGNORECASE,
    )

    for motif in motifs:
        for chemin in racine.glob(motif):
            if not chemin.is_file():
                continue
            try:
                texte = chemin.read_text(encoding="utf-8")
            except Exception as exc:
                logger.warning("Impossible de lire %s : %s", chemin, exc)
                continue

            for match in adr_pattern.finditer(texte):
                suite = match.group(1)

                # Gestion d’une plage éventuelle
                if re.search(r"\s*(?:a|à|-)\s*", suite, re.IGNORECASE):
                    borne_basse, borne_haute = re.split(r"\s*(?:a|à|-)\s*", suite, maxsplit=1, flags=re.IGNORECASE)
                    if not (re.fullmatch(r"\d{4}", borne_basse) and re.fullmatch(r"\d{4}", borne_haute)):
                        continue
                    debut = int(borne_basse)
                    fin = int(borne_haute)
                    if fin < debut:
                        logger.warning(
                            "Plage ADR invalide (borne haute < borne basse) : %s – ignorée.", suite
                        )
                        continue
                    if fin - debut + 1 > 50:
                        logger.warning(
                            "Plage ADR trop large (>50 numéros) : %s – ignorée.", suite
                        )
                        continue
                    for num in range(debut, fin + 1):
                        numero = f"{num:04d}"
                        compteur[numero] = compteur.get(numero, 0) + 1
                    continue

                # Gestion d’une liste (ou d’un seul numéro)
                # Séparateurs possibles : virgule, le mot « et », ou les deux.
                parties = re.split(r"\s*(?:,|et)\s*", suite, flags=re.IGNORECASE)
                for part in parties:
                    if re.fullmatch(r"\d{4}", part):
                        numero = part
                        compteur[numero] = compteur.get(numero, 0) + 1

    return compteur


# --------------------------------------------------------------------------- #
# Vérification globale
# --------------------------------------------------------------------------- #
def verifier(racine: Path) -> Dict:
    """
    Assemble les informations d'ADR et les citations.

    Retourne un dictionnaire contenant :
    * ``adrs`` : liste des ADR (voir :func:`lire_adrs`),
    * ``citations_code`` : dict des citations dans le code,
    * ``citations_questions`` : dict des citations dans les Q‑R,
    * ``citations_slides`` : dict des citations dans les diapositives,
    * ``orphelins`` : liste des numéros d'ADR non cités dans le code ni les Q‑R,
    * ``fantomes`` : liste des numéros cités alors qu'aucune ADR ne les possède.
    """
    adrs = lire_adrs(racine)

    # « Code » au sens large : tout fichier que quelqu'un ouvrira pour comprendre
    # comment la décision est appliquée. Une décision d'infrastructure vit dans le
    # compose ou dans un Dockerfile, pas dans un module Python.
    motifs_code = [
        "src/reviewpulse/**/*.py",
        "dags/**/*.py",
        "tools/**/*.py",
        "dashboard/**/*.py",
        "docker-compose.yml",
        "docker/*.Dockerfile",
        "Makefile",
        "requirements.txt",
        ".github/workflows/*.yml",
        "dbt/models/**/*.sql",
        "dbt/models/**/*.yml",
    ]
    motifs_questions = ["docs/07_questions_jury.md"]
    motifs_slides = ["docs/presentation/**/*.json"]

    citations_code = citations(motifs_code, racine)
    citations_questions = citations(motifs_questions, racine)
    citations_slides = citations(motifs_slides, racine)

    numeros_adrs = {a["numero"] for a in adrs}
    cites_totaux = set(citations_code) | set(citations_questions) | set(citations_slides)

    orphelins = sorted(
        [
            num
            for num in numeros_adrs
            if citations_code.get(num, 0) + citations_questions.get(num, 0) == 0
        ]
    )
    fantomes = sorted([num for num in cites_totaux if num not in numeros_adrs])

    return {
        "adrs": adrs,
        "citations_code": citations_code,
        "citations_questions": citations_questions,
        "citations_slides": citations_slides,
        "orphelins": orphelins,
        "fantomes": fantomes,
    }


# --------------------------------------------------------------------------- #
# Génération du rapport Markdown
# --------------------------------------------------------------------------- #
def rapport_markdown(resultat: Dict, date_utc: str, commit: str) -> str:
    """
    Construit le rapport Markdown à partir du résultat de :func:`verifier`.

    Le tableau possède les colonnes : ADR, titre, code, questions, diapositives.
    Les sections « Orphelins » et « Fantômes » listent les numéros concernés,
    suivies d’un récapitulatif des totaux.
    """
    lignes = []
    lignes.append("# Justifications des décisions d'architecture")
    lignes.append("")
    lignes.append(f"*Date UTC* : {date_utc}")
    lignes.append(f"*Commit* : {commit}")
    lignes.append("")
    lignes.append("| ADR | titre | code | questions | diapositives |")
    lignes.append("|-----|-------|------|-----------|--------------|")

    for adr in resultat["adrs"]:
        num = adr["numero"]
        titre = adr["titre"]
        code_cnt = resultat["citations_code"].get(num, 0)
        ques_cnt = resultat["citations_questions"].get(num, 0)
        slide_cnt = resultat["citations_slides"].get(num, 0)
        lignes.append(f"| {num} | {titre} | {code_cnt} | {ques_cnt} | {slide_cnt} |")

    lignes.append("")
    if resultat["orphelins"]:
        lignes.append("## Orphelins")
        lignes.append("")
        lignes.append(", ".join(resultat["orphelins"]))
        lignes.append("")
    if resultat["fantomes"]:
        lignes.append("## Fantômes")
        lignes.append("")
        lignes.append(", ".join(resultat["fantomes"]))
        lignes.append("")

    total_code = sum(resultat["citations_code"].values())
    total_ques = sum(resultat["citations_questions"].values())
    total_slides = sum(resultat["citations_slides"].values())
    lignes.append("## Totaux")
    lignes.append("")
    lignes.append(f"* Citations dans le code : {total_code}")
    lignes.append(f"* Citations dans les questions‑réponses : {total_ques}")
    lignes.append(f"* Citations dans les diapositives : {total_slides}")
    lignes.append("")

    return "\n".join(lignes)


# --------------------------------------------------------------------------- #
# Fonction principale
# --------------------------------------------------------------------------- #
def _obtenir_commit() -> str:
    """Renvoie le hash court du commit Git ou la variable d'env, ou « inconnu »."""
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


def main() -> int:
    """Parse les arguments, exécute la vérification et écrit le rapport."""
    parser = argparse.ArgumentParser(
        description="Vérifie que chaque ADR est correctement justifiée."
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
        default=Path("docs/evidence/justifications.md"),
        help="Chemin du fichier de rapport Markdown (défaut docs/evidence/justifications.md).",
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

    # Affichage du tableau (première partie du markdown)
    print("\n".join(markdown.splitlines()[: len(resultat["adrs"]) + 5]))

    # Code de sortie : 1 s’il existe orphelins ou fantômes
    return 1 if resultat["orphelins"] or resultat["fantomes"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
