# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""ReviewPulse API
===================

Rôle
----
Servir le modèle champion via les endpoints : ``/health``, ``/predict`` et ``/insights``.

Place dans la chaîne
--------------------
Dernier maillon exposé aux consommateurs. Il est appelé par le tableau de bord
``dashboard/app.py`` et par les contrôles A1 à A4 de ``tools/forward_test.py``.
Il lit le modèle champion dans le registre MLflow via ``score.load_champion`` et
le fichier de résumé quotidien pointé par ``config.SUMMARY_FILE`` ; il n'écrit
aucune donnée métier, seulement des métriques de latence en mémoire.

Fonctionnement
--------------
L'application FastAPI démarre sans exiger le modèle. Le premier appel à
``/health`` ou ``/predict`` déclenche le chargement paresseux du champion,
mis en cache par ``functools.lru_cache`` et protégé par un verrou pour éviter
les chargements concurrents. Si le chargement échoue, l'API renvoie ``503`` et
réessaie au prochain appel. Les requêtes ``/predict`` et ``/explain`` passent
par la dépendance ``get_model`` qui centralise cette logique. L'endpoint
``/insights`` lit le résumé parquet, filtre sur l'``app_id`` demandé et
retourne les ``days`` dernières journées comptées depuis la dernière date
disponible. Un middleware mesure la latence de chaque requête et expose les
centiles via ``/metrics``.

Pourquoi
--------
L'API doit rester démarrable même lorsqu'aucun modèle n'est promu champion,
car le pipeline d'entraînement est hebdomadaire et le service peut être
déployé avant la première promotion (constaté le 16/09/2026). La validation
des entrées côté API évite d'appeler le modèle avec des charges inadaptées et
de journaliser des textes d'avis complets.

Choix de conception
-------------------
* Chargement paresseux du modèle champion, mis en cache ; le cache ne conserve que les chargements réussis : si le modèle n’est pas disponible, l’API renvoie ``503`` et réessaie au prochain appel (constaté le 16/09/2026) [ADR 0008].
  - Alternative écartée : charger le modèle au démarrage de l'application. Raison : l'API serait impossible à démarrer sans champion, ce qui bloquerait les déploiements initiaux et les redémarrages en l'absence de modèle.
* Validation des requêtes avec Pydantic : 1 ≤ nombre de textes ≤ 100, chaque texte 1 ≤ longueur ≤ 5 000 caractères.
  - Alternative écartée : laisser le modèle ou le scorer rejeter les entrées. Raison : obtenir une réponse ``422`` structurée avant tout appel coûteux et éviter de propager des erreurs opaques.
* Aucun texte d’avis n’est journalisé ; seules les exceptions sont loggées.
  - Alternative écartée : logger les préfixes ou les identifiants des textes. Raison : les textes d'avis sont des données métier sensibles ; seules les métadonnées de requête et les erreurs techniques sont conservées.
* Le seuil de décision est renvoyé avec chaque prédiction et dans ``/health`` (seuil 0,5 documenté).
  - Alternative écartée : hardcoder le seuil dans la réponse. Raison : le seuil voyage avec le modèle (``decision.model_threshold``) et peut varier d'une version à l'autre ; le client doit connaître le seuil appliqué.
