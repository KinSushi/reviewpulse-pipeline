# ADR 0014 — Zone silver en PySpark et Iceberg, pandas comme référence

**Date** : 16/09/2026 · **Statut** : acceptée · **Complète** l'ADR 0003

## Contexte

Le programme de la Lead enseigne PySpark (module Big Data, exercice sur des données de jeu vidéo) et Iceberg avec PyIceberg (module Modern Data Stack). Le référentiel AIA 3 attend une architecture médaillon, le retraitement de l'historique et le versioning des données ; le CDSD 1 et 2 exigent Spark.

## Décision

1. **PySpark est le moteur de production** de la zone silver (`spark_silver.py`), orchestré par le DAG quotidien (`ingest >> spark_silver >> gx_validate >> score`).
2. **pandas reste l'implémentation de référence** (`transform.py`, disponible en ligne de commande) : un test exige que **les deux moteurs produisent exactement le même résultat**.
3. La zone silver est écrite en **table Iceberg** `silver.reviews` (PyIceberg, catalogue SQLite, comme en cours), réécrite entièrement depuis le bronze à chaque exécution : l'historique est retraité si les règles changent, et chaque écriture crée un **instantané** (versioning des données). Les prédictions vont dans `silver.predictions`.
4. Le fichier Parquet de la zone propre est conservé pour la compatibilité avec l'entraînement, le score et l'API.

## Faits mesurés qui ont façonné l'implémentation

| Constat | Traitement |
|---|---|
| PyIceberg refuse `timestamp[ns, tz=UTC]` | Conversion en `timestamp[us, tz=UTC]` avant toute création ou écriture |
| `table.schema` est une méthode ; `schema().as_arrow()` rend des `large_string` ; `Table.cast` lève `ValueError` si les colonnes diffèrent | Écriture refusée si les colonnes changent : pas d'évolution de schéma silencieuse |
| Spark n'a pas de HMAC natif | `pandas_udf` avec `hmac` pour la pseudonymisation |
| `toPandas()` rend des dates sans fuseau (session en UTC) | Localisation UTC avant conversion |
| **Sur les données réelles, 11 textes sur 8 800 différaient** (espace insécable U+00A0, séparateur de ligne U+2028) : `\s` est Unicode en Python, ASCII en Java | Expression `(?U)\s+` côté Spark ; cas ajoutés au test, qui échoue bien sans le correctif |
| Hadoop exige un nom d'utilisateur pour l'uid courant | Les images définissent un utilisateur pour l'uid 1000 |

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Spark seul, sans référence pandas | Aucun moyen simple de prouver la justesse du nettoyage distribué |
| Écriture Iceberg par Spark (`iceberg-spark-runtime`) | Ajoute un JAR et un catalogue JDBC ; le cours utilise PyIceberg |
| Delta Lake ou Hudi | Hors du programme (Iceberg y est enseigné) |

## Conséquences et limites, à dire au jury

- **À ce volume, Spark est plus lent que pandas** : 7,8 s contre 1,7 s pour 8 231 lignes (16/09/2026), à cause du démarrage de la JVM. Spark se justifie par le passage à l'échelle (ADR 0003 : seuil d'environ 10 millions d'avis) et par l'alignement sur le programme.
- Catalogue SQLite local : adapté à la démo ; en production, catalogue REST ou Glue (schéma 06).

## Preuves

- `tests/test_spark_silver.py` : équivalence stricte (doublons, deux flux, BBCode, textes vides, espaces Unicode) ; écriture, historique, dernière version lue ; schéma incompatible refusé.
- Exécution réelle du 16/09/2026 : **équivalence stricte sur 8 231 lignes** (5 977 naturelles, 2 254 complémentaires) ; `spark_silver.main()` en 5,3 s ; table `silver.reviews` écrite.
