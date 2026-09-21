#!/bin/sh
# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
# Refuse une version d'un module qui explique MOINS que celle qu'elle remplace.
#
# Quoi     : compare deux versions d'un fichier Python sur trois mesures -- le nombre d'appels de
#            journal, le nombre de commentaires de raisonnement (« Pourquoi : », « Comment : »),
#            et la taille. Trois refus :
#            - un appel de journal a disparu ;
#            - les commentaires de raisonnement ont chute de plus d'un cinquieme ;
#            - le fichier a fondu (moins de 0,9 fois) ou enfle (plus de 2,5 fois).
# Pourquoi : le 21/09/2026, des modeles charges d'ARBITRER des constats de relecture -- donc de
#            corriger des commentaires -- ont rendu des fichiers amaigris : huit « Pourquoi » sur
#            huit effaces dans `expectations.py`, six journaux retires de `train.py`, un module
#            reduit d'un quart. La porte d'equivalence ne le voit pas : ni un journal ni un
#            commentaire n'est de la logique. Supprimer une paraphrase est permis, d'ou la marge
#            d'un cinquieme ; vider l'explication ne l'est pas.
# Ou       : appele par tools/appliquer_enrichissement.sh avant la porte d'equivalence ; utilisable
#            seul, a la racine du depot.
# Comment  : sh tools/explication_appauvrie.sh <ancien> <nouveau>
#            Rend 0 et n'ecrit rien si la nouvelle version n'appauvrit rien ; rend 1 et nomme le
#            motif sur la sortie standard sinon.
set -u

if [ "$#" -ne 2 ]; then
    echo "usage : sh tools/explication_appauvrie.sh <ancien> <nouveau>" >&2
    exit 2
fi

python - "$1" "$2" <<'PY'
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MOTIF_JOURNAL = re.compile(r"(?:logger|_logger|log|LOGGER|logging)[.](?:debug|info|warning|error|exception|critical)[(]")
MOTIF_RAISON = re.compile(r"Pourquoi ?:|Comment ?:")

ancien = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
nouveau = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")

j_avant, j_apres = len(MOTIF_JOURNAL.findall(ancien)), len(MOTIF_JOURNAL.findall(nouveau))
r_avant, r_apres = len(MOTIF_RAISON.findall(ancien)), len(MOTIF_RAISON.findall(nouveau))
rapport = len(nouveau) / max(1, len(ancien))

if j_apres < j_avant:
    print("journaux retires (%d -> %d)" % (j_avant, j_apres))
    sys.exit(1)
if r_apres < 0.8 * r_avant:
    print("raisonnement appauvri (%d -> %d commentaires Pourquoi / Comment)" % (r_avant, r_apres))
    sys.exit(1)
if not 0.9 <= rapport <= 2.5:
    print("taille hors bornes (x %.2f)" % rapport)
    sys.exit(1)
sys.exit(0)
PY
