# ADR 0013 — Pile du programme Lead et environnements séparés

**Date** : 16/09/2026 · **Statut** : acceptée

## Contexte

Enzo demande d'appliquer le programme de la Lead v2 (Spark, Iceberg, dbt, Kafka, Great Expectations, Airflow, CI/CD), tout en restant conforme au Demo Day et réemployable pour les blocs CDSD et AIA (`08_exigences_par_bloc.md`).

Mesures du 16/09/2026 :

| Essai | Résultat |
|---|---|
| Pile initiale (MLflow 2.17.2, Streamlit 1.40.2, pyarrow 17) + dbt-core 1.12 / 1.10 | impossible : dbt exige protobuf 6, refusé par MLflow 2.17 et Streamlit 1.40 |
| dbt-core 1.9 + PyIceberg 0.12 | impossible : PyIceberg 0.12 refuse pyarrow 17 |
| **MLflow 3.16.0, Streamlit 1.60.0**, pyarrow 24, protobuf 6 + PySpark 4.2.0, PyIceberg 0.12.0, DuckDB 1.5.5, dbt-core 1.12.5, dbt-duckdb 1.11.0, confluent-kafka 2.15.1, Great Expectations 1.23.0 | **résolution trouvée**, `pip check` propre |
| Même pile avec FastAPI 0.115.5 | `ImportError: DEFAULT_EXCLUDED_CONTENT_TYPES` (Starlette trop ancien) → **FastAPI 0.141.1** |
| Pile installée dans l'environnement d'Airflow 2.10.3 | pip remplace SQLAlchemy 1.4 par 2.0, alors qu'Airflow exige < 2.0 |
| Image Airflow complète | conflits supplémentaires avec les fournisseurs Google, Snowflake, Azure (inutilisés) |
| Serveur MLflow 3.16 appelé sous le nom `mlflow:5000` | **403** « Invalid Host header » |

## Décision

1. **Une seule pile Python pour le projet**, figée dans `requirements.txt` : MLflow 3.16, Streamlit 1.60, FastAPI 0.141.1, plus les briques du programme.
2. **Deux environnements dans l'image Airflow** : celui d'Airflow (`slim-2.10.3`, intact) et `/opt/rp-venv` pour le projet ; les tâches s'exécutent par **`ExternalPythonOperator`**, la méthode prévue par Airflow pour les conflits de dépendances. Chaque environnement passe `pip check` à la construction.
3. **Java** : 21 dans les images Debian 13 (application, développement), 17 dans l'image Airflow (Debian 12 ne propose pas le 21) ; PySpark 4 exige Java 17 au minimum.
4. Serveur MLflow lancé avec **`--allowed-hosts`** listant les noms de service.
5. **Entrepôt analytique : DuckDB** (dbt-duckdb) ; Snowflake, enseigné en cours, n'est pas utilisé : il exige un compte et des identifiants, et la démo ne doit dépendre d'aucun service externe. Passer à Snowflake revient à changer d'adaptateur dbt et de profil.
6. **Airbyte n'est pas utilisé** : il n'existe pas de connecteur pour l'API des avis Steam ; l'ingestion Python existante est idempotente et testée. Une source Airbyte construite avec le Connector Builder reste une évolution possible.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Rester en MLflow 2.17 et renoncer à dbt ou Iceberg | Contraire à la demande d'appliquer le programme |
| Une image par rôle (Spark, dbt, application) orchestrée par `DockerOperator` | Exige le socket Docker dans Airflow (risque de sécurité) et complique les tests ; gardée pour une cible Kubernetes (`KubernetesPodOperator`) |
| Installer le projet dans l'environnement d'Airflow | Casse Airflow (SQLAlchemy 2.0) |
| Airflow 3 | Migration supplémentaire non nécessaire au Demo Day ; à réévaluer |

## Conséquences

- Les DAG n'importent plus le paquet au niveau du module (Airflow les analyse avec son propre Python).
- Le registre MLflow existant (versions 1 à 5, créées sous MLflow 2) est repris sans action par le serveur 3.16 ; le champion reste la version 2.
- Avertissement MLflow 3 : `artifact_path` est obsolète au profit de `name`.

## Preuves

- 54 tests réussis sous MLflow 3.16 (16/09/2026).
- Image Airflow : Airflow 2.10.3 avec SQLAlchemy 1.4.54 ; projet avec MLflow 3.16.0, PySpark 4.2.0, SQLAlchemy 2.0.54.
- Job réel sous MLflow 3 : 19 nouveaux avis, version 6 entraînée (F1 0,793) et non promue, score avec le champion version 2.