* L’endpoint ``/insights`` renvoie les indicateurs agrégés des ``days`` dernières journées comptées depuis la dernière date disponible pour l’application demandée.
  - Alternative écartée : une fenêtre calendaire fixe (par exemple les 7 derniers jours depuis aujourd'hui). Raison : la démo doit être rejouable avec des données historiques ; la dernière date disponible dans le résumé sert d'ancrage.

Limites connues
---------------
* ``/metrics`` mélange les requêtes à froid et à chaud ; le premier passage
  emporte le chargement du modèle et peut produire un centile très élevé qui
  ne reflète pas la latence à chaud.
* Le compteur ``_TOTAL_REQUESTS`` est global au processus uvicorn ; en mode
  multi-processus il ne compte que les requêtes du worker courant.
* ``/insights`` ne vérifie pas que le modèle est chargé : il répond dès que
  le fichier de résumé existe, même si le champion est indisponible.
* Les métriques de latence sont stockées en mémoire ; elles disparaissent au
  redémarrage du service.

Tests associés
--------------
* ``test_api.py`` couvre les trois endpoints et les cas d’erreur (modèle indisponible, fichier de résumé manquant) ; ``test_artifacts_location.py`` vérifie le comportement ``503`` lorsque le champion est absent.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import threading
import time
import uuid
from collections import deque
from functools import lru_cache
from pathlib import Path
from typing import Annotated, List, Tuple

import pandas as pd
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from reviewpulse import config
from reviewpulse import decision
from reviewpulse import explain

# Initialise le logger dédié à ce module (pas de prints ailleurs)
logger = logging.getLogger(__name__)

# Instance FastAPI unique pour l’ensemble du service
app = FastAPI(title="ReviewPulse API")

# --- Mesure de latence (ADR 0029) ---
# La consigne du Demo Day exige de suivre « latency, accuracy, and drift » et
# évalue une surveillance proactive. Le projet mesurait déjà la dérive en continu
# et la latence une seule fois ; ce bloc ajoute un suivi continu de la latence.
# Attention : /metrics mélange les requêtes à froid et à chaud. Le premier passage
# sur un service fraîchement démarré porte le chargement du modèle — on a
# constaté un p99 à 5 874 ms au premier essai contre 925 ms à chaud. Un centile
# lu sans cette précision est trompeur.

# Taille maximale du registre par endpoint. 2048 échantillons suffisent pour
# estimer les centiles sur un service à trafic modéré tout en bornant la mémoire
# utilisée : un service de longue durée ne doit pas voir sa mémoire croître
# indéfiniment avec le nombre de requêtes.
MAX_LATENCY_SAMPLES: int = 2048

# Registre en mémoire des durées, une structure par point d'accès observé.
LATENCY_REGISTRY: dict[str, deque[float]] = {
    "/health": deque(maxlen=MAX_LATENCY_SAMPLES),
    "/predict": deque(maxlen=MAX_LATENCY_SAMPLES),
    "/explain": deque(maxlen=MAX_LATENCY_SAMPLES),
    "/insights": deque(maxlen=MAX_LATENCY_SAMPLES),
}

# Heure de démarrage du service, utilisée pour calculer la durée de fonctionnement.
_STARTUP_TIME: float = time.perf_counter()

# Compteur REEL des requetes depuis le demarrage. Il ne peut pas etre deduit de
# LATENCY_REGISTRY : ces files sont bornees a MAX_LATENCY_SAMPLES, donc leur somme
# plafonne et sous-compte des la 2049e requete. Annoncer « total depuis le
# demarrage » a partir d'une file bornee serait un chiffre faux.
_TOTAL_REQUESTS: int = 0


def _percentile(valeurs: List[float], centile: float) -> float:
    """Calcule un centile sur une liste de valeurs déjà triée.

    Convention retenue : **interpolation linéaire** entre les deux valeurs qui
    encadrent la position réelle — c'est la définition dite « type 7 », celle de
    NumPy et de R par défaut. Ce n'est PAS un rang le plus proche : sur cinq
    échantillons, le p99 vaut donc une valeur interpolée, non le maximum.
    Pour une liste vide, renvoie 0.0 plutôt que de lever : un point d'accès
    d'observation ne doit jamais échouer faute de données.

    Parameters
    ----------
    valeurs : List[float]
        Liste triée de valeurs numériques.
    centile : float
        Centile demandé, entre 0 et 100.

    Returns
    -------
    float
        Le centile calculé, en millisecondes.

    Pourquoi :
        L'interpolation linéaire est cohérente avec les outils scientifiques
        habituels et évite de surestimer systématiquement les queues de
        distribution.
    """
    if not valeurs:
        return 0.0
    n = len(valeurs)
    if n == 1:
        return valeurs[0]
    # Position dans l'index 0-based ; centile exprimé en pourcentage.
    k = (centile / 100.0) * (n - 1)
    f = int(k)
    c = f + 1
    if c >= n:
        return valeurs[-1]
    d = k - f
    return valeurs[f] * (1.0 - d) + valeurs[c] * d


@app.middleware("http")
async def latency_middleware(request, call_next):
    """Mesure la durée de chaque requête HTTP et l'enregistre par endpoint.

    Parameters
    ----------
    request : Request
        Requête HTTP entrante.
    call_next : Callable
        Fonction appelée pour passer la requête au endpoint suivant.

    Returns
    -------
    Response
        Réponse HTTP produite par l'application.

    Pourquoi :
        Le suivi continu de la latence est requis par la consigne Demo Day
        (latency, accuracy, drift) et permet de détecter les dégradations sans
        instrumentation externe.
    """
    start = time.perf_counter()
    response = await call_next(request)
    duration_s = time.perf_counter() - start
    duration_ms = round(duration_s * 1000.0, 3)

    global _TOTAL_REQUESTS
    _TOTAL_REQUESTS += 1

    path = request.url.path
    if path in LATENCY_REGISTRY:
        LATENCY_REGISTRY[path].append(duration_ms)

    log_entry = {
        "request_id": str(uuid.uuid4())[:8],
        "path": path,
        "method": request.method,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
    }
    # Pourquoi : une seule ligne de journal par requête, sans texte d'avis,
    # pour conserver une trace technique sans exposer les données métier.
    logger.info(json.dumps(log_entry, ensure_ascii=False))

    return response


@app.get("/metrics")
def metrics():
    """Rend les métriques de latence observées sur les quatre endpoints.

    Ce point d'accès est indépendant du modèle : il répond même si le champion
    n'est pas chargé, contrairement à /health.

    Returns
    -------
    dict
        Dictionnaire contenant les centiles par endpoint, le nombre total de
        requêtes, le nombre d'échantillons retenus et le temps de fonctionnement.

    Pourquoi :
        Fournir un endpoint dédié aux opérateurs pour surveiller la santé du
        service sans dépendre de la disponibilité du modèle.
    """
    endpoints: dict[str, dict[str, float]] = {}
    echantillons_retenus: int = 0

    for path, samples in LATENCY_REGISTRY.items():
        n = len(samples)
        echantillons_retenus += n
        if n == 0:
            endpoints[path] = {
                "count": 0.0,
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "mean_ms": 0.0,
                "max_ms": 0.0,
            }
            continue

        sorted_samples = sorted(samples)
        total = sum(sorted_samples)
        endpoints[path] = {
            "count": float(n),
            "p50_ms": round(_percentile(sorted_samples, 50.0), 3),
            "p95_ms": round(_percentile(sorted_samples, 95.0), 3),
            "p99_ms": round(_percentile(sorted_samples, 99.0), 3),
            "mean_ms": round(total / n, 3),
            "max_ms": round(sorted_samples[-1], 3),
        }

    uptime_s = round(time.perf_counter() - _STARTUP_TIME, 3)

    return {
        "endpoints": endpoints,
        "total_requests": _TOTAL_REQUESTS,
        "samples_retained": echantillons_retenus,
        "uptime_seconds": uptime_s,
    }


# Verrou du premier chargement. `lru_cache` memorise un resultat, mais il ne dedoublonne
# PAS les appels concurrents : N requetes simultanees executent N chargements avant que
# le cache ne soit rempli. Mesure du 20/09/2026 : le controle de sante de l'image
# interrogeait /health toutes les 30 s avec un delai de 5 s, chaque appel declenchait un
# chargement du champion depuis MLflow, et ils s'empilaient sur un unique processus
# uvicorn -- /metrics a mesure un appel a 184 542 ms. Le verrou fait attendre les
# suivants au lieu de les faire recharger : un seul chargement, les autres recuperent
# le cache. Sujet R55.
_VERROU_CHARGEMENT = threading.Lock()


@lru_cache(maxsize=1)
def _load_model() -> Tuple[object, str]:
    """Charge le modèle champion et sa version une seule fois (mise en cache).

    Returns
    -------
    Tuple[object, str]
        Le modèle chargé et sa version (identifiant de version MLflow).

    Raises
    ------
    Exception
        Toute exception levée par ``score.load_champion`` est propagée au
        gestionnaire de dépendance.

    Pourquoi :
        Le chargement du modèle implique un accès disque/MLflow coûteux ; le cache
        évite de le répéter à chaque requête tout en restant rafraîchissable en cas
        d’échec.
    """
    # Import local pour éviter un import lourd au niveau du module
    from reviewpulse import score  # pylint: disable=import-outside-toplevel

    logger.info("Chargement du modele champion depuis MLflow")
    return score.load_champion(tracking_uri=config.MLFLOW_TRACKING_URI)


def get_model() -> Tuple[object, str]:
    """Dépendance FastAPI qui renvoie le modèle et sa version, en gérant les erreurs de chargement.

    Returns
    -------
    Tuple[object, str]
        Le modèle et sa version.

    Raises
    ------
    HTTPException
        503 si le modèle ne peut pas être chargé.

    Pourquoi :
        Centralise la logique de récupération du modèle et permet le remplacement
        dans les tests via ``app.dependency_overrides``.
    """
    try:
        # Le verrou ne protege que le PREMIER chargement : une fois le cache rempli,
        # `_load_model` rend immediatement et le verrou n'est tenu que le temps d'un
        # appel de fonction.
        with _VERROU_CHARGEMENT:
            return _load_model()
    except Exception as exc:
        logger.exception("Erreur lors du chargement du modele")
        raise HTTPException(status_code=503, detail="Modèle indisponible") from exc


class PredictRequest(BaseModel):
    """Requête de prédiction contenant une liste de textes à analyser.

    Attributes
    ----------
    texts : List[str]
        Liste de 1 à 100 chaînes, chacune de 1 à 5 000 caractères.

    Pourquoi :
        Utilise la validation Pydantic pour garantir les contraintes de taille
        avant d’appeler le modèle.
    """
    texts: Annotated[
        List[Annotated[str, Field(min_length=1, max_length=5000)]],
        Field(min_length=1, max_length=100),
    ]

    @field_validator("texts", mode="after")
    @classmethod
    def no_empty_texts(cls, v: List[str]) -> List[str]:
        """Vérifie qu’aucun texte n’est vide.

        Parameters
        ----------
        v : List[str]
            Liste de textes déjà validée par Pydantic.

        Returns
        -------
        List[str]
            La liste inchangée si aucun texte n'est vide.

        Raises
        ------
        ValueError
            Si un texte est une chaîne vide.

        Pourquoi :
            La validation Pydantic ne garantit pas que chaque chaîne contienne
            au moins un caractère après le ``min_length`` global.
        """
        for txt in v:
            if not txt:
                raise ValueError("Chaque texte doit contenir au moins un caractère")
        return v


class PredictionItem(BaseModel):
    """Objet représentant la prédiction d’un texte individuel.

    Attributes
    ----------
    text_preview : str
        Les 80 premiers caractères du texte (pour éviter de logger le texte complet).
    proba_negative : float
        Probabilité que le texte soit négatif.
    label : str
        ``"negative"`` ou ``"positive"`` selon le seuil.

    Pourquoi :
        Sépare la logique de présentation (preview) de la donnée brute et évite
        d'exposer le texte complet dans la réponse.
    """
    text_preview: str
    proba_negative: float
    label: str

    model_config = ConfigDict(protected_namespaces=())


class PredictResponse(BaseModel):
    """Réponse de l’endpoint ``/predict``.

    Attributes
    ----------
    model_version : str
        Version du modèle utilisé.
    decision_threshold : float
        Seuil de décision appliqué.
    predictions : List[PredictionItem]
        Liste des prédictions pour chaque texte fourni.

    Pourquoi :
        Fournit toutes les métadonnées nécessaires au client pour interpréter les
        résultats.
    """
    model_version: str
    decision_threshold: float
    predictions: List[PredictionItem]

    model_config = ConfigDict(protected_namespaces=())


class ExplainRequest(BaseModel):
    """Requête d’explication d’un texte unique.

    Attributes
    ----------
    text : str
        Texte à expliquer, 1 ≤ longueur ≤ 5 000 caractères.
    n : int, optional
        Nombre maximal de contributions locales à retourner (1..50, défaut = 10).

    Pourquoi :
        Restreindre l'explication à un seul texte et un nombre borné de termes
        pour maîtriser le temps de réponse et la charge du serveur.
    """
    text: Annotated[
        str,
        Field(min_length=1, max_length=5000, description="Texte à expliquer"),
    ]
    n: Annotated[
        int,
        Field(ge=1, le=50, default=10, description="Nombre de contributions locales"),
    ] = 10


class TermContribution(BaseModel):
    """Terme et sa contribution locale.

    Attributes
    ----------
    terme : str
        Mot ou n-gramme concerné.
    contribution : float
        Contribution pondérée au score de la classe négative.

    Pourquoi :
        Structurer la réponse d'explication locale pour le tableau de bord.
    """
    terme: str
    contribution: float

    model_config = ConfigDict(protected_namespaces=())


class TermCoeff(BaseModel):
    """Terme et son coefficient global.

    Attributes
    ----------
    terme : str
        Mot ou n-gramme concerné.
    coefficient : float
        Coefficient appris par le modèle pour la classe négative.

    Pourquoi :
        Structurer la réponse d'explication globale pour la Model Card et le
        tableau de bord.
    """
    terme: str
    coefficient: float

    model_config = ConfigDict(protected_namespaces=())


class ExplainResponse(BaseModel):
    """Réponse de l’endpoint ``/explain``.

    Attributes
    ----------
    model_version : str
        Version du modèle utilisé.
    terms : List[TermContribution]
        Contributions locales triées par valeur absolue décroissante.
    global_negative : List[TermCoeff]
        Dix termes les plus influents pour la classe négative.
    global_positive : List[TermCoeff]
        Dix termes les plus influents pour la classe positive.

    Pourquoi :
        Fournir à la fois l'explication locale et les termes globaux dans un seul
        objet de réponse.
    """
    model_version: str
    terms: List[TermContribution]
    global_negative: List[TermCoeff]
    global_positive: List[TermCoeff]

    model_config = ConfigDict(protected_namespaces=())


class HealthResponse(BaseModel):
    """Réponse de l’endpoint ``/health``.

    Attributes
    ----------
    status : str
        ``"ok"`` si le service fonctionne.
    model_version : str
        Version du modèle chargé.
    decision_threshold : float
        Seuil de décision actuellement utilisé.

    Pourquoi :
        Permet aux opérateurs de vérifier rapidement la disponibilité du service
        et la version du modèle.
    """
    status: str
    model_version: str
    decision_threshold: float

    model_config = ConfigDict(protected_namespaces=())


class InsightItem(BaseModel):
    """Objet représentant un indicateur agrégé d’avis pour une application donnée.

    Attributes
    ----------
    app_id : int
        Identifiant Steam de l’application.
    language : str
        Langue des avis (``english`` ou ``french``).
    date : str
        Date ISO (YYYY-MM-DD) du jour agrégé.
    n_reviews : int
        Nombre d’avis considérés ce jour-là.
    share_negative_pred : float
        Part des avis prédits négatifs.
    share_negative_true : float
        Part des avis réellement négatifs.
    model_version : str
        Version du modèle ayant généré les prédictions.

    Pourquoi :
        Structure les données renvoyées par ``/insights`` pour une consommation
        directe par le tableau de bord.
    """
    app_id: int
    language: str
    date: str
    n_reviews: int
    share_negative_pred: float
    share_negative_true: float
    model_version: str

    model_config = ConfigDict(protected_namespaces=())


@app.get("/health", response_model=HealthResponse)
def health(model_info: Tuple[object, str] = Depends(get_model)) -> HealthResponse:
    """Renvoie l'état de l'API, la version du modèle et le seuil de décision appliqué.

    Parameters
    ----------
    model_info : Tuple[object, str]
        Tuple contenant le modèle et sa version, fourni par la dépendance ``get_model``.

    Returns
    -------
    HealthResponse
        Objet contenant le statut, la version du modèle et le seuil.

    Pourquoi :
        Fournit un point de contrôle simple pour les orchestrateurs et les
        opérateurs.
    """
    model, version = model_info
    threshold = decision.model_threshold(model)
    return HealthResponse(
        status="ok",
        model_version=str(version),
        decision_threshold=threshold,
    )


@app.post("/predict", response_model=PredictResponse)
def predict(
    payload: PredictRequest,
    model_info: Tuple[object, str] = Depends(get_model),
) -> PredictResponse:
    """Prédit la polarité d'une liste de textes en utilisant la convention de décision unique.

    Parameters
    ----------
    payload : PredictRequest
        Requête contenant les textes à analyser.
    model_info : Tuple[object, str]
        Modèle et version fournis par la dépendance ``get_model``.

    Returns
    -------
    PredictResponse
        Résultat contenant la version du modèle, le seuil et les prédictions.

    Raises
    ------
    HTTPException
        500 si le calcul des probabilités échoue.

    Pourquoi :
        Centralise la logique de prédiction et garantit que le même seuil que
        ``/health`` est utilisé.
    """
    model, version = model_info
    texts = payload.texts

    # Calcul de la probabilité négative via le module décision (source unique).
    try:
        proba_negative = decision.negative_proba(model, texts)
    except Exception as exc:
        logger.exception("Erreur lors du calcul des probabilités négatives")
        raise HTTPException(status_code=500, detail="Model prediction failed") from exc

    threshold = decision.model_threshold(model)
    labels = decision.predict_labels(proba_negative, threshold)

    predictions = []
    for txt, prob, lbl in zip(texts, proba_negative, labels):
        predictions.append(
            PredictionItem(
                text_preview=txt[:80],
                proba_negative=float(prob),
                label=decision.label_name(int(lbl)),
            )
        )

    return PredictResponse(
        model_version=str(version),
        decision_threshold=threshold,
        predictions=predictions,
    )


@app.post("/explain", response_model=ExplainResponse)
def explain_endpoint(
    payload: ExplainRequest,
    model_info: Tuple[object, str] = Depends(get_model),
) -> ExplainResponse:
    """Explique la décision pour le texte fourni.

    Parameters
    ----------
    payload : ExplainRequest
        Texte à expliquer et nombre de contributions demandées.
    model_info : Tuple[object, str]
        Modèle et version fournis par la dépendance ``get_model``.

    Returns
    -------
    ExplainResponse
        Contributions locales et termes globaux pour les deux classes.

    Pourquoi :
        Offrir une explication compréhensible par le community manager sans
        dépendre d'une bibliothèque d'explicabilité externe (ADR 0019).

    Notes
    -----
    Une contribution positive pousse vers l'étiquette négative,
    tandis qu'une contribution négative pousse vers l'étiquette positive.
    """
    model, version = model_info
    n_local = payload.n

    # Contributions locales
    local = explain.local_contributions(model, payload.text, n=n_local)
    terms = [TermContribution(terme=t, contribution=c) for t, c in local]

    # Termes globaux (toujours 10 par classe)
    global_dict = explain.global_terms(model, n=10)
    global_negative = [
        TermCoeff(terme=t, coefficient=c) for t, c in global_dict["negative"]
    ]
    global_positive = [
        TermCoeff(terme=t, coefficient=c) for t, c in global_dict["positive"]
    ]

    return ExplainResponse(
        model_version=str(version),
        terms=terms,
        global_negative=global_negative,
        global_positive=global_positive,
    )


@app.get("/insights", response_model=list[InsightItem])
def insights(
    app_id: int = Query(..., description="Identifiant Steam de l'application"),
    days: int = Query(
        7,
        ge=1,
        le=90,
        description="Nombre de jours à remonter (1..90)",
    ),
) -> List[InsightItem]:
    """Renvoie les indicateurs agrégés sur les dernières *days* journées comptées depuis la
    dernière date disponible pour cet *app_id*.

    Parameters
    ----------
    app_id : int
        Identifiant Steam de l'application.
    days : int, optional
        Nombre de jours à considérer (défaut 7, entre 1 et 90).

    Returns
    -------
    List[InsightItem]
        Liste d’indicateurs agrégés, éventuellement vide.

    Raises
    ------
    HTTPException
        404 si le fichier de résumé est absent,
        500 si la lecture du fichier échoue.

    Pourquoi :
        Fournit aux utilisateurs finaux les métriques nécessaires au suivi quotidien
        sans exposer les données brutes.
    """
    summary_path: Path = config.SUMMARY_FILE
    if not summary_path.is_file():
        raise HTTPException(status_code=404, detail="Summary file not found")

    try:
        df = pd.read_parquet(summary_path)
    except Exception as exc:
        logger.exception("Impossible de lire le fichier de résumé")
        raise HTTPException(status_code=500, detail="Failed to read summary file") from exc

    df = df[df["app_id"] == app_id]

    if df.empty:
        return []

    if pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = df["date"].dt.date
    else:
        df["date"] = pd.to_datetime(df["date"]).dt.date

    max_date: datetime.date = df["date"].max()
    cutoff = max_date - datetime.timedelta(days=days - 1)

    df = df[df["date"] >= cutoff]

    insights_list: List[InsightItem] = []
    for _, row in df.iterrows():
        insights_list.append(
            InsightItem(
                app_id=int(row["app_id"]),
                language=str(row["language"]),
                date=row["date"].isoformat(),
                n_reviews=int(row["n_reviews"]),
                share_negative_pred=float(row["share_negative_pred"]),
                share_negative_true=float(row["share_negative_true"]),
                model_version=str(row["model_version"]),
            )
        )

    return insights_list


def main() -> int:
    """Point d'entrée minimal pour lancer le serveur API.

    Returns
    -------
    int
        Code de sortie (0 en cas de succès).

    Pourquoi :
        Permet d’exécuter le service via ``python -m reviewpulse.api`` ou dans les
        scripts CI.
    """
    host = os.getenv("REVIEWPULSE_API_HOST", "0.0.0.0")
    port = int(os.getenv("REVIEWPULSE_API_PORT", "8000"))
    uvicorn.run("reviewpulse.api:app", host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
