"""ReviewPulse API
===================

Rôle
----
Servir le modèle champion via les endpoints : ``/health``, ``/predict`` et ``/insights``.

Choix de conception
--------------------
* Chargement paresseux du modèle champion, mis en cache ; le cache ne conserve que les chargements réussis : si le modèle n’est pas disponible, l’API renvoie ``503`` et réessaie au prochain appel (constaté le 16/09/2026) [ADR 0008].
* Validation des requêtes avec Pydantic : 1 ≤ nombre de textes ≤ 100, chaque texte 1 ≤ longueur ≤ 5 000 caractères.
* Aucun texte d’avis n’est journalisé ; seules les exceptions sont loggées.
* Le seuil de décision est renvoyé avec chaque prédiction et dans ``/health`` (seuil 0,5 documenté).
* L’endpoint ``/insights`` renvoie les indicateurs agrégés des ``days`` dernières journées comptées depuis la dernière date disponible pour l’application demandée.

Tests associés
--------------
* ``test_api.py`` couvre les trois endpoints et les cas d’erreur (modèle indisponible, fichier de résumé manquant) ; ``test_artifacts_location.py`` vérifie le comportement ``503`` lorsque le champion est absent.
"""

from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path
from typing import Annotated, List, Tuple

import pandas as pd
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from functools import lru_cache

from reviewpulse import config
from reviewpulse import decision
from reviewpulse import explain

# Initialise le logger dédié à ce module (pas de prints ailleurs)
logger = logging.getLogger(__name__)

# Instance FastAPI unique pour l’ensemble du service
app = FastAPI(title="ReviewPulse API")


@lru_cache(maxsize=1)
def _load_model() -> Tuple[object, str]:
    """Charge le modèle champion et sa version une seule fois (mise en cache).

    Retourne
    -------
    Tuple[object, str]
        Le modèle chargé et sa version (identifiant de version MLflow).

    Pourquoi :
        Le chargement du modèle implique un accès disque/MLflow coûteux ; le cache
        évite de le répéter à chaque requête tout en restant rafraîchissable en cas
        d’échec.
    """
    # Import local pour éviter un import lourd au niveau du module
    from reviewpulse import score  # pylint: disable=import-outside-toplevel

    return score.load_champion(tracking_uri=config.MLFLOW_TRACKING_URI)


def get_model() -> Tuple[object, str]:
    """Dépendance FastAPI qui renvoie le modèle et sa version, en gérant les erreurs de chargement.

    Retourne
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
        return _load_model()
    except Exception as exc:
        logger.exception("Erreur lors du chargement du modèle")
        raise HTTPException(status_code=503, detail="Modèle indisponible") from exc


class PredictRequest(BaseModel):
    """Requête de prédiction contenant une liste de textes à analyser.

    Attributes
    ----------
    texts : List[str]
        Liste de 1 à 100 chaînes, chacune de 1 à 5 000 caractères.

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
        Sépare la logique de présentation (preview) de la donnée brute.
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
        Texte à expliquer, 1 ≤ longueur ≤ 5 000 caractères.
    n : int, optional
        Nombre maximal de contributions locales à retourner (1..50, défaut = 10).
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
    """Terme et sa contribution locale."""
    terme: str
    contribution: float

    model_config = ConfigDict(protected_namespaces=())


class TermCoeff(BaseModel):
    """Terme et son coefficient global."""
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
        Date ISO (YYYY‑MM‑DD) du jour agrégé.
    n_reviews : int
        Nombre d’avis considérés ce jour‑là.
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
