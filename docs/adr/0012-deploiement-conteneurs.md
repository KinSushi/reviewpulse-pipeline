# ADR 0012 — Déploiement Docker Compose

**Date** : 16/09/2026 · **Statut** : acceptée

## Contexte

Le poste de développement est en Python 3.14, mal supporté par MLflow, Spark et Airflow. La démo doit tourner à l'identique partout. La fiche AIA admet « le cloud ou on-premise ».

## Décision

- Python **3.11** dans toutes les images ; versions figées.
- Docker Compose : `mlflow` (5000), `api` (8000), `dashboard` (8501) ; profils `jobs` (pipeline ponctuel) et `airflow` (8080).
- Utilisateur non-root ; contrôles de santé **propres à chaque service** ; fin de ligne LF imposée par `.gitattributes`.
- Sel lu dans `.env` (facultatif, jamais versionné) ou dans l'environnement.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Environnement virtuel local | Non reproductible chez le jury ; Python 3.14 incompatible |
| Kubernetes | Surdimensionné pour la démo ; la cible cloud est décrite dans le schéma 06 |
| Cloud public dès maintenant | Coût, comptes et secrets à gérer ; reporté après validation locale |

## Preuves (16/09/2026)

- Trois services « healthy » après correction du contrôle de santé du tableau de bord (il interrogeait le port de l'API).
- Parcours utilisateur réel dans un navigateur : saisie d'un avis dans le tableau de bord → API de conteneur à conteneur → « negative (97,90 %, seuil 0,75) ».
- Défauts trouvés en déploiement et corrigés : installation du paquet dans l'image Airflow (disposition `src/` aplatie, filtre `-e .` inopérant), URL de l'API codée en dur dans le tableau de bord.
