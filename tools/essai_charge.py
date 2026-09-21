# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""tools.essai_charge
====================

Mesure de charge (débit et latence) d’une instance de l’API ReviewPulse.

Pourquoi ?
-----------
L’indicateur **AIA 4** du référentiel « conteneurs et orchestration sous charge » requiert
une preuve que le service supporte un trafic soutenu.  Le code actuel ne mesure
ni débit ni latence ; cet outil réalise une campagne de requêtes parallèles
et produit un rapport Markdown placé dans ``docs/evidence/``.

Où ?
----
* Point d’accès de santé : ``GET {base_url}/health``
* Point d’accès de prédiction : ``POST {base_url}/predict`` avec corps JSON
  ``{"texts": ["…"]}``

Comment ?
---------
* Bibliothèque standard uniquement : ``urllib.request`` pour les appels HTTP,
  ``concurrent.futures.ThreadPoolExecutor`` pour la concurrence.
* Aucun arrêt de la campagne en cas d’erreur réseau : chaque requête renvoie
  un tuple indiquant le succès, la durée et le code HTTP éventuel.
* Les percentiles sont calculés avec la méthode *nearest‑rank* :
  pour un percentile *p* (ex. 99) et *n* valeurs triées, l’indice est
  ``ceil(p/100 * n) - 1`` (indice 0‑based).  Cette convention est documentée
  dans le code.

Choix de conception
--------------------
- **Bibliothèque standard uniquement** : on évite d’ajouter la dépendance ``requests`` ou ``httpx`` afin de rester compatible avec les environnements minimalistes (exécution CI, conteneurs légers).  
  *Alternative écartée* : utilisation d’``httpx`` + ``asyncio`` qui aurait introduit une complexité asynchrone non justifiée pour ce script de mesure.  
- **Méthode *nearest‑rank* pour les percentiles** : choisie pour sa simplicité et sa conformité avec la spécification de l’indicateur AIA 4.  
  *Alternative écartée* : interpolation linéaire, qui aurait nécessité un traitement supplémentaire et aurait pu introduire des variations de résultats entre exécutions.
- **Concurrence via ``ThreadPoolExecutor``** : les appels HTTP sont I/O‑bound ; les threads offrent un parallélisme suffisant sans la surcharge d’un processus complet.  
  *Alternative écartée* : ``ProcessPoolExecutor`` qui aurait augmenté la consommation mémoire sans bénéfice notable.

Limites connues
---------------
- La mesure est réalisée sur une seule machine ; elle ne garantit pas le
  comportement d’un déploiement réparti sur plusieurs nœuds ou sous des
  conditions réseau différentes.
- Le point d’accès ``/predict`` accepte uniquement une **liste** de textes de
  taille 1 à 100 ; le script ne supporte pas l’envoi de listes plus longues.
- Aucun mécanisme d’ajustement dynamique des seuils d’erreur ou de latence n’est
  prévu ; les valeurs sont fixées via les arguments de ligne de commande.

"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import sys
import time
import math
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# 1. Vérification du service
# --------------------------------------------------------------------------- #

def verifier_service(base_url: str, delai: float) -> None:
    """
    Vérifie la disponibilité du service via l’endpoint ``/health``.
    Pourquoi : garantir que la campagne ne démarre pas si le service n’est pas joignable,
    évitant ainsi une perte de temps et des mesures vides.
    Parameters
    ----------
    base_url : str
        URL de base du service (ex. ``http://localhost:8000``).
    delai : float
        Timeout en secondes pour la requête.

    Raises
    ------
    RuntimeError
        Si la connexion échoue ou si le code HTTP n’est pas 200.
    """
    logger.info("Vérification du service health à %s avec délai %s", base_url, delai)
    url = f"{base_url.rstrip('/')}/health"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=delai) as resp:
            code = resp.getcode()
            if code != 200:
                raise RuntimeError(
                    # L'URL fait partie du message : sans elle, on ne sait pas quel
                    # deploiement a echoue quand on en eprouve plusieurs.
                    f"Le service {url} a répondu {code} au lieu de 200 sur /health."
                )
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Impossible de joindre le service à {url} : {exc}") from exc
    logger.info("Service health OK (code 200)")

# --------------------------------------------------------------------------- #
# 2. Une requête individuelle
# --------------------------------------------------------------------------- #

