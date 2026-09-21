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
| soir | Historique Git à assainir : les commits de l'ancien dépôt portaient des lignes de paternité automatiques ; dépôt à recréer (choix d'Enzo) | [U] |
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
| Dépôt privé `KinSushi/reviewpulse` créé ; CI verte sur `main` ; commits portant des lignes de paternité automatiques → historique propre recréé localement (`propre-main`, `propre-premium`), **suppression du dépôt GitHub à faire par Enzo** | [X] |
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
| 18/09 : module `explain.py` (explicabilité) et ses cinq tests produits par le banc. Deux défauts corrigés après relecture : l'indice de la classe négative était calculé puis neutralisé par un `noqa` (le signe ne dépendait donc pas de l'ordre des classes), et le test de la somme comparait dix contributions tronquées à la fonction de décision complète — il ne pouvait que mentir | [X] |
| Ces fichiers **n'ont jamais été exécutés** : scikit-learn n'est pas installé sur l'hôte, et c'est voulu (les dépendances restent dans les images) | [X] |
| 18/09 : note d'orientation technologique rédigée ; contrôle des chiffres et des numéros d'ADR : aucun nombre étranger aux sources, aucun ADR inexistant cité | [X] |
| Correction : le banc annonçait « pandas 1,7 s, Spark 5,3 s » en mélangeant deux mesures de l'ADR 0014 (comparaison pandas 1,7 s / Spark 7,8 s sur 8 231 lignes, et `spark_silver.main()` en 5,3 s) | [X] |
| 18/09 : plan de monitoring rédigé ; contrôle des noms cités : `quality.check_clean`, `config.SUMMARY_FILE`, suite `zone_propre`, DAG `reviewpulse_weekly_train` existent bien | [X] |
| Correction : le banc plaçait les zones brute et propre sous `lakehouse/`, alors qu'elles sont sous `data/` (`config.RAW_DIR`, `config.CLEAN_FILE`) | [X] |
| 18/09 : module `drift.py` et six tests produits ; contrôles : colonnes employées conformes à `config.CLEAN_COLUMNS` (`created_at`, `text_len`, `language`, `app_id`, `sample_source`), attributs de `config` tous existants, tolérances des tests explicites et non triviales | [X] |
| README complété d'une ligne datée : les chiffres du 16/09 valent pour 48 tests ; l'état au 18/09 est distinct et non encore exécuté | [X] |
| 18/09 : ADR 0015 (surveillance de la dérive) et ADR 0016 (déploiement progressif) rédigés, statut « proposée », inscrits au registre ; aucun chiffre étranger aux sources | [X] |
| Correction dans l'ADR 0016 : « le hash modulo 1 » n'a pas de sens ; le texte décrit maintenant les huit premiers octets du hachage ramenés dans [0, 1) | [X] |
| 18/09, 05:30 : Docker rebasculé sur D: en moteur WSL 2 (`D:\DockerDesktop\DockerDesktopWSL`). Le blocage « owners mismatch » venait d'un seul dossier, `D:\DockerDesktop\DockerDesktop`, créé au nom de `dibac` ; un `icacls /setowner` ciblé l'a levé | [X] |
| Le lac a survécu à la perte du volume Docker : il est monté depuis D:, écriture comprise. Seuls le registre MLflow et les artefacts avaient été détruits | [X] |
| Images reconstruites : `reviewpulse-app` 3,38 Go (36 min), `reviewpulse-dev` 3,35 Go | [X] |
| **Batterie : 73 tests, 68 verts, 5 rouges.** Les 62 tests d'origine passent. Les échecs sont dans le code écrit le 18/09 sans pouvoir l'exécuter : 4 dans `explain.py` (`coo_matrix` n'a pas d'attribut `indices`, ligne 201) et 1 dans `tests/test_drift.py` (`np.random.choice(..., random_state=...)`, argument inexistant — défaut du test, pas du module) | [X] |
| **Pipeline complet réussi** : ingest → spark → gx → train → score → gold ; dbt 43/43, catalogue généré | [X] |
| **F1 macro 0,782** (et non 0,807), rappel négatif 0,595, précision 0,611, AUC 0,931, F1 en validation croisée 0,809. **Explication vérifiée** : l'étape d'ingestion a collecté 223 avis nouveaux sur la source vivante (9 partitions datées du 18/09, zone brute passée de 8 831 à 9 054 lignes). Le jeu de test a changé (1 239 lignes contre ~1 195) : ce n'est pas une régression de code, c'est un jeu de données différent | [X] |
| Modèle promu `champion` version 1 : la barrière F1 ≥ 0,75 est respectée. Le registre repart de zéro, comme prévu après la perte du volume | [X] |
| **Test de stack : 14 contrôles sur 14**, F7 et F8 compris — leur première exécution réelle. `docs/evidence/forward_test.md` régénéré | [X] |
| Les tests inverses attendent la correction des cinq échecs : `reverse_tests.py` lance `pytest -x`, donc chaque mutation s'arrêterait sur l'échec d'`explain`, sans rapport avec elle | [X] |
| Correctifs en attente du banc gratuit : la passerelle `localhost:4000` ne répond pas (seuls `litellm-db` et `litellm-redis` tournent) ; délai demandé à la session local-llm-docker | [X] |
| 18/09, 09:10 : passerelle du banc rétablie par la session local-llm-docker (le retard venait d'un `initdb` Postgres interrompu par la migration, pas du téléchargement). Les deux correctifs ont donc été produits par le banc, comme le veut le contrat | [X] |
| Correctif `explain.py` : `X.multiply(coeff_neg)` rend une matrice COO, sans attribut `indices` ; conversion en CSR. Le banc a repéré le **même défaut latent dans `explain_batch`**, jamais atteint par les tests en échec | [X] |
| Correctif `tests/test_drift.py` : `np.random.choice(..., random_state=…)` remplacé par `np.random.default_rng(graine).choice(...)`, trois graines distinctes, seuils inchangés | [X] |
| Vérification par exécution : **11 tests sur 11 au vert** sur `test_explain.py` et `test_drift.py` | [X] |
| 18/09 : **batterie complète 73 tests sur 73**, en 31 min, après les deux correctifs | [X] |
| **DAG à 5 tâches : 5/5** (ingest 9 s, spark_silver 17 s, gx 8 s, score 10 s, gold 14 s), `gold` exécutée dans Airflow pour la première fois. Défaut rencontré et compris : solliciter Airflow pendant son démarrage tue le scheduler (SQLite verrouillé) — attendre quatre minutes avant toute commande | [X] |
| Défaut d'outillage corrigé : `reverse_tests.py` imposait un délai de 600 s par exécution, hérité d'une batterie de 2 min ; elle dure 31 min. `TimeoutExpired` n'était pas capturé. Délai désormais paramétrable (`--timeout`, défaut 3 600 s), dépassement rendu comme échec explicite | [X] |
| **Reproductibilité mesurée.** Trois entraînements ont donné 0,782 (08:12), puis 0,797 (11:00), puis **0,797 exactement identique** (11:05) : `f1_macro=0.7972008452503808`, `recall=0.6339285714285714`, `roc_auc=0.9350803650372617`, `n_train=7225`, `n_test=1243`. Conclusion : **le code est déterministe** (graine 42), et **la seule source de variation est l'ingestion en direct** — 223 avis nouveaux le matin, d'autres après le DAG | [X] |
| La barrière de promotion s'est comportée comme documentée : le troisième entraînement, à métriques égales, **n'a pas été promu** (`promoted: false`) | [X] |
| Failles de reproductibilité restantes : aucune empreinte du jeu de données n'est enregistrée dans les runs MLflow ; les images de base sont épinglées par étiquette et non par empreinte (`python:3.11-slim`, `apache/airflow:slim-2.10.3-python3.11`) ; aucun mode « jeu gelé » documenté pour rejouer un entraînement à l'identique ; aucune procédure de restauration depuis un instantané Iceberg | [X] |
| 18/09, 12:54 : **tests inverses 16 sur 16 TUÉES**, témoin vert (43 tests, 12 min). Les trois mutations Spark et Iceberg sont détectées : M14 et M15 par `test_spark_vs_pandas`, M16 par `test_lakehouse_write_and_history` | [X] |
| Outil rendu praticable : chaque mutation déclare le fichier de test censé la détecter, l'outil ne lance que celui-là, et le rapport porte une colonne « Portée ». Durée passée de plusieurs heures à 20 minutes. La correspondance des treize mutations d'origine a été **récupérée dans l'historique git**, le rapport ayant été écrasé par l'exécution ratée du matin | [X] |
| Batterie depuis un dossier temporaire : **73 sur 73**. L'échec du témoin de 10:47 était donc une instabilité ponctuelle, non un défaut lié au chemin | [X] |
| Régression que j'avais introduite et corrigée : l'empreinte du jeu de données ouvrait la zone propre sans vérifier son existence, alors que les tests entraînent depuis un tableau en mémoire | [X] |
| CI : le workflow ne se déclenchait que sur `main`, alors que tout le travail est sur `plateforme-v3` — il n'aurait jamais tourné. Il se déclenche désormais sur toutes les branches | [X] |
| 18/09, phase 1 : **dérive et explicabilité branchées**. Tâche `drift` ajoutée au DAG entre `score` et `gold` ; cible `make drift` ; point d'entrée **`POST /explain`** dans l'API (contributions locales et termes globaux) ; section « Termes qui pèsent » dans le tableau de bord, qui tient enfin la promesse de la charte | [X] |
| Le tableau de bord ne charge aucun modèle : il interroge l'API. L'explicabilité passe donc par l'API, ce qui la rend disponible pour tout consommateur | [X] |
| **Défaut sémantique trouvé dans `explain.global_terms`** : la liste « négative » retenait les coefficients inférieurs à zéro, c'est-à-dire les termes qui poussent vers le positif — les deux listes désignaient la même direction. Corrigé : les deux listes portent désormais des coefficients positifs, qui expriment une force | [X] |
| **Un test avait été écrit pour épouser ce défaut** (`test_global_terms_n_et_signes` exigeait des coefficients négatifs). Il est corrigé et vérifie maintenant un effet réel : coefficients strictement positifs des deux côtés, et listes disjointes | [X] |
| Quatre tests ajoutés pour `/explain` (contributions présentes dans le texte soumis, tri par valeur absolue, dix termes globaux de chaque côté, texte vide refusé en 422). **25 tests verts** sur le périmètre touché | [X] |
| Récidive du marqueur tronqué par le banc, sur `AVANT` cette fois, avec en prime une ancre abrégée par des points de suspension. Artefact conservé intact (`phase1.jsonl`) et signalé à la session local-llm-docker. Remède employé : fournir moi-même l'ancre exacte et un gabarit littéral dans la consigne | [X] |
| 19/09, 08:26 : **DAG à six tâches, 6 sur 6**, `drift` exécutée pour la première fois dans Airflow. Le scheduler a survécu à une interrogation par minute pendant toute l'exécution — c'est le test du correctif, puisque c'est cet usage qui le tuait | [X] |
| **Airflow migré de SQLite vers PostgreSQL** (service `airflow-db`, `LocalExecutor`). Trois défauts successifs trouvés par l'exécution : test de santé sans délai de grâce (la première initialisation dépasse 50 s) ; pilote `psycopg2` absent de l'image slim ; et surtout un correctif du banc qui avait **supprimé la ligne `USER airflow`**, installant le pilote pour `root` — le conteneur a bouclé toute la nuit sur la même erreur | [X] |
| Leçon d'outillage : `nexus_appliquer.py` affiche « RETIRE : le bloc supprime N ligne(s) de l'AVANT absente(s) de l'APRES ». J'ai traité ce message comme du bruit ; c'est un **signal d'alerte** disant que le remplacement perd des lignes. Il doit interrompre, pas informer | [X] |
| 19/09 : **registre de suivi créé** (`docs/16_registre_suivi.md`) — 26 sujets ouverts, 13 fermés avec leur preuve, chacun avec critère de fin et prochaine action. Il manquait : rien ne garantissait qu'un sujet ancien ne disparaisse par oubli de contexte | [U] [X] |
| Contrôle mécanique ajouté au rituel : `python -m compileall` sur `src`, `tools`, `dags`, `dashboard`, `tests` — code de sortie 0 le 19/09 | [X] |
| Matrice de réversibilité écrite (`docs/15_reversibilite.md`) et **étiquette `preuves-2026-09-19`** posée sur le dernier état prouvé : git devient un point de retour nommé, pas seulement un historique | [X] |
| Constat git : `main` (2 commits) et `plateforme-v3` (24 commits) **n'ont aucun ancêtre commun** — deux départs distincts, pas une divergence. La lecture « 2 commits d'avance » donnée hier était fausse | [X] |
| 19/09 : **présentation du Demo Day construite** à partir du gabarit Jedha existant (le projet Telco d'Enzo) : thème, mises en page et **logo conservés par construction**. Neuf diapositives, aucun texte Telco résiduel, archive valide | [U] [X] |
| Le script `tools/construire_slides.py` régénère le fichier à l'identique depuis le gabarit : la présentation est reproductible, et son contenu traçable jusqu'aux chiffres du dépôt | [X] |
| Script minuté écrit (`docs/presentation/script_10_minutes.md`) : la démonstration en direct occupe 2 min 30 au cœur des dix minutes, avec chemin de secours si l'API Steam ou un service manque | [X] |
| Contrôle visuel non automatisable ici : ni LibreOffice ni convertisseur PDF sur la machine, et rien ne doit être installé sur l'hôte. À ouvrir par Enzo | [X] |

### Questions ouvertes (à Jedha)

1. Passage du Demo Day seul ou en équipe ; heure de passage.
2. Réemploi du Final Project pour l'AIA 4 : confirmer ; un même système devant deux jurys ?
3. CDSD 4 : le référentiel impose le sentiment, le projet imposé est AT&T (spam).
4. AIA 1 absent du courriel du 11/09 alors que le contrat le prévoit.

### Actions en attente d'Enzo

1. Supprimer le dépôt GitHub `KinSushi/reviewpulse` (il contient les commits avec la mention d'outil), puis me le dire pour que je le recrée depuis l'historique propre.
2. Valider le seuil de promotion de 0,75.
3. Autoriser la création du secret `REVIEWPULSE_SALT` dans le dépôt (sinon le workflow planifié échouera chaque jour).

---

## 19/09/2026 — après-midi

### Cinq défauts réels, tous trouvés par un outil

| Heure | Fait | Source |
|---|---|---|
| 15 h | **`import os` absent de `train.py`** : 6 échecs et 5 erreurs dans la batterie. Trouvé par le **témoin** des tests inverses. J'avais pris le premier signal, la veille, pour une intermittence — c'était faux. Corrigé, batterie **84 verte** en 45 min | [X] |
| 15 h | Le contrôle **F10** encodait une attente contredite par le contrat dbt documenté (`fct_review_predictions` garde les deux flux). Contrôle corrigé, pas la donnée. Test de stack **16 sur 16** | [X] |
| 15 h | Le banc de tests inverses ne recopiait pas `dbt/`, donc `test_gold.py` — le seul qui détecte M18 — ne pouvait pas tourner dans la copie temporaire | [X] |
| 16 h | **La dérive mesurait notre plan de collecte, pas la population.** Fenêtre ancienne à 85 % francophone, récente à 91 % anglophone : PSI 3,10 sur la langue, sans qu'aucun avis n'ait changé de nature. Mesure désormais sur le flux naturel seul, et seules les colonnes de `COLONNES_ALERTE` peuvent alerter. ADR 0015 révisée | [X] |
| 16 h | `pipeline.yml` exécutait encore `ingest → transform → train → score`, la chaîne d'avant Spark, Iceberg et dbt. Aligné sur le DAG quotidien | [D] |

### Ce qui a été outillé et prouvé

| Heure | Fait | Source |
|---|---|---|
| 14 h | **Retour arrière réel** : champion 2 → 1, vérifié, puis 1 → 2, vérifié | [X] |
| 15 h | **Restauration d'un instantané Iceberg** : `lakehouse.read_table_at` et `restore_snapshot`, `make snapshots`, test avec témoin (la lecture d'instantané ne modifie pas la table). 19 instantanés réels sur `silver.reviews` | [X] |
| 16 h | **Alerte de dérive hors du journal Airflow** : fichier daté portant motifs, horodatage UTC et commit. Réentraînement déclenché par `ShortCircuitOperator` puis `TriggerDagRunOperator`, **en dérivation** pour que la zone gold ne soit jamais sautée | [X] |
| 16 h | **Sauvegarde du registre MLflow hors du volume Docker** : archive de 15 Mo (277 Mo d'artefacts), restaurée dans un volume d'essai, versions 1 à 4 et alias champion retrouvés | [X] |
| 16 h | **Les dix schémas** refaits et rendus. `make diagrams` échoue si un schéma est invalide : c'est ce qui a trouvé trois erreurs de syntaxe. Trois contresens corrigés, une affirmation non tenue retirée (RACI avec DPO) | [X] |
| 16 h | **Images de base épinglées par empreinte**. Confirmation indépendante : le `docker pull` de `python:3.11-slim` a rendu exactement l'empreinte épinglée | [X] |
| 17 h | **Les huit PDF du cas Spotify, lus** dans un conteneur avec `pypdf`, rien installé sur la machine. 56 pages. Correction d'une note antérieure : le critère de sélection du vrai PDF est l'**en-tête `%PDF-`**, pas la taille | [D] |
| 17 h | `docs/17_gouvernance.md` écrit sur les six tâches du cas ; chaque manque nommé | [D] |
| 17 h | **Great Expectations sur silver et gold** : 4 suites, 28 attentes, toutes vertes sur les données réelles ; témoin : deux valeurs faussées donnent `success=False`. Tâche `gx_lake` après `gold`, DAG à **9 tâches** | [X] |
| 17 h | Constructeur de diapositives piloté par **spécification JSON**, une par soutenance ; refonte prouvée non régressive (deck reproduit **au bit près**) ; il refuse désormais un indice de run inexistant. Présentation **AIA 4** produite | [X] |

### Reste à faire, dans l'ordre

1. Batterie sur l'arbre courant, puis **24 mutations** seules (le premier lancement a expiré, la machine portant déjà la batterie).
2. Reconstruire les trois images, bases épinglées.
3. Déclencher `reviewpulse_daily` en réel : 9 tâches attendues.
4. Rafraîchir les chiffres partout : `docs/evidence/`, README, `05_conformite_demo_day.md`, le deck du Demo Day (9 054 → 9 271 lignes brutes ; 9 → 19 instantanés ; 14 → 16 contrôles ; 6 → 9 tâches ; 73 → 84 tests ; 16 → 24 mutations) et `script_10_minutes.md`.
5. Quatre présentations sur six restent à produire : CDSD, AIA 1, AIA 2, AIA 3.

## 20/09/2026

| Moment | Fait | Source |
|---|---|---|
| nuit | **DAG quotidien exécuté en réel, 9 tâches** : 8 vertes, 1 sautée par conception (dérive sous le seuil). 4 suites Great Expectations sur silver et gold, **29 attentes**, 0 échec | [X] `evidence/dag_execution_reelle.md` |
| matin | Batterie complète sur copie neuve : **131 tests verts** | [X] `evidence/campagne_20260920-045514.log` |
| matin | **Réglage des hyperparamètres** : 12 points, validation croisée 5 plis ; `C=10.0` retenu, version 5 **promue** par la barrière (F1 macro 0,8027), qui refuse le même jour un modèle à l'ancienne valeur | [X] `evidence/reglage_hyperparametres.md` |
| midi | **Dépôt propre publié** : `KinSushi/reviewpulse-pipeline`, intégration continue verte ; `pipeline.yml` sur un runner vierge, zone brute vide : 5 798 avis collectés en direct, modèle entraîné et promu (F1 0,7982) | [X] onglet Actions |
| après-midi | **27 mutations sur 27 tuées en un seul passage**, en CI. La 27e retire le verrou du premier chargement du modèle : `/health` avait mesuré 184 s sous ses propres contrôles de santé concurrents | [X] ADR 0029, R55 |
| après-midi | Point d'accès `/metrics` (p50, p95, p99, sans dépendance nouvelle), décidé par arbitrage entre trois familles de modèles ; trois défauts du code rendu corrigés à l'audit | [X] ADR 0029 |
| 18 h 55 | **Toute la pile tombe** (blocage du disque externe). Relancée ; historique MLflow et Airflow intact | [X] R64 |
| soir | Rapport sur les données, guide de l'API, runbook de déploiement, neuf ADR (0021 à 0029), supports AIA 2 et AIA 3, **discours du Demo Day mot pour mot**, sept réponses « Comment le projet se prouve » | [D] |
| soir | Point de reprise **`KG-2026-09-20-c`** : tous les niveaux franchis, preuves de niveau 4 et 5 venues d'un runner GitHub | [X] `19_known_good.md` |

## Nuit du 20 au 21/09/2026 — « le dépôt est très insuffisant »

Enzo lit le dépôt sur GitHub et le dit sans détour : très insuffisant, projet pas achevé, code pas
premium. Les trois étaient vrais, et visibles en dix minutes de lecture. La nuit leur répond.

### Ce qui a été trouvé

| Moment | Constat | Source |
|---|---|---|
| 22 h | Le README était un journal de mesures : chiffres périmés (26 mutations, douze décisions, quatre points d'accès), chaîne décrite en v1, historique du 16/09 en pleine page | [X] lecture sur GitHub |
| 22 h | Un module enrichi sur dix-neuf était publié. Le modèle local rendait un module en quinze minutes, et cinq rendus sur neuf étaient refusés | [X] R66 |
| 23 h | La grille de conformité datait du 16/09 : cases ouvertes pour le dépôt, les diapositives et Great Expectations — tous faits | [X] `grep` des cases ouvertes |
| 00 h 30 | **La première capture réelle du tableau de bord affiche « version du modèle 2, seuil 0,750 »** : les scores sur disque dataient d'avant la promotion de la version 5 | [X] `docs/captures/` |
| 00 h 40 | **Le serveur web d'Airflow était mort** depuis la panne de disque : planificateur vivant, interface injoignable | [X] `ps` dans le conteneur |

### Ce qui a été fait

| Moment | Fait | Source |
|---|---|---|
| 22 h 30 | Quota cloud revenu : le modèle local est arrêté, **19 modules envoyés à cinq familles cloud en parallèle** | [X] |
| 23 h – 01 h | **19 modules de production sur 19 au standard**, chacun à travers les portes mécaniques ; CI verte sur la branche de travail puis sur `main` : batterie et 27 mutations avec le code premium | [X] onglet Actions |
| 23 h – 01 h | Les portes sont durcies et assouplies **par la mesure**, chaque règle avec son témoin : citations inventées refusées ; réparation typographique (un module ne se perd plus pour une espace fine) ; ordre des imports de tête ; `except X as exc` de pur journal ; bloc conditionnel de pur journal à condition sans effet de bord ; **non-appauvrissement** | [X] `tools/tester_portes.sh`, 18 témoins |
| 23 h 30 | README réécrit : problème et utilisateur, chaîne réelle à 9 tâches, données, choix ML contre LLM, preuves, limites. Noms des trois jeux vérifiés auprès de l'API Steam | [D] |
| 00 h | Relecture croisée par trois familles : **435 constats, plus de la moitié faux** — 19 « fuites » signalées sur des journaux qui n'écrivent que des comptes. Le contrôle d'arbre tranche : 207 appels, 0 fautif | [X] `tools/verifier_journaux.sh` |
| 00 h 30 | Arbitrage par une troisième famille : 3 modules améliorés ; 9 rendus refusés, amaigris ou tronqués | [X] `tools/explication_appauvrie.sh` |
| 00 h 30 | Captures réelles par un Chromium piloté, dans l'image Mermaid déjà présente : documentation de l'API, registre MLflow (champion version 5, challenger version 6 refusé) | [X] `tools/capture_ecrans.js` |
| 00 h 47 | Conteneur Airflow redémarré, interface à 200 ; **DAG quotidien relancé avec le code premium** | [X] `premium-20260921-0048` |
| vers 1 h | Quota cloud de nouveau épuisé (les appels expirent) ; reset à 2 h 00. Restent quatre outils à porter au standard : lot prêt | [X] |

### La leçon

Je mesurais l'avancement à mon registre et à la CI, jamais à ce que voit un lecteur. Un registre à
jour ne prouve pas qu'un dépôt est présentable : il faut l'ouvrir dans un navigateur et le lire
comme un inconnu, chasser les chiffres périmés, et **regarder les écrans** — c'est une capture qui
a trouvé le modèle périmé du tableau de bord et l'interface morte d'Airflow, pas un test.
