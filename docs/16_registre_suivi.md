# Registre de suivi — sujets ouverts et fermés

Registre **persistant** du projet. Il survit aux changements de session, de modèle et de contexte : ce qui n'y figure pas risque d'être oublié.

**Règles.** Un sujet n'est *terminé* que si son critère de fin est satisfait **et vérifié par une preuve**. Un sujet non mentionné depuis plusieurs jours reste ouvert tant qu'il n'est pas fermé explicitement. « Modifié » n'est pas « validé » ; « planifié » n'est pas « traité ».

**États** : ✅ terminé · 🔄 en cours · ⛔ bloqué · 🔍 à vérifier · ⬜ non traité · ✖ abandonné.

Mise à jour : 19/09/2026, 21 h. **Sept sujets P1 attendent le retour de Docker (R40).**

## Sujets ouverts

| ID | Sujet | Source | Prio | État | Critère de fin | Preuve | Prochaine action |
|---|---|---|---|---|---|---|---|
| R01 | Publier le dépôt sur GitHub et créer le secret `REVIEWPULSE_SALT` | plan du 12/09, jalon 22/09 | P1 | ⛔ Enzo | Dépôt en ligne, CI verte, secret configuré | — | Décision d'Enzo |
| R02 | Supprimer l'ancien dépôt `KinSushi/reviewpulse` (commits avec mention d'outil) | 16/09 | P1 | ⛔ Enzo | Dépôt supprimé | — | Décision d'Enzo |
| R03 | Vidéo de la solution en production | livrable AIA 4, jalon 23/09 | P1 | ⛔ Enzo | Vidéo enregistrée et archivée | — | Enregistrer après répétition |
| R04 | Six présentations calibrées (Demo Day 10 min ; CDSD 7-8 diapositives ; AIA 1 15 min ; AIA 2, 3 et 4 5 min) | référentiels | P1 | 🔄 | Un jeu par soutenance, avec script parlé, minuté | **3 sur 6** : Demo Day (9 diapositives), **AIA 1** (9, adossée au dossier de gouvernance) et AIA 4 (5). Aucun texte du gabarit Telco ne subsiste dans les trois. Constructeur piloté par spécification JSON, refuse un indice de run inexistant | Chiffres à rafraîchir ; CDSD, AIA 2 et AIA 3 restent bloquées sur R09 |
| R05 | Script de démonstration vérifié **contre l'écran réel** | 19/09 | P1 | 🔄 | Script minute par minute rejoué sans surprise, chronomètre en main | `docs/presentation/script_10_minutes.md`, écrit d'après l'écran parcouru le 19/09 | Répétition chronométrée par Enzo |
| R06 | Rafraîchir les preuves : batterie, **26 mutations**, test de stack | 19/09 | P1 | ⛔ | Les trois rapports régénérés dans `docs/evidence/` | stack **16/16** le 19/09 ; batterie et mutations **jamais rendues** sur l'arbre courant — la campagne du 19/09 a été perdue (voir R40) | `make campagne` dès le retour du démon Docker |
| R07 | Aligner README et `05_conformite_demo_day.md` sur les chiffres du jour | 18/09 | P1 | ✅ | Plus aucun chiffre périmé | commit `e2af00a` : chiffres datés 16/09 contre 18-19/09, avertissement sur les preuves détruites puis reconstituées | À revoir après R06 (18 mutations, 16 contrôles) |
| R08 | Dossier de gouvernance (AIA 1, pilote Spotify) | `08_exigences_par_bloc.md` | P1 | 🔍 | Les six livrables du cas écrits à partir du cas réel, relus contre le code | `docs/17_gouvernance.md` écrit sur les six tâches, chaque manque nommé ; exigences dans `docs/00_sources/2026-09-19_cas_spotify_gouvernance.md` | Relecture ligne à ligne contre le code, puis présentation AIA 1 |
| R09 | Lire les sources Julie : énoncés Kayak, Tinder, Steam, AT&T, Getaround ; modules `lead-data-v2` | 18/09 | P1 | ⛔ Enzo | Exigences relevées, non supposées | — | **Bloque trois présentations sur six** (CDSD, AIA 2, AIA 3) : Enzo ouvre une session dans le navigateur intégré |
| R10 | Great Expectations sur silver et gold | S3-1 | P1 | 🔍 | Suites écrites, porte bloquante dans le DAG, exécutées, avec tests unitaires | `expectations_lake.py` : 4 suites, 28 attentes vertes sur données réelles, témoin rouge sur données faussées ; 7 tests verts isolément ; DAG à **9 tâches**, aucune erreur d'import | Exécution réelle du DAG, dépend de R40 |
| R11 | Alerte de dérive hors journal Airflow et réentraînement déclenché par la dérive | AIA 4 C4.4 | P1 | 🔍 | Une exécution réelle du DAG montre les neuf tâches, dont le déclenchement | mécanisme en place et mesuré hors Airflow ; DAG chargé, 9 tâches listées | Déclencher `reviewpulse_daily`, dépend de R40 |
| R13 | Épingler les images de base par empreinte | reproductibilité | P2 | 🔍 | Les trois images épinglées **et** reconstruites sans erreur | `python:3.11-slim@sha256:da047cb8…`, `apache/airflow:slim-2.10.3-python3.11@sha256:18eaa3e1…`, `ghcr.io/mlflow/mlflow:v3.16.0@sha256:470607da…` relevées par `docker buildx imagetools inspect` | Reconstruire les images quand la machine sera libre |
| R16 | Trancher la stratégie de branches (`main` et `plateforme-v3` sans ancêtre commun) | audit du 19/09 | P1 | ⛔ Enzo | Une seule ligne principale | 2 commits contre 24, histoires disjointes | Décision d'Enzo à la publication |
| R17 | Briques de réemploi : MinIO, Kafka, Terraform, déploiement public | `03_matrice_reemploi_blocs.md` | P2 | ⬜ | Chaque bloc visé peut réemployer la brique | Terraform absent de la machine | Cadrer avec Enzo |
| R18 | Droits sur D: : huit dossiers portent encore une interdiction de l'ancien compte | 18/09 | P2 | ⛔ Enzo | Plus aucune entrée orpheline | `icacls` interrompu volontairement | Passe ciblée (22 500 fichiers) |
| R19 | Exécuter les **26 mutations** (M17 à M26 jamais passées) | 19/09 | P1 | ⛔ | 26 mutations sur 26 détectées | M01 à M16 tuées le 18/09 ; les dix suivantes n'ont jamais tourné | Dépend de R40 |
| R21 | Vérifier la mesure de sur- et sous-apprentissage | critère transverse CDSD | P1 | ⛔ | Test vert dans la batterie complète | `test_ecart_train_test_raisonnable` vert le 19/09 dans une batterie de 90, mais pas sur l'arbre courant | Dépend de R40 |
| R24 | Tests unitaires de `rollback.py` | 19/09 | P1 | ⛔ | Six tests verts dans la batterie complète | 6 verts isolément le 19/09 ; jamais dans une batterie complète de l'arbre courant | Dépend de R40 |
| R25 | Mutations pour `explain.py` et `drift.py` | audit du 18/09 | P2 | ⬜ | Chaque module branché a sa mutation | non couverts | Après R19 |
| R26 | Fonction de coût du modèle écrite noir sur blanc | critère CDSD bloc 4 | P2 | ✅ | Mentionnée dans la Model Card | `docs/12_model_card.md` : entropie croisée, `class_weight="balanced"`, régularisation L2 `C=4.0`, vérifié dans `train.py` | — |
| R27 | `import os` absent de `train.py` : 6 échecs et 5 erreurs | témoin des tests inverses, 19/09 | P1 | ⛔ | Batterie verte sur l'arbre courant | défaut reproduit puis corrigé ; batterie de **90 verte** sur l'arbre du 19/09 à 17 h | Confirmer sur l'arbre courant, dépend de R40 |
| R28 | Le banc de tests inverses ne recopiait pas `dbt/` | témoin, 19/09 | P1 | ⛔ | `tests/test_gold.py` s'exécute dans la copie temporaire | `_copy_project` corrigé ; jamais vérifié par une campagne complète | Dépend de R40 |
| R29 | Base de documents (NoSQL) : **exigée par le bloc AIA 2** | `08_exigences_par_bloc.md`, cas Stripe | P2 | ⬜ | Le modèle NoSQL et les requêtes NoSQL du dossier Stripe sont produits ; décidé si ReviewPulse en fait la démonstration | Le cas Stripe demande une architecture OLTP + OLAP + **NoSQL**, avec « modèle NoSQL » et « requêtes SQL et NoSQL » parmi les livrables ; un travail de référence du parcours employait DocumentDB | Cadrer avec Enzo : livrable sur papier pour Stripe, ou démonstration réelle sur la zone brute de ReviewPulse |
| R30 | Justifier l'architecture et les décisions dans les diapositives, le code et les questions du jury | Enzo, 19/09 | P1 | ✅ | Chaque ADR cité dans le code **et** dans les questions-réponses ; contrôle mécanique qui échoue sinon | `make justifications` : **20 ADR sur 20** cités des deux côtés. Mesure de départ : 6 sur 16 orphelins. Quatre ADR écrits (0017 à 0020), section « Architecture, choix et décisions » de 2 035 mots, renvois ajoutés aux trois jeux de diapositives | — |
| R31 | Déploiement progressif : A/B ou canari | AIA 4, `18_briques_exigees.md` | P2 | ⬜ | Une part de trafic configurable, ou la décision écrite de s'en tenir à la bascule par alias | ADR 0016 est une proposition, aucune implémentation | Trancher avec Enzo : implémenter ou assumer par écrit |
| R32 | Secrets et chiffrement : coffre, chiffrement en transit | AIA 2 et AIA 3, `18_briques_exigees.md` | P2 | ⬜ | Coffre en place ou décision écrite ; chiffrement en transit entre services | sel obligatoire hors du dépôt, mais aucun coffre ; seule l'API Steam est en HTTPS | Cadrer avec R17 |
| R33 | Garde-fous : biais et injections | AIA 4, `18_briques_exigees.md` | P2 | ⬜ | Contrôle de biais mesuré, ou décision écrite | rien dans le code ; les correspondances trouvées étaient « injection de dépendance » | À cadrer |
| R34 | FinOps, GreenOps, dimensionnement CPU/GPU | AIA 2 et AIA 4, `18_briques_exigees.md` | P2 | ⬜ | Une mesure de coût et une d'empreinte, si modestes soient-elles | aucune mesure | À cadrer |
| R35 | Modélisation OLAP en étoile avec **SCD2** | AIA 2, `18_briques_exigees.md` | P2 | ⬜ | Dimensions à historisation lente modélisées dans le dossier Stripe | `dim_game` et `dim_date` sont sans historisation | Cadrer avec R29 : livrable papier ou démonstration |
| R36 | Backlog conduit en sprints | Bloc 3, `18_briques_exigees.md` | P3 | ⬜ | Un découpage en sprints daté, ou la décision écrite de s'en passer | `10_backlog.md` et le registre existent, aucun sprint | Trancher avec Enzo |
| R37 | Tracing de l'explicabilité | AIA 4, `18_briques_exigees.md` | P3 | ⬜ | Traces d'explication conservées, ou décision écrite | contribution linéaire exacte servie par `/explain`, rien n'est tracé | Après R11 |
| R39 | Démonstration de résilience : consommateur arrêté puis relancé | AIA 3, `18_briques_exigees.md` | P2 | ⬜ | Une coupure provoquée puis rattrapée, mesurée | dépend de la brique Kafka, absente | Dépend de R17 |
| R40 | Docker Desktop ne démarre plus : `docker daemon did not become ready` | 19/09, 20 h | P1 | ⛔ Enzo | `docker version` rend une version de serveur | processus présents, démon absent ; survenu après un redémarrage pour un réglage IPv4/IPv6 | Enzo relance Docker Desktop ; ensuite `make campagne` |
| R41 | Garde de temps **par test** dans la batterie | incident du 19/09 | P2 | ⬜ | Un test bloqué échoue seul, sans emporter la campagne | `pytest-timeout` absent de l'image ; la garde actuelle est par phase, pas par test | Ajouter `pytest-timeout` à `requirements-dev.txt` et reconstruire l'image de développement |
| R42 | « Conteneurs et orchestration **sous charge** » : aucun essai de charge | AIA 4, indicateur du référentiel | P1 | 🔍 | Une mesure réelle : débit, latence et taux d'erreur de l'API sous requêtes concurrentes, avec le chiffre écrit | `tools/essai_charge.py` écrit, bibliothèque standard seule (importé sur Python 3.14 de l'hôte, sans dépendance du projet). Trois témoins verts : refus clair sur service absent, centiles justes sur une série connue, **code de retour 1** sur service absent. `make charge` | Lancer contre la stack, après la campagne en cours |
| R43 | Le détecteur d'exigences ne lit que le gras | Enzo, 19/09 | P2 | ⬜ | Les exigences non mises en gras sont détectées aussi | `verifier_briques.py` extrait les termes entre doubles astérisques ; « orchestration sous charge » lui a échappé | Découper aussi les listes d'indicateurs sur le point-virgule |

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
| F24 | Toute exigence en gras de `08_exigences_par_bloc.md` est classée et suivie | `docs/18_briques_exigees.md` : **73 briques techniques** — 27 présentes, 16 partielles, 30 absentes — et 38 termes non techniques ; chaque brique non présente porte un sujet vivant du registre. `make briques` rend 0. Né de l'erreur du 19/09 : j'avais nié une exigence qui dormait dans le dépôt | 19/09 |
| F25 | Le contrôle des briques a trouvé quatre exigences que mon classement manuel avait ratées | `SCD2`, `médaillon batch et streaming` (AIA 2), `notification e-mail`, `démonstration de résilience` (AIA 3) ; sujets R35, R39 ouverts, R11 et R17 complétés | 19/09 |
| F26 | Une campagne ne peut plus tourner des heures sans rien montrer | `tools/campagne_preuves.sh` : journal daté écrit au fil de l'eau (`stdbuf`), une garde `timeout` par phase, dépassement signalé et code de sortie non nul. `make campagne`, syntaxe shell vérifiée | 19/09 |

## Comment se servir de ce registre

1. **Avant** toute sous-tâche : relire la table des sujets ouverts et repérer ceux que la sous-tâche touche ou risque de faire oublier.
2. **Après** : repasser sur le registre entier, pas seulement sur la ligne traitée.
3. Un sujet ne se ferme qu'en déplaçant sa ligne vers la table des sujets fermés, **avec sa preuve**.
4. Le plan détaillé vit à part (`.claude/plans/`) ; ce registre est la liste de ce qui reste dû.
