# Registre de suivi — sujets ouverts et fermés

Registre **persistant** du projet. Il survit aux changements de session, de modèle et de contexte : ce qui n'y figure pas risque d'être oublié.

**Règles.** Un sujet n'est *terminé* que si son critère de fin est satisfait **et vérifié par une preuve**. Un sujet non mentionné depuis plusieurs jours reste ouvert tant qu'il n'est pas fermé explicitement. « Modifié » n'est pas « validé » ; « planifié » n'est pas « traité ».

**États** : ✅ terminé · 🔄 en cours · ⛔ bloqué · 🔍 à vérifier · ⬜ non traité · ✖ abandonné.

Mise à jour : 19/09/2026, 16 h 20.

## Sujets ouverts

| ID | Sujet | Source | Prio | État | Critère de fin | Preuve | Prochaine action |
|---|---|---|---|---|---|---|---|
| R01 | Publier le dépôt sur GitHub et créer le secret `REVIEWPULSE_SALT` | plan du 12/09, jalon 22/09 | P1 | ⛔ Enzo | Dépôt en ligne, CI verte, secret configuré | — | Décision d'Enzo |
| R02 | Supprimer l'ancien dépôt `KinSushi/reviewpulse` (commits avec mention d'outil) | 16/09 | P1 | ⛔ Enzo | Dépôt supprimé | — | Décision d'Enzo |
| R03 | Vidéo de la solution en production | livrable AIA 4, jalon 23/09 | P1 | ⛔ Enzo | Vidéo enregistrée et archivée | — | Enregistrer après répétition |
| R04 | Six présentations calibrées (Demo Day 10 min ; CDSD 7-8 diapositives ; AIA 1 15 min ; AIA 2, 3 et 4 5 min) | référentiels | P1 | 🔄 | Un jeu par soutenance, avec script parlé, minuté | **3 sur 6** : Demo Day (9 diapositives), **AIA 1** (9, adossée au dossier de gouvernance) et AIA 4 (5). Aucun texte du gabarit Telco ne subsiste dans les trois. Constructeur piloté par spécification JSON, refuse un indice de run inexistant | Chiffres à rafraîchir ; CDSD, AIA 2 et AIA 3 restent bloquées sur R09 |
| R05 | Script de démonstration vérifié **contre l'écran réel** | 19/09 | P1 | 🔄 | Script minute par minute rejoué sans surprise, chronomètre en main | `docs/presentation/script_10_minutes.md`, écrit d'après l'écran parcouru le 19/09 | Répétition chronométrée par Enzo |
| R06 | Rafraîchir les preuves : batterie, **18 mutations**, test de stack **16 contrôles** | 19/09 | P1 | 🔄 | Les trois rapports régénérés dans `docs/evidence/` après la correction de R27 | stack **16/16** le 19/09 (`docs/evidence/forward_test.md`) ; batterie et mutations relancées | Attendre la batterie, puis relancer les tests inverses |
| R07 | Aligner README et `05_conformite_demo_day.md` sur les chiffres du jour | 18/09 | P1 | ✅ | Plus aucun chiffre périmé | commit `e2af00a` : chiffres datés 16/09 contre 18-19/09, avertissement sur les preuves détruites puis reconstituées | À revoir après R06 (18 mutations, 16 contrôles) |
| R08 | Dossier de gouvernance (AIA 1, pilote Spotify) | `08_exigences_par_bloc.md` | P1 | 🔍 | Les six livrables du cas écrits à partir du cas réel, relus contre le code | `docs/17_gouvernance.md` écrit sur les six tâches, chaque manque nommé ; exigences dans `docs/00_sources/2026-09-19_cas_spotify_gouvernance.md` | Relecture ligne à ligne contre le code, puis présentation AIA 1 |
| R09 | Lire les sources Julie : énoncés Kayak, Tinder, Steam, AT&T, Getaround ; modules `lead-data-v2` | 18/09 | P1 | ⛔ Enzo | Exigences relevées, non supposées | — | **Bloque trois présentations sur six** (CDSD, AIA 2, AIA 3) : Enzo ouvre une session dans le navigateur intégré |
| R10 | Great Expectations sur silver et gold | S3-1 | P1 | 🔍 | Suites écrites, porte bloquante dans le DAG, exécutées, **avec tests unitaires** | `expectations_lake.py` : 4 suites, 28 attentes, **toutes vertes** sur les données réelles ; témoin : deux valeurs faussées donnent `success=False` et 2 échecs nommés. Tâche `gx_lake` après `gold`, DAG à **9 tâches**, aucune erreur d'import | Écrire `tests/test_expectations_lake.py`, puis exécution réelle du DAG |
| R11 | Alerte de dérive hors journal Airflow et réentraînement déclenché par la dérive | AIA 4 C4.4 | P1 | 🔍 | Une exécution réelle du DAG montre les huit tâches, dont le déclenchement | mécanisme en place et mesuré hors Airflow (voir F17) ; DAG chargé, 8 tâches listées, aucune erreur d'import | Déclencher `reviewpulse_daily` après la batterie |
| R13 | Épingler les images de base par empreinte | reproductibilité | P2 | 🔍 | Les trois images épinglées **et** reconstruites sans erreur | `python:3.11-slim@sha256:da047cb8…`, `apache/airflow:slim-2.10.3-python3.11@sha256:18eaa3e1…`, `ghcr.io/mlflow/mlflow:v3.16.0@sha256:470607da…` relevées par `docker buildx imagetools inspect` | Reconstruire les images quand la machine sera libre |
| R16 | Trancher la stratégie de branches (`main` et `plateforme-v3` sans ancêtre commun) | audit du 19/09 | P1 | ⛔ Enzo | Une seule ligne principale | 2 commits contre 24, histoires disjointes | Décision d'Enzo à la publication |
| R17 | Briques de réemploi : MinIO, Kafka, Terraform, déploiement public | `03_matrice_reemploi_blocs.md` | P2 | ⬜ | Chaque bloc visé peut réemployer la brique | Terraform absent de la machine | Cadrer avec Enzo |
| R18 | Droits sur D: : huit dossiers portent encore une interdiction de l'ancien compte | 18/09 | P2 | ⛔ Enzo | Plus aucune entrée orpheline | `icacls` interrompu volontairement | Passe ciblée (22 500 fichiers) |
| R19 | Exécuter les mutations M17 et M18 (porte de qualité, entrepôt) | 19/09 | P1 | 🔄 | 18 mutations sur 18 détectées | premier lancement interrompu par le témoin : il a trouvé R27, défaut réel | Relancer après la batterie verte |
| R21 | Vérifier la mesure de sur- et sous-apprentissage | critère transverse CDSD | P1 | 🔍 | Test vert dans la batterie | `test_ecart_train_test_raisonnable` **en échec** le 19/09 par le défaut R27 | Relire le résultat après la batterie |
| R24 | Tests unitaires de `rollback.py` | 19/09 | P1 | 🔍 | Cinq tests verts, dont un témoin | `tests/test_rollback.py`, faux client MLflow ; le résultat du 19/09 matin appartient à une batterie non reproductible | Relire le résultat après la batterie |
| R25 | Mutations pour `explain.py` et `drift.py` | audit du 18/09 | P2 | ⬜ | Chaque module branché a sa mutation | non couverts | Après R19 |
| R26 | Fonction de coût du modèle écrite noir sur blanc | critère CDSD bloc 4 | P2 | ✅ | Mentionnée dans la Model Card | `docs/12_model_card.md` : entropie croisée, `class_weight="balanced"`, régularisation L2 `C=4.0`, vérifié dans `train.py` | — |
| R27 | `import os` absent de `train.py` : 6 échecs et 5 erreurs dans la batterie | témoin des tests inverses, 19/09 | P1 | 🔄 | Batterie verte, reproduite depuis une copie neuve | défaut reproduit puis corrigé ; `NameError: name 'os' is not defined` à `train.py:352` | Attendre la batterie de contrôle |
| R28 | Le banc de tests inverses ne recopiait pas `dbt/` | témoin, 19/09 | P1 | 🔄 | `tests/test_gold.py` s'exécute dans la copie temporaire | `_copy_project` corrigé : `dbt` ajouté à la liste | Vérifier au prochain lancement des mutations |
| R29 | Base de documents (NoSQL) : **exigée par le bloc AIA 2** | `08_exigences_par_bloc.md`, cas Stripe | P2 | ⬜ | Le modèle NoSQL et les requêtes NoSQL du dossier Stripe sont produits ; décidé si ReviewPulse en fait la démonstration | Le cas Stripe demande une architecture OLTP + OLAP + **NoSQL**, avec « modèle NoSQL » et « requêtes SQL et NoSQL » parmi les livrables ; un travail de référence du parcours employait DocumentDB | Cadrer avec Enzo : livrable sur papier pour Stripe, ou démonstration réelle sur la zone brute de ReviewPulse |
| R30 | Justifier l'architecture et les décisions dans les diapositives, le code et les questions du jury | Enzo, 19/09 | P1 | ✅ | Chaque ADR cité dans le code **et** dans les questions-réponses ; contrôle mécanique qui échoue sinon | `make justifications` : **20 ADR sur 20** cités des deux côtés. Mesure de départ : 6 sur 16 orphelins. Quatre ADR écrits (0017 à 0020), section « Architecture, choix et décisions » de 2 035 mots, renvois ajoutés aux trois jeux de diapositives | — |

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
| F14 | Test de la stack déployée, zone gold comprise | **16 contrôles sur 16**, F9 et F10 compris ; F10 corrigé pour suivre le contrat dbt (deux flux) | 19/09 |
| F15 | Retour arrière **réellement exécuté** sur le modèle en service | champion 2 → 1, vérifié, puis 1 → 2, vérifié, via `python -m reviewpulse.rollback --vers N` | 19/09 |
| F16 | Restauration d'un instantané Iceberg, outillée et prouvée | `lakehouse.read_table_at` et `restore_snapshot`, interface `python -m reviewpulse.lakehouse --table T [--restaurer ID]`, cible `make snapshots` ; `test_lakehouse_restore_snapshot` vert (témoin : la lecture d'instantané ne modifie pas la table) ; historique réel listé, 19 instantanés sur `silver.reviews` | 19/09 |
| F17 | Alerte de dérive hors du journal Airflow | `drift.evaluer_alerte` et `ecrire_alerte` ; fichier daté `scored/alertes/derive_20260919-153751.json` portant motifs, horodatage UTC et `code_commit` ; 11 tests verts dans `tests/test_drift.py` | 19/09 |
| F18 | La dérive mesurait la collecte, pas la population | corrigé : mesure sur le flux naturel seul, et seules les colonnes de `COLONNES_ALERTE` (`text_len`) peuvent alerter. Mesuré : fenêtre ancienne 85 % francophone contre récente 91 % anglophone, PSI `language` 3,098 écarté ; `text_len` 0,036 stable. ADR 0015 révisée, témoin dans `test_evaluer_alerte_ignore_les_colonnes_de_collecte` | 19/09 |
| F19 | Sauvegarde du registre MLflow hors du volume Docker, **restauration essayée** | `make sauvegarde-mlflow` : archive de 15 Mo (277 Mo d'artefacts) écrite dans le lac ; `make restaure-mlflow` la restaure dans un volume d'essai, jamais sur le registre en service. Registre restauré relu : versions 1 à 4, alias champion sur la 2 | 19/09 |
| F20 | Les dix schémas remis à niveau et rendus | 10 sur 10 rendus sans erreur ; `make diagrams` échoue si un schéma est invalide — c'est ce qui a trouvé trois erreurs de syntaxe. Trois contresens corrigés (dbt lisait les parquet, le journal Airflow déclenchait le réentraînement, le challenger était servi) et une affirmation non tenue retirée (RACI avec DPO, marquée « à définir ») | 19/09 |
| F21 | Le workflow planifié `pipeline.yml` exécutait la chaîne d'avant Spark | corrigé : ingest, spark_silver, expectations, train, score, drift, gold, avec Java 17 ; les deux workflows relus par un analyseur YAML | 19/09 |
| F22 | Les huit PDF du cas Spotify, lus | extraits dans un conteneur `python:3.11-slim` avec `pypdf`, rien installé sur la machine ; 8 documents, 56 pages. Le critère de sélection du vrai PDF est l'en-tête `%PDF-`, **pas la taille** — la note antérieure était fausse | 19/09 |
| F23 | `confluent-kafka`, déclaré et jamais importé | vérifié sur tout le dépôt : une seule occurrence, dans `requirements.txt`. Retiré, la ligne exacte conservée en commentaire pour le jour où la brique Kafka sera construite (R17) | 19/09 |

## Comment se servir de ce registre

1. **Avant** toute sous-tâche : relire la table des sujets ouverts et repérer ceux que la sous-tâche touche ou risque de faire oublier.
2. **Après** : repasser sur le registre entier, pas seulement sur la ligne traitée.
3. Un sujet ne se ferme qu'en déplaçant sa ligne vers la table des sujets fermés, **avec sa preuve**.
4. Le plan détaillé vit à part (`.claude/plans/`) ; ce registre est la liste de ce qui reste dû.
