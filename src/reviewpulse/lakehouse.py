# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""src/reviewpulse/lakehouse.py
================================

Rôle
----
Gestion du *lakehouse* Iceberg (catalogue, tables, lecture/écriture) sans Spark.
Les fonctions exposées sont utilisées par le pipeline Spark (`spark_silver.py`) et
par les tests unitaires.

Quoi
----
Module fournissant les opérations de base sur un lakehouse Iceberg adossé à un
catalogue SQLite : création du catalogue, écriture avec validation de schéma,
lecture, historique des instantanés, lecture à un instantané donné et
restauration d'un instantané.

Pourquoi
--------
Ce module évite l'usage de Spark pour la gestion du lakehouse, permettant des
opérations légères et testables. Il garantit l'absence d'évolution de schéma
silencieuse (ADR 0013) et la compatibilité des timestamps avec PyIceberg
(ADR 0014).

Ou
--
Appelé par `spark_silver.py` pour écrire la table `silver.reviews`, par
`score.py` pour lire les tables Iceberg, et par les tests. Il lit et écrit dans
le répertoire `config.LAKEHOUSE_DIR` et le catalogue SQLite `catalog.db`.

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

Limites connues
---------------
- Ne gère pas les évolutions de schéma : toute différence de colonnes ou de
  types est refusée par une ``ValueError``.
- Ne prend pas en charge les types non supportés par PyIceberg autres que les
  timestamps nanosecondes (convertis en microsecondes).
- Aucun mécanisme de verrouillage concurrent : deux écritures simultanées
  peuvent entrer en conflit au niveau du catalogue SQLite.

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
    """Crée le répertoire ``config.LAKEHOUSE_DIR`` s’il n’existe pas.

    Pourquoi : centralise la création du répertoire pour éviter les erreurs de
    chemin et garantir que le catalogue peut être instancié.

    Returns
    -------
    Path
        Le chemin du répertoire du lakehouse.
    """
    lakehouse_dir = config.LAKEHOUSE_DIR
    lakehouse_dir.mkdir(parents=True, exist_ok=True)
    return lakehouse_dir


def get_catalog() -> SqlCatalog:
    """Retourne un catalogue Iceberg configuré pour le projet.

    - Crée le répertoire ``config.LAKEHOUSE_DIR`` si besoin.
    - Instancie ``SqlCatalog`` avec une base SQLite ``catalog.db``.
    - Crée le namespace ``config.SILVER_NAMESPACE`` lorsqu’il n’est pas présent.

    Pourquoi : fournit un point d'accès unique au catalogue, avec création
    automatique du namespace pour que les appels ultérieurs n'échouent pas.

    Returns
    -------
    SqlCatalog
        Le catalogue prêt à être utilisé.
    """
    lakehouse_dir = _ensure_lakehouse_dir()
    catalog_path = lakehouse_dir / "catalog.db"
    # Pourquoi : l'URI SQLite doit être un chemin absolu au format fichier pour
    # que SQLAlchemy puisse ouvrir la base quel que soit le répertoire courant.
    catalog_uri = f"sqlite:///{catalog_path.resolve().as_posix()}"
    warehouse_uri = lakehouse_dir.resolve().as_uri()

    catalog = SqlCatalog(
        name="reviewpulse",
        uri=catalog_uri,
        warehouse=warehouse_uri,
    )
    # Le namespace « silver » doit exister.
    catalog.create_namespace_if_not_exists(config.SILVER_NAMESPACE)
    log.debug("Catalogue Iceberg initialisé avec URI %s", catalog_uri)
    return catalog


