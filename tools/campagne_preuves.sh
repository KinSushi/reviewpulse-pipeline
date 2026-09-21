#!/bin/sh
# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
# Campagne de preuves ReviewPulse — batterie puis tests inverses, en série.
#
# Quoi     : enchaîne compilation, batterie complète et tests inverses, chaque phase
#            sous une garde de temps, et écrit tout dans un journal daté.
# Pourquoi : le 19/09/2026, une campagne a tourné 3 h 09 à 0,13 % de CPU sans que
#            rien ne le montre — la sortie était tuyautée dans « tail », donc
#            invisible jusqu'à la fin, et aucune garde de temps ne l'arrêtait.
#            Trois heures perdues, zéro preuve. Ce script existe pour que cela ne
#            se reproduise plus : progression observable, dépassement bruyant.
# Où       : s'exécute dans l'image reviewpulse-dev, le dépôt monté sous /app.
# Comment  : sh tools/campagne_preuves.sh [répertoire_de_journal]
#            Le code de sortie vaut 0 seulement si toutes les phases passent.
set -u

JOURNAL_DIR="${1:-docs/evidence}"
mkdir -p "${JOURNAL_DIR}"
# Chemin ABSOLU, sans quoi le journal suit le repertoire courant : la batterie tourne
# dans une copie temporaire, ou "docs/evidence" n'existe pas. Le tee echouait alors,
# le tuyau se rompait, et la phase mourait en silence (constate le 19/09/2026).
JOURNAL_DIR=$(cd "${JOURNAL_DIR}" && pwd)
HORODATAGE=$(date -u +%Y%m%d-%H%M%S)
JOURNAL="${JOURNAL_DIR}/campagne_${HORODATAGE}.log"

# Budgets en secondes. Généreux mais finis : un dépassement est un signal, pas un drame.
BUDGET_COMPILE=${BUDGET_COMPILE:-300}
BUDGET_BATTERIE=${BUDGET_BATTERIE:-5400}
BUDGET_INVERSES=${BUDGET_INVERSES:-10800}

code_global=0

phase() {
    nom="$1"
    budget="$2"
    shift 2
    debut=$(date +%s)
    printf '\n=== %s — début %s UTC, budget %ss ===\n' "$nom" "$(date -u +%H:%M:%S)" "$budget" | tee -a "${JOURNAL}"
    # stdbuf force l'écriture au fil de l'eau : sans lui la progression reste dans
    # le tampon, et le journal est vide tant que la phase n'est pas terminée.
    # Le code de sortie est ecrit dans un fichier PUIS relu : apres un tuyau, "$?"
    # rend le statut de tee, jamais celui de la commande. Une batterie rouge etait
    # donc rapportee « code 0 » (constate le 19/09/2026). dash n'a pas pipefail.
    fichier_code=$(mktemp)
    { timeout --signal=TERM --kill-after=60 "$budget" stdbuf -oL -eL "$@" 2>&1; echo $? > "${fichier_code}"; } | tee -a "${JOURNAL}"
    code=$(cat "${fichier_code}")
    rm -f "${fichier_code}"
    duree=$(( $(date +%s) - debut ))
    if [ "$code" -eq 124 ]; then
        printf '=== %s — DÉPASSEMENT DU BUDGET après %ss ===\n' "$nom" "$duree" | tee -a "${JOURNAL}"
    else
        printf '=== %s — code %s en %ss ===\n' "$nom" "$code" "$duree" | tee -a "${JOURNAL}"
    fi
    [ "$code" -eq 0 ] || code_global=1
    return 0
}

printf 'Campagne de preuves ReviewPulse — %s UTC\nCommit : %s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${REVIEWPULSE_COMMIT:-inconnu}" | tee "${JOURNAL}"

phase "compilation" "${BUDGET_COMPILE}" python -m compileall -q src tools dags tests

# Le lint vient APRES la compilation et AVANT la batterie, et ce n'est pas un detail de
# style : la regle F821 de ruff detecte un nom non defini, ce que compileall ne voit pas.
# Mesure du 20/09/2026 : un « import os » manquant dans un outil neuf a compile sans bruit,
# puis tue le script apres sept minutes de calcul, au moment d'ecrire son rapport. Le meme
# defaut avait deja coute six echecs et cinq erreurs dans train.py le 19/09. Le garde
# existait -- la CI et « make lint » lancent ruff sur tools/ -- mais la campagne ne le
# passait pas. « Le code compile » n'est pas « le code fonctionne ».
phase "lint" "${BUDGET_COMPILE}" ruff check src tests dags dashboard tools

# Chaque document numerote doit etre cite par le README, et aucun lien ne doit etre mort.
# Mesure du 20/09/2026 : six documents manquaient a l appel, dont les trois que la consigne
# du Demo Day exige nommement -- rapport de donnees, guide de l API, runbook. Un jury ouvre
# le README en premier ; un livrable qui n y figure pas n existe pas pour lui.
phase "documentation" "${BUDGET_COMPILE}" sh tools/verifier_documentation.sh

# Les portes qui jugent un module reecrit sont eprouvees a chaque campagne : seize temoins,
# chaque tolerance avec le refus voisin (21/09/2026). Puis le controle des journaux : un journal
# est une sortie, aucune donnee issue de personnes ne doit y passer.
phase "portes" "${BUDGET_COMPILE}" sh tools/tester_portes.sh
phase "journaux" "${BUDGET_COMPILE}" sh tools/verifier_journaux.sh
phase "chiffres" "${BUDGET_COMPILE}" sh tools/verifier_chiffres.sh
phase "droit d'auteur" "${BUDGET_COMPILE}" sh tools/copyright.sh verifier

# La batterie tourne sur une copie neuve : un test qui écrirait dans le dépôt
# fausserait la mesure suivante.
COPIE=$(mktemp -d /tmp/campagne.XXXXXX)
# tools/ est recopie aussi : trois fichiers de tests importent les outils qui y vivent,
# et leur absence faisait echouer la collecte de pytest (97 tests, 3 erreurs, 19/09/2026).
cp -r /app/src /app/tests /app/dashboard /app/dags /app/dbt /app/tools "${COPIE}/"
cp /app/pyproject.toml "${COPIE}/"
cd "${COPIE}" || exit 1

# Garde de temps PAR TEST si pytest-timeout est present dans l'image : un test bloque
# echoue alors seul, au lieu d'emporter toute la campagne. Sans la dependance, la garde
# par phase reste le seul filet (registre R41).
OPTIONS_DELAI=""
if python -c "import pytest_timeout" >/dev/null 2>&1; then
    OPTIONS_DELAI="--timeout=900 --timeout-method=thread"
    echo "Garde par test active : ${OPTIONS_DELAI}" | tee -a "${JOURNAL}"
else
    echo "pytest-timeout absent de l'image : garde par phase seulement (R41)" | tee -a "${JOURNAL}"
fi

# shellcheck disable=SC2086
PYTHONPATH="${COPIE}/src" phase "batterie" "${BUDGET_BATTERIE}" \
    python -m pytest -p no:warnings -p no:cacheprovider -rf --durations=10 -v ${OPTIONS_DELAI}
cd /app || exit 1

phase "tests inverses" "${BUDGET_INVERSES}" python tools/reverse_tests.py --timeout 2400

printf '\n=== CAMPAGNE TERMINÉE — code global %s ===\nJournal : %s\n' \
    "$code_global" "${JOURNAL}" | tee -a "${JOURNAL}"
exit "$code_global"
