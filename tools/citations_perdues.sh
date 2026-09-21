#!/bin/sh
# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
# Refuse un enrichissement qui perd une citation de l'original, ou qui en invente une.
#
# Quoi     : compare les citations d'ADR (`ADR 0004`), de tests (`test_boost.py`) et d'entrees du
#            registre (`R55`) entre deux versions d'un fichier. Deux refus possibles :
#            - PERDUE   : une citation de l'original a disparu de la nouvelle version ;
#            - INVENTEE : la nouvelle version cite un ADR, un test ou une entree de registre qui
#                         n'existe pas dans le depot.
# Pourquoi : le 20/09/2026, le banc a reecrit la docstring de `transform.py` en laissant tomber
#            ses sections « Preuves » et « Tests associes ». La porte d'equivalence ne le voit
#            pas : une docstring n'execute rien. Or ces citations sont ce que
#            `verifier_justifications.py` controle, et ce qu'un jury lit. L'invention est le
#            defaut symetrique : un modele qui redige un « Pourquoi » cite volontiers une decision
#            plausible qui n'a jamais ete prise. Une citation se prouve par l'existence du fichier.
# Ou       : appele par tools/appliquer_enrichissement.sh avant la porte d'equivalence ; utilisable
#            seul, a la racine du depot.
# Comment  : sh tools/citations_perdues.sh <ancien> <nouveau>
#            Rend 0 et n'ecrit rien si tout est conserve et rien n'est invente ; rend 1 et nomme
#            les citations fautives sur la sortie standard sinon.
set -u

if [ "$#" -ne 2 ]; then
    echo "usage : sh tools/citations_perdues.sh <ancien> <nouveau>" >&2
    exit 2
fi

python - "$1" "$2" <<'PY'
import pathlib
import re
import sys

MOTIF_ADR = re.compile(r"ADR [0-9]{4}")
MOTIF_TEST = re.compile(r"test_[a-z0-9_]+[.]py")
MOTIF_REGISTRE = re.compile(r"(?<![A-Za-z0-9])R[0-9]{2}(?![0-9])")
MOTIFS = (MOTIF_ADR, MOTIF_TEST, MOTIF_REGISTRE)


def citations(chemin):
    texte = pathlib.Path(chemin).read_text(encoding="utf-8", errors="replace")
    return {c for motif in MOTIFS for c in motif.findall(texte)}


def existe(citation):
    """Une citation existe si le depot porte le fichier ou la ligne qu'elle designe."""
    if MOTIF_ADR.fullmatch(citation):
        return any(pathlib.Path("docs/adr").glob(citation.split()[1] + "-*.md"))
    if MOTIF_TEST.fullmatch(citation):
        return any(pathlib.Path("tests").rglob(citation))
    registre = pathlib.Path("docs/16_registre_suivi.md")
    return registre.exists() and ("| " + citation + " |") in registre.read_text(encoding="utf-8", errors="replace")


avant, apres = citations(sys.argv[1]), citations(sys.argv[2])
perdues = sorted(avant - apres)
inventees = sorted(c for c in apres - avant if not existe(c))
messages = []
if perdues:
    messages.append("perdues : " + ", ".join(perdues))
if inventees:
    messages.append("inventees : " + ", ".join(inventees))
if messages:
    print(" ; ".join(messages))
    sys.exit(1)
sys.exit(0)
PY
