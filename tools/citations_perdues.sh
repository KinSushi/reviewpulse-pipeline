#!/bin/sh
# Refuse un enrichissement qui fait disparaitre une citation presente dans l'original.
#
# Quoi     : compare les citations d'ADR (`ADR 0004`), de tests (`test_boost.py`) et d'entrees du
#            registre (`R55`) entre deux versions d'un fichier, et nomme celles que la nouvelle
#            version a perdues.
# Pourquoi : le 20/09/2026, le banc local a reecrit la docstring de `transform.py` avec une
#            structure Quoi / Pourquoi / Ou / Comment... et a laisse tomber les sections
#            « Preuves » et « Tests associes ». La porte d'equivalence ne le voit pas : une
#            docstring n'execute rien. Or ces citations sont ce que `verifier_justifications.py`
#            controle, et ce qu'un jury lit. Une explication qui perd des preuves n'enrichit pas.
# Ou       : appele par tools/appliquer_enrichissement.sh avant la porte d'equivalence ; utilisable
#            seul, a la racine du depot.
# Comment  : sh tools/citations_perdues.sh <ancien> <nouveau>
#            Rend 0 et n'ecrit rien si aucune citation n'est perdue ; rend 1 et ecrit la liste
#            des citations perdues sur la sortie standard sinon.
set -u

if [ "$#" -ne 2 ]; then
    echo "usage : sh tools/citations_perdues.sh <ancien> <nouveau>" >&2
    exit 2
fi

python - "$1" "$2" <<'PY'
import pathlib
import re
import sys

MOTIFS = (
    re.compile(r"ADR [0-9]{4}"),
    re.compile(r"test_[a-z0-9_]+[.]py"),
    re.compile(r"(?<![A-Za-z0-9])R[0-9]{2}(?![0-9])"),
)


def citations(chemin):
    texte = pathlib.Path(chemin).read_text(encoding="utf-8", errors="replace")
    return {c for motif in MOTIFS for c in motif.findall(texte)}


perdues = sorted(citations(sys.argv[1]) - citations(sys.argv[2]))
if perdues:
    print(", ".join(perdues))
    sys.exit(1)
sys.exit(0)
PY
