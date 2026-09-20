# Questions probables du jury — réponses et preuves

Chaque réponse renvoie à une preuve consultable. **Les chiffres des sections métier sont ceux du 16/09/2026** ; ceux de la section « Architecture, choix et décisions » sont ceux du jour de chaque décision. Les mesures courantes sont dans `docs/evidence/`.

---

## Cas métier et données

**Pourquoi ce sujet ?**
Une équipe community & live-ops reçoit des centaines d'avis par jour en plusieurs langues et repère les problèmes avec retard. L'étiquette `voted_up` est fournie par l'auteur lui-même : la qualité se mesure sans annotation. → `01_charte.md`, ADR 0001.

**Ces données sont-elles « réelles et sales » comme l'exige l'énoncé ?**
Oui : flux mis à jour en continu, BBCode, textes vides, doublons entre passages, plus de vingt langues, 9 % seulement d'avis négatifs. → ADR 0001, `transform.py`.

**Avez-vous le droit de les utiliser ?**
API publique sans clé ; usage analytique agrégé, sans republication des textes ; les conditions d'utilisation de Steam sont à citer dans le dossier. Données personnelles traitées selon l'ADR 0004.

**Qui possède la donnée ?**
Valve et les auteurs des avis. → Charte.

## Architecture et pipeline

**Montrez-moi que la zone brute est inchangée.**
Une ligne = l'objet reçu, écrit par `json.dumps` ; le test `test_ingest.py` relit chaque ligne et la compare à l'objet reçu. → ADR 0002.

**Que se passe-t-il si je relance l'ingestion deux fois ?**
Rien de nouveau n'est écrit : 6 000 avis puis 0 le 16/09. Le contrôle F1 du test réel vérifie, **par flux et sur tous les fichiers**, autant de lignes que d'identifiants distincts (6 005 / 6 005 et 2 797 / 2 797). → `evidence/forward_test.md`.

**Et si le programme s'arrête au milieu ?**
Manifeste puis lot sont écrits dans des fichiers temporaires puis renommés : aucun avis brut n'existe sans être référencé. → ADR 0002.

**Pourquoi pandas et pas Spark ?**
Quelques milliers de lignes, quelques Mo : Spark coûterait une JVM pour rien. Seuil de bascule écrit : environ 10 millions d'avis. → ADR 0003.

