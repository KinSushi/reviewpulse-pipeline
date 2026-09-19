# ReviewPulse — architecture

**Version** : v3, 19/09/2026.  
Le système collecte les avis Steam, les nettoie, entraîne un modèle de sentiment et expose les scores aux équipes community & live‑ops.  
Il s’adresse aux développeurs, data‑engineers et aux responsables produit qui doivent suivre la qualité et la dérive du modèle.

## La chaine, en une image
Les schémas d’ensemble sont rendus par `make diagrams`. La commande échoue si l’un d’eux est invalide.  
- Vue d’ensemble : `diagrams/png/01_architecture_globale.png`  
- Zones de données et flux : `diagrams/png/02_flux_et_zones_de_donnees.png`  
- DAG Airflow : `diagrams/png/03_dag_airflow.png`  
Les sources Mermaid vivent dans `diagrams/src/`.

## Les zones de donnees, et leur contrat
| Zone   | Format                     | Ecrite par                | Contrat (vérifiable) |
|--------|---------------------------|---------------------------|----------------------|
| brute  | JSONL (une ligne = objet `review` tel que reçu) | `ingest.py` (ADR 0002) | Manifeste listant les identifiants déjà écrits ; écriture atomique via `os.replace` garantit l’absence de doublons. |
| propre | Parquet, fichier unique réécrit à chaque exécution | `spark_silver.py`, par `transform.write_clean` (ADR 0003, 0004, 0014) | Contrôles qualité bloquants (`quality.check_clean`, ADR 0005) ; schéma fixe (`CLEAN_COLUMNS`). |
| silver | Tables Iceberg `silver.reviews` et `silver.predictions` | `spark_silver.py` pour la première, `score.py` pour la seconde (ADR 0014) | Chaque écriture crée un instantané restaurable ; la validation du schéma refuse toute évolution silencieuse (ADR 0014). |
| scorée | Parquet `reviews_scored.parquet` et `daily_summary.parquet`, plus `drift_report.json` et les alertes datées | `score.py` et `drift.py` (ADR 0007, 0015) | Le résumé quotidien ne retient que le flux naturel ; le rapport de dérive porte son verdict et ses seuils (ADR 0015). |
| gold | Base DuckDB unique | `gold.py`, par dbt (ADR 0020) | Contrats et tests dbt, puis 28 attentes Great Expectations sur `main.fct_review_predictions` et `main.mart_sentiment_daily` ; toute violation arrête le DAG (ADR 0005, 0020). |

## Les choix, et leur justification
| Choix | Pourquoi, mesure à l’appui | Alternative écartée | Decision |
|-------|----------------------------|---------------------|----------|
| Cas métier : avis Steam | Besoin d’un cas réel avec flux continu (API publique répond sans clé, 23 172 – 504 467 avis / jeu / langue, 16/09/2026) | Jeux Kaggle, scraping, données synthétiques, LLM sur RSS | ADR 0001 |
| Zone brute inchangée, idempotence par manifeste | 6 000 avis au premier passage, 0 au second (16/09/2026) ; aucun doublon après relance | Dédoublonnage en aval, métadonnées dans chaque ligne, base de données pour le manifeste | ADR 0002 |
| Transformation en pandas | Volume réel ≈ 10 000 avis (8 797 lignes brutes le 16/09/2026) ; transformation en < 1 s | PySpark (coût JVM), dbt (requiert entrepôt SQL) | ADR 0003 |
| Pseudonymisation HMAC salée | Sel obligatoire, code de sortie 1 sans sel (16/09/2026) ; HMAC résiste aux dictionnaires | SHA‑256 simple, suppression pure du `steamid`, contrôle du sel dans Compose | ADR 0004 |
| Contrôles qualité bloquants | Tests avant écriture : colonnes/types exacts, part négative 0,5 %–95 % (ADR 0005) ; un échec arrête la tâche | Great Expectations seul, contrôles non bloquants | ADR 0005 |
| Modèle ML sur n‑grammes de caractères | Meilleur rappel négatif (0,639) avec F1 0,759 (tableau mesures, 16/09/2026) | LLM (coût/latence), réseau profond (hors périmètre) | ADR 0006 |
| Avis négatifs complémentaires & seuil appris | Ajout de 2 263 avis négatifs → F1 0,807, rappel 0,639, précision 0,657, AUC 0,948 (mesures, 16/09/2026) | Baisser la barrière, choisir le seuil sur le test, mélanger les flux, SMOTE | ADR 0007 |
| Barrière de promotion & alias MLflow | Promotion uniquement si F1 ≥ 0,75 et strictement supérieur au champion (mesure 0,807 vs 0,7498, 16/09/2026) | Promotion automatique, promotion manuelle uniquement, critère « ≥ » | ADR 0008 |
| Convention de décision centralisée | Double inversion détectée (étiquette 0 = négatif, 1 = positif) ; module unique évite toute comparaison hors `decision.py` (16/09/2026) | Réétiqueter, corriger chaque endroit séparément | ADR 0009 |
| Emplacement des artefacts & écritures | Artefacts écrits hors du répertoire courant (`DATA_DIR/mlartifacts`), écriture atomique, création de dossiers parents (tests réels 16/09/2026) | Écriture dans le dossier courant, écriture directe sans `os.replace`, absence de création de dossiers | ADR 0010 |
| Orchestration Airflow & GitHub Actions | DAG quotidien à 06 h UTC, DAG hebdomadaire à 07 h UTC, deux tentatives, pas de rattrapage (16/09/2026) | Cron seul, Airflow seul, réentrainement quotidien | ADR 0011 |
| Déploiement Docker Compose | Python 3.11 partout, images figées, sel dans `.env`, services `mlflow`, `api`, `dashboard` (16/09/2026) | Environnement virtuel local, Kubernetes, cloud public dès le départ | ADR 0012 |
| Pile du programme Lead & environnements séparés | Stack unique (MLflow 3.16, Spark 4.2, Iceberg, DuckDB, dbt‑duckdb, Great Expectations, Airflow) fonctionnelle après résolution des conflits (16/09/2026) | Versions antérieures incompatibles, dbt‑core 1.9 + PyIceberg 0.12, FastAPI 0.115, installation dans l’image Airflow | ADR 0013 |
| Zone silver en PySpark & Iceberg, pandas comme référence | Spark produit exactement le même résultat que pandas (tests stricts, 8 231 lignes, 5,3 s) ; version pandas plus rapide à petit volume (7,8 s vs 1,7 s) | Spark seul, écriture Iceberg via `iceberg-spark-runtime`, Delta Lake ou Hudi | ADR 0014 |
| Surveillance de la dérive | PSI `text_len` = 0,036 (stable), `language` = 3,098, `app_id` = 0,332 ; part hors bornes = 10,13 % → alerte (mesures 19/09/2026) | Kolmogorov‑Smirnov, KL divergence, bibliothèque tierce `alibi-detect` | ADR 0015 |
| Déploiement progressif champion / challenger (proposé) | Aucun test ni mesure disponible ; proposition d’une part de trafic configurable | Bascule binaire, ombre sans réponse, passerelle externe | ADR 0016 |
| Airflow sur PostgreSQL | Migration résout le verrouillage SQLite (planificateur survit aux requêtes concurrentes, 19/09/2026) | Garder SQLite, CeleryExecutor | ADR 0017 |
| Reproductibilité : empreintes, traçabilité, sauvegarde | Trois entraînements identiques à la 16ᵉ décimale, empreinte SHA‑256 du jeu de données, sauvegarde MLflow (19/09/2026) | Étiquette seule, sauvegarde SQLite uniquement, restauration directe sur le volume en service | ADR 0018 |
| Explicabilité linéaire exacte | Contribution exacte = TF‑IDF × coefficient, test de somme égale à la décision (mutations M21 détectées) | SHAP, LIME, aucune explicabilité | ADR 0019 |
| Porte de qualité étendue aux zones silver et gold | 28 attentes Great Expectations, 2 valeurs cassées provoquent l’échec du DAG (tests verts, 19/09/2026) | Étendre `expectations.py`, se contenter des tests dbt, contrôle non bloquant | ADR 0020 |

