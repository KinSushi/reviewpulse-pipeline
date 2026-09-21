#!/bin/sh
# Eprouve les portes elles-memes : une porte qui n'a jamais refuse ne prouve rien.
#
# Quoi     : fabrique de petits fichiers temoins et exige de chaque porte le verdict attendu --
#            `verifier_equivalence.sh` (dix temoins), `citations_perdues.sh` (trois),
#            `verifier_journaux.sh` (trois). Chaque regle de tolerance a son temoin dans les deux
#            sens : le cas qu'elle doit laisser passer, et le cas voisin qu'elle doit refuser.
# Pourquoi : ces portes decident seules de ce qui entre dans le depot quand un modele reecrit
#            un module. Elles ont ete assouplies quatre fois le 20 et le 21/09/2026 (noms de
#            journal, ordre des imports, `except ... as exc`, bloc conditionnel de pur journal).
#            Chaque assouplissement est un risque : sans temoin du refus voisin, une tolerance
#            devient un trou. Ce script est la non-regression des portes.
# Ou       : a la racine du depot ; appele par la campagne de preuves et par la CI.
# Comment  : sh tools/tester_portes.sh      -- rend 0 si les seize verdicts sont les bons.
set -u

T="$(mktemp -d)"
if command -v cygpath >/dev/null 2>&1; then T="$(cygpath -m "${T}")"; fi
echecs=0

attendre() {  # attendre <libelle> <code_attendu> <commande...>
    libelle="$1"; attendu="$2"; shift 2
    "$@" > "${T}/sortie.txt" 2>&1
    obtenu=$?
    if [ "${obtenu}" -eq "${attendu}" ]; then
        echo "ok      ${libelle}"
    else
        echo "ECHEC   ${libelle} : code ${obtenu}, attendu ${attendu}"
        echecs=$((echecs + 1))
    fi
}

# --- Porte d'equivalence -------------------------------------------------------------------
cat > "${T}/base.py" <<'EOF'
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def f(x, g):
    """Role."""
    try:
        y = int(x)
    except ValueError:
        pass
    return Path(os.sep) / str(x)
EOF

cat > "${T}/journal_ajoute.py" <<'EOF'
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def f(x, g):
    """Role. Pourquoi : temoin."""
    logger.info("entree recue")
    try:
        y = int(x)
    except ValueError as exc:
        logging.getLogger(__name__).warning("valeur illisible : %s", exc)
    if not x or len(x) == 0:
        logger.warning("entree vide")
    return Path(os.sep) / str(x)
EOF

cat > "${T}/imports_reordonnes.py" <<'EOF'
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


def f(x, g):
    """Role."""
    try:
        y = int(x)
    except ValueError:
        pass
    return Path(os.sep) / str(x)
EOF

cat > "${T}/import_retire.py" <<'EOF'
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def f(x, g):
    """Role."""
    try:
        y = int(x)
    except ValueError:
        pass
    return Path(os.sep) / str(x)
EOF

cat > "${T}/variable_ajoutee.py" <<'EOF'
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def f(x, g):
    """Role."""
    try:
        y = int(x)
    except ValueError:
        pass
    resultat = Path(os.sep) / str(x)
    return resultat
EOF

cat > "${T}/instruction_supprimee.py" <<'EOF'
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def f(x, g):
    """Role."""
    return Path(os.sep) / str(x)
EOF

cat > "${T}/exc_relu.py" <<'EOF'
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def f(x, g):
    """Role."""
    try:
        y = int(x)
    except ValueError as exc:
        raise RuntimeError(str(exc))
    return Path(os.sep) / str(x)
EOF

cat > "${T}/condition_avec_appel.py" <<'EOF'
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def f(x, g):
    """Role."""
    try:
        y = int(x)
    except ValueError:
        pass
    if g(x):
        logger.warning("chemin degrade")
    return Path(os.sep) / str(x)
EOF

cat > "${T}/print_ajoute.py" <<'EOF'
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def f(x, g):
    """Role."""
    try:
        y = int(x)
    except ValueError:
        pass
    print("termine")
    return Path(os.sep) / str(x)