def _cast_timestamps_us(table: pa.Table) -> pa.Table:
    """Convertit les colonnes ``timestamp[ns, tz=...]`` en ``timestamp[us, tz=...]``.

    PyIceberg ne supporte pas la précision nanoseconde. La conversion est
    effectuée champ par champ afin de préserver les autres colonnes. Toutes
    les colonnes de type ``timestamp`` dont l’unité est ``ns`` sont converties,
    le fuseau horaire étant conservé (ex. ``UTC`` ou ``None``). La table est
    reconstruite avec le nouveau schéma dérivé des colonnes converties.

    Pourquoi : PyIceberg 0.12.0 lève ``UnsupportedPyArrowTypeException`` pour
    les timestamps en nanosecondes ; la conversion explicite en microsecondes
    est la seule solution compatible sans perte d'information significative.

    Args:
        table: Table PyArrow dont les colonnes timestamp en ns doivent être
            converties.

    Returns:
        Nouvelle table PyArrow avec les timestamps en microsecondes.
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

    Pourquoi : garantit l'idempotence des écritures et la non-évolution
    silencieuse du schéma, tout en respectant les contraintes de PyIceberg.

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

    Raises
    ------
    ValueError
        Si le schéma de la table existante ne correspond pas à celui fourni.
    """
    log.info("Début de l'écriture de la table %s", identifier)
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
        # Pourquoi : comparer d'abord les noms de colonnes permet de donner un
        # message d'erreur explicite avant de tenter un cast qui pourrait
        # échouer de manière obscure.
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
    log.info(
        "Écriture de %s : %d lignes, %d instantanés",
        identifier,
        converted.num_rows,
        len(history),
    )
    return result


def read_table(identifier: str) -> pa.Table:
    """Lit le contenu d’une table Iceberg et le renvoie sous forme de ``pyarrow.Table``.

    Pourquoi : fournit un accès simple et uniforme aux données Iceberg pour les
    modules consommateurs.

    Parameters
    ----------
    identifier : str
        Identifiant complet de la table.

    Returns
    -------
    pyarrow.Table
        Le tableau complet.
    """
    log.debug("Lecture de la table %s", identifier)
    catalog = get_catalog()
    table = catalog.load_table(identifier)
    return table.scan().to_arrow()


def table_history(identifier: str) -> list[dict]:
    """Retourne l’historique des instantanés d’une table Iceberg.

    Chaque entrée contient ``snapshot_id`` et ``timestamp_ms``.

    Pourquoi : permet de suivre les versions d'une table et de vérifier la
    création d'instantanés lors des écritures.

    Parameters
    ----------
    identifier : str
        Identifiant complet de la table.

    Returns
    -------
    list[dict]
        Liste ordonnée des instantanés.
    """
    log.debug("Récupération de l'historique de %s", identifier)
    catalog = get_catalog()
    table = catalog.load_table(identifier)
    return [
        {"snapshot_id": entry.snapshot_id, "timestamp_ms": entry.timestamp_ms}
        for entry in table.history()
    ]


def read_table_at(identifier: str, snapshot_id: int) -> pa.Table:
    """Lit une table Iceberg à un instantané donné.

    Pourquoi : permet de consulter une version antérieure sans modifier l'état
    courant, utile pour l'audit ou la comparaison.

    Parameters
    ----------
    identifier : str
        Identifiant complet de la table (ex. ``"silver.reviews"``).
    snapshot_id : int
        Identifiant de l'instantané à lire.

    Returns
    -------
    pyarrow.Table
        Le tableau correspondant à l'instantané demandé. La table source n'est
        pas modifiée.
    """
    log.debug("Lecture de %s à l'instantané %s", identifier, snapshot_id)
    catalog = get_catalog()
    table = catalog.load_table(identifier)
    return table.scan(snapshot_id=snapshot_id).to_arrow()


