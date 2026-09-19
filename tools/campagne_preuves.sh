#!/bin/sh
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
HORODATAGE=$(date -u +%Y%m%d-%H%M%S)
JOURNAL="${JOURNAL_DIR}/campagne_${HORODATAGE}.log"
mkdir -p "${JOURNAL_DIR}"

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
    timeout --signal=TERM --kill-after=60 "$budget" stdbuf -oL -eL "$@" 2>&1 | tee -a "${JOURNAL}"
    code=$?
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

# La batterie tourne sur une copie neuve : un test qui écrirait dans le dépôt
# fausserait la mesure suivante.
COPIE=$(mktemp -d /tmp/campagne.XXXXXX)
cp -r /app/src /app/tests /app/dashboard /app/dags /app/dbt "${COPIE}/"
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
