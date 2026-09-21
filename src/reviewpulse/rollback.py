"""reviewpulse.rollback
=====================

Rôle
----
Module de rollback manuel pour le modèle MLflow champion. Permet de lister les versions,
identifier le champion actuel, et déplacer l'alias champion vers une version antérieure.

Place dans la chaîne
--------------------
Utilisé manuellement par les opérateurs ou dans des scripts d'administration.
Aucun autre module du projet ne dépend directement de ce fichier.

Fonctionnement
--------------
* ``versions_disponibles`` interroge le registre MLflow via :class:`mlflow.tracking.MlflowClient`,
  récupère les versions du modèle ``config.MODEL_NAME`` et, pour chaque version,
  extrait :
  - le numéro de version,
  - le timestamp de création,
  - les métriques ``f1_macro`` et ``ecart_train_test`` si elles existent,
  - la liste des alias qui pointent vers cette version.
  Le résultat est trié du plus récent au plus ancien.
* ``champion_actuel`` renvoie la version associée à l'alias ``config.ALIAS_CHAMPION``,
  ou ``None`` si l'alias n'est pas défini.
* ``basculer`` vérifie que la version demandée existe, puis déplace l'alias
  ``champion`` vers celle‑ci en appelant ``client.set_registered_model_alias``.
  L'ancienne version (ou ``None``) et la nouvelle version sont retournées dans un
  dictionnaire.
* ``main`` expose une interface CLI simple : sans argument, il affiche la liste
  des versions et le champion actuel ; avec ``--vers VERSION`` il effectue la
  bascule.

Le module suit le style du projet : typage strict, journalisation via le module
``logging`` et utilisation du même client MLflow.

Décision envisagée ici : ADR 0016 — le déploiement progressif passe par l'alias `champion`, et le retour arrière aussi.

Quoi
----
Module de rollback manuel pour le modèle MLflow champion. Permet de lister les versions,
identifier le champion actuel, et déplacer l'alias champion vers une version antérieure.

Pourquoi
--------
Le projet ne possède aucun mécanisme automatique de retour en arrière. L'alias ``champion``
ne fait que progresser lors des promotions. Ce module évite le défaut où un opérateur
devrait modifier manuellement le registre MLflow sans trace, sans validation et sans
journalisation. Il garantit que chaque rollback est vérifié (la version existe), journalisé
et réversible par la commande inverse.

Ou
----
Appelé manuellement par les opérateurs ou dans des scripts d'administration. Lit et écrit
dans le registre MLflow (config.MLFLOW_TRACKING_URI, config.MODEL_NAME, config.ALIAS_CHAMPION).
Aucun autre module du projet ne dépend directement de ce fichier.

Comment
-------
Le module instancie un client MLflow avec l'URI de tracking configurée. Il interroge le
registre pour lister les versions du modèle, extrait les métriques depuis les runs associés,
et récupère les alias. Pour le rollback, il vérifie d'abord que la version cible existe,
relève l'ancien champion, déplace l'alias via l'API MLflow, et journalise l'opération.
Les timestamps MLflow (millisecondes) sont convertis en datetime UTC pour l'affichage.

Choix de conception
-------------------
* Déplacer un alias plutôt que recopier un artefact : l'opération est atomique côté registre
  et se défait par la commande inverse. Alternative écartée : copier les artefacts du modèle
  (non atomique, risque d'incohérence, pas de trace dans le registre).
* Vérification explicite de l'existence de la version avant bascule : lève ValueError si
  la version n'existe pas. Alternative écartée : laisser MLflow lever MlflowException
  (message moins clair pour l'opérateur).
* Tri décroissant par timestamp : les versions les plus récentes en premier pour faciliter
  la lecture. Alternative écartée : tri par numéro de version (ordre non garanti dans MLflow).
* Récupération des métriques non critique : si échec, on logue en debug et on continue.
  Alternative écartée : échec complet de la liste (bloquerait le rollback pour un détail).

Limites connues
---------------
* Ne garantit pas que la version cible est fonctionnelle (pas de test de chargement du modèle).
* Ne journalise pas dans un fichier d'audit dédié (utilise le logging standard).
* Ne gère pas les rollbacks en cascade (un seul alias à la fois).
* Dépend de la disponibilité du serveur MLflow au moment de l'exécution.
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import mlflow
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from reviewpulse import config

logger = logging.getLogger(__name__)


def _client(tracking_uri: Optional[str] = None) -> MlflowClient:
    """
    Instancie un client MLflow pour accéder au registre.

    Pourquoi : centraliser la création du client avec gestion de l'URI de tracking,
    permettant aux tests de fournir une URI différente sans modifier config.

    Args
    ----
    tracking_uri : Optional[str]
        URI du serveur MLflow. Si None, utilise config.MLFLOW_TRACKING_URI.

    Returns
    -------
    MlflowClient
        Client MLflow configuré avec l'URI fournie.
    """
    if tracking_uri is None:
        tracking_uri = config.MLFLOW_TRACKING_URI
    mlflow.set_tracking_uri(tracking_uri)
    return MlflowClient(tracking_uri=tracking_uri)


def versions_disponibles(tracking_uri: str | None = None) -> List[Dict[str, Any]]:
    """
    Liste les versions du modèle config.MODEL_NAME dans le registre MLflow.

    Pourquoi : fournir aux opérateurs une vue complète des versions disponibles
    avec leurs métriques et alias, pour décider quelle version utiliser en rollback.

    Args
    ----
    tracking_uri : str | None
        URI du serveur MLflow. Si None, utilise la valeur par défaut de config.

    Returns
    -------
    List[Dict[str, Any]]
        Liste de dictionnaires, chacun contenant :
        - version (str) : numéro de version,
        - creation_timestamp (int | float) : timestamp (ms depuis epoch) de création,
        - f1_macro (float | None) : métrique si disponible,
        - ecart_train_test (float | None) : métrique si disponible,
        - aliases (list[str]) : alias pointant sur la version.
        Trié du plus récent au plus ancien.

    Raises
    ------
    MlflowException si l'appel au registre échoue. Les autres erreurs sont propagées.
    """
    client = _client(tracking_uri)
    versions = client.search_model_versions(f"name='{config.MODEL_NAME}'")
    result: List[Dict[str, Any]] = []

    for mv in versions:
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
            # Pourquoi : la récupération des métriques est secondaire pour le rollback.
            # Un échec ici ne doit pas bloquer la liste des versions.
            # Alternative écartée : lever une exception (bloquerait l'opérateur).
            logger.debug("Échec récupération métriques version %s", version_str)

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

    # Pourquoi : l'opérateur voit d'abord le champion actuel et les versions récentes.
    # Alternative écartée : tri par numéro de version (ordre non garanti dans MLflow).
    result.sort(key=lambda d: d["creation_timestamp"], reverse=True)
    return result


def champion_actuel(tracking_uri: str | None = None) -> str | None:
    """
    Retourne la version désignée par l'alias config.ALIAS_CHAMPION.

    Pourquoi : identifier quelle version porte l'alias champion avant
    d'effectuer un rollback, et pour afficher l'état actuel à l'opérateur.

    Args
    ----
    tracking_uri : str | None
        URI du serveur MLflow. Si None, utilise la valeur par défaut de config.

    Returns
    -------
    str | None
        Numéro de version du champion actuel, ou None si l'alias n'existe pas.

    Raises
    ------
    Aucune exception levée explicitement. MlflowException est capturée et retourne None.
    """
    client = _client(tracking_uri)
    try:
        mv = client.get_model_version_by_alias(
            name=config.MODEL_NAME, alias=config.ALIAS_CHAMPION
        )
        return str(mv.version)
    except MlflowException:
        # Pourquoi : l'absence d'alias champion est un état valide (premier déploiement).
        # On logue en debug pour tracer sans alerter l'opérateur.
        logger.debug("Alias champion absent pour le modèle %s", config.MODEL_NAME)
        return None


def basculer(version: str, tracking_uri: str | None = None) -> Dict[str, Optional[str]]:
    """
    Déplace l'alias ``champion`` vers la version demandée après vérification.

    Pourquoi : effectuer le rollback de manière journalisée, en vérifiant
    que la version cible existe avant de modifier le registre.

    Args
    ----
    version: str
        Numéro de version cible (exemple : ``"3"``).
    tracking_uri: str | None
        URI du serveur MLflow ; si ``None``, la valeur par défaut du
        fichier de configuration est utilisée.

    Returns
    -------
    Dict[str, Optional[str]]
        ``{"ancienne": <ancienne_version>, "nouvelle": <version>}``.

    Raises
    ------
    ValueError
        Si la version cible n'existe pas dans le registre.
    MlflowException
        Si le déplacement de l'alias échoue côté MLflow.
    """
    client = _client(tracking_uri)

    # Vérification de l'existence de la version cible
    try:
        client.get_model_version(name=config.MODEL_NAME, version=version)
    except MlflowException as exc:
        # Pourquoi : message d'erreur clair pour l'opérateur plutôt que l'exception MLflow brute.
        # Alternative écartée : laisser propaguer MlflowException (message moins explicite).
        raise ValueError(f"La version {version} n'existe pas pour le modèle {config.MODEL_NAME}") from exc

    # Pourquoi : relever l'ancien champion avant de déplacer l'alias pour journalisation.
    ancienne = champion_actuel(tracking_uri)

    # Déplacement de l'alias
    try:
        client.set_registered_model_alias(
            name=config.MODEL_NAME,
            alias=config.ALIAS_CHAMPION,
            version=version,
        )
        logger.info(
            "Rollback : alias %s déplacé vers version %s",
            config.ALIAS_CHAMPION,
            version,
        )
    except MlflowException as exc:
        # Pourquoi : journaliser l'échec pour trace d'audit avant de propager.
        logger.error("Échec déplacement alias %s vers version %s", config.ALIAS_CHAMPION, version)
        raise

    return {"ancienne": ancienne, "nouvelle": version}


def _afficher_versions(versions: List[Dict[str, Any]]) -> None:
    """
    Affiche de façon lisible la liste des versions retournées par versions_disponibles.

    Pourquoi : présenter les timestamps et métriques des versions dans un format tabulaire lisible
    pour l'opérateur en ligne de commande.

    Args
    ----
    versions : List[Dict[str, Any]]
        Liste de dictionnaires de versions (sortie de versions_disponibles).

    Returns
    -------
    None
        Affiche sur stdout via print.
    """
    if not versions:
        print("Aucune version disponible.")
        return

    print(f"{'Version':<8} {'Créée le':<20} {'F1_macro':<10} {'Ecart_train_test':<18} Aliases")
    print("-" * 80)
    for v in versions:
        ts = v["creation_timestamp"]
        # Conversion du timestamp MLflow (ms) en datetime UTC pour affichage.
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

    Pourquoi : exposer les fonctions de rollback via une CLI simple pour les opérateurs,
    avec deux modes : liste des versions (sans argument) ou bascule (avec --vers).

    Returns
    -------
    int
        0 en cas de succès, 1 en cas d'erreur.

    Raises
    ------
    Aucune exception levée explicitement, sauf SystemExit en cas d'erreur.
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
        # Pourquoi : journaliser toute erreur pour diagnostic avant de retourner un code d'erreur.
        # Alternative écartée : laisser propager (pas de trace dans les logs).
        logger.error("Erreur lors du rollback : %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
