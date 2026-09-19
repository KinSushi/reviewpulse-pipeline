# Revenir en arrière : ce qui est réversible, par quel moyen

## 1. Principe
Chaque couche du système possède son propre mécanisme de retour arrière. Aucun mécanisme ne dépend d’une sauvegarde manuelle ; la réversibilité est intégrée dans le processus de chaque couche.

## 2. Tableau réversibilité

| Couche | Ce qui peut être défait | Mécanisme | Commande ou geste | Limite |
|-------|--------------------------|-----------|-------------------|--------|
| Code, configuration, documentation | Modifications de code, fichiers de configuration, documentation | Git (commits, branches, **étiquettes**) | `git revert <commit>` ; `git checkout <tag>` ; `git tag preuves-2026-09-19` | Le revert crée un nouveau commit ; l’historique reste visible. |
| Modèle en service | Version du modèle MLflow désignée comme **champion** | Alias MLflow géré par le module `reviewpulse.rollback` | `make rollback VERSION=<n>` (ex. `make rollback VERSION=3`) | Le registre vit dans un volume Docker ; si le volume est supprimé, les artefacts sont perdus. |
| Données de la zone **silver** | Contenu des tables Iceberg (ex. `silver.reviews`) | Instantanés Iceberg | `make snapshots TABLE=silver.reviews` liste l’historique ; `make snapshots TABLE=silver.reviews SNAPSHOT=<id>` restaure. Lecture sans bascule : `lakehouse.read_table_at`. | La restauration bascule l’instantané courant ; l’historique reste entier, l’opération est donc elle-même réversible. Prouvé par `tests/test_spark_silver.py::test_lakehouse_restore_snapshot`, témoin compris. |
| Zone **brute** | Aucun élément modifiable (ingestion uniquement en écriture) | Conception immuable (ADR 0002) | Aucun geste de rollback ; on reprend l’ingestion depuis le dernier état connu. | La zone ne peut pas être modifiée ; la perte de données brute nécessite une nouvelle ingestion. |
| Zone **propre**, scorée et **gold** | Tables dérivées (clean, scored, gold) | Re‑exécution du pipeline sans nouvelles données | `make pipeline-gele` | La chaîne se rejoue en lecture seule des tables existantes ; aucune donnée nouvelle n’est ingérée. |
| Environnement d’exécution | Images Docker, conteneurs en cours d’exécution | Reconstruction d’images depuis le dépôt | `make down` puis `make up` | Les images de base sont épinglées par étiquette ; aucune épinglage par empreinte (hash) n’est actuellement appliqué. |

## 3. Ce qui n’est pas réversible aujourd’hui
- **Suppression d’un volume Docker** : le registre MLflow et les artefacts qu’il contient sont perdus (ex. incident du 16/09/2026).  
- **Ingestion de nouvelles données** : chaque passage ajoute des avis et met à jour les métriques ; il n’existe pas de mécanisme de retrait sélectif des avis déjà ingérés.

## 4. Ce qu’il reste à outiller
- Épinglage des images Docker de base par empreinte (hash) plutôt que par simple étiquette.  
- Sauvegarde du registre MLflow hors du volume Docker (ex. export vers un stockage persistant).

*Document rédigé le 19/09/2026*.
