# Registre de suivi — sujets ouverts et fermés

Registre **persistant** du projet. Il survit aux changements de session, de modèle et de contexte : ce qui n'y figure pas risque d'être oublié.

**Règles.** Un sujet n'est *terminé* que si son critère de fin est satisfait **et vérifié par une preuve**. Un sujet non mentionné depuis plusieurs jours reste ouvert tant qu'il n'est pas fermé explicitement. « Modifié » n'est pas « validé » ; « planifié » n'est pas « traité ».

**États** : ✅ terminé · 🔄 en cours · ⛔ bloqué · 🔍 à vérifier · ⬜ non traité · ✖ abandonné.

Mise à jour : 19/09/2026.

## Sujets ouverts

| ID | Sujet | Source | Prio | État | Critère de fin | Preuve | Prochaine action |
|---|---|---|---|---|---|---|---|
| R01 | Publier le dépôt sur GitHub et créer le secret `REVIEWPULSE_SALT` | plan du 12/09, jalon 22/09 | P1 | ⛔ Enzo | Dépôt en ligne, CI verte, secret configuré | — | Décision d'Enzo |
| R02 | Supprimer l'ancien dépôt `KinSushi/reviewpulse` (commits avec mention d'outil) | 16/09 | P1 | ⛔ Enzo | Dépôt supprimé | — | Décision d'Enzo |
| R03 | Vidéo de la solution en production | livrable AIA 4, jalon 23/09 | P1 | ⛔ Enzo | Vidéo enregistrée et archivée | — | Enregistrer après répétition |
| R04 | Six présentations calibrées (Demo Day 10 min ; CDSD 7-8 diapositives ; AIA 1 15 min ; AIA 2, 3 et 4 5 min) | référentiels | P1 | ⬜ | Un jeu par soutenance, avec script parlé, minuté | — | Commencer par le Demo Day |
| R05 | Script de démonstration vérifié **contre l'écran réel** | 19/09 | P1 | 🔄 | Script minute par minute rejoué sans surprise | `04_plan_jusqu_au_demo_day.md` (version non vérifiée) | Rejouer l'écran et corriger le script |
| R06 | Rafraîchir les preuves : batterie, **18 mutations**, test de stack **16 contrôles** | 19/09 | P1 | 🔄 | Rapports régénérés dans `docs/evidence/` | batterie 73/73 (18/09), mutations 16/16 (18/09), stack 14/14 (18/09) | Exécuter après les ajouts du 19/09 |
| R07 | Aligner README et `05_conformite_demo_day.md` sur les chiffres du jour | 18/09 | P1 | ⬜ | Plus aucun chiffre périmé (48 tests, 12 contrôles, F1 non daté) | — | Reprendre après R06 |
| R08 | Dossier de gouvernance (AIA 1, pilote Spotify) | `08_exigences_par_bloc.md` | P1 | ⛔ | Dossier écrit à partir du cas réel | 8 PDF repérés sur D: | Lire les PDF dans un conteneur |
| R09 | Lire les sources Julie : énoncés Kayak, Tinder, Steam, AT&T, Getaround ; modules `lead-data-v2` | 18/09 | P1 | ⛔ | Exigences relevées, non supposées | — | Enzo ouvre une session dans le navigateur intégré |
| R10 | Great Expectations sur silver et gold | S3-1 | P1 | ⬜ | Suites écrites, porte bloquante dans le DAG, exécutées | GE couvre la zone propre seulement | Phase 2 du plan |
| R11 | Alerte de dérive hors journal Airflow et réentraînement déclenché par la dérive | AIA 4 C4.4 | P1 | ⬜ | Alerte émise hors journal ; réentraînement déclenché sur seuil | `drift.py` branché au DAG | Après R06 |
| R12 | Restaurer un instantané Iceberg (outillé et prouvé) | AIA 4 « versioning avec restauration » | P1 | ⬜ | Commande de restauration + contrôle qui la prouve | `table_history` lit l'historique | Écrire `lakehouse.restore_snapshot` |
| R13 | Épingler les images de base par empreinte | reproductibilité | P2 | ⬜ | `FROM` avec `@sha256:` dans les trois Dockerfiles | — | Relever les empreintes |
| R14 | Sauvegarder le registre MLflow hors du volume Docker | incident du 16/09 | P1 | ⬜ | Sauvegarde automatisée et restauration essayée | — | Décider du support |
| R15 | Mettre à niveau les schémas (8 sur 10 ignorent Spark, Iceberg, dbt) | audit du 18/09 | P1 | ⬜ | Schémas conformes au code | `docs/diagrams/src/*.mmd` | Avant la soutenance |
| R16 | Trancher la stratégie de branches (`main` et `plateforme-v3` sans ancêtre commun) | audit du 19/09 | P1 | ⛔ Enzo | Une seule ligne principale | 2 commits contre 24, histoires disjointes | Décision d'Enzo à la publication |
| R17 | Briques de réemploi : MinIO, Kafka, Terraform, déploiement public | `03_matrice_reemploi_blocs.md` | P2 | ⬜ | Chaque bloc visé peut réemployer la brique | Terraform absent de la machine | Cadrer avec Enzo |
| R18 | Droits sur D: : huit dossiers portent encore une interdiction de l'ancien compte | 18/09 | P2 | ⛔ Enzo | Plus aucune entrée orpheline | `icacls` interrompu volontairement | Passe ciblée (22 500 fichiers) |
| R19 | Exécuter les mutations M17 et M18 (porte de qualité, entrepôt) | 19/09 | P1 | 🔍 | 18 mutations sur 18 détectées | écrites, ancres vérifiées | Lancer les tests inverses |
| R20 | Exécuter les contrôles F9 et F10 (zone gold) | 19/09 | P1 | 🔍 | 16 contrôles sur 16 | écrits | Lancer le test de stack |
| R21 | Vérifier la mesure de sur- et sous-apprentissage | critère transverse CDSD | P1 | 🔍 | Test vert dans la batterie | écrit | Batterie en cours |
| R22 | Vérifier `rollback.py` en réel | 19/09 | P1 | 🔍 | Bascule d'alias effectuée puis annulée | défaut d'horodatage corrigé | Rejouer après reconstruction |
| R23 | Trancher `confluent-kafka`, déclaré mais jamais importé | audit du 18/09 | P3 | ⬜ | Retiré, ou assumé par écrit | poids inutile dans chaque image | Décider avec R17 |
| R24 | Tests unitaires de `rollback.py` | 19/09 | P1 | ⬜ | Fonctions couvertes, un témoin par test | aucun test | Faire produire par le banc |
| R25 | Mutations pour `explain.py` et `drift.py` | audit du 18/09 | P2 | ⬜ | Chaque module branché a sa mutation | non couverts | Après R19 |
| R26 | Fonction de coût du modèle écrite noir sur blanc | critère CDSD bloc 4 | P2 | ⬜ | Mentionnée dans la Model Card | — | À ajouter |

