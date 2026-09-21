#!/bin/sh
# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
# Delegue une tache au banc de modeles gratuits, standard du projet inclus.
#
# Quoi     : enveloppe nexus_agent.py en y injectant toujours tools/standard_agent.txt
#            par --systeme. Tous les autres arguments sont passes tels quels.
# Pourquoi : jusqu'au 20/09/2026, chaque tache partait SANS consigne de projet. Les modeles
#            travaillaient a leur maniere et l'audit rattrapait ensuite -- il rattrapait
#            souvent, mais rattraper coute plus cher que prescrire. Un standard qu'on ne
#            transmet pas n'est pas un standard. Cette enveloppe rend l'heritage mecanique
#            au lieu de declaratif.
# Ou       : s'execute a la racine du depot ReviewPulse.
# Comment  : sh tools/deleguer.sh --lot lot.json --parallele 2 --sortie sortie.jsonl
#            sh tools/deleguer.sh --tache "..." --fichiers a.py b.py --modele <alias>
#
# Note : --competence et --systeme s'excluent du cote du banc. Si l'appelant passe
#        --competence, cette enveloppe n'injecte PAS le standard et le dit, plutot que de
#        produire une commande silencieusement invalide.
set -u

BANC="C:/local-llm-docker/scripts/nexus_agent.py"
STANDARD="tools/standard_agent.txt"

if [ ! -f "${STANDARD}" ]; then
    echo "ABSENT : ${STANDARD}. Le standard du projet est introuvable, je refuse de deleguer sans lui." >&2
    exit 1
fi

for arg in "$@"; do
    if [ "$arg" = "--competence" ]; then
        echo "NOTE : --competence fournit deja une consigne systeme ; le standard du projet n'est pas injecte." >&2
        exec python "${BANC}" "$@"
    fi
done

exec python "${BANC}" --systeme "$(cat "${STANDARD}")" "$@"
