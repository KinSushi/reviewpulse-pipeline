# Carte des modules — où, quoi, comment, pourquoi

Ordre d'exécution de la chaîne : **ingest → transform (+ quality) → train → score → api / dashboard**, orchestrée par `dags/reviewpulse_daily.py` et `.github/workflows/pipeline.yml`. `config` et `decision` sont transverses.

---

## `config.py`

- **Rôle** : source unique des paramètres (chemins, source, seuils, schéma de la zone propre, sel).
- **Place** : importé par tous les modules ; lu **au moment de l'appel** (`config.X`), jamais copié à l'import, pour que les tests puissent rediriger les chemins.
- **Choix** : tout paramètre modifiable passe par une variable d'environnement (même image en local, dans Airflow et dans GitHub Actions). `salt()` n'a **aucune valeur par défaut** (ADR 0004). `F1_MACRO_MIN = 0.75` (ADR 0008). `THRESHOLD_GRID` de 0,30 à 0,80 par pas de 0,025 (ADR 0007).
- **Tests** : tous, via la fixture `data_env`.

## `decision.py`

- **Rôle** : seule définition de la convention de décision : étiquette 0 = négatif, 1 = positif ; prédiction négative si `proba_negative >= seuil`.
- **Place** : appelé par `train`, `score`, `api` et le tableau de bord.
- **Pourquoi il existe** : la convention a été inversée deux fois le 16/09/2026 (F1 = 0 à l'entraînement ; 95 % de négatifs prédits pour 4 % réels au score). ADR 0009.
- **Choix** : `negative_proba` lit `model.classes_` au lieu de supposer que la colonne 0 est la classe 0.
- **Tests** : `test_decision.py` (dont un test de sens de bout en bout), `test_api.py`.

## `ingest.py`

- **Rôle** : collecter les avis Steam et les déposer **tels que reçus** dans la zone brute, sans doublon.
- **Place** : première étape ; alimente `transform`.
- **Fonctionnement** : pour chaque jeu et chaque langue, flux naturel (`MAX_PAGES` pages) puis flux négatif complémentaire (`BOOST_MAX_PAGES` pages, `review_type=negative`) ; pagination par curseur ; arrêt sur page vide, page sans nouvel avis, curseur répété ou nombre maximal de pages ; nouvelles tentatives sur 429 et 5xx avec attente exponentielle ; écriture du manifeste puis du lot par fichiers temporaires et `os.replace`.
- **Choix** : manifeste par flux (ADR 0002) ; le type d'avis demandé découle **uniquement** du flux, pour ne jamais écrire d'avis positifs dans la partition négative ; chemins du flux naturel inchangés pour rester compatible avec les données déjà collectées.
- **Preuves** : 16/09/2026, 6 000 avis puis 0 au passage suivant ; défaut « dossier du manifeste absent » trouvé en exécution réelle et corrigé.
- **Tests** : `test_ingest.py`, `test_fresh_dirs.py`, `test_boost.py`.

## `transform.py`

- **Rôle** : produire la zone propre, pseudonymisée et typée, **seulement si** les contrôles qualité passent.
- **Place** : après `ingest`, avant `train` et `score`.
- **Fonctionnement** : lecture de tous les JSONL (le flux est déduit de la partition `sample=`, `natural` par défaut) ; dédoublonnage (priorité au flux naturel, puis à la mise à jour la plus récente) ; suppression des balises BBCode et des textes vides ; types ; `author_pseudo` par HMAC-SHA256 salé ; suppression des identifiants directs ; `quality.assert_quality` ; écriture atomique ; purge de la zone brute au-delà de 30 jours.
- **Choix** : pandas (ADR 0003) ; pseudonymisation (ADR 0004) ; contrôle bloquant avant écriture (ADR 0005).
- **Preuves** : sans sel, la tâche s'arrête et la zone propre n'est pas modifiée (16/09/2026).
- **Tests** : `test_transform_quality.py`, `test_fresh_dirs.py`, `test_boost.py`.

## `quality.py`

- **Rôle** : dire si la zone propre est utilisable ; lever une erreur sinon.
- **Contrôles** : colonnes et types, au moins une ligne, identifiant non nul et unique, étiquette 0 ou 1, langue autorisée, texte non vide, aucune colonne interdite, pseudonyme en 64 caractères hexadécimaux, flux connu, part de négatifs **naturels** entre 0,5 % et 95 %.
- **Choix** : renvoyer **tous** les échecs d'un coup (diagnostic complet en une exécution). ADR 0005.
- **Tests** : `test_transform_quality.py`, `test_boost.py`.

## `train.py`

- **Rôle** : entraîner, mesurer, enregistrer et, si c'est mérité, promouvoir le modèle.
- **Place** : après `transform` ; DAG hebdomadaire ; alimente `score` et `api` via le registre MLflow.
- **Fonctionnement** : test de 20 % tiré **uniquement** des avis naturels ; entraînement = reste des naturels + tous les négatifs complémentaires ; seuil choisi par validation croisée 5 plis sur les naturels d'entraînement ; modèle final ; métriques au seuil retenu ; enregistrement, alias `challenger`, promotion `champion` si F1 ≥ 0,75 et strictement meilleur.
- **Choix** : n-grammes de caractères + régression logistique (ADR 0006, quatre variantes mesurées) ; flux complémentaire et seuil appris (ADR 0007) ; barrière (ADR 0008) ; pas d'`input_example` car le chemin générique de MLflow passe un tableau au vectoriseur (erreur « 'int' object has no attribute 'lower' » constatée) ; `mlflow.log_dict` et emplacement absolu des artefacts (ADR 0010).
- **Preuves** : F1 0,807 sur test naturel, AUC 0,948 ; réentraînement identique → mêmes métriques, non promu.
- **Tests** : `test_train_score.py`, `test_boost.py`, `test_decision.py`, `test_artifacts_location.py`, `test_fresh_dirs.py`.

## `score.py`

- **Rôle** : charger le champion, scorer la zone propre, produire le résumé quotidien.
- **Place** : après `train` (ou directement après `transform` dans le DAG quotidien) ; alimente le tableau de bord et `/insights`.
- **Choix** : seuil lu sur le modèle (il voyage avec lui) ; résumé limité aux avis **naturels** (sinon la part négative serait gonflée par le flux complémentaire) ; horodatage `pd.Timestamp.now(tz="UTC")`.
- **Preuves** : part prédite ÷ part réelle entre 0,79 et 1,21 par jeu et langue (16/09/2026).
- **Tests** : `test_train_score.py`, `test_boost.py`, `test_decision.py`.

## `api.py`

- **Rôle** : servir le champion : `/health`, `/predict`, `/insights`.
- **Choix** : chargement paresseux et mis en cache **seulement en cas de succès** : l'API démarre même sans modèle et répond **503** jusqu'à ce qu'un champion existe, puis le charge sans redémarrage (constaté le 16/09/2026) ; 1 à 100 textes de 1 à 5 000 caractères (422 sinon) ; aucun texte journalisé ; seuil renvoyé avec chaque prédiction ; fenêtre de `/insights` comptée depuis la dernière date disponible (démo rejouable).
- **Tests** : `test_api.py`, `test_artifacts_location.py` ; contrôles A1 à A4 de `tools/forward_test.py`.

## `dashboard/app.py`

- **Rôle** : restitution pour la ou le community manager.
- **Choix** : avis naturels seulement ; aucune information d'auteur ; texte tronqué à 200 caractères ; parts négatives calculées sur les étiquettes (pas sur les probabilités) ; URL de l'API lue dans `REVIEWPULSE_API_URL` (dans Docker, `localhost` désigne le conteneur du tableau de bord) ; appel direct à `main()` (un `SystemExit` bloque le moteur de test Streamlit).
- **Preuves** : défauts vus dans le navigateur le 16/09/2026 et corrigés (part réelle affichée = part positive ; plantage sur les dates du résumé).
- **Tests** : `test_dashboard.py` (exécution réelle du script avec `AppTest`).

## `dags/reviewpulse_daily.py`

- **Rôle** : automatiser la chaîne (quotidien : ingest → transform_and_check → score ; hebdomadaire : train → score).
- **Choix** : chaque tâche appelle le `main()` du module et échoue si le code de retour est non nul ; deux nouvelles tentatives à 5 minutes ; pas de rattrapage. ADR 0011.
- **Preuves** : exécutions réussies dans Airflow le 16/09/2026 après alignement de l'uid.

## `lakehouse.py`

- **Rôle** : gestion du lakehouse Iceberg (catalogue, tables, lecture/écriture) sans Spark.
- **Place** : utilisé par `spark_silver.py` pour écrire la table `silver.reviews` et par `score.py` (ou les tests) pour lire les tables Iceberg.
- **Fonctionnement** : crée le répertoire configuré, instancie un `SqlCatalog` SQLite, crée le namespace `silver` si absent, fournit `write_table` (conversion timestamps ns→us, création ou validation du schéma, `overwrite` → nouveau snapshot), `read_table` (scan → `pyarrow.Table`), `table_history` (liste des snapshots) et un `main` minimal, sans logique autonome, qui renvoie 0.
- **Choix** : aucune évolution de schéma silencieuse — l'écriture est refusée si les colonnes changent (`ValueError`) ; conversion explicite des timestamps nanosecondes en microsecondes avant écriture (ADR 0014).
- **Tests** : `tests/test_spark_silver.py` (écriture, historique, schéma incompatible refusé), `tests/test_gold.py`.

## `spark_silver.py`

- **Rôle** : construire la zone « silver » avec Spark, reproduire le résultat de `transform.clean`, puis persister en parquet et Iceberg.
- **Place** : s’insère après `ingest` et avant les contrôles Great Expectations, alimente `score` et la couche gold.
- **Fonctionnement** : crée une `SparkSession` avec les variables d’environnement appropriées, lit les fichiers JSONL bruts, extrait les partitions (`app_id`, `language`, `sample_source`), nettoie le texte (suppression BBCode, espaces Unicode), dédoublonne selon priorité `natural`/`negative_boost`, crée les colonnes dérivées (`review_id`, `label`, timestamps, scores, etc.), pseudonymise le `steamid` via `pandas_udf` HMAC-SHA256, sélectionne les colonnes définies dans `config.CLEAN_COLUMNS`, convertit en pandas, localise les timestamps en UTC, cast les types, trie par `review_id`; convertit le DataFrame pandas en `pyarrow.Table` en castant les timestamps en µs, écrit le parquet (`transform.write_clean`) puis Iceberg (`lakehouse.write_table`), purge les données brutes.
- **Choix** : spark uniquement pour la lecture/traitement massif, puis pandas pour réutiliser les fonctions existantes (ADR 0014) ; gestion explicite de `PYSPARK_PYTHON`/`PYSPARK_DRIVER_PYTHON` ; `pandas_udf` pour HMAC afin d’éviter les limites Spark natives ; chaque `overwrite` crée un snapshot, garantissant l’idempotence.
- **Tests** : `tests/test_spark_silver.py`.

## `expectations.py`

- **Rôle** : définir et exécuter une suite Great Expectations sur la zone propre, générant un rapport HTML exploitable.
- **Place** : exécuté après `transform.main` (écriture du parquet) et avant `score.main` dans le DAG quotidien.
- **Fonctionnement** : `build_expectations` crée la liste d’attentes (ordre des colonnes, comptage de lignes, non-null, unicité, ensembles autorisés, longueur texte, bornes de scores, format du pseudo) ; `validate` crée ou réutilise un contexte (éphémère ou fourni) et exécute la suite, `_summarize` construit un dictionnaire de synthèse ; `run_and_document` crée un contexte « file », exécute la suite, génère les Data Docs et renvoie le chemin `index.html` ; `main` lit le parquet, lance la génération et renvoie un code de sortie selon le succès.
- **Choix** : contexte éphémère par défaut pour les tests unitaires, contexte « file » pour la persistance du rapport, réinitialisation du contexte avant chaque exécution afin d’éviter les duplications, messages d’erreur normalisés pour faciliter les assertions.
- **Tests** : `tests/test_expectations.py`.

## `gold.py`

- **Rôle** : orchestrer la construction de l’entrepôt DuckDB via dbt après l’étape `score`.
- **Place** : s’exécute dans le DAG quotidien après `score`, fournit la couche *gold* aux analystes.
- **Fonctionnement** : `silver_vars` récupère les `metadata_location` des tables Iceberg `silver.reviews` et `silver.predictions` via `lakehouse.get_catalog`; `_prepare_env` crée les répertoires `GOLD_DIR` et `DUCKDB_EXT_DIR` et définit les variables d’environnement requises par dbt; `run_dbt` construit la ligne de commande dbt avec les répertoires configurés et les variables JSON, puis invoque `dbtRunner`; `main` exécute `dbt build`, journalise le comptage des statuts, arrête le pipeline en cas d’échec, exécute `dbt docs generate` et consigne le chemin du fichier DuckDB final.
- **Choix** : utilisation de l’API Python `dbtRunner` plutôt que d’un sous-processus, passage des métadonnées Iceberg via `--vars` JSON, création explicite des répertoires et des variables d’environnement pour garantir la reproductibilité.
- **Tests** : `tests/test_gold.py`.

## `explain.py`

- **Rôle** : expliquer une prédiction, globalement et avis par avis.
- **Place** : lecture seule sur le modèle champion ; destiné au tableau de bord et à la Model Card, sans écriture disque ni appel à MLflow.
- **Fonctionnement** : `global_terms` classe les coefficients du modèle par valeur absolue et rend les termes qui poussent vers « négatif » et vers « positif » ; `local_contributions` multiplie, pour un texte, chaque valeur TF-IDF par le coefficient de la classe négative, écarte les traits de valeur nulle, trie par valeur absolue et rend les `n` premiers ; `explain_batch` vectorise toute la liste en une fois. L'indice de la classe négative est cherché dans `clf.classes_`, comme dans `decision.negative_proba`, et le signe des coefficients en découle.
- **Choix** : contribution linéaire exacte (le modèle est une régression logistique sur TF-IDF), donc pas besoin d'approximation par échantillonnage ; `ValueError` explicite si le modèle ne porte pas les étapes « tfidf » et « clf ».
- **Tests** : `tests/test_explain.py` (tri et troncature, terme absent, somme des contributions égale à la fonction de décision, signes des termes globaux, cohérence de `explain_batch`) — **exécutés et verts** depuis le 18/09/2026. Mutation M21 : le signe des coefficients de la classe négative.

## `drift.py`

- **Rôle** : mesurer la dérive des données d'entrée et celle des prédictions.
- **Place** : tâche `drift` du DAG quotidien, après `score` ; lit la zone propre et le résumé quotidien, écrit le rapport et, le cas échéant, une alerte.
- **Fonctionnement** : `psi_numerique` et `psi_categoriel` calculent l'indice de stabilité de population, les bornes venant des quantiles de la fenêtre de référence ; `derive_entrees` l'applique à `text_len`, `language`, `app_id` et `sample_source`, en ignorant une colonne absente ; `derive_predictions` compare `share_negative_pred` à `share_negative_true` du résumé quotidien et marque les lignes hors bornes, en sautant les groupes de moins de `n_min` avis ; `interpretation` classe l'indice en « stable », « à surveiller » ou « dérive » ; `main` **filtre d'abord le flux naturel** — le flux `negative_boost` est une collecte ponctuelle qui n'arrive jamais en production —, coupe le reste en deux fenêtres selon `created_at`, la plus ancienne servant de référence, écrit `drift_report.json` dans la zone scorée, puis `evaluer_alerte` rend un verdict et `ecrire_alerte` dépose un fichier daté dans `scored/alertes/` quand un seuil est franchi. Seules les colonnes de `COLONNES_ALERTE` peuvent lever une alerte.
- **Choix** : indice de stabilité de population plutôt qu'un test statistique, car il se lit par seuils (0,1 et 0,2) et supporte les variables catégorielles ; aucune écriture hors du dossier de données, aucun appel à MLflow. `language` et `app_id` restent **informatifs** : leur composition vient de notre plan de collecte, pas d'une population observée (mesure du 19/09/2026, ADR 0015).
- **Tests** : `tests/test_drift.py`, **onze tests verts** le 19/09/2026, dont `test_evaluer_alerte_ignore_les_colonnes_de_collecte` et son témoin. Mutations M19 et M20.

## `expectations_lake.py`

- **Rôle** : porter les attentes Great Expectations des zones **silver (Iceberg)** et **gold (DuckDB)**, que `expectations.py` ne couvre pas.
- **Place** : tâche `gx_lake` du DAG quotidien, après `gold` ; porte bloquante, le code de retour arrête le DAG.
- **Fonctionnement** : quatre constructeurs d'attentes (`attentes_silver_reviews`, `attentes_silver_predictions`, `attentes_gold_faits`, `attentes_gold_mart`) ; `valider` exécute une suite sur un DataFrame dans un contexte éphémère et rend `{"suite", "success", "evaluees", "echecs"}` ; `lire_silver` passe par `lakehouse.read_table`, `lire_gold` par une connexion DuckDB en lecture seule ; `main(argv)` accepte `--zone silver|gold|toutes` et rend 1 dès qu'une suite échoue.
- **Choix** : module **distinct** de `expectations.py`, qui fonctionne et garde la zone propre — on n'a pas voulu refondre une porte de qualité à quelques jours de la soutenance. `main` accepte une liste d'arguments parce qu'un module lancé par Airflow ne peut pas lire `sys.argv` : il appartient au processus hôte.
- **Tests** : `tests/test_expectations_lake.py`, **sept tests verts**, dont le témoin (une table conforme passe). Mutations M23 et M24.

## `rollback.py`

- **Rôle** : ramener le modèle en service sur une version antérieure, en déplaçant l'alias `champion`.
- **Place** : hors DAG, à la main ou par `make rollback VERSION=n` ; lit et écrit le registre MLflow, rien d'autre.
- **Fonctionnement** : `versions_disponibles` liste les versions avec leurs métriques et leurs alias ; `champion_actuel` rend la version portant l'alias ; `basculer` vérifie que la version cible existe — sinon `ValueError` —, relève l'ancienne, déplace l'alias et rend `{"ancienne", "nouvelle"}` ; `main` affiche l'historique sans `--vers`, bascule avec.
- **Choix** : déplacer un alias plutôt que recopier un artefact — l'opération est atomique côté registre et se défait par la commande inverse. L'horodatage est calculé par `datetime.fromtimestamp(ts / 1000, tz=timezone.utc)`.
- **Tests** : `tests/test_rollback.py`, **six tests verts** avec un faux client MLflow, dont un témoin. Mutations M25 et M26. Vérifié **en réel** le 19/09/2026 : champion 2 → 1, puis 1 → 2.

## `tools/forward_test.py` et `tools/reverse_tests.py`

- **`forward_test.py`** : contrôle la stack **déployée** (API, tableau de bord, MLflow, fichiers réels) et écrit un rapport daté dans `docs/evidence/`.
- **`reverse_tests.py`** : injecte des défauts connus dans une copie du code et vérifie que la batterie de tests les détecte ; rapport dans `docs/evidence/`.

## `tools/comparaison_modeles.py`

- **Rôle** : répondre par une mesure à « ne peut-on pas obtenir un meilleur score avec un autre modèle ? ». Compare le modèle en service à huit autres candidats de familles différentes — SVM linéaire, SGD, Bayes naïf complémentaire, Ridge, gradient boosting sur SVD, forêt aléatoire, XGBoost, régression logistique sur mots.
- **Place** : hors chaîne ; lit la zone propre, écrit `docs/evidence/comparaison_modeles.md`. Tourne à la demande sur un runner GitHub (`.github/workflows/comparaison.yml`).
- **Fonctionnement** : les **mêmes plis** pour tous les candidats ; le flux complémentaire d'avis négatifs ajouté à l'entraînement de chaque pli, jamais à la validation ; probabilités hors plis par `decision.negative_proba` ; seuil choisi sur `config.THRESHOLD_GRID` avec le même départage que `train.py`. Rend F1 macro, seuil, AUC, rappel et précision des négatifs, coût d'entraînement, latence pour 1 000 avis, et si l'explication terme par terme reste exacte.
- **Choix** : le candidat en service est `train.build_pipeline()` tel quel — c'est le **témoin** du banc. XGBoost n'est pas une dépendance du projet : absent, il s'écrit « non mesuré » et l'outil ne tombe pas. La décision qui en découle est l'ADR 0030.
- **Tests** : `tests/test_comparaison_modeles.py`, six tests, dont le témoin (le candidat en service **est** le pipeline du projet) et celui qui compte (aucun avis du flux complémentaire n'est jamais validé).

## Les portes d'un module réécrit

- **`tools/appliquer_enrichissement.sh`** enchaîne cinq portes avant de remplacer un fichier rendu par un modèle : syntaxe ; `tools/citations_perdues.sh` (aucune citation perdue ni inventée) ; `tools/explication_appauvrie.sh` (la nouvelle version n'explique pas moins) ; `tools/verifier_equivalence.sh` (arbre syntaxique identique, docstrings et journaux retirés) ; copie de l'original en quarantaine.
- **`tools/tester_portes.sh`** éprouve ces portes par dix-huit témoins, chaque tolérance avec le refus voisin ; **`tools/verifier_journaux.sh`** refuse qu'un journal écrive un texte d'avis, un identifiant, le sel ou un DataFrame ; **`tools/verifier_chiffres.sh`** refuse qu'un document tourné vers le jury contredise le dépôt ; **`tools/lint_conteneur.sh`** passe `ruff` dans l'image de dev avant un envoi. Détail et mesures : `docs/23_standard_agents.md`.
