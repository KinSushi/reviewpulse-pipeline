# ADR 0010 — Emplacement des artefacts et des écritures

**Date** : 16/09/2026 · **Statut** : acceptée

## Contexte

Trois défauts, tous invisibles en tests unitaires et révélés par les exécutions réelles du 16/09/2026 :

1. **Modèle introuvable** : avec une base MLflow SQLite sans emplacement explicite, les artefacts partaient dans `./mlruns` **du dossier courant** ; entraîné dans un conteneur, le modèle était perdu pour l'API (erreur 500).
2. **Écriture refusée** : `top_terms.json` était écrit dans le dossier courant, non accessible en écriture à l'utilisateur non-root du conteneur.
3. **Dossiers absents** : aucune écriture ne créait son dossier parent.

## Décision

- Suivi local (`sqlite:` ou `file:`) : l'expérience est créée avec un emplacement absolu `DATA_DIR/mlartifacts`. Avec un serveur MLflow HTTP, le serveur gère les artefacts (`--serve-artifacts`).
- Artefacts JSON envoyés par `mlflow.log_dict`, **sans fichier local**.
- Toute écriture crée son dossier parent et passe par un fichier temporaire suivi de `os.replace`.
- L'image donne à l'utilisateur `app` la propriété de `/app`.

## Constat sur MLflow

MLflow crée lui-même un dossier `./mlruns` **vide** dès qu'il ouvre une base SQLite (sonde du 16/09/2026 : après `get_experiment_by_name`). Le test vérifie donc qu'aucun **fichier** n'est écrit dans le dossier courant.

## Preuves

- API relancée dans un **autre conteneur et un autre dossier courant** : `/health` 200, prédictions correctes.
- Tests : `test_artifacts_location.py` (entraînement et service dans deux dossiers différents, aucun fichier écrit, 503 sans modèle), `test_fresh_dirs.py`.