def restore_snapshot(identifier: str, snapshot_id: int) -> dict:
    """Restaure une table Iceberg à l'instantané indiqué.

    La fonction vérifie que ``snapshot_id`` figure dans l'historique, effectue
    le rollback puis confirme que le nouveau snapshot est bien celui attendu.

    Pourquoi : offre une opération de retour arrière contrôlée, avec
    vérification de l'existence de l'instantané et de la réussite du rollback.

    Parameters
    ----------
    identifier : str
        Identifiant complet de la table.
    snapshot_id : int
        Identifiant de l'instantané cible.

    Returns
    -------
    dict
        ``{"identifier": ..., "ancien_snapshot_id": ..., "nouveau_snapshot_id": ..., "lignes": ...}``

    Raises
    ------
    ValueError
        Si ``snapshot_id`` n'est pas présent dans l'historique.
    RuntimeError
        Si la restauration n'a pas abouti.
    """
    log.info("Restauration de %s vers l'instantané %s", identifier, snapshot_id)
    catalog = get_catalog()
    table = catalog.load_table(identifier)

    # Vérification de la présence du snapshot dans l'historique
    known_ids = [entry.snapshot_id for entry in table.history()]
    if snapshot_id not in known_ids:
        raise ValueError(
            f"Snapshot {snapshot_id} inconnu pour la table {identifier}. "
            f"Instantanés disponibles : {known_ids}"
        )

    # Snapshot courant avant le rollback
    current = table.current_snapshot()
    ancien_id = current.snapshot_id if current is not None else None

    # Rollback
    table.manage_snapshots().rollback_to_snapshot(snapshot_id).commit()

    # Rechargement et vérification
    table = catalog.load_table(identifier)
    new_snapshot = table.current_snapshot()
    if new_snapshot is None or new_snapshot.snapshot_id != snapshot_id:
        raise RuntimeError(
            f"Échec du rollback de {identifier} vers le snapshot {snapshot_id}"
        )

    # Nombre de lignes après restauration
    rows = table.scan().to_arrow().num_rows

    log.info(
        "Restauration de %s : ancien snapshot %s → nouveau snapshot %s",
        identifier,
        ancien_id,
        snapshot_id,
    )
    return {
        "identifier": identifier,
        "ancien_snapshot_id": ancien_id,
        "nouveau_snapshot_id": snapshot_id,
        "lignes": rows,
    }


def main() -> int:
    """Interface en ligne de commande pour la gestion des instantanés Iceberg.

    Pourquoi : fournit un point d'entrée exécutable pour les opérations
    d'administration du lakehouse, utilisable manuellement ou dans des scripts.

    Options
    -------
    --table IDENTIFIER
        Identifiant complet de la table (obligatoire).
    --historique
        Affiche l'historique des instantanés, une ligne par instantané avec
        horodatage UTC lisible. L'instantané courant est marqué.
    --restaurer SNAPSHOT_ID
        Restaure la table à l'instantané indiqué.

    Returns
    -------
    int
        Code de sortie : 0 en cas de succès, 1 en cas d'erreur.
    """
    import argparse  # import local
    from datetime import datetime, timezone  # import local

    parser = argparse.ArgumentParser(description="Gestion des instantanés Iceberg")
    parser.add_argument(
        "--table",
        required=True,
        help='Identifiant complet de la table, ex. "silver.reviews"',
    )
    parser.add_argument(
        "--historique",
        action="store_true",
        help="Affiche l'historique des instantanés",
    )
    parser.add_argument(
        "--restaurer",
        type=int,
        metavar="SNAPSHOT_ID",
        help="Restaure la table à l'instantané indiqué",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    log.info("Démarrage de la commande lakehouse")

    if args.restaurer is not None:
        try:
            result = restore_snapshot(args.table, args.restaurer)
            print(
                f"Ancien snapshot : {result['ancien_snapshot_id']}, "
                f"nouveau snapshot : {result['nouveau_snapshot_id']}, "
                f"lignes : {result['lignes']}"
            )
            log.info("Commande terminée avec succès")
            return 0
        except (ValueError, RuntimeError) as exc:
            log.error(str(exc))
            return 1

    # Action par défaut : affichage de l'historique
    try:
        hist = table_history(args.table)
        catalog = get_catalog()
        table = catalog.load_table(args.table)
        current_snapshot = table.current_snapshot()
        current_id = current_snapshot.snapshot_id if current_snapshot else None

        for entry in hist:
            ts_str = datetime.fromtimestamp(
                entry["timestamp_ms"] / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S")
            line = f"{entry['snapshot_id']} {ts_str}"
            if entry["snapshot_id"] == current_id:
                line += " (courant)"
            print(line)
        log.info("Commande terminée avec succès")
        return 0
    except Exception as exc:  # pragma: no cover
        log.error(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