## Sujets fermés (avec leur preuve)

| ID | Sujet | Preuve | Fermé le |
|---|---|---|---|
| F01 | Chaîne complète reconstruite après la perte du volume Docker | quatre images, pipeline complet, dbt 43/43 | 18/09 |
| F02 | Batterie de tests | **73 sur 73**, y compris depuis un dossier temporaire | 18/09 |
| F03 | Tests inverses | **16 mutations sur 16 tuées**, témoin vert | 18/09 |
| F04 | Test de la stack déployée | **14 contrôles sur 14**, F7 et F8 compris | 18/09 |
| F05 | DAG Airflow avec la dérive | **6 tâches sur 6** | 19/09 |
| F06 | Déterminisme du modèle | métriques identiques à la seizième décimale, non-promotion correcte | 18/09 |
| F07 | Explicabilité servie par l'API et le tableau de bord | `/explain` interrogé en production | 19/09 |
| F08 | Airflow sur PostgreSQL (le scheduler survit aux interrogations) | DAG déclenché pendant une interrogation par minute | 19/09 |
| F09 | Traçabilité du commit jusqu'aux runs MLflow et aux rapports | `REVIEWPULSE_COMMIT` propagé, étiquette `code_commit` | 19/09 |
| F10 | Empreinte du jeu de données dans chaque entraînement | condensé, lignes, bornes de dates | 18/09 |
| F11 | Retour arrière outillé sur le modèle en service | `rollback.py`, `make rollback VERSION=n` | 19/09 |
| F12 | Point de retour marqué | étiquette `preuves-2026-09-19` | 19/09 |
| F13 | Matrice de réversibilité | `docs/15_reversibilite.md` | 19/09 |

## Comment se servir de ce registre

1. **Avant** toute sous-tâche : relire la table des sujets ouverts et repérer ceux que la sous-tâche touche ou risque de faire oublier.
2. **Après** : repasser sur le registre entier, pas seulement sur la ligne traitée.
3. Un sujet ne se ferme qu'en déplaçant sa ligne vers la table des sujets fermés, **avec sa preuve**.
4. Le plan détaillé vit à part (`.claude/plans/`) ; ce registre est la liste de ce qui reste dû.
