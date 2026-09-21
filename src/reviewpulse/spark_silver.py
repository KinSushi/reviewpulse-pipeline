# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""reviewpulse.spark_silver
==========================

Rôle
----
Construire la zone « silver » à l'aide de Spark, en reproduisant exactement le
résultat de :func:`reviewpulse.transform.clean`.  Le DataFrame obtenu est
validé, écrit au format Parquet (compatibilité avec le pipeline existant) et
stocké dans Iceberg via :mod:`reviewpulse.lakehouse`.

Place dans la chaîne
--------------------
Après :mod:`reviewpulse.ingest` et avant les étapes de validation Great
Expectations, d'entraînement et de scoring.  Ce module constitue le
remplacement Spark de :mod:`reviewpulse.transform` pour le DAG quotidien.

Fonctionnement
-------------
1. **Construction de la session Spark** avec les paramètres du fichier
   :mod:`reviewpulse.config` (master, mémoire, fuseau horaire UTC, UI désactivée).
2. **Lecture des fichiers bruts** (`*.jsonl`) en mode récursif, extraction des
   partitions ``app_id``, ``language`` et ``sample_source`` via
   :func:`pyspark.sql.functions.regexp_extract`.
3. **Nettoyage** :
   - Suppression du BBCode avec ``regexp_replace`` ;
   - Réduction des espaces multiples et ``trim`` ;
   - Filtrage des lignes dont le texte devient vide.
4. **Dédoublonnage** : fenêtre ``row_number`` ordonnée par priorité
   (``natural`` = 0, ``negative_boost`` = 1) puis par
   ``timestamp_updated`` décroissant.  On ne garde que le rang 1.
5. **Conversion des champs** : types, dates UTC, scores, temps de jeu, longueur
   du texte, etc.
6. **Pseudonymisation** du ``steamid`` via un ``pandas_udf`` qui applique
   ``hmac.new(salt, steamid.encode(), hashlib.sha256).hexdigest()``.  Le sel
   provient de :func:`reviewpulse.config.salt` (ou du paramètre ``salt``).
7. **Alignement** du DataFrame Spark → pandas, puis cast aux types définis dans
   ``config.CLEAN_COLUMNS`` (ordre strict).
8. **Contrôle qualité** avec :func:`reviewpulse.quality.assert_quality`.
9. **Écriture** :
   - Parquet atomique via :func:`reviewpulse.transform.write_clean` (compatibilité
     avec les modules non‑Spark) ;
   - Table Iceberg « silver.reviews » via :func:`reviewpulse.lakehouse.write_table`
     (un ``overwrite`` crée un instantané).
10. **Purge** des partitions brutes anciennes via
    :func:`reviewpulse.transform.purge_raw`.
11. Journalisation du nombre de lignes traitées et du nombre d'instantanés
    créés.

Choix de conception
-------------------
- **Spark vs Pandas** : on utilise Spark uniquement pour la lecture et le
  pré‑traitement massifs, puis on convertit en pandas pour réutiliser les
  fonctions de contrôle et d'écriture déjà testées (ADR 0013, ADR 0014).
- **Gestion du temps** : Iceberg ne supporte pas les timestamps en nanosecondes,
  on les convertit en ``timestamp[us, tz=UTC]`` avec ``pyarrow.compute.cast``.
- **UDF HMAC** : implémentée en ``pandas_udf`` (type ``string``) afin d'éviter
  les limitations de Spark native.
- **Idempotence** : chaque appel de :func:`main` écrase la table Iceberg,
  créant ainsi un nouveau snapshot, conformément aux exigences mesurées.

Tests associés
--------------
- ``tests/test_spark_silver.py`` : comparaison stricte Spark / pandas,
  écriture Iceberg et relecture identique, gestion des instantanés,
  validation du schéma (déclenchement de ``ValueError`` en cas de divergence).