def une_requete(base_url: str, texte: str, delai: float) -> Tuple[bool, float, int | None]:
    """
    Envoie une requête POST vers ``/predict`` et renvoie le succès, la durée et le code HTTP.
    Pourquoi : encapsuler la logique d’appel unique afin de pouvoir la paralléliser
    et de centraliser la gestion des erreurs réseau.
    Parameters
    ----------
    base_url : str
        URL de base du service.
    texte : str
        Texte à analyser.
    delai : float
        Timeout en secondes pour la requête.

    Returns
    -------
    tuple[bool, float, int | None]
        ``(succes, duree_en_secondes, code_http)``.
        ``succes`` vaut ``False`` en cas d’exception réseau,
        ``code_http`` vaut ``None`` dans ce cas.
    """
    url = f"{base_url.rstrip('/')}/predict"
    # Le contrat reel de /predict est une LISTE de textes, `texts`, de 1 a 100
    # elements — verifie dans src/reviewpulse/api.py, classe PredictRequest. Un corps
    # `{"text": ...}` est refuse avec un code 422, et la campagne ne mesurerait alors
    # que des rejets (constate le 19/09/2026 en lancant l'outil contre le service).
    payload = json.dumps({"texts": [texte]}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    debut = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=delai) as resp:
            code = resp.getcode()
            # Lecture du corps pour s’assurer que la réponse est bien reçue
            resp.read()
            duree = time.perf_counter() - debut
            return True, duree, code
    except urllib.error.URLError as exc:
        duree = time.perf_counter() - debut
        logger.debug("Requête /predict échouée : %s", exc)
        return False, duree, None

# --------------------------------------------------------------------------- #
# 3. Mesure de charge
# --------------------------------------------------------------------------- #

def _calculer_percentile(valeurs: List[float], percentile: float) -> float:
    """
    Retourne le percentile indiqué (0‑100) selon la méthode *nearest‑rank*.
    Pourquoi : fournir une fonction de calcul de percentile fiable et conforme
    à la spécification AIA 4, réutilisable dans le reste du module.
    La liste ``valeurs`` doit être triée en ordre croissant.
    """
    if not valeurs:
        return 0.0
    n = len(valeurs)
    rank = math.ceil(percentile / 100.0 * n)
    index = max(rank - 1, 0)
    return valeurs[index]

def mesurer(
    base_url: str,
    textes: List[str],
    concurrence: int,
    nb_requetes: int,
    delai: float,
) -> Dict[str, Any]:
    """
    Lance ``nb_requetes`` requêtes réparties sur ``concurrence`` threads.
    Pourquoi : mesurer le débit, la latence et le taux d’erreur du service sous
    une charge contrôlée, afin de fournir les métriques requises par l’indicateur AIA 4.
    Parameters
    ----------
    base_url : str
        URL de base du service.
    textes : list[str]
        Liste de textes à cycler.
    concurrence : int
        Nombre de threads simultanés.
    nb_requetes : int
        Nombre total de requêtes à envoyer.
    delai : float
        Timeout en secondes pour chaque requête.

    Returns
    -------
    dict
        Dictionnaire contenant les métriques décrites dans la spécification.
    """
    if not textes:
        raise ValueError("La liste de textes d’essai ne doit pas être vide.")

    logger.info(
        "Lancement de la campagne de mesure : %d requêtes avec %d threads",
        nb_requetes,
        concurrence,
    )
    debut_campagne = time.perf_counter()
    futures = []
    durees: List[float] = []
    succes = 0
    echec = 0

    with ThreadPoolExecutor(max_workers=concurrence) as executor:
        for i in range(nb_requetes):
            txt = textes[i % len(textes)]
            futures.append(
                executor.submit(une_requete, base_url, txt, delai)
            )

        for fut in as_completed(futures):
            ok, duree, _ = fut.result()
            durees.append(duree)
            if ok:
                succes += 1
            else:
                echec += 1

    duree_totale = time.perf_counter() - debut_campagne
    taux_erreur = echec / nb_requetes if nb_requetes else 0.0
    debit = nb_requetes / duree_totale if duree_totale > 0 else 0.0

    # Statistiques de latence (en millisecondes)
    durees_ms = [d * 1000.0 for d in durees]
    durees_ms.sort()
    p50 = _calculer_percentile(durees_ms, 50)
    p90 = _calculer_percentile(durees_ms, 90)
    p99 = _calculer_percentile(durees_ms, 99)
    moyenne = sum(durees_ms) / len(durees_ms) if durees_ms else 0.0
    max_lat = max(durees_ms) if durees_ms else 0.0

    logger.info(
        "Mesure terminée : débit %.2f req/s, taux d'erreur %.4f, p99 %.2f ms",
        debit,
        taux_erreur,
        p99,
    )

    return {
        "requetes": nb_requetes,
        "succes": succes,
        "echecs": echec,
        "taux_erreur": taux_erreur,
        "duree_totale": duree_totale,
        "debit": debit,
        "p50": p50,
        "p90": p90,
        "p99": p99,
        "moyenne": moyenne,
        "max": max_lat,
    }


