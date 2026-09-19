"""reviewpulse.rollback
=====================

Rôle
----
Fournit des outils en ligne de commande pour revenir à une version antérieure
du modèle MLflow « champion ». Le projet ne possède aucun mécanisme
automatique de retour en arrière : l’alias ``champion`` ne fait que progresser.
Ce module permet de :

* lister les versions disponibles avec leurs métadonnées,
* identifier la version actuellement désignée comme champion,
* déplacer l’alias ``champion`` vers une version antérieure, en journalisant
  l’opération.

Place dans la chaîne
--------------------
Utilisé manuellement par les opérateurs ou dans des scripts d’administration.
Aucun autre module du projet ne dépend directement de ce fichier.

Fonctionnement
--------------
* ``versions_disponibles`` interroge le registre MLflow via :class:`mlflow.tracking.MlflowClient`,
  récupère les versions du modèle ``config.MODEL_NAME`` et, pour chaque version,
  extrait :
  - le numéro de version,
  - le timestamp de création,
  - les métriques ``f1_macro`` et ``ecart_train_test`` si elles existent,
  - la liste des alias qui pointent vers cette version.
  Le résultat est trié du plus récent au plus ancien.
* ``champion_actuel`` renvoie la version associée à l’alias ``config.ALIAS_CHAMPION``,
  ou ``None`` si l’alias n’est pas défini.
* ``basculer`` vérifie que la version demandée existe, puis déplace l’alias
  ``champion`` vers celle‑ci en appelant ``client.set_registered_model_alias``.
  L’ancienne version (ou ``None``) et la nouvelle version sont retournées dans un
  dictionnaire.
* ``main`` expose une interface CLI simple : sans argument, il affiche la liste
  des versions et le champion actuel ; avec ``--vers VERSION`` il effectue la
  bascule.

Le module suit le même style que :pymod:`reviewpulse.score` : typage strict,
journalisation via le module ``logging`` et utilisation du même client MLflow.

"""

from __future__ import annotations

import argparse
import logging
from typing import Any, Dict, List, Optional

import mlflow
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException

from reviewpulse import config
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _client(tracking_uri: Optional[str] = None) -> MlflowClient:
    """Instancie un :class:`MlflowClient` avec l'URI fourni ou la valeur par défaut."""
    if tracking_uri is None:
        tracking_uri = config.MLFLOW_TRACKING_URI
    mlflow.set_tracking_uri(tracking_uri)
    return MlflowClient(tracking_uri=tracking_uri)


def versions_disponibles(tracking_uri: str | None = None) -> List[Dict[str, Any]]:
    """
    Liste les versions du modèle ``config.MODEL_NAME`` dans le registre MLflow.

    Chaque dictionnaire retourné contient :
    - ``version`` (str) : numéro de version,
    - ``creation_timestamp`` (int) : timestamp (ms depuis epoch) de création,
    - ``f1_macro`` (float | None) : métrique si disponible,
    - ``ecart_train_test`` (float | None) : métrique si disponible,
    - ``aliases`` (list[str]) : alias pointant sur la version.

    Le résultat est trié du plus récent au plus ancien.
    """
    client = _client(tracking_uri)
    versions = client.search_model_versions(f"name='{config.MODEL_NAME}'")
    result: List[Dict[str, Any]] = []

    for mv in versions:
        # mv est de type ModelVersion
        version_str = str(mv.version)
        creation_ts = mv.creation_timestamp  # type: ignore[attr-defined]

        # Récupération des métriques via le run associé
        f1_macro: Optional[float] = None
        ecart_train_test: Optional[float] = None
        try:
            run = client.get_run(mv.run_id)  # type: ignore[attr-defined]
            metrics = run.data.metrics
            f1_macro = metrics.get("f1_macro")
            ecart_train_test = metrics.get("ecart_train_test")
        except Exception:  # pragma: no cover – récupération des métriques non critique
            logger.debug("Impossible de récupérer les métriques pour la version %s", version_str)

        # Alias – l'attribut ``aliases`` existe depuis MLflow 2.0
        aliases: List[str] = getattr(mv, "aliases", [])  # type: ignore[attr-defined]

        result.append(
            {
                "version": version_str,
                "creation_timestamp": creation_ts,
                "f1_macro": f1_macro,
                "ecart_train_test": ecart_train_test,
                "aliases": list(aliases),
            }
        )

    # Tri décroissant selon le timestamp de création
    result.sort(key=lambda d: d["creation_timestamp"], reverse=True)
    return result


