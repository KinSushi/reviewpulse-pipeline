#!/bin/sh
# Applique un lot d'enrichissements de code, un module a la fois, derriere la porte
# d'equivalence -- jamais sans elle.
#
# Quoi     : lit le JSONL rendu par le banc, extrait pour chaque tache le fichier complet entre
#            <<<CREER>>> et <<<FIN>>>, le compare au fichier courant par
#            tools/verifier_equivalence.sh, et ne remplace l'original QUE si la logique est
#            identique. Chaque original remplace est d'abord copie en quarantaine, date.
# Pourquoi : l'enrichissement (docstrings, journaux, commentaires) est produit par un modele
#            local qui reecrit des fichiers entiers. Sans porte, une divergence de logique
#            passerait avec l'explication. Avec la porte, elle est nommee et refusee. Et sans
#            copie prealable, un remplacement serait irreversible : regle d'Enzo, rien ne se
#            supprime, tout se deplace avec une trace.
# Ou       : s'execute a la racine du depot.
# Comment  : sh tools/appliquer_enrichissement.sh <sortie.jsonl>
#            Rend 0 si chaque tache a ete appliquee ou refusee proprement, 1 si une extraction
#            a echoue. Le lint et les tests se passent ensuite, sur la vague entiere.
set -u

if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
    echo "usage : sh tools/appliquer_enrichissement.sh <sortie.jsonl>" >&2
    exit 2
fi

JSONL="$1"
QUARANTAINE="/d/ReviewPulse_work/quarantaine/$(date +%Y%m%d)"
mkdir -p "${QUARANTAINE}"
JOURNAL="/d/ReviewPulse_work/quarantaine/JOURNAL.md"
code=0

python - "$JSONL" > /tmp/enrichissement_plan.txt <<'PY'
import json, re, sys, pathlib
for ligne in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines():
    d = json.loads(ligne)
    if "texte" not in d:
        continue
    nom = d.get("nom", "?")
    joints = d.get("fichiers_joints") or []
    cible = joints[0]["chemin"] if joints else ""
    m = re.search(r"<<<CREER>>+\s*\n(.*?)\n\s*<<<FIN>>+", d["texte"], re.S)
    if not m or not cible:
        print("REFUS\t%s\t%s\tmarqueurs ou cible absents" % (nom, cible))
        continue
    corps = m.group(1)
    # Un modele qui entoure le fichier d'une cloture de code : on la retire.
    corps = re.sub(r"^```[a-z]*\n", "", corps)
    corps = re.sub(r"\n```\s*$", "", corps)
    tmp = pathlib.Path("/tmp/enrichi_" + nom + ".py")
    tmp.write_text(corps + ("\n" if not corps.endswith("\n") else ""), encoding="utf-8")
    print("CANDIDAT\t%s\t%s\t%s" % (nom, cible, tmp))
PY

while IFS="$(printf '\t')" read -r statut nom cible tmp; do
    case "$statut" in
        REFUS)
            echo "REFUS      ${nom} : ${tmp}"
            code=1
            ;;
        CANDIDAT)
            if [ ! -f "${cible}" ]; then
                echo "REFUS      ${nom} : cible ${cible} introuvable"
                code=1
                continue
            fi
            if python -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" "${tmp}" 2>/dev/null; then
                :
            else
                echo "REFUS      ${nom} : le rendu n'est pas du Python valide"
                continue
            fi
            if sh tools/verifier_equivalence.sh "${cible}" "${tmp}" > /tmp/eq_${nom}.txt 2>&1; then
                copie="${QUARANTAINE}/$(echo "${cible}" | tr '/' '_').avant_enrichissement"
                cp "${cible}" "${copie}"
                printf '| %s | `%s` | `%s` | Original avant enrichissement par le banc local ; logique prouvee identique par `verifier_equivalence.sh` | `cp` inverse |\n' \
                    "$(date +%d/%m/%Y)" "$(basename "${copie}")" "${cible}" >> "${JOURNAL}"
                cp "${tmp}" "${cible}"
                echo "APPLIQUE   ${nom} -> ${cible}"
            else
                echo "DIVERGENT  ${nom} : logique changee, NON applique"
                sed -n '2,3p' "/tmp/eq_${nom}.txt"
            fi
            ;;
    esac
done < /tmp/enrichissement_plan.txt
exit "$code"