**Où est votre test de qualité ?**
Une série de contrôles bloquants (liste exhaustive dans l'ADR 0005) avant l'écriture de la zone propre ; un échec arrête la tâche et laisse la zone précédente intacte. → ADR 0005.

**Comment savez-vous que vos tests servent à quelque chose ?**
Tests inverses : **26 défauts graves** injectés un par un dans une copie du code, **26 détectés**, chacun par un test nommé ; la mesure témoin sans défaut passe. Deux mutations avaient survécu au passage du 19/09 — la porte de qualité n'était pas prouvée bloquante, et un test était satisfait par la mauvaise cause, `pytest.raises(ValueError)` étant honoré par la bibliothèque elle-même. Les deux trous ont été comblés, puis les deux mutations rejouées et tuées. → `evidence/reverse_tests.md`.

**Pourquoi DuckDB comme entrepôt, et pas une base de documents type MongoDB ?**
Parce qu'elles ne répondent pas à la même question. La zone gold sert des agrégations SQL sur des colonnes — part d'avis négatifs par jeu, par langue et par jour, calculée sur des Parquet — c'est un travail OLAP, et DuckDB le fait en local, sans serveur, avec des contrats et des tests dbt. Une base de documents est un magasin **opérationnel** : elle excelle à stocker et mettre à jour des objets JSON pour une application, pas à balayer des colonnes. Le seul endroit où elle aurait un sens ici est la zone brute, qui reçoit bien des documents JSON de l'API Steam ; nous y avons préféré des fichiers immuables, parce que c'est cette immuabilité qui fonde l'idempotence et la réversibilité (ADR 0002) et qu'elle ne demande aucun service à maintenir le jour de la démonstration. Le choix de DuckDB face à **Snowflake**, lui, est tranché dans l'ADR 0013 : la démonstration ne doit dépendre d'aucun compte externe, et changer d'entrepôt revient à changer d'adaptateur dbt et de profil.

## Données personnelles et conformité

**Vos données sont-elles anonymes ?**
**Non, pseudonymisées.** `steamid` est remplacé par un HMAC-SHA256 salé ; pseudonyme, profil et avatar sont supprimés. Une donnée pseudonymisée reste une donnée personnelle au sens du RGPD. → ADR 0004.

**Pourquoi un HMAC et pas un simple SHA-256 ?**
Les `steamid` sont des entiers sur 17 chiffres, énumérables : un hachage simple se renverse par dictionnaire.

**Que se passe-t-il sans sel ?**
Le job s'arrête avec un message explicite et la zone propre n'est pas modifiée (vérifié le 16/09). → ADR 0004.

**Et l'AI Act ?**
Classement de sentiment sur des avis de produits, sans décision sur des personnes : risque minimal. La transparence est assurée (seuil et version affichés).

## Modèle

**Pourquoi pas un LLM ?**
L'étiquette est fournie : une classification linéaire résout la tâche en secondes, s'explique terme par terme et ne coûte rien à servir. → ADR 0006.

**Pourquoi des n-grammes de caractères ?**
Quatre variantes mesurées ; celle-ci a le meilleur rappel des négatifs (0,639) pour un F1 équivalent, avec un seul vectoriseur, et tolère fautes et mélange de langues. → ADR 0006.

**Quel est votre chiffre de qualité ?**
Champion en service au 20/09/2026, **version 5** : F1 macro **0,8027** sur un test **100 % naturel** tenu à l'écart, AUC **0,940**, rappel **0,650** et précision **0,633** sur les négatifs, sur 8 768 lignes. La mesure du 16/09 — F1 0,807, AUC 0,948 — portait sur un jeu plus petit ; les deux ne sont pas comparables, et le dire vaut mieux que choisir le plus flatteur. Le gain de la version 5 vient du réglage des hyperparamètres : `C=10.0` retenu sur une recherche à 12 points, puis **promu par la barrière**, qui a **refusé** le même jour un réentraînement à `C=4.0`. → README, ADR 0006, ADR 0007, ADR 0008.

**Comment gérez-vous le déséquilibre ?**
Pondération des classes, plus un flux d'avis négatifs réels **réservé à l'entraînement**. Le test reste naturel, sinon la mesure serait flatteuse. Gain mesuré sur le même test : F1 0,750 → 0,798. → ADR 0007.

**Comment avez-vous choisi le seuil de 0,75 ?**
Par validation croisée sur les données d'entraînement uniquement, jamais sur le test. → ADR 0007.

**Votre modèle est-il cohérent en production ?**
Pour chaque jeu et chaque langue, la part négative prédite vaut entre 0,797 et 1,209 fois la part réelle (contrôle F4, tolérance fixée à [0,5 ; 2]). → `evidence/forward_test.md`.

**Un avis sur deux signalé comme négatif est-il faux ?**
C'était le cas avant l'amélioration (précision 0,50) ; c'est maintenant environ un sur trois (0,657). Pour un outil de **priorisation de lecture**, une lecture inutile coûte peu ; le rappel compte davantage.

**Comment expliquez-vous une prédiction ?**
Modèle linéaire : les 20 termes les plus négatifs et positifs sont enregistrés à chaque entraînement (`artifacts/top_terms.json` dans MLflow).

## Industrialisation

**Que se passe-t-il si le nouveau modèle est moins bon ?**
Il n'est pas promu : la version 5, entraînée par le DAG hebdomadaire (F1 0,798), n'a pas remplacé la version 2 (F1 0,807). → ADR 0008.

**Et s'il est exactement aussi bon ?**
Pas de promotion non plus (« strictement meilleur ») : la version 3, entraînée sur les mêmes données, a donné **exactement les mêmes métriques** — preuve de reproductibilité.

**Comment revenir en arrière ?**
Déplacer l'alias `champion` vers la version précédente dans MLflow ; l'API la charge au redémarrage.

**Que se passe-t-il à la première installation, sans modèle ?**
L'API démarre et répond 503 « Modèle indisponible », puis charge le champion dès qu'il existe, sans redémarrage (constaté le 16/09). → ADR 0008.

**Qu'est-ce qui tourne tout seul ?**
Deux DAG Airflow (quotidien et hebdomadaire, une exécution à la fois, deux nouvelles tentatives) et un workflow GitHub Actions planifié indépendant de la machine locale. → ADR 0011.

**Avez-vous eu des problèmes au déploiement ?**
Oui, et ils sont documentés : modèle introuvable (artefacts relatifs au dossier courant), écriture refusée pour l'utilisateur non-root, droits différents entre Airflow et l'application, contrôle de santé du tableau de bord sur le mauvais port, URL de l'API codée en dur, inversion de la convention de décision. Chacun a sa correction et, quand c'est possible, son test. → ADR 0009, 0010, 0011, 0012.

**Comment prouvez-vous que tout marche ailleurs que sur votre poste ?**
`make up && make jobs && make evidence` : tests unitaires, tests inverses et test de la stack déployée, avec rapports datés et numéro de commit. → `evidence/`.

## Architecture, choix et décisions

Chaque décision structurante a son ADR. Les renvois `→ ADR NNNN` pointent vers le registre [`adr/README.md`](adr/README.md), qui compte **vingt décisions** au 19/09/2026.

**Les chiffres cités ci-dessous sont ceux du jour de la décision**, pas ceux d'aujourd'hui : c'est ce qui les rend vérifiables. Les mesures courantes vivent dans `docs/evidence/`. Quand une décision a été révisée, la réponse le dit.

`tools/verifier_justifications.py` vérifie mécaniquement que chaque ADR est cité dans le code **et** ici, et signale tout renvoi vers un ADR qui n'existe pas.

**Pourquoi avez‑vous choisi d’utiliser l’API publique de Steam et ces trois jeux pour le cas métier ?**  
Nous aidons l’équipe community & live‑ops à prioriser les avis négatifs en récupérant les avis via l’API publique `store.steampowered.com/appreviews/<appid>?json=1` pour les jeux 1903340, 1086940 et 2622380, en anglais et français. L’API ne nécessite aucune clé et fournit entre 23 172 et 504 467 avis par jeu et langue, assurant un flux réel et idempotent. Les jeux de données statiques (Kaggle, Hugging Face) ont été écartés car figés, le scraping a été rejeté pour ses conditions d’utilisation restrictives, les données synthétiques du Demo Day ne correspondaient pas à l’exigence d’authenticité, et les actualités RSS avec LLM manquaient d’étiquette fiable. → ADR 0001.

**Comment garantissez‑vous l’idempotence de l’ingestion et pourquoi ne pas simplement dédoublonner en aval ?**  
Nous stockons chaque avis brut tel que reçu en ligne JSONL, partitionné par `app_id`, `language` et `date`, et nous utilisons un manifeste listant les identifiants déjà écrits ; seuls les nouveaux avis sont écrits puis le manifeste est remplacé atomiquement. La pagination s’arrête dès qu’une page ne contient aucun nouvel avis, est vide, ou que le curseur se répète. Un test du 16/09/2026 a montré 6 000 avis au premier passage et 0 au second, prouvant l’absence de doublons. Le dédoublonnage en aval a été rejeté car la zone brute aurait grossi indéfiniment, l’ajout de métadonnées aurait violé le critère « inchangé », et une base de données pour le manifeste était jugée surdimensionnée. → ADR 0002.

**Pourquoi avez‑vous retenu pandas pour la transformation alors que PySpark ou dbt étaient possibles ?**  
Le volume réel est d’environ 10 000 avis (8 797 lignes brutes le 16/09/2026), soit quelques mégaoctets, ce qui rend pandas très rapide (temps de transformation de l’ordre de la seconde) et simple à utiliser en un seul fichier Parquet réécrit atomiquement. PySpark a été écarté car le démarrage d’une JVM pour quelques Mo serait coûteux sans bénéfice, et dbt supposait un entrepôt SQL alors que le nettoyage de texte et le HMAC sont plus lisibles en Python. → ADR 0003.

**Quelle méthode de pseudonymisation avez‑vous adoptée et pourquoi le sel est‑il obligatoire ?**  
Nous générons `author_pseudo = HMAC‑SHA256(sel, steamid)` puis supprimons `personaname`, `profile_url`, `avatar` et `steamid`. Le sel (`REVIEWPULSE_SALT`) est un secret obligatoire sans valeur par défaut ; l’application refuse de démarrer si le sel est absent ou vide. Un simple SHA‑256 a été rejeté car réversible par dictionnaire, la suppression pure de `steamid` aurait perdu l’analyse par auteur, et le contrôle du sel via Docker Compose a échoué le 16/09/2026 en bloquant `docker compose ps` et `down`. → ADR 0004.

**Comment les contrôles qualité sont‑ils bloquants et quels seuils avez‑vous fixé ?**  
`quality.check_clean` valide avant l’écriture de la zone propre que les colonnes et types sont exacts, qu’il y a au moins une ligne, que les identifiants sont non nuls et uniques, que l’étiquette appartient à {0, 1}, que la langue est autorisée, que le texte n’est pas vide, qu’aucune colonne interdite n’est présente, que le format du pseudonyme est correct, que le flux est connu, et que la part des négatifs naturels se situe entre 0,5 % et 95 %. Tout échec lève une exception Airflow (code 1) et arrête la tâche, laissant la zone propre précédente intacte. Great Expectations seul a été repoussé à plus tard, et les contrôles non bloquants ont été écartés car ils laisseraient passer des données corrompues jusqu’au modèle. → ADR 0005.

**Pourquoi avez‑vous choisi un modèle basé sur des n‑grammes de caractères plutôt que des mots ou un LLM ?**  
Le modèle utilise `TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, max_features=100 000, sublinear_tf=True)` suivi d’une `LogisticRegression(C=4.0, class_weight="balanced", max_iter=2000)`. Sur 5 974 avis naturels (test stratifié de 1 195 avis), cette configuration a atteint un rappel des négatifs de 0,639 et un F1 macro de 0,759, le meilleur parmi les variantes testées. Les LLM ont été rejetés pour leur coût et latence inutiles, et les réseaux profonds ont été réservés au bloc 4 du CDSD. → ADR 0006.

**Comment avez‑vous traité le déséquilibre des avis négatifs et pourquoi ne pas simplement ajuster le seuil sur le jeu de test ?**  
Nous avons ajouté un second flux qui collecte les avis négatifs (`review_type=negative`) stockés sous `sample=negative_boost` et les utilisons uniquement pour l’entraînement. Le seuil de décision est appris par validation croisée à 5 plis sur les avis naturels d’entraînement, avec une grille de 0,30 à 0,80, le meilleur étant 0,75, ce qui donne un F1 macro hors‑plis de 0,802 et un F1 macro final de 0,807. Le test reste composé à 100 % d’avis naturels pour refléter la production. Baisser la barrière de promotion, choisir le seuil sur le test, mélanger les flux dans le test et le suréchantillonnage SMOTE ont été écartés pour leurs risques de fuite d’information ou d’inadéquation. → ADR 0007.

**Quel critère utilisez‑vous pour promouvoir un nouveau modèle et pourquoi l’alias « champion » n’est‑il pas mis à jour automatiquement à chaque version ?**  
Chaque entraînement crée une version `challenger` dans MLflow ; l’alias `champion` n’est déplacé que si le F1 macro est ≥ 0,75 **et** strictement supérieur à celui du champion actuel. Le seuil de 0,75 a été fixé après mesure le 16/09 (quatre variantes plafonnaient entre 0,756 et 0,766). Promouvoir chaque version a été rejeté car cela ne protège pas contre les régressions, la promotion manuelle seule contredit l’automatisation demandée, et la condition « ≥ » a été écartée pour éviter des remplacements inutiles. → ADR 0008.

**Comment avez‑vous résolu les inversions de convention d’étiquetage rencontrées lors du développement ?**  
Nous avons centralisé la convention dans le module `reviewpulse/decision.py` qui définit `LABEL_NEGATIVE`, `LABEL_POSITIVE`, expose `negative_proba` en lisant `model.classes_`, et fournit `model_threshold`, `predict_labels` et `label_name`. Aucun composant (entraînement, scoring, API, tableau de bord) n’effectue de comparaison au seuil en dehors de ce module. Réétiqueter les données ou corriger chaque point séparément a été rejeté car cela avait déjà conduit aux deux inversions observées. → ADR 0009.

**Où stockez‑vous les artefacts MLflow et comment évitez‑vous les échecs d’écriture rencontrés précédemment ?**  
Nous utilisons un emplacement absolu `DATA_DIR/mlartifacts` pour la base SQLite ou le serveur HTTP, et nous loggons les artefacts JSON via `mlflow.log_dict` sans créer de fichiers locaux. Toutes les écritures créent d’abord le répertoire parent, écrivent dans un fichier temporaire puis le remplacent atomiquement avec `os.replace`. L’image Docker attribue l’utilisateur `app` la propriété de `/app` pour garantir les permissions. Le comportement par défaut qui créait un dossier `./mlruns` vide et perdait le modèle a été rejeté, tout comme l’écriture dans le répertoire courant qui échouait en conteneur. → ADR 0010.

Chaque décision structurante possède son ADR, les renvois pointent vers le registre `adr/README.md`.

**Pourquoi dbt pour la zone gold, alors que le reste de la chaîne est en Python ?**
Parce que la zone gold est le seul endroit où le travail est de la modélisation SQL, et où le contrat compte plus que le code. Six modèles — deux de préparation, quatre de restitution, dont un schéma en étoile — portent `contract: enforced`, qui impose noms et types de colonnes et refuse une évolution silencieuse. Les tests dbt accompagnent chaque modèle, et `dbt docs generate` produit le lignage. Écrire ces jointures et ces agrégats en pandas aurait redonné du code à tester au lieu d'un contrat à déclarer. dbt est invoqué par `gold.py` à travers son API Python, et non par un sous-processus, pour que son code de retour arrête la tâche Airflow. → ADR 0013, ADR 0020.

**Pourquoi DuckDB comme entrepôt, et pas MongoDB ou un entrepôt géré ?**
Ce ne sont pas les mêmes catégories. La zone gold sert des agrégations SQL sur colonnes — part d'avis négatifs par jeu, par langue et par jour — c'est du travail analytique, et DuckDB le fait en local, sans serveur, sur des fichiers. Une base de documents comme MongoDB est un magasin **opérationnel** : elle excelle à stocker et mettre à jour des objets JSON pour une application, pas à balayer des colonnes. Le seul endroit où elle aurait un sens ici est la zone brute, qui reçoit bien du JSON de l'API Steam ; nous y avons préféré des fichiers immuables, parce que c'est cette immuabilité qui fonde l'idempotence et la réversibilité. Face à Snowflake, la raison est autre : la démonstration ne doit dépendre d'aucun compte externe, et changer d'entrepôt revient à changer d'adaptateur dbt et de profil. **Une base de documents est en revanche exigée ailleurs** : le cas Stripe du bloc AIA 2 demande une architecture intégrant OLTP, OLAP **et NoSQL**, et compte parmi ses livrables un modèle NoSQL et des requêtes NoSQL. Ce livrable appartient au dossier Stripe, pas à ReviewPulse ; mais la zone brute de ReviewPulse, qui reçoit déjà des documents JSON, en serait le pilote naturel — c'est un arbitrage ouvert, inscrit au registre sous R29. → ADR 0002, ADR 0013.

**Pourquoi MLflow, et pas simplement un fichier de modèle versionné dans git ?**
Parce qu'un fichier versionné ne répond pas à la question « quelle version sert en ce moment, et pourquoi celle-là ». MLflow porte quatre choses qu'un fichier ne porte pas : l'historique des essais avec leurs métriques, un registre où l'alias `champion` **désigne** la version servie, la barrière qui refuse une promotion qui ne serait pas strictement meilleure, et l'empreinte du jeu de données plus l'étiquette `code_commit`, qui rattachent chaque métrique à ses données et à son code. Le retour arrière consiste alors à déplacer un alias — opération qui se défait par la commande inverse — au lieu de recopier un artefact. La contrepartie est connue et nous a coûté cher : le registre vivait dans un volume Docker, dont la suppression le 16/09 a tout détruit. D'où la sauvegarde hors volume, dont la restauration a été essayée. → ADR 0008, ADR 0016, ADR 0018.

**Pourquoi avez‑vous combiné Airflow et GitHub Actions au lieu d’utiliser uniquement cron ou Airflow seul ?**  
Nous exécutons les DAG `reviewpulse_daily` et `reviewpulse_weekly_train` avec Airflow et utilisons GitHub Actions pour le lint, les tests et un pipeline planifié à 6 h 30 UTC, afin d’obtenir visibilité sur les échecs et un filet de secours. Le conteneur Airflow tourne avec l’uid 1000 et le groupe 0 pour aligner les permissions. L’alternative « cron seul » a été rejetée faute de suivi des échecs, et « Airflow seul » a été rejetée car dépend d’une machine allumée. → ADR 0011.

**Pourquoi avez‑vous choisi Docker Compose avec Python 3.11 plutôt qu’un environnement virtuel local ou Kubernetes ?**  
Toutes les images utilisent Python 3.11 figé dans `requirements.txt` et sont orchestrées par Docker Compose, garantissant une reproduction identique sur chaque poste et lors de la démo. Les services sont non‑root, disposent de contrôles de santé propres et les secrets sont lus depuis `.env`. Un environnement virtuel local a été écarté car non reproductible chez le jury, et Kubernetes a été jugé surdimensionné pour la démo. → ADR 0012.

**Pourquoi avez‑vous maintenu une seule pile Python avec deux environnements séparés dans l’image Airflow ?**  
Nous figons la pile (MLflow 3.16, Streamlit 1.60, FastAPI 0.141.1, etc.) dans `requirements.txt` et créons un environnement `/opt/rp-venv` dédié au projet, tandis que l’environnement d’Airflow reste intact (`slim‑2.10.3`). Les tâches s’exécutent via `ExternalPythonOperator` pour éviter le conflit SQLAlchemy 2.0 imposé par le projet. Installer le projet dans l’environnement d’Airflow a été rejeté car cela casse Airflow, et une image par rôle a été écartée pour des raisons de sécurité et de complexité. → ADR 0013.

**Pourquoi avez‑vous retenu PySpark comme moteur de production pour la zone silver alors que pandas est plus rapide sur le jeu de données actuel ?**  
PySpark produit la zone silver dans Iceberg et est orchestré par le DAG quotidien, tandis que pandas sert de référence et les deux moteurs doivent donner exactement le même résultat. Bien que Spark prenne 7,8 s contre 1,7 s pour 8 231 lignes (mesure du 16/09/2026), il se justifie par le passage à l’échelle (seuil d’environ 10 M d’avis) et l’alignement avec le programme Lead. L’alternative « Spark seul, sans référence pandas » a été rejetée car aucune preuve de justesse du nettoyage distribué. → ADR 0014.

**Comment surveillez‑vous la dérive du modèle et pourquoi avez‑vous choisi le PSI plutôt que d’autres tests statistiques ?**  
Nous calculons le PSI sur les colonnes d’intérêt de la zone propre, avec des seuils < 0,1 stable, 0,1‑0,2 à surveiller, ≥ 0,2 dérive, et déclenchons un réentraînement via un `ShortCircuitOperator` si une alerte est levée. Le PSI gère les zéros grâce à un epsilon, ce qui le rend plus adapté que le test de Kolmogorov‑Smirnov ou la divergence KL, rejetées pour incompatibilité avec les variables catégorielles ou complexité. L’alerte est écrite dans un fichier JSON, ce qui limite le canal mais suffit pour l’audit. → ADR 0015.

**Pourquoi introduire un déploiement progressif champion/challenger alors que le basculement binaire était déjà fonctionnel ?**  
Nous lisons la proportion de trafic à servir par le challenger dans `REVIEWPULSE_CHALLENGER_TRAFFIC` et routons chaque requête de façon déterministe via un hash, afin de comparer les performances en production avant toute bascule définitive. Le champ `served_by` indique le modèle utilisé. L’alternative « bascule binaire » a été rejetée car elle contrevient à l’exigence de déploiement progressif, et le routage par passerelle externe a été écarté pour complexité inutile. → ADR 0016.

**Pourquoi avez‑vous migré la base d’Airflow de SQLite vers PostgreSQL ?**  
Le planificateur mourait avec SQLite dès qu’une requête concurrente était exécutée (observation 18/09/2026). En passant à PostgreSQL 16 avec `LocalExecutor` et un `start_period` de 60 s, le planificateur survit aux accès concurrents (mesure 19/09/2026). Garder SQLite a été rejeté pour son incapacité à gérer la concurrence, et le `CeleryExecutor` a été écarté car il nécessite un courtier de messages superflu. → ADR 0017.

**Comment assurez‑vous la reproductibilité des runs MLflow et pourquoi avez‑vous choisi les empreintes SHA‑256 plutôt que des étiquettes ?**  
Chaque run enregistre une empreinte SHA‑256 du jeu de données, le nombre de lignes, les bornes de dates et les comptes par flux, ainsi que le tag `code_commit`. Les images de base sont épinglées par empreinte, et le registre MLflow est sauvegardé hors du volume Docker avec `make sauvegarde-mlflow`. Utiliser uniquement des étiquettes a été rejeté car elles peuvent changer de contenu, alors que l’empreinte reste stable. → ADR 0018.

**Pourquoi avez‑vous implémenté une explicabilité linéaire exacte plutôt que d’utiliser SHAP ou LIME ?**  
Le modèle est un TF‑IDF suivi d’une régression logistique, donc chaque terme contribue exactement par son poids TF‑IDF multiplié par le coefficient. Nous exposons ces contributions via `/explain` et les affichons dans le tableau de bord, garantissant une explication exacte et instantanée. SHAP et LIME ont été écartés car ils sont approximatifs, plus lourds et redondants pour un modèle linéaire. → ADR 0019.

**Pourquoi avez‑vous étendu la porte de qualité aux zones silver et gold au lieu de simplement renforcer les tests dbt ?**  
Nous avons créé `expectations_lake.py` avec 29 attentes — 8, 7, 7 et 7, mesurées en exécution réelle le 20/09/2026 couvrant `silver.reviews`, `silver.predictions`, les faits gold et le mart quotidien, et ajouté la tâche `gx_lake` bloquante dans le DAG quotidien, portant le DAG à neuf tâches. Étendre `expectations.py` a été rejeté pour le risque de perturber une porte déjà stable à quelques jours de la soutenance, et se contenter des tests dbt a été écarté car ils ne bloquent pas la chaîne. → ADR 0020.

## Ce que vous feriez ensuite

- Suite Great Expectations avec rapport HTML (cours du 21/09).
- Suivi de dérive (distribution de `proba_negative`, part négative) avec alerte. → schéma 10.
- Détection de thèmes (bug, prix, performance) par un LLM sur les seuls avis négatifs.
- Modèle profond de sentiment et création de données, branchés dans la même chaîne (bloc 4 du CDSD). → schéma 09.
- Cible cloud : stockage objet chiffré, MLflow et Airflow managés, Terraform. → schéma 06.

## Comment le projet se prouve

Un jury d'examen professionnel ne demande pas « est-ce que ça marche ? » mais « comment le
savez-vous ? ». Chaque réponse ci-dessous nomme la preuve, sa date, et ce qu'elle ne couvre pas.

**Pourquoi des tests inverses, des mutations, et pas seulement des tests classiques ?**
Parce qu'un test classique prouve qu'un chemin autorisé passe, jamais qu'un contrôle refuse. Une batterie entièrement verte peut coexister avec une porte de qualité qui laisse tout passer : aucun test ne l'aurait jamais sollicitée. Une mutation injecte un défaut volontaire dans une copie du code — la convention de décision inversée, la pseudonymisation supprimée, la barrière de promotion retirée — puis relance la batterie et exige qu'un test **nommé** échoue. Si aucun n'échoue, la mutation « survit », et c'est un trou de couverture réel, jamais un test à assouplir. Nous en avons vingt-sept, chacune reliée au test qui la tue. Le 20/09/2026, sur un runner d'intégration continue vierge, **27 mutations sur 27** ont été tuées en un seul passage, zéro survivante. Les deux survivantes de la veille avaient chacune révélé un défaut : l'une, une porte non prouvée bloquante ; l'autre, un test qui passait pour la mauvaise raison. → ADR 0005.

**Qu'est-ce qu'un témoin, et pourquoi y tenez-vous ?**
Un témoin est le cas qui échouerait si le contrôle ne fonctionnait pas. Sans lui, un test peut passer pour une raison qui n'a rien à voir avec ce qu'il prétend vérifier — et l'on croit couvert ce qui ne l'est pas. Nous l'avons mesuré : la mutation M22 supprimait notre garde contre la restauration d'un instantané Iceberg inexistant, et elle a **survécu**, parce que le test se contentait d'attendre une `ValueError`. Or pyiceberg lève lui aussi une `ValueError` dans ce cas ; le test passait donc sans notre garde, pour la mauvaise raison. Il vérifie désormais le **message** de la garde, celui qui nomme la table et le mot « inconnu ». Chaque test important du dépôt suit cette règle : d'abord le cas qui réussit, puis le cas qui doit échouer. Une porte qui n'a jamais refusé ne prouve rien ; le témoin est ce qui la fait refuser une fois, sous nos yeux.

**Que prouve le test de la pile déployée, que la batterie ne prouve pas ?**
La batterie exerce des fonctions, en mémoire, avec des données de fixture ; elle ne sait rien des conteneurs, des ports, des volumes, ni des secrets. Le test de la pile interroge les services **réellement levés** par `docker compose` : l'API répond-elle et avec quelle version de modèle, le tableau de bord se charge-t-il, MLflow désigne-t-il bien un champion, une seconde ingestion n'écrit-elle aucun doublon, la zone propre porte-t-elle un identifiant en clair, la part négative prédite est-elle cohérente avec la part réelle par jeu et par langue. Ce sont **16 contrôles**, et ils passent tous. C'est ce test qui a trouvé, le 16/09, que 95 % des avis étaient prédits négatifs pour 4 % réels — une convention de décision inversée entre deux modules que la batterie, module par module, ne pouvait pas voir. → ADR 0009.

**Pourquoi plusieurs niveaux de validation plutôt qu'une seule suite de tests ?**
Parce que chaque niveau attrape ce que le précédent laisse passer, et que nous l'avons mesuré à chaque étage. « Le code compile » n'est pas « le code fonctionne » : un `import os` manquant a compilé sans bruit, puis tué un outil **après sept minutes de calcul**, au moment d'écrire son rapport. « Le code fonctionne » n'est pas « les dépendances sont correctes » : `pip check` a refusé une image dont `pyproject.toml` et `requirements.txt` se contredisaient, à la dernière étape d'une construction de trente et une minutes. Et la relecture par un humain n'est pas un niveau : le jour où `ruff` a été ajouté à la campagne, il a trouvé **dix défauts dormants** que personne n'avait vus. La campagne enchaîne donc compilation, lint, documentation, batterie, tests inverses, chacun sous une garde de temps, et écrit son journal dans un chemin absolu — parce qu'une campagne muette de trois heures nous avait déjà coûté une nuit.

**Pourquoi une campagne en intégration continue, si tout tourne déjà sur votre machine ?**
Parce qu'une preuve produite sur la machine du développeur ne répond pas à « ça marche chez moi ». Le 20/09/2026, la chaîne entière a tourné sur un runner GitHub **vierge**, en repartant d'une zone brute vide : **5 798 avis** collectés sur l'API Steam en direct, zone silver écrite, modèle entraîné et **promu** par la barrière avec un F1 macro de 0,7982, score et dérive calculés. Rien de cela ne dépendait d'un fichier, d'un cache ou d'un secret laissé sur un poste. La même intégration a aussi rendu un service que nous n'attendions pas : la campagne inverse complète y a pris **six minutes**, là où le disque de la machine locale, un disque externe, n'y arrivait plus — la batterie y mettait dix fois sa durée. L'écart de F1 avec le local, 0,8027, tient au jeu de données, pas au code : 5 462 lignes contre 8 768, et chaque run porte l'empreinte du sien. → ADR 0018.

**Comment savez-vous que votre porte de qualité bloque, et ne se contente pas de journaliser ?**
Par la mutation M17. Elle remplace la condition de succès de la porte par un `True` inconditionnel — la porte continue de tout journaliser, mais ne refuse plus rien. Le 19/09, cette mutation a **survécu** : aucun test n'appelait `main()`, donc rien ne vérifiait le code de retour. C'était un trou réel, et il a été comblé par deux tests — le témoin, qui vérifie que `main()` rend 0 sur une zone propre conforme, et le test qui compte, qui vérifie qu'il rend **1** quand un pseudonyme d'auteur n'a pas le bon format. Depuis, M17 est tuée à chaque campagne. La même discipline vaut pour les zones silver et gold : les mutations M23 et M24 relâchent une borne et suppriment un contrôle de format, et sont tuées par les tests d'`expectations_lake`. → ADR 0005, ADR 0020.

**Que ne prouvent pas vos tests ?**
Ils ne prouvent pas la tenue sous un trafic réparti : l'essai de charge — 300 requêtes, 0 % d'erreur, p99 925 ms — est mesuré sur une seule machine, et son premier passage à froid donne 5 874 ms. Ils ne prouvent pas le comportement sur des langues que le modèle n'a pas vues, ni sur des avis d'une longueur inhabituelle. Ils ne prouvent pas l'absence de biais par langue et par jeu : cette mesure **manque**, l'AI Act la demande, et c'est écrit plutôt que masqué. Ils ne prouvent pas non plus qu'une alerte de dérive déclenche bien le réentraînement — seulement qu'une absence d'alerte ne le déclenche pas ; le chemin inverse est couvert par les tests, pas par une exécution réelle. Un passage vert ne prouve que ce que le test vérifie. Dire où s'arrête la preuve fait partie de la preuve. → ADR 0021.

## Ce que le projet ne fait pas, et pourquoi

Huit décisions assumées par écrit plutôt qu'implémentées. Un jury qui repère un manque pose la
question ; une réponse qui l'esquive coûte plus cher que le manque lui-même. Chacune dit donc le
choix, sa raison, et la condition à laquelle il changerait.


**Pourquoi n'avez‑vous pas implémenté de garde‑fous contre les biais par langue ou jeu alors que le référentiel AIA 4 l'exige ?**
Nous reconnaissons l’absence de garde‑fous mesurant le biais par langue ou par jeu dans la version actuelle. Cette décision repose sur le fait que le classifieur linéaire ne peut être manipulé par une injection de prompt et que la mise en place immédiate de métriques différenciées nécessiterait des travaux d’ingénierie (extraction, agrégation et stockage) qui ne sont pas prévus dans le sprint en cours. Nous avons donc consigné cette lacune comme garde‑fou administratif, conformément au référentiel AIA 4. La condition de retour est claire : dès que des **ressources** de développement ou une aide externe seront disponibles, nous implémenterons le calcul des métriques (f1_macro, recall_negative, etc.) séparément pour chaque langue et chaque `app_id`, et les exposerons via MLflow et l’endpoint `/insights`. → ADR 0021.

**Vous n'avez ni coffre à secrets, ni chiffrement entre vos services, ni journal d'audit. Comment défendez-vous cela ?**
Nous l'assumons, et nous disons à quelle condition cela changerait. Le projet porte **un** secret, le sel de pseudonymisation, sur une machine et pour un porteur : un coffre externe n'ajouterait aucune garantie que nous n'ayons déjà, puisque le sel n'est jamais versionné, qu'il est passé par variable d'environnement obligatoire, et que la chaîne **refuse de démarrer** sans lui. Un coffre devient nécessaire au premier de ces trois seuils : plusieurs environnements, plusieurs porteurs, ou une rotation. Le trafic sortant vers Steam est déjà en HTTPS ; entre conteneurs il circule en clair sur un réseau Docker privé, et le chiffrer supposerait du TLS mutuel dont le coût d'exploitation dépasse aujourd'hui le risque. Quant à l'audit des accès, il manque réellement : les journaux Airflow tracent des exécutions, pas des lectures de données. → ADR 0022.

**Pourquoi n’avez‑vous pas de métriques d’énergie alors que le référentiel AIA 4 l’exige ?**  
Nous reconnaissons que le coût monétaire est nul, mais le **FinOps** reste applicable en incluant le temps machine, l’espace disque et l’énergie. Nous avons donc retenu comme indicateurs mesurables la durée totale du DAG quotidien (34 min 27 s), les tailles des images Docker (4,18 Go, 3,37 Go, 3,35 Go) et la durée de la batterie de tests (8 min 07 s), tous disponibles dans les logs existants, et nous avons déjà constaté un gain concret en retirant `confluent‑kafka`. L’absence de métriques énergétiques constitue le gap identifié ; nous prévoyons d’installer un moniteur de puissance (ex. `powermetrics` ou wattmètre) et de commencer à reporter les kWh dès que le dispositif sera disponible, ce qui permettra de combler la lacune **GreenOps**. → ADR 0023.

**Pourquoi n’avez‑vous pas installé de base de documents NoSQL alors que l’exigence du bloc AIA 2 le demande ?**
Nous reconnaissons que la zone *brute* ne constitue pas un magasin de documents : les fichiers JSON/JSONL y sont stockés sans index ni requêtes par champ, ce qui ne répond pas à l’exigence de base NoSQL du bloc AIA 2. Nous avons donc **choisi** de ne pas installer de moteur de documents avant le Demo Day et de livrer uniquement la spécification papier de la future brique (schéma, exigences d’indexation, API). Cette décision repose sur le fait que l’ajout d’un moteur impliquerait des changements d’infrastructure, des migrations et des tests d’intégration impossibles à réaliser en moins de cinq jours, ce qui représenterait un risque inacceptable. Nous installerons le magasin en amont de la zone *brute* uniquement après le Demo Day, lorsque les conditions de test seront réunies → ADR 0024.

**Pourquoi n’avez‑vous pas mis en place de SCD2 sur la dimension jeu alors que le nom du jeu peut évoluer ?**
Nous reconnaissons que la dimension `dim_game` pourrait nécessiter un suivi historique du nom du jeu, mais aucune évolution n’est observée dans les données actuelles et les contrats ne prévoient pas les colonnes nécessaires au SCD2 ; ajouter une clé de substitution, des dates de validité et un indicateur de version augmenterait la complexité du modèle et le temps d’exécution quotidien sans répondre à un besoin réel. Ainsi, nous avons choisi de garder la dimension **statique** (type 1) et de ne pas implémenter le **SCD2** pour le moment. Nous reviendrons sur cette décision uniquement si les changements de `game_name` deviennent fréquents et justifient l’ajout de ces colonnes. → ADR 0025.

**Pourquoi le système ne persiste‑t‑il pas le texte original avec le tracing, alors que cela empêche de reconstruire l’explication si le texte est perdu ?**  
Nous reconnaissons que le tracing de décision, tel que défini dans l’ADR 0026, ne stocke que les contributions, la version du modèle et le timestamp, sans conserver le texte source. Ce choix a été motivé par la volonté d’éviter la redondance avec le stockage existant, de limiter la charge de persistance et de respecter les contraintes de confidentialité ; le texte peut être volumineux et n’est pas indispensable pour la plupart des audits qui se concentrent sur le raisonnement du modèle. Nous ajouterons toutefois la persistance du texte original si les exigences de conformité ou les besoins d’audit exigent une reconstruction complète et fiable des explications. → ADR 0026.

**Pourquoi n’avez‑vous pas intégré MinIO, Kafka, Terraform et le déploiement public alors que le jury voit le manque ?**
Nous reconnaissons que les briques MinIO, Kafka, Terraform et le workflow de déploiement public ne sont pas présentes dans notre démonstration ; la décision d’**assumer** leur absence provient de l’ADR 0027, qui indique que ces composants ne sont pas requis par le bloc AIA 4, support déclaré, et que leur mise en place dépasserait le délai de cinq jours avant le Demo Day. Nous nous appuyons donc sur les projets externes des autres blocs ou sur le workflow Hugging Face déjà existant. Nous changerions cette approche uniquement si les livrables des blocs concernés étaient fournis à temps ou si un créneau supplémentaire permettait d’installer et de valider ces services. → ADR 0027.

**Pourquoi n'utilisez‑vous pas de sprints pour piloter le backlog alors que cela semble standard ?**
Nous reconnaissons que l’absence de sprints peut donner l’impression d’un manque de structure, mais le choix repose sur le fait que le projet ReviewPulse est mené par une seule personne, sans équipe ni parties prenantes à synchroniser. Les fonctions principales d’un sprint – **coordination** et **engagement collectif** – sont donc sans objet, et les cérémonies n’apportent aucune valeur ajoutée supplémentaire à notre registre de suivi, qui garantit la traçabilité et la preuve de chaque sujet. Nous continuons à piloter le backlog via le registre, en fonction de notre disponibilité. Si une deuxième personne rejoint le projet, nous réévaluerons alors l’introduction d’un cadre de sprint. → ADR 0028.
