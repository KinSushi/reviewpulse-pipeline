# Journal de bord — tout ce qui a été établi, dans l'ordre

Règle : **rien ne se travaille de mémoire.** Chaque constat, mesure, décision ou question ouverte est écrit ici, daté, avec sa source. Les décisions structurantes ont en plus leur ADR (`adr/`), les exigences leur document (`08_exigences_par_bloc.md`), le travail restant son backlog (`10_backlog.md`).

Légende des sources : **[J]** lu sur Julie · **[R]** référentiel officiel · **[M]** courriel · **[D]** fichier sur disque · **[X]** exécution ou mesure · **[U]** consigne d'Enzo.

---

## 16/09/2026

### Contexte et consignes

| Heure | Fait | Source |
|---|---|---|
| matin | Objectif : préparer le Demo Day de la Lead et rendre le projet réutilisable pour les blocs CDSD 1 à 6 et AIA 1 à 4, sans travail en double, en réemployant l'existant | [U] |
| matin | Le programme et les cours ont changé en cours de route à la suite d'un litige ; des courriels ont été échangés | [U] |
| matin | Ressources à exploiter : Julie (navigateur Edge), `Jedha_Exercices`, fichiers téléchargeables de Julie, dépôts GitHub listés dans des `.txt`, bibliothèque KOS et code source sur `D:` | [U] |
| matin | Utiliser les agents locaux et le banc gratuit ; ne rien modifier dans `C:\local-llm-docker` ; signaler ses problèmes à NEXUS | [U] |
| après-midi | Code « premium » : tests, tests inverses, tests en conditions réelles ; où/quoi/comment/pourquoi dans le code ; zéro zone d'ombre pour le jury | [U] |
| après-midi | Déploiement réel autorisé pour tester ; créer un dépôt GitHub pour la reproductibilité et la livraison | [U] |
| soir | « Claude apparaît partout » : aucune mention d'outil dans l'historique Git ; dépôt à recréer (choix d'Enzo) | [U] |
| soir | Reprendre les éléments du programme de formation (dbt, Spark, etc.) ; « le top du top », tout ce qui est cohérent avec le Demo Day | [U] |
| soir | Lire les contraintes et consignes de chaque bloc et de chaque certification avant de concevoir | [U] |
| soir | Les dépôts GitHub des `.txt` servent aux blocs AIA 1, 2 et 3 | [U] |
| soir | **Le projet Tinder existe aussi** pour valider un ou plusieurs blocs ; **tout noter, ne pas travailler de mémoire** | [U] |

### Parcours et certifications

| Fait | Source |
|---|---|
| La cohorte dal-ft-18 suit **`path/lead-data-v2`** (Data Lead, 20 jours, 8 modules, se termine par « AI Architect Certification ») | [J] |
| L'ancien parcours `lead-data-analysis` est encore en ligne mais n'est plus celui de la cohorte | [J] |
| Final Project : « Build a Data Pipeline That Feeds an AI Model », **sujet libre**, cinq exigences, 10 min + 5 min de questions, équipes de 2 ou 3 conseillées | [J] |
| Gabarit de slides lié par l'énoncé (Google Slides) | [J] |
| Planning : Airflow 17 et 18/09, Great Expectations 21/09, GitHub Actions 22/09, Final Project 23 à 25/09 | [D] `.ics` |
| Fiche RNCP41993 : seul l'**AIA 4** prend le Final Project de la Lead comme support ; AIA 1, 2, 3 = Spotify, Stripe, Fraud Detection | [J] |
| Fiche RNCP35288 : projets imposés par bloc (Kayak ; **Tinder** + Steam ; Walmart, Conversion, Uber ; AT&T ; Getaround ; Final Project) ; démo **en direct**, 7 à 8 slides ; plus d'inscriptions depuis le 10/02/2026 | [J] |
| Courriel de Jedha du 11/09 : accès aux contenus pour CDSD 1, 4, 5 (`path/full-stack-full-time`) et AIA 2, 3, 4 (`path/dse-lead`) ; **l'AIA 1 n'est pas cité** alors que le contrat porte BC01 à BC04 | [M] |
| Courriel du 16/09 (Guilhem, program@) : reprise du dossier, retour « d'ici la fin de semaine » | [M] |
| Référentiels complets lus : voir `08_exigences_par_bloc.md` | [R] |
| Énoncés AIA lus (Spotify, Stripe, Fraud Detection) : voir `08_exigences_par_bloc.md` §6 | [J] |
| Contenu du parcours Lead v2 relevé : Airbyte vers Snowflake ; Kafka (Avro, Schema Registry, Debezium) ; dbt sur Snowflake (dbt Studio) ; Iceberg avec **PyIceberg** et DuckDB ; Airflow ; Great Expectations ; GitHub Actions ; pile locale Docker, PostgreSQL, DuckDB, PySpark (Java 17 ou plus) ; exercice PySpark « in-game purchases » (jeu vidéo) | [J] |
| Page Julie « Build Your First Iceberg Table » (`build-your-first-iceberg-table`) : erreur de la plateforme ; la bonne adresse est `first-steps-with-iceberg-lead-data-v2` | [J] |
| Les pages de `dse-lead` ne s'affichent qu'en y accédant par clic depuis le parcours | [J] |

### Existant sur le disque

| Élément | Emplacement | Source |
|---|---|---|
| Dossier du litige et plan du 12/09 | `Downloads/Dossier-Jedha/` (`00-INDEX.md`, `06-rapports/plan_de_production_10_blocs.md`) | [D] |
| Référentiels PDF CDSD et AIA | `Dossier-Jedha/02-certification/` | [D] |
| Dépôts de coaching clonés | `Dossier-Jedha/03-plateforme/depots-coaching/` | [D] |
| Liens GitHub des coachings | `Jedha_Exercices/AIA/**/*.txt` | [D] |
| Projets CDSD 3 (Walmart, Conversion, Uber) | `Jedha_Exercices/Data_Full_stack/Machine _Learning/Exercices_Projet_BLOC_3_Certif/` | [D] |
| Projet Churn et **gabarit de slides Demo Day** | `Jedha_Exercices/Data_Essentiels/Projet_Final/` | [D] |
| Dépôt bancaire (bloc 6 du CDSD) | `D:/banking_dataops_monitoring_demoday` | [D] |
| **Tinder / Speed Dating** : données, dictionnaire, énoncé exporté | `Downloads/Speed+Dating+Data.csv`, `Downloads/Speed+Dating+Data.Key.doc`, `D:/JEDHA_JULIE/GLOBALC_COURS_MASTER/01_CORPUS_SOURCE_NORMALISE/02_data_analysis_fullstack_fulltime_v2/06_crawl_detaille/pages_text/*speed-dating*` ; **aucun notebook réalisé trouvé** | [D] |
| Notebook de départ **Kayak**, mal rangé | `Jedha_Exercices/AIA/Bloc 1/bloc1_data_gouv/01-Plan_your_trip_with_Kayak.ipynb` | [D] |
| Squelettes MLOps, gouvernance, Terraform | `D:/BACKUP_G/swiss-data-ai-engineering-lab/` | [D] |
| Livres et parses | `D:/Bibliotheque_Ultime_KOS_IA`, `..._Qwen_Parse` | [D] |
| Dépôts publics KinSushi utiles | `jedha-rncp35288-portfolio`, `fraud-mlops-control-tower`, `banking-dataops-monitoring`, `secure-wealth-rag-assistant` (données synthétiques) ; forks de coaching ; `dbt-jaffle-shop` | [X] API GitHub |

### Construction et mesures

| Fait | Source |
|---|---|
| Projet choisi : **ReviewPulse** (sentiment des avis Steam), aligné sur le thème imposé du CDSD 4 | décision |
| Premier code produit par le banc gratuit (26 fichiers), puis corrections successives ; un hook interdit l'écriture directe du code | [X] |
| 6 000 avis naturels, 0 au second passage ; défaut « dossier du manifeste absent » trouvé en réel et corrigé | [X] |
| Modèle mots : F1 0,735 ; quatre variantes : 0,756 à 0,766 ; retenu : caractères 2-5 (F1 0,759, rappel 0,639) | [X] ADR 0006 |
| Flux négatif complémentaire : F1 0,750 → 0,798 sur le même test ; stack déployée : **0,807**, AUC 0,948 | [X] ADR 0007 |
| Barrière de promotion 0,80 → 0,75 après mesure | [X] ADR 0008 |
| Défauts trouvés en réel et corrigés : artefacts MLflow relatifs, écriture non-root, inversion de convention (entraînement puis score), healthcheck du tableau de bord, URL d'API codée en dur, uid Airflow, `SystemExit` dans Streamlit, dates sans fuseau | [X] ADR 0009 à 0012 |
| Tests inverses : premier passage faussement 13/13 (copie incomplète) ; avec témoin : 10/13, puis **13/13** après trois tests ajoutés | [X] `evidence/reverse_tests.md` |
| Test de la stack déployée : **12/12** ; il échoue bien quand on le pousse à échouer | [X] `evidence/forward_test.md` |
| Documentation générée par le banc : affirmations fausses détectées (dont « anonymat ») ; réécrite depuis `06_carte_des_modules.md` ; AST identique vérifié | [X] |
| Relecture par `glm-4.7-flash-local` : 2 146 s puis refus du repli `qwen3.5:9b` ; inutilisable | [X] |
| `nexus_valide --base main` : verdict RAS mais code de sortie 1 (docstrings comptées comme fonctions touchées) | [X] signalé à NEXUS |
| Dépôt privé `KinSushi/reviewpulse` créé ; CI verte sur `main` ; commits avec `Co-Authored-By` → historique propre recréé localement (`propre-main`, `propre-premium`), **suppression du dépôt GitHub à faire par Enzo** | [X] |
| Great Expectations 1.23.0 : compatible, API mesurée, suite et Data Docs en place ; toutes les attentes passent sur les données réelles | [X] |
| Pile du programme testée : PySpark 4.2.0 + Java 21, PyIceberg 0.12.0 (catalogue SQLite), DuckDB 1.5.5 (`iceberg_scan` fonctionne), dbt-core 1.12.5 + dbt-duckdb 1.11.0, confluent-kafka 2.15.1 | [X] |
| Conflit : dbt-core ≥ 1.10 exige protobuf 6, refusé par MLflow 2.17 et Streamlit 1.40 ; pyiceberg 0.12 refuse pyarrow 17 | [X] |
| Résolution trouvée : **MLflow 3.16.0**, **Streamlit 1.60.0**, pyarrow 24, protobuf 6 ; image serveur `ghcr.io/mlflow/mlflow:v3.16.0` disponible | [X] |
| Après mise à jour : `ImportError: DEFAULT_EXCLUDED_CONTENT_TYPES` de `starlette.middleware.gzip` → FastAPI 0.115.5 trop ancien pour MLflow 3.16 → **FastAPI 0.141.1** ; **54 tests réussis** | [X] ADR 0013 |
| Image Airflow complète : conflits avec les fournisseurs Google, Snowflake, Azure ; **SQLAlchemy remplacé par la 2.0**, incompatible avec Airflow 2.10 (masqué au premier passage par une sortie tronquée de `pip check`) | [X] |
| Image Airflow `slim` : pas de Java 21 sur Debian 12 → Java 17 ; projet isolé dans `/opt/rp-venv` ; DAG via `ExternalPythonOperator` ; deux `pip check` propres | [X] ADR 0013 |
| Serveur MLflow 3.16 : 403 « Invalid Host header » depuis les conteneurs → `--allowed-hosts` | [X] ADR 0013 |
| Registre MLflow 2 repris par le serveur 3.16 sans action ; job réel : 19 nouveaux avis, version 6 (F1 0,793) non promue, champion version 2 | [X] |
| Avertissement MLflow 3 : `artifact_path` obsolète → `name` ; corrigé ; 54 tests réussis, lint propre | [X] |
| Airflow (`ExternalPythonOperator`) : une exécution manuelle attend derrière l'exécution planifiée à cause de `max_active_runs=1` (comportement voulu) ; mettre le DAG en pause bloque la file | [X] |
| `gx_validate` en échec dans Airflow : `data/quality_reports` appartenait à **root**, créé par mon essai manuel lancé en root ; propriété rendue à 1000:0 ; ensuite **deux exécutions quotidiennes réussies, 4 tâches sur 4** | [X] |
| **Règle** : tout conteneur lancé à la main sur `./data` ou `docs/evidence` doit tourner avec `--user 1000:0` | [X] |
| **Quasi-erreur** : le rapport `forward_test.md` lu après la mise à jour était l'**ancien** (écriture refusée, fichier root) ; seul le code de sortie 1 l'a révélé. Règle : vérifier la **date du rapport** avant de le citer | [X] |
| Test de stack sous MLflow 3 : **12/12** (22:57 UTC, commit `a274445+mlflow3`) ; 6 023 avis naturels uniques, 2 798 complémentaires | [X] `evidence/forward_test.md` |
| Tests inverses sous MLflow 3 : **13/13**, témoin 54 tests (23:11 UTC) | [X] `evidence/reverse_tests.md` |
| API PyIceberg mesurée : refus de `timestamp[ns]` ; `schema()` est une méthode ; `as_arrow()` en `large_string` ; `cast` lève `ValueError` sur colonnes différentes | [X] ADR 0014 |
| Brique Spark → Iceberg produite ; défauts corrigés : syntaxe pandas sur une colonne Spark, namespace passé en liste, conversion ns→us qui réutilisait l'ancien schéma, dates sans fuseau après `toPandas()` ; **Hadoop exige un nom pour l'uid 1000** (image de développement corrigée) | [X] |
| **Divergence Spark/pandas trouvée sur données réelles** (11 textes sur 8 800 : U+00A0, U+2028) ; correctif `(?U)\s+` ; test enrichi, qui **échoue sans le correctif** | [X] ADR 0014 |
| Équivalence stricte sur **8 231 lignes réelles** ; Spark 7,8 s contre pandas 1,7 s ; table `silver.reviews` écrite | [X] |
| Régression de documentation dans `score.py` (lignes « Pourquoi » et « Preuves » supprimées par le banc) : à rétablir à la prochaine passe | [X] backlog |
| Commit `a56708e` (pile du programme, Spark, Iceberg) ; aucune mention d'outil | [X] |
| Image applicative : Java 21 et utilisateur nommé uid 1000 ajoutés ; job Compose aligné sur le DAG (ingest → spark_silver → expectations → train → score) | [X] |
| **Défaut de conception** : le catalogue Iceberg enregistre des chemins **absolus** ; table créée sous `/data` introuvable pour un conteneur voyant le lac sous `/app/data` → **lac monté sous `/data` dans tous les conteneurs** | [X] ADR 0014, `docker-compose.yml` |
| Job Compose réel complet : 10 nouveaux avis ; silver 8 241 lignes ; Great Expectations OK ; version 7 (F1 0,796) non promue ; score champion v2 ; table `silver.predictions` 8 241 lignes | [X] |
| Message « 3 snapshots créés » trompeur (c'est la taille de l'historique) | [X] backlog |
| Pile du programme vérifiée sur Julie ; **Tinder** = projet « Speed Dating » (CDSD 2) ; données dans `Downloads` ; aucun notebook réalisé | [J] [D] |
| DAG dans Airflow : `spark_silver` échoue, `ModuleNotFoundError: No module named 'pandas'` dans le worker Python de Spark (la `pandas_udf` tourne avec l'interpréteur d'Airflow) | [X] |
| 1er correctif (conf `spark.pyspark.python`) **inopérant** en réel malgré un test vert : le test lisait la conf, pas l'interpréteur utilisé. Lecture de PySpark 4.2 : `SparkContext.pythonExec = os.environ.get("PYSPARK_PYTHON", "python3")` | [X] `pyspark/core/context.py:342` |
| 2e correctif : `os.environ.setdefault("PYSPARK_PYTHON", sys.executable)` avant la session ; test sur `sparkContext.pythonExec`, **qui échoue sans le correctif** (témoin) ; 4/4 | [X] |
| Scheduler Airflow arrêté au démarrage (« database is locked », SQLite) quand des commandes CLI sont lancées pendant son initialisation → attendre ~2 min après un redémarrage | [X] |
| Leçon : un test doit vérifier l'effet réel, pas la configuration qu'on croit utile | [X] |
| DAG quotidien `spark_v3` : **ingest, spark_silver (18 s), gx_validate, score en succès dans Airflow** (17/09, 00:26 UTC) ; DAG remis en pause | [X] |
| Gold dbt-duckdb : **`dbt build` réel 43/43 PASS** (silver Iceberg → DuckDB, 8 241 avis) ; parts négatives prédites proches du réel (Nightreign 14,2 % contre 17,7 %) | [X] |
| Rendu du banc pour dbt inutilisable tel quel (colonnes et macros inventées, commentaires SQL dans du YAML, config dupliquée) → SQL et YAML réécrits à la main d'après les schémas mesurés | [X] |
| dbt-duckdb garde sa connexion ouverte dans le processus : ouverture `read_only` refusée juste après ; banc qui « ajuste » les données d'un test pour coller à ses attentes fausses → corrigé | [X] |
| `conftest.py` ne redirigeait ni `LAKEHOUSE_DIR` ni `GX_DIR` : un `pytest` lancé depuis la racine aurait écrit dans le vrai lac → corrigé | [X] |
| **62 tests verts** (54 + 4 Spark + 4 dbt) ; témoin : le test de fraîcheur échoue sans `assert_every_review_is_scored` | [X] |
| DAG : tâche `gold` après `score` (quotidien et hebdomadaire), rappels d'alerte (échec, SLA 1 h) vers le journal d'Airflow ; `tags` sortis de `default_args` | [X] |
| **Incident disque (16/09, soir)** : C: plein (0 Go à 19:40 selon la session local-llm-docker ; 2,8 Go mesurés ensuite). Cache de construction Docker 24 Go dont 19 récupérables. **Cause : mes Dockerfiles copiaient le code avant `pip install`** ; chaque modification reconstruisait la couche de ~3 Go. Les images `pipeline`, `api`, `dashboard` sont une seule image (15 Ko propres chacune) | [X] |
| Correctifs sans reconstruction : dépendances avant le code dans les deux Dockerfiles ; une seule image `reviewpulse-app` ; `.dockerignore`. Nettoyage du cache et compaction du disque virtuel : **décision d'Enzo** | [X] |
| `docker builder prune` (autorisé par Enzo : « fais ce qu'il convient ») : 19,22 Go libérés **dans** le disque virtuel, mais rien rendu à Windows (C: 2,6 Go). Image `reviewpulse-app` reconstruite en 221 s ; la reconstruction Airflow a saturé C: (« Read-only file system », moteur en erreur 500) | [X] |
| Consigne d'Enzo : **construire sur D: (3 To), ne garder sur C: que le reproductible et léger**. Lac copié vers `D:\ReviewPulse_work\data` ; `docker-compose.override.yml` local (non versionné) monte ce dossier sous `/data` ; le dépôt garde `./data` par défaut | [U] [X] |
| Déplacement du disque de Docker Desktop vers `D:\DockerDesktop` : à faire par Enzo dans l'interface (redémarre Docker, donc aussi la passerelle local-llm-docker, à prévenir avant et après) | [U] |
| Consigne d'Enzo : **tout ce qui concerne ReviewPulse passe sur D:**. Projet déplacé vers `D:\ReviewPulse_work\ReviewPulse` (396 fichiers, copie vérifiée : aucun écart robocopy, `git status` propre, `git fsck` sans erreur) ; fichiers de travail vers `D:\ReviewPulse_work\session_scratch`. 82 fichiers OneDrive restent dans l'ancien dossier sur C: : leur suppression est refusée à ma session, **à supprimer par Enzo** (doublons vérifiés) | [U] [X] |
| 20:30–20:45 : Enzo a supprimé toutes les images Docker et lancé la bascule du disque vers `D:\Program Files\DockerDesktopWSL` ; à 20:39, les deux copies (63,7 Go) existent encore, Docker est arrêté, et le réglage n'est pas enregistré. Rien à lancer avant la confirmation de la session local-llm-docker | [U] [X] |
| Consigne d'Enzo : **rendre tout durable et reprenable** → `docs/11_reprise.md` (emplacements, état, blocages, étapes, règles), README et mémoire persistante mis à jour | [U] |
| 18/09, sans Docker : carte des modules complétée par le banc gratuit pour `lakehouse.py`, `spark_silver.py`, `expectations.py`, `gold.py` ; trois inventions corrigées après vérification dans le code (test `test_lakehouse.py` inexistant, ADR 0013 cité à tort deux fois, fichier de test « non identifié » alors que `test_expectations.py` existe) | [U] [X] |
| Docstring ajoutée à `_hash_steamid` ; contrôle AST : code identique hors documentation | [X] |
| S1-7 déjà satisfait par les ADR 0013 et 0014 ; `score.py` déjà documenté (5 objets sur 5) : les deux lignes du backlog sont closes | [X] |
| 18/09 : CI complétée (Java 17 temurin, `JAVA_TOOL_OPTIONS: -Xss4m`) ; contrôle par analyse YAML : Java présent avant l'installation des dépendances dans les deux jobs | [X] |
| Mutations M14, M15, M16 (Spark et Iceberg) ajoutées ; pour chacune, l'ancre existe une seule fois dans le fichier cible et le code muté reste syntaxiquement valide (contrôle AST) | [X] |
| Contrôles F7 et F8 écrits dans `tools/forward_test.py`, inscrits dans la liste ordonnée ; ils n'emploient que `read_table` et `table_history`, réellement présents dans `lakehouse.py`. Documentation de F8 corrigée : elle annonçait une comparaison avec F7 que le code ne fait pas | [X] |
| Deux ADR mal cités par le banc dans les mutations, corrigés : espaces Unicode → ADR 0014, priorité de dédoublonnage → ADR 0002 | [X] |
| Ces trois travaux sont **écrits et contrôlés statiquement, jamais exécutés** : la CI demande le dépôt en ligne, les mutations et les contrôles demandent Docker | [X] |
| 18/09 : Model Card rédigée par le banc puis contrôlée : aucun chiffre absent des sources, hyperparamètres conformes à `train.py` (char_wb 2-5, min_df 2, 100 000 traits, C=4.0, max_iter=2000), rétention 30 jours conforme à `config.RAW_RETENTION_DAYS` | [X] |
| Trois corrections apportées à la Model Card : 48 tests → 62 ; base légale présentée comme à valider par le DPO et non comme acquise ; identité du modèle renseignée depuis `config.MODEL_NAME` | [X] |

### Questions ouvertes (à Jedha)

1. Passage du Demo Day seul ou en équipe ; heure de passage.
2. Réemploi du Final Project pour l'AIA 4 : confirmer ; un même système devant deux jurys ?
3. CDSD 4 : le référentiel impose le sentiment, le projet imposé est AT&T (spam).
4. AIA 1 absent du courriel du 11/09 alors que le contrat le prévoit.

### Actions en attente d'Enzo

1. Supprimer le dépôt GitHub `KinSushi/reviewpulse` (il contient les commits avec la mention d'outil), puis me le dire pour que je le recrée depuis l'historique propre.
2. Valider le seuil de promotion de 0,75.
3. Autoriser la création du secret `REVIEWPULSE_SALT` dans le dépôt (sinon le workflow planifié échouera chaque jour).