def champion_actuel(tracking_uri: str | None = None) -> str | None:
    """
    Retourne la version désignée par l'alias ``config.ALIAS_CHAMPION``.

    Si l'alias n'existe pas, renvoie ``None``.
    """
    client = _client(tracking_uri)
    try:
        mv = client.get_model_version_by_alias(
            name=config.MODEL_NAME, alias=config.ALIAS_CHAMPION
        )
        return str(mv.version)
    except MlflowException:
        logger.debug("Alias %s non trouvé pour le modèle %s", config.ALIAS_CHAMPION, config.MODEL_NAME)
        return None


def basculer(version: str, tracking_uri: str | None = None) -> Dict[str, Optional[str]]:
    """
    Déplace l'alias ``champion`` vers la version demandée.

    Parameters
    ----------
    version: str
        Numéro de version cible (exemple : ``"3"``).
    tracking_uri: str | None
        URI du serveur MLflow ; si ``None``, la valeur par défaut du
        fichier de configuration est utilisée.

    Returns
    -------
    dict
        ``{"ancienne": <ancienne_version>, "nouvelle": <version>}``.

    Raises
    ------
    ValueError
        Si la version cible n'existe pas dans le registre.
    """
    client = _client(tracking_uri)

    # Vérification de l'existence de la version cible
    try:
        client.get_model_version(name=config.MODEL_NAME, version=version)
    except MlflowException as exc:
        raise ValueError(f"La version {version} n'existe pas pour le modèle {config.MODEL_NAME}") from exc

    ancienne = champion_actuel(tracking_uri)

    # Déplacement de l'alias
    try:
        client.set_registered_model_alias(
            name=config.MODEL_NAME,
            alias=config.ALIAS_CHAMPION,
            version=version,
        )
        logger.info(
            "Alias %s déplacé de %s vers %s",
            config.ALIAS_CHAMPION,
            ancienne if ancienne is not None else "None",
            version,
        )
    except MlflowException as exc:
        logger.error("Échec du déplacement de l'alias %s vers la version %s : %s", config.ALIAS_CHAMPION, version, exc)
        raise

    return {"ancienne": ancienne, "nouvelle": version}


def _afficher_versions(versions: List[Dict[str, Any]]) -> None:
    """Affiche de façon lisible la liste des versions retournées par ``versions_disponibles``."""
    if not versions:
        print("Aucune version disponible.")
        return

    print(f"{'Version':<8} {'Créée le':<20} {'F1_macro':<10} {'Ecart_train_test':<18} Aliases")
    print("-" * 80)
    for v in versions:
        ts = v["creation_timestamp"]
        # Le registre MLflow rend un horodatage en millisecondes depuis l'époque Unix.
        date_str = (
            datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            if isinstance(ts, (int, float))
            else str(ts)
        )
        f1 = f"{v['f1_macro']:.4f}" if v["f1_macro"] is not None else "N/A"
        ecart = f"{v['ecart_train_test']:.4f}" if v["ecart_train_test"] is not None else "N/A"
        aliases = ", ".join(v["aliases"])
        print(f"{v['version']:<8} {date_str:<20} {f1:<10} {ecart:<18} {aliases}")


def main() -> int:
    """
    Interface en ligne de commande.

    - Sans argument : affiche les versions disponibles et le champion actuel.
    - Avec ``--vers VERSION`` : déplace l'alias ``champion`` vers la version indiquée.

    Retourne ``0`` en cas de succès, ``1`` sinon.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    parser = argparse.ArgumentParser(description="Gestion du rollback du modèle champion.")
    parser.add_argument(
        "--vers",
        dest="target_version",
        metavar="VERSION",
        help="Version du modèle vers laquelle déplacer l'alias champion.",
    )
    args = parser.parse_args()

    try:
        if args.target_version:
            result = basculer(args.target_version)
            print(f"Alias déplacé : ancienne version = {result['ancienne']}, nouvelle version = {result['nouvelle']}")
        else:
            versions = versions_disponibles()
            _afficher_versions(versions)
            champ = champion_actuel()
            print(f"\nChampion actuel : {champ if champ is not None else 'Aucun'}")
        return 0
    except Exception as exc:  # pragma: no cover
        logger.exception("Erreur lors de l'exécution du rollback : %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