## Ce que l'architecture garantit
**Traçabilité** – Chaque ingestion crée un manifeste listant les identifiants (ADR 0002). Chaque run MLflow enregistre l’empreinte SHA‑256 du jeu de données et le commit Git (ADR 0018). Les snapshots Iceberg offrent une historique immuable des tables silver.

**Reproductibilité** – Le code utilise une graine fixe (42) et les mêmes versions de dépendances (requirements.txt). La cible `make pipeline-gele` rejoue la chaîne sur la zone brute déjà présente, sans ingérer d’avis nouveaux (ADR 0018). Les images de base sont épinglées par empreinte, et non par étiquette. Les tests unitaires couvrent chaque étape.

**Réversibilité** – `rollback.py` déplace l’alias `champion` vers une version antérieure du registre (ADR 0016) ; l’opération se défait par la commande inverse et ne touche à aucune donnée. `lakehouse.restore_snapshot` ramène une table silver à un instantané antérieur, l’historique restant entier (ADR 0014). La matrice complète est dans `15_reversibilite.md`.

**Qualité bloquante** – La fonction `quality.check_clean` (ADR 0005) arrête la tâche si un contrôle échoue. Les suites Great Expectations sur les zones propre, silver et gold sont bloquantes dans le DAG (ADR 0005, 0020). Aucun jeu de données corrompu ne peut atteindre le modèle.

## Ce que l'architecture ne fait pas
- Aucun webhook, email ou système de notification externe n’est déclenché en cas d’alerte de dérive (ADR 0015).  
- Le déploiement progressif du challenger reste une proposition non implémentée (ADR 0016).  
- Aucun connecteur Airbyte n’est utilisé pour l’ingestion (ADR 0013).  
- La chaîne ne supporte pas de modèles LLM ou de réseaux profonds ; le passage à ces technologies est prévu uniquement pour les blocs futurs (ADR 0006, 0019).  
- Snowflake, Delta Lake et Hudi sont explicitement exclus (ADR 0013, 0014).  
- Le monitoring en temps réel au‑delà du fichier `drift_report.json` n’est pas fourni (ADR 0015).  
- Aucune gouvernance outillée : ni catalogue de données, ni contrôle d’accès par rôle, ni journal des accès, ni calendrier d’audits. Ce qui est tenu et ce qui manque est détaillé dans `17_gouvernance.md`.
- Aucun stockage objet compatible S3, aucun flux Kafka, aucune infrastructure décrite en Terraform, aucune URL publique. Ces briques conditionnent le réemploi par d’autres blocs : registre `16_registre_suivi.md`, sujet R17.

## Le modele est une boite remplacable
Le contrat d’entrée (zone propre, colonnes, types, pseudonymes) et le contrat de sortie (probabilité négative, seuil, métriques) ne changent pas quand le modèle évolue. Cette stabilité rend la chaîne ré‑employable pour d’autres blocs CDSD ou AIA. Voir le détail du matriçage de réemploi dans `03_matrice_reemploi_blocs.md`.
