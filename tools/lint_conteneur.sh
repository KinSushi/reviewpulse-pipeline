#!/bin/sh
# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
# Passe `ruff` sur tout l'arbre, dans l'image de dev, AVANT un envoi -- sans rien installer sur l'hote.
#
# Quoi     : lance `ruff check` sur src, tests, dags, dashboard et tools dans un conteneur
#            `reviewpulse-dev`, le depot monte en lecture seule, attend la fin, rend le verdict.
# Pourquoi : le 21/09/2026, une version de `rollback.py` rendue par un arbitre a franchi les cinq
#            portes locales et rougi la CI : `except MlflowException as exc` laisse sans emploi
#            (F841). La porte d'equivalence tolere ce nom quand il ne sert qu'au journal ; `ruff`,
#            lui, le refuse quand il ne sert plus a rien. `ruff` n'est pas installe sur l'hote, et
#            rien ne doit l'etre : la CI etait donc le premier endroit ou il tournait. Un defaut
#            trouve en CI coute un aller-retour de dix minutes ; trouve ici, une minute.
# Ou       : a la racine du depot, sur la machine de developpement (Docker requis).
# Comment  : sh tools/lint_conteneur.sh
#            Rend le code de `ruff`. Le conteneur est lance detache et nomme, jamais `--rm` : sur
#            cette machine un `docker run --rm` reste suspendu a l'arret (voir le runbook).
set -u

NOM="rp-lint-$$"
RACINE="$(pwd)"
if command -v cygpath >/dev/null 2>&1; then RACINE="$(cygpath -m "${RACINE}")"; fi

MSYS_NO_PATHCONV=1 docker run -d --name "${NOM}" -v "${RACINE}:/depot:ro" reviewpulse-dev:latest \
    sh -c "cd /depot && ruff check --no-cache src tests dags dashboard tools" > /dev/null || exit 2

code="$(docker wait "${NOM}")"
docker logs "${NOM}" 2>&1 | tail -n 40
docker rm "${NOM}" > /dev/null 2>&1
exit "${code}"