Limites connues
---------------
- La conversion Spark → pandas limite la taille des données à la mémoire disponible.
- Une divergence de schéma lors de l'écriture Iceberg lève ``ValueError`` (ADR 0014).
- Chaque exécution crée un nouveau snapshot Iceberg, ce qui peut augmenter l'espace de stockage.
"""

import logging
import hashlib
import hmac
import sys
import os
from pathlib import Path
from typing import Optional

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
from pyspark.sql import SparkSession, functions as F, Window
from pyspark.sql.types import StringType

from reviewpulse import config, lakehouse, transform, quality

_logger = logging.getLogger(__name__)

# Pourquoi : Regex identique à celle de transform.clean pour assurer la cohérence du nettoyage BBCode.
_BBCODE_REGEX = r"\[/?[a-zA-Z*]+(?:=[^\]]*)?\]"


def build_spark(app_name: str = "reviewpulse-silver") -> SparkSession:
    """Construit une ``SparkSession`` configurée selon ``config``.

    Depuis le 16/09/2026 et confirmé le 17/09/2026, dans l'image Airflow
    l'interpréteur Python par défaut (``python3``) ne possède pas *pandas*.
    Avec PySpark 4.2, ``SparkContext.pythonExec`` lit **uniquement** les
    variables d'environnement ``PYSPARK_PYTHON`` (et
    ``PYSPARK_DRIVER_PYTHON``) ; la configuration ``spark.pyspark.python`` n'est
    plus prise en compte.  On définit donc, avant la création de la session,
    ces variables d'environnement avec ``sys.executable`` via
    ``os.environ.setdefault``.  ``setdefault`` laisse la priorité à une valeur
    déjà explicitement définie, ce qui permet de surcharger le comportement si
    nécessaire.

    Pourquoi : Garantir que Spark utilise l'interpréteur du projet qui dispose de pandas, requis pour les pandas_udf.

    Args:
        app_name: Nom de l'application Spark.

    Returns:
        SparkSession: Session Spark configurée.

    Raises:
        Aucun : la session est créée avec les paramètres de config.

    """
    # Pourquoi : setdefault préserve les variables d'environnement déjà définies, permettant un surchargement si nécessaire.
    os.environ.setdefault('PYSPARK_PYTHON', sys.executable)
    os.environ.setdefault('PYSPARK_DRIVER_PYTHON', sys.executable)

    _logger.info("Création de la session Spark : %s", app_name)

    return (
        SparkSession.builder.appName(app_name)
        .master(config.SPARK_MASTER)
        .config("spark.driver.memory", config.SPARK_DRIVER_MEMORY)
        .config("spark.ui.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def _priority_expr(sample_col: str) -> F.Column:
    """Renvoie l'expression de priorité de dédoublonnage.

    ``natural`` → 0, ``negative_boost`` → 1.  Valeur par défaut 1.

    Pourquoi : Assurer que le flux naturel (plus fiable) prime sur le flux négatif complémentaire lors du dédoublonnage.

    Args:
        sample_col: Nom de la colonne contenant la source de l'échantillon.

    Returns:
        F.Column: Expression Spark pour le tri par priorité.

    Raises:
        Aucun.

    """
    return F.when(F.col(sample_col) == config.SAMPLE_NATURAL, 0).otherwise(1)


def build_silver(
    spark: SparkSession,
    raw_dir: Optional[Path] = None,
    salt: Optional[bytes] = None,
) -> pd.DataFrame:
    """Produit le DataFrame « silver » identique à ``transform.clean``.

    Le résultat est un ``pandas.DataFrame`` avec les colonnes et types définis
    dans ``config.CLEAN_COLUMNS`` et trié par ``review_id``.

    Pourquoi : Permettre le traitement massif des données brutes avec Spark tout en conservant la compatibilité avec les fonctions de contrôle et d'écriture pandas existantes (ADR 0014).

    Args:
        spark: Session Spark déjà construite.
        raw_dir: Répertoire racine des fichiers bruts. ``None`` → ``config.RAW_DIR``.
        salt: Sel HMAC. ``None`` → ``config.salt()``.

    Returns:
        DataFrame pandas conforme à la spécification.

    Raises:
        Aucun : les erreurs de qualité sont levées par ``quality.assert_quality`` appelé après.

    """
    raw_dir = raw_dir or config.RAW_DIR
    salt = salt or config.salt()

    _logger.info("Lecture des fichiers bruts depuis %s", raw_dir)

    # ------------------------------------------------------------------ #
    # Lecture des JSONL avec récupération du chemin complet
    # ------------------------------------------------------------------ #
    df_raw = (
        spark.read.option("recursiveFileLookup", "true")
        .option("pathGlobFilter", "*.jsonl")
        .json(str(raw_dir))
        .withColumn("input_path", F.input_file_name())
    )

    # Extraction des partitions depuis le chemin
    df = df_raw.withColumn(
        "app_id",
        F.regexp_extract(F.col("input_path"), r"app_id=(\d+)", 1).cast("long"),
    ).withColumn(
        "language",
        F.regexp_extract(F.col("input_path"), r"language=([^/]+)", 1),
    ).withColumn(
        "sample_source",
        F.when(
            F.col("input_path").rlike(r"sample=([^/]+)"),
            F.regexp_extract(F.col("input_path"), r"sample=([^/]+)", 1),
        ).otherwise(config.SAMPLE_NATURAL),
    )

    # ------------------------------------------------------------------ #
    # Nettoyage du texte
    # ------------------------------------------------------------------ #
    # NOTE : En Python, ``\\s`` reconnait les espaces Unicode (ex. U+00A0, U+2028).
    # En Spark/Java, ``\\s`` ne reconnait que l'ASCII sauf si le drapeau
    # ``(?U)`` (Unicode‑aware) est activé.  Une mesure effectuée le 16/09/2026
    # sur les données réelles a montré 11 divergences sur 8 800 avis (10 fois
    # U+00A0, 1 fois U+2028).  On utilise donc ``(?U)\\s+`` pour obtenir le même
    # comportement que ``reviewpulse.transform.clean``.
    # Pourquoi : Le drapeau (?U) active la reconnaissance des espaces Unicode pour cohérence avec transform.clean.
    df = df.withColumn(
        "review_text",
        F.trim(
            F.regexp_replace(
                F.regexp_replace(F.col("review"), _BBCODE_REGEX, ""),
                r"(?U)\s+",
                " ",
            )
        )
    ).filter(F.col("review_text") != "")

    # ------------------------------------------------------------------ #
    # Dédoublonnage avec priorité
    # ------------------------------------------------------------------ #
    # Pourquoi : Priorité au flux naturel (0) puis au flux négatif (1), et dans chaque flux à la mise à jour la plus récente.
    w = Window.partitionBy("recommendationid").orderBy(
        _priority_expr("sample_source").asc(),
        F.col("timestamp_updated").desc_nulls_last(),
    )
    df = df.withColumn("_rank", F.row_number().over(w)).filter(F.col("_rank") == 1)

    # ------------------------------------------------------------------ #
    # Colonnes dérivées
    # ------------------------------------------------------------------ #
    df = df.withColumn("review_id", F.col("recommendationid"))
    df = df.withColumn(
        "label",
        F.when(F.col("voted_up"), F.lit(1)).otherwise(F.lit(0)).cast("long"),
    )
    df = df.withColumn(
        "created_at",
        F.to_timestamp(F.col("timestamp_created")).cast("timestamp"),
    )
    df = df.withColumn(
        "updated_at",
        F.coalesce(
            F.to_timestamp(F.col("timestamp_updated")),
            F.to_timestamp(F.col("timestamp_created")),
        ).cast("timestamp")
    )
    df = df.withColumn(
        "weighted_vote_score", F.col("weighted_vote_score").cast("double")
    )
    df = df.withColumn("votes_up", F.col("votes_up").cast("long"))
    df = df.withColumn(
        "playtime_at_review_min",
        F.when(
            F.col("author").isNotNull(),
            F.col("author").getItem("playtime_at_review").cast("long"),
        ).otherwise(F.lit(0)),
    )
    df = df.withColumn("text_len", F.length(F.col("review_text")).cast("long"))

    # ------------------------------------------------------------------ #
    # Pseudonymisation du steamid via pandas_udf
    # ------------------------------------------------------------------ #
    # Pourquoi : pandas_udf évite les limitations de Spark native pour HMAC et permet l'utilisation de hashlib.
    @F.pandas_udf(StringType())
    def _hash_steamid(steamid_series: pd.Series) -> pd.Series:
        """Pseudonymise le steamid en appliquant HMAC‑SHA256 avec le sel du projet, série par série.

        Pourquoi : Appliquer le même algorithme de hachage que transform.clean pour cohérence (ADR 0004).

        Args:
            steamid_series: Série pandas contenant les steamid.

        Returns:
            pd.Series: Série pandas contenant les steamid hachés.

        Raises:
            Aucun.

        """
        return steamid_series.apply(
            lambda sid: hmac.new(salt, str(sid).encode(), hashlib.sha256).hexdigest()
        )

    df = df.withColumn(
        "author_pseudo",
        _hash_steamid(F.col("author").getItem("steamid")),
    )

    # ------------------------------------------------------------------ #
    # Sélection finale et conversion pandas
    # ------------------------------------------------------------------ #
    clean_cols = list(config.CLEAN_COLUMNS.keys())
    df = df.select(*clean_cols)

    # Conversion Spark → pandas
    pdf = df.toPandas()

    _logger.info("Conversion Spark → pandas : %d lignes", len(pdf))

    # --------------------------------------------------------------
    # Gestion des timestamps : si la série est timezone‑naïve,
    # on la localise explicitement en UTC avant le cast.
    # --------------------------------------------------------------
    # Pourquoi : Garantir que tous les timestamps sont en UTC avant conversion Arrow (ADR 0014).
    for ts_col in ("created_at", "updated_at"):
        if pd.api.types.is_datetime64_any_dtype(pdf[ts_col]):
            if pdf[ts_col].dt.tz is None:
                pdf[ts_col] = pdf[ts_col].dt.tz_localize("UTC")

    # Cast aux types pandas attendus et ordre strict
    for col, typ in config.CLEAN_COLUMNS.items():
        pdf[col] = pdf[col].astype(typ)

    pdf = pdf.sort_values("review_id").reset_index(drop=True)
    return pdf


def _arrow_table_from_df(df: pd.DataFrame) -> pa.Table:
    """Convertit le DataFrame pandas en ``pyarrow.Table`` avec timestamps en µs.

    Pourquoi : Iceberg ne supporte pas les timestamps en nanosecondes ; la conversion en microsecondes est requise pour l'écriture (ADR 0014).

    Args:
        df: DataFrame pandas avec des colonnes datetime64[ns, UTC].

    Returns:
        pa.Table: Table PyArrow avec timestamps en timestamp[us, tz=UTC].

    Raises:
        Aucun.

    """
    table = pa.Table.from_pandas(df, preserve_index=False)

    # Pourquoi : Conversion explicite ns→us requise par Iceberg (ADR 0014).
    for name, dtype in df.dtypes.items():
        if pd.api.types.is_datetime64tz_dtype(dtype):
            col = table.column(name)
            col_us = pc.cast(col, pa.timestamp("us", tz="UTC"))
            table = table.set_column(table.schema.get_field_index(name), name, col_us)
    return table


def main() -> int:
    """Exécute le pipeline Spark → Iceberg.

    Retourne 0 en cas de succès, 1 sinon (qualité insuffisante,
    sel manquant ou autre exception).

    Pourquoi : Orchestrer la construction de la zone silver, la validation qualité, l'écriture Parquet et Iceberg, et la purge des données brutes.

    Returns:
        int: 0 en cas de succès, 1 en cas d'échec.

    Raises:
        Aucun : les exceptions sont capturées et journalisées.

    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    spark = None
    try:
        _logger.info("Démarrage du pipeline Spark silver")
        spark = build_spark()
        silver_df = build_silver(spark)

        _logger.info("DataFrame silver produit : %d lignes", len(silver_df))

        # Validation qualité (bloquante)
        quality.assert_quality(silver_df)
        _logger.info("Validation qualité passée")

        # Écriture parquet compatible avec le reste du pipeline
        transform.write_clean(silver_df)
        _logger.info("Parquet écrit")

        # Écriture Iceberg (overwrite → nouveau snapshot)
        arrow_tbl = _arrow_table_from_df(silver_df)
        result = lakehouse.write_table(config.SILVER_REVIEWS_TABLE, arrow_tbl)

        _logger.info("Table Iceberg écrite : %d instantané(s)", result.get("snapshots", 0))

        # Purge des données brutes
        transform.purge_raw()
        _logger.info("Purge des données brutes effectuée")

        _logger.info(
            "Spark silver terminé : %d lignes écrites, historique de la table : %d instantané(s)",
            len(silver_df),
            result.get("snapshots", 0),
        )
        return 0
    except quality.DataQualityError as exc:
        _logger.error("Échec de la validation qualité : %s", exc)
        return 1
    except Exception:  # pragma: no cover
        _logger.exception("Erreur inattendue dans spark_silver")
        return 1
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
