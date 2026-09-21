# ADR 0018 — Reproductibilite : empreintes, tracabilite, sauvegarde

**Date** : 19/09/2026 · **Statut** : acceptée

## Contexte

Trois entraînements successifs ont donné 0,782 puis 0,797 puis 0,797, identique à la seizième décimale. Le code est déterministe (graine 42). La seule source de variation est l’ingestion en direct. Le 16/09/2026, la suppression d’un volume Docker a détruit le registre MLflow et ses artefacts, alors que le lac de données sur disque a survécu.

## Decision

1. Ajouter dans chaque run MLflow une empreinte condensée SHA‑256 du jeu de données, le nombre de lignes, les bornes de dates et les comptes par flux.  
2. Appliquer l’étiquette `code_commit` sur chaque run.  
3. Épingler les images de base par empreinte, non par étiquette, relevé le 19/09/2026.  
4. Sauvegarder le registre MLflow hors du volume Docker avec `make sauvegarde-mlflow`.  
5. Restaurer avec `make restaure-mlflow` dans un volume d’essai, jamais sur le registre en service.  
6. Utiliser la cible `make pipeline-gele` pour rejouer la chaîne sans ingérer de nouvelles données.

## Alternatives ecartees

| Option | Pourquoi |
|---|---|
| Épingler par étiquette seule | Une étiquette peut changer de contenu, l’empreinte reste stable. |
| Sauvegarder uniquement le fichier SQLite du registre | Les artefacts (277 Mo) seraient perdus. |
| Restaurer directement sur le volume en service | Une sauvegarde ne doit pas pouvoir détruire le service en cours. |

## Consequences

Une reconstruction dans un mois produit la même image. Toute métrique est rattachable à ses données et à sa version de code. La démonstration peut être rejouée sans dépendre de l’API Steam.

## Preuves

- Les trois entraînements ont confirmé la déterminisme du code.  
- Le téléchargement de `python:3.11-slim` le 19/09 a produit exactement l’empreinte épinglée.  
- L’archive de sauvegarde fait 15 Mo, contient 277 Mo d’artefacts, et la restauration a relu les versions 1 à 4 ainsi que l’alias `champion`.  
- La cible `pipeline-gele` rejoue la chaîne sans nouvelle ingestion.  

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
