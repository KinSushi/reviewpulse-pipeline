#!/bin/sh
# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
# La seule commande du jour J : lever la pile, attendre qu'elle soit chaude, verifier qu'elle est prete.
#
# Quoi     : `docker compose up -d` sans reconstruction (airflow compris), attente de /health avec
#            un delai large, puis tools/prevol_demo.sh qui rend PRET ou PAS PRET.
# Pourquoi : le premier appel apres un demarrage charge le modele -- jusqu'a trois minutes sur ce
#            disque (190 s mesures le 21/09/2026). Une demonstration ouverte sur une pile froide
#            commence par un silence. Et une pile levee n'est pas une pile coherente : le controle
#            avant vol a deja trouve un tableau de bord sur un modele perime et une interface morte.
# Comment  : sh tools/jour_j.sh   -- quinze minutes avant de passer, puis ne plus rien toucher.
set -u
cd "$(dirname "$0")/.." || exit 2
if [ -z "${REVIEWPULSE_SALT:-}" ] && [ -f .env ]; then
    # Le sel n'est jamais affiche : on charge .env sans l'echo.
    set -a; . ./.env; set +a
fi
echo "1. Lever la pile (sans reconstruire)"
docker compose --profile airflow up -d --no-build 2>&1 | tail -n 6
echo "2. Attendre que l'API soit chaude (jusqu'a 6 min)"
n=0
until curl -s -o /dev/null -w '%{http_code}' --max-time 300 http://localhost:8000/health | grep -q 200; do
    n=$((n + 1)); [ "$n" -ge 12 ] && { echo "   l'API ne repond pas apres 6 min : PAS PRET"; exit 1; }
    sleep 30
done
echo "   API en ligne."
# Airflow demarre apres l API : le 23/09, le controle avant vol l a trouve a froid et a rendu PAS PRET a tort.
echo "2b. Attendre l'interface et le planificateur d'Airflow (jusqu'a 10 min)"
n=0
until curl -s --max-time 30 http://localhost:8080/health | grep -q '"scheduler": {[^}]*"status": "healthy"'; do
    n=$((n + 1)); [ "$n" -ge 20 ] && { echo "   Airflow ne repond pas apres 10 min : PAS PRET"; exit 1; }
    sleep 30
done
echo "   Airflow en ligne."
echo "3. Controle avant vol"
sh tools/prevol_demo.sh