# --------------------------------------------------------------------------- #
# 4. Rapport Markdown
# --------------------------------------------------------------------------- #

def rapport_markdown(
    mesure: Dict[str, Any],
    base_url: str,
    concurrence: int,
    date_utc: str,
    commit: str,
) -> str:
    """
    Génère le rapport Markdown à partir du dictionnaire de mesures.
    Pourquoi : produire un artefact lisible et versionnable qui sert de preuve
    d’acquisition de la métrique AIA 4 pour les revues et les audits.
    Le tableau présente les métriques principales, suivi d’une phrase de lecture
    précisant les limites de la mesure (machine unique, pas de déploiement distribué).
    """
    lignes: List[str] = []
    lignes.append("# Rapport de charge – ReviewPulse API")
    lignes.append("")
    lignes.append(f"*Date UTC* : {date_utc}")
    lignes.append(f"*Commit* : {commit}")
    lignes.append(f"*URL cible* : `{base_url}`")
    lignes.append(f"*Concurrence* : {concurrence}")
    lignes.append("")
    lignes.append("| Métrique | Valeur |")
    lignes.append("|---|---|")
    lignes.append(f"| Requêtes totales | {mesure['requetes']} |")
    lignes.append(f"| Succès | {mesure['succes']} |")
    lignes.append(f"| Échecs | {mesure['echecs']} |")
    lignes.append(f"| Taux d’erreur | {mesure['taux_erreur']:.4%} |")
    lignes.append(f"| Durée totale (s) | {mesure['duree_totale']:.2f} |")
    lignes.append(f"| Débit (req/s) | {mesure['debit']:.2f} |")
    lignes.append(f"| p50 (ms) | {mesure['p50']:.2f} |")
    lignes.append(f"| p90 (ms) | {mesure['p90']:.2f} |")
    lignes.append(f"| p99 (ms) | {mesure['p99']:.2f} |")
    lignes.append(f"| Moyenne (ms) | {mesure['moyenne']:.2f} |")
    lignes.append(f"| Max (ms) | {mesure['max']:.2f} |")
    lignes.append("")
    lignes.append(
        "Cette mesure a été réalisée sur une seule machine ; elle ne garantit pas "
        "le comportement d’un déploiement réparti sur plusieurs nœuds ou sous des "
        "conditions réseau différentes."
    )
    lignes.append("")
    return "\n".join(lignes)


# --------------------------------------------------------------------------- #
# 5. Fonction principale
# --------------------------------------------------------------------------- #

def _obtenir_commit() -> str:
    """
    Retourne le hash court du commit Git, la variable d’environnement
    ``REVIEWPULSE_COMMIT`` ou la chaîne « inconnu ».
    Pourquoi : fournir un identifiant de version dans le rapport afin de
    garantir la traçabilité des mesures.
    """
    env = os.getenv("REVIEWPULSE_COMMIT")
    if env:
        return env
    try:
        import subprocess
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or "inconnu"
    except Exception:
        return "inconnu"