EOF

cat > "${T}/appel_non_journal.py" <<'EOF'
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def f(x, g):
    """Role."""
    try:
        y = int(x)
    except ValueError:
        pass
    logging.shutdown()
    return Path(os.sep) / str(x)
EOF

E="tools/verifier_equivalence.sh"
attendre "equivalence : identique a lui-meme"                          0 sh "$E" "${T}/base.py" "${T}/base.py"
attendre "equivalence : journaux, except as exc, if de pur journal"    0 sh "$E" "${T}/base.py" "${T}/journal_ajoute.py"
attendre "equivalence : imports de tete reordonnes"                    0 sh "$E" "${T}/base.py" "${T}/imports_reordonnes.py"
attendre "equivalence : import retire -> refus"                        1 sh "$E" "${T}/base.py" "${T}/import_retire.py"
attendre "equivalence : variable intermediaire -> refus"               1 sh "$E" "${T}/base.py" "${T}/variable_ajoutee.py"
attendre "equivalence : instruction supprimee -> refus"                1 sh "$E" "${T}/base.py" "${T}/instruction_supprimee.py"
attendre "equivalence : nom d'exception relu par le corps -> refus"    1 sh "$E" "${T}/base.py" "${T}/exc_relu.py"
attendre "equivalence : condition avec appel inconnu -> refus"         1 sh "$E" "${T}/base.py" "${T}/condition_avec_appel.py"
attendre "equivalence : print ajoute -> refus"                         1 sh "$E" "${T}/base.py" "${T}/print_ajoute.py"
attendre "equivalence : appel logging non journal -> refus"            1 sh "$E" "${T}/base.py" "${T}/appel_non_journal.py"

# --- Porte des citations -------------------------------------------------------------------
printf '%s\n' '"""Voir ADR 0004 et test_ingest.py."""' > "${T}/cite.py"
printf '%s\n' '"""Voir ADR 0004."""' > "${T}/cite_perdue.py"
printf '%s\n' '"""Voir ADR 0004, test_ingest.py, ADR 9999 et test_fantome_inexistant.py."""' > "${T}/cite_inventee.py"
printf '%s\n' '"""Voir ADR 0004, test_ingest.py et ADR 0005."""' > "${T}/cite_ajout_legitime.py"
C="tools/citations_perdues.sh"
attendre "citations : citation perdue -> refus"                        1 sh "$C" "${T}/cite.py" "${T}/cite_perdue.py"
attendre "citations : citation inventee -> refus"                      1 sh "$C" "${T}/cite.py" "${T}/cite_inventee.py"
attendre "citations : ajout d'un ADR existant"                         0 sh "$C" "${T}/cite.py" "${T}/cite_ajout_legitime.py"

# --- Porte des journaux --------------------------------------------------------------------
cat > "${T}/journal_propre.py" <<'EOF'
import logging
logger = logging.getLogger(__name__)
def g(df, chemin):
    logger.info("%d lignes lues depuis %s", len(df), chemin)
EOF
cat > "${T}/journal_fuite.py" <<'EOF'
import logging
logger = logging.getLogger(__name__)
def g(df, review_text):
    logger.info("avis recu : %s", review_text)
    logger.warning("jeu de donnees : %s", df)
EOF
cat > "${T}/journal_fstring.py" <<'EOF'
import logging
logger = logging.getLogger(__name__)
def g(n):
    logger.info(f"{n} lignes")
EOF
J="tools/verifier_journaux.sh"
attendre "journaux : comptes et chemins seulement"                     0 sh "$J" "${T}/journal_propre.py"
attendre "journaux : texte d'avis et DataFrame entiers -> refus"       1 sh "$J" "${T}/journal_fuite.py"
attendre "journaux : f-string dans l'appel -> refus"                   1 sh "$J" "${T}/journal_fstring.py"

if [ "${echecs}" -eq 0 ]; then
    echo "Portes : seize verdicts sur seize conformes."
    exit 0
fi
echo "Portes : ${echecs} verdict(s) non conforme(s) -- une porte ne juge plus comme elle le doit."
exit 1
