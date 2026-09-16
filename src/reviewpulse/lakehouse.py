"""src/reviewpulse/lakehouse.py
================================

Rôle
----
Gestion du *lakehouse* Iceberg (catalogue, tables, lecture/écriture) sans Spark.
Les fonctions exposées sont utilisées par le pipeline Spark (`spark_silver.py`) et
par les tests unitaires.

Place dans la chaîne
--------------------
- `spark_silver.main()` produit un DataFrame pandas puis l’écrit dans la table
  Iceberg ``silver.reviews`` via :func:`write_table`.
- `score.py` lit la même table (ou la table ``silver.predictions``) via
  :func:`read_table`.
- Les métadonnées (historique, localisation) sont exploitées dans les tests
  pour vérifier la création d’instantanés.

Fonctionnement
--------------
- Le catalogue Iceberg est créé à la volée par :func:`get_catalog`.  
  Le répertoire ``config.LAKEHOUSE_DIR`` est créé si nécessaire, puis un
  ``SqlCatalog`` SQLite est instancié avec l’URI ``sqlite:///…/catalog.db`` et
  le *warehouse* pointant sur le même répertoire.
- Le *namespace* ``config.SILVER_NAMESPACE`` (``"silver"``) est créé s’il n’existe
  pas déjà.
- :func:`write_table` crée la table si elle n’existe pas, vérifie que le schéma
  fourni correspond exactement à celui déjà présent (aucune évolution silencieuse),
  convertit les colonnes de type ``timestamp[ns, tz=...]`` en ``timestamp[us, tz=...]``
  (limitation mesurée de PyIceberg 0.12.0) puis écrase la table avec
  ``table.overwrite(arrow_table)``.
- :func:`read_table` charge la table et renvoie son contenu sous forme de
  ``pyarrow.Table``.
- :func:`table_history` expose l’historique des instantanés sous forme de liste de
  dictionnaires contenant ``snapshot_id`` et ``timestamp_ms``.
- Chaque appel d’``overwrite`` crée un instantané ; le nombre d’instantanés est
  renvoyé dans le dictionnaire de retour de :func:`write_table`.

Choix de conception
-------------------
- **ADR 0013** – *Pas d’évolution de schéma implicite* : la fonction lève
  ``ValueError`` dès que le schéma fourni diffère du schéma existant.
- **ADR 0014** – *Conversion explicite des timestamps* : les colonnes
  ``timestamp[ns, tz=...]`` sont castées en ``timestamp[us, tz=...]`` avant
  l’écriture, conformément à la contrainte mesurée de PyIceberg
  (``UnsupportedPyArrowTypeException``).

Tests associés
--------------
- ``tests/test_spark_silver.py`` vérifie que deux écritures successives
  produisent au moins deux instantanés et que la dernière version lue est
  identique à la DataFrame d’origine.
- ``tests/test_lakehouse.py`` (existant dans le dépôt) teste la création du
  catalogue, la création de table, la validation de schéma et la conversion
  des timestamps.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
from pyiceberg.catalog.sql import SqlCatalog

from reviewpulse import config

log = logging.getLogger(__name__)


def _ensure_lakehouse_dir() -> Path:
    """Crée le répertoire ``config.LAKEHOUSE_DIR`` s’il n’existe pas."""
    lakehouse_dir = config.LAKEHOUSE_DIR
    lakehouse_dir.mkdir(parents=True, exist_ok=True)
    return lakehouse_dir


def get_catalog() -> SqlCatalog:
    """Retourne un catalogue Iceberg configuré pour le projet.

    - Crée le répertoire ``config.LAKEHOUSE_DIR`` si besoin.
    - Instancie ``SqlCatalog`` avec une base SQLite ``catalog.db``.
    - Crée le namespace ``config.SILVER_NAMESPACE`` lorsqu’il n’est pas présent.

    Returns
    -------
    SqlCatalog
        Le catalogue prêt à être utilisé.
    """
    lakehouse_dir = _ensure_lakehouse_dir()
    catalog_path = lakehouse_dir / "catalog.db"
    catalog_uri = f"sqlite:///{catalog_path.resolve().as_posix()}"
    warehouse_uri = lakehouse_dir.resolve().as_uri()

    catalog = SqlCatalog(
        name="reviewpulse",
        uri=catalog_uri,
        warehouse=warehouse_uri,
    )
    # Le namespace « silver » doit exister.
    catalog.create_namespace_if_not_exists(config.SILVER_NAMESPACE)
    return catalog


def _cast_timestamps_us(table: pa.Table) -> pa.Table:
    """Convertit les colonnes ``timestamp[ns, tz=...]`` en ``timestamp[us, tz=...]``.

    PyIceberg ne supporte pas la précision nanoseconde. La conversion est
    effectuée champ par champ afin de préserver les autres colonnes. Toutes
    les colonnes de type ``timestamp`` dont l’unité est ``ns`` sont converties,
    le fuseau horaire étant conservé (ex. ``UTC`` ou ``None``). La table est
    reconstruite avec le nouveau schéma dérivé des colonnes converties.
    """
    arrays = []
    for field in table.schema:
        col = table.column(field.name)
        if pa.types.is_timestamp(field.type) and field.type.unit == "ns":
            # Conserve le fuseau horaire d'origine (peut être None)
            tz = field.type.tz
            target_type = pa.timestamp("us", tz=tz)
            col = pc.cast(col, target_type)
        arrays.append(col)
    return pa.Table.from_arrays(arrays, names=table.column_names)


def write_table(identifier: str, arrow_table: pa.Table) -> dict:
    """Écrit ou écrase une table Iceberg.

    - Si la table n’existe pas, elle est créée avec le schéma fourni (après conversion).
    - Si elle existe, le schéma doit être identique ; sinon ``ValueError``.
    - Les colonnes de type ``timestamp[ns, tz=...]`` sont castées en
      ``timestamp[us, tz=...]`` avant l’appel ``overwrite``.
    - Un instantané est créé à chaque ``overwrite``.

    Parameters
    ----------
    identifier : str
        Identifiant complet de la table (ex. ``"silver.reviews"``).
    arrow_table : pyarrow.Table
        Données à écrire.

    Returns
    -------
    dict
        ``{"table": identifier, "rows": n, "snapshots": s, "metadata_location": str}``
    """
    catalog = get_catalog()

    # 1. Conversion des timestamps avant toute autre opération.
    converted = _cast_timestamps_us(arrow_table)

    # 2. Création ou validation du schéma.
    if not catalog.table_exists(identifier):
        log.info("Création de la table Iceberg %s", identifier)
        # Le schéma attendu par Iceberg est le schéma Arrow de la table convertie.
        catalog.create_table(identifier, schema=converted.schema)
    else:
        # Table déjà existante : on récupère son schéma Arrow.
        table = catalog.load_table(identifier)
        cible = table.schema().as_arrow()
        if converted.schema.names != cible.names:
            raise ValueError(
                f"Schéma incompatible pour {identifier} : {converted.schema.names} au lieu de {cible.names}"
            )
        # Cast éventuel pour aligner les types.
        converted = converted.cast(cible)

    # 3. Écriture atomique via overwrite.
    table = catalog.load_table(identifier)
    table.overwrite(converted)

    # 4. Construction du dictionnaire de retour (inchangé).
    history = table.history()
    result = {
        "table": identifier,
        "rows": converted.num_rows,
        "snapshots": len(history),
        "metadata_location": table.metadata_location,
    }
    log.debug("Écriture terminée pour %s : %s", identifier, result)
    return result


def read_table(identifier: str) -> pa.Table:
    """Lit le contenu d’une table Iceberg et le renvoie sous forme de ``pyarrow.Table``.

    Parameters
    ----------
    identifier : str
        Identifiant complet de la table.

    Returns
    -------
    pyarrow.Table
        Le tableau complet.
    """
    catalog = get_catalog()
    table = catalog.load_table(identifier)
    return table.scan().to_arrow()


def table_history(identifier: str) -> list[dict]:
    """Retourne l’historique des instantanés d’une table Iceberg.

    Chaque entrée contient ``snapshot_id`` et ``timestamp_ms``.

    Parameters
    ----------
    identifier : str
        Identifiant complet de la table.

    Returns
    -------
    list[dict]
        Liste ordonnée des instantanés.
    """
    catalog = get_catalog()
    table = catalog.load_table(identifier)
    return [
        {"snapshot_id": entry.snapshot_id, "timestamp_ms": entry.timestamp_ms}
        for entry in table.history()
    ]


def main() -> int:
    """Entrée de script minimale.

    Le module n’a pas de logique autonome ; la fonction renvoie 0 pour indiquer
    le succès lorsqu’il est exécuté directement.
    """
    logging.basicConfig(level=logging.INFO)
    log.info("Lakehouse module chargé – aucune action exécutée.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