def main() -> int:
    """
    Point d’entrée de l’outil de mesure de charge.
    Pourquoi : orchestrer les étapes de vérification du service, de campagne
    de mesure, de génération et d’écriture du rapport, puis retourner un code
    d’état conforme aux exigences d’intégration continue.
    """
    parser = argparse.ArgumentParser(
        description="Outil de mesure de charge pour l’API ReviewPulse (indicateur AIA 4)."
    )
    # Pourquoi : URL par défaut pointant vers l’instance locale de développement.
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="URL de base du service (défaut http://localhost:8000).",
    )
    # Pourquoi : 10 threads offrent un bon compromis entre charge et consommation
    # de ressources sur les machines CI standard.
    parser.add_argument(
        "--concurrence",
        type=int,
        default=10,
        help="Nombre de threads simultanés (défaut 10).",
    )
    # Pourquoi : 200 requêtes permettent d’obtenir des percentiles stables sans
    # allonger excessivement la durée du test.
    parser.add_argument(
        "--requetes",
        type=int,
        default=200,
        help="Nombre total de requêtes à envoyer (défaut 200).",
    )
    # Pourquoi : 10 s de timeout couvrent la plupart des latences observées tout en
    # évitant que des requêtes bloquées n’éternisent le test.
    parser.add_argument(
        "--delai",
        type=float,
        default=10.0,
        help="Timeout en secondes pour chaque requête (défaut 10).",
    )
    # Pourquoi : seuil d’erreur maximal fixé à 1 % conformément aux exigences de
    # robustesse du service.
    parser.add_argument(
        "--taux-erreur-max",
        type=float,
        default=0.01,
        help="Seuil maximal de taux d’erreur (défaut 0.01).",
    )
    # Pourquoi : p99 maximal de 2000 ms correspond à la contrainte de latence
    # définie dans le référentiel de performance.
    parser.add_argument(
        "--p99-max-ms",
        type=float,
        default=2000.0,
        help="Seuil maximal de latence p99 en millisecondes (défaut 2000).",
    )
    # Pourquoi : le rapport est stocké dans la zone d’évidence pour être
    # consultable par les revues et les audits.
    parser.add_argument(
        "--rapport",
        type=Path,
        default=Path("docs/evidence/essai_charge.md"),
        help="Chemin du fichier de rapport Markdown (défaut docs/evidence/essai_charge.md).",
    )
    args = parser.parse_args()

    logger.info("Démarrage de l'outil avec URL %s", args.url)

    # Textes d’essai (environ 10, français et anglais)
    textes_exemple = [
        "Excellent produit, je le recommande vivement.",
        "Terrible expérience, le service était lent.",
        "Great game, had a lot of fun!",
        "Not worth the price, very disappointing.",
        "Le design est élégant et moderne.",
        "The battery life is too short for daily use.",
        "Très bon rapport qualité‑prix.",
        "I encountered several bugs during gameplay.",
        "Service client très réactif, merci !",
        "The installation process was painless.",
    ]

    # Vérifier que le service est disponible
    try:
        verifier_service(args.url, args.delai)
    except RuntimeError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1

    # Lancer la campagne de mesure
    mesures = mesurer(
        base_url=args.url,
        textes=textes_exemple,
        concurrence=args.concurrence,
        nb_requetes=args.requetes,
        delai=args.delai,
    )

    # Générer le rapport
    # Horodatage conscient du fuseau : utcnow() est deprecie et rend un objet naif.
    date_utc = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    commit = _obtenir_commit()
    markdown = rapport_markdown(
        mesure=mesures,
        base_url=args.url,
        concurrence=args.concurrence,
        date_utc=date_utc,
        commit=commit,
    )

    # Écriture du rapport
    args.rapport.parent.mkdir(parents=True, exist_ok=True)
    args.rapport.write_text(markdown, encoding="utf-8")
    logger.info("Rapport écrit dans %s", args.rapport)

    # Affichage d’un résumé concis
    print("\n".join([
        f"Requêtes : {mesures['requetes']}",
        f"Taux d’erreur : {mesures['taux_erreur']:.2%}",
        f"p99 (ms) : {mesures['p99']:.2f}",
    ]))

    # Décision de code de sortie
    if (
        mesures["taux_erreur"] > args.taux_erreur_max
        or mesures["p99"] > args.p99_max_ms
    ):
        logger.warning(
            "Seuil dépassé : taux_erreur %.4f (max %.4f) ou p99 %.2f ms (max %.2f ms)",
            mesures["taux_erreur"],
            args.taux_erreur_max,
            mesures["p99"],
            args.p99_max_ms,
        )
        return 1
    logger.info("Mesure conforme aux seuils définis")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
