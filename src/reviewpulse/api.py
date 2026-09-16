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

logger = logging.getLogger(__name__)

app = FastAPI(title="ReviewPulse API")


@lru_cache(maxsize=1)
def _load_model() -> Tuple[object, str]:
    """Charge le modèle champion et sa version une seule fois (mise en cache)."""
    # La fonction load_champion est la source unique de vérité pour le modèle.
    from reviewpulse import score  # import local pour éviter un import inutile au niveau module

    return score.load_champion(tracking_uri=config.MLFLOW_TRACKING_URI)


def get_model() -> Tuple[object, str]:
    """Dépendance FastAPI qui renvoie le modèle et sa version, en gérant les erreurs de chargement."""
    try:
        return _load_model()
    except Exception as exc:  # NON VERIFIE
        logger.exception("Erreur lors du chargement du modèle")
        raise HTTPException(status_code=503, detail="Modèle indisponible") from exc


class PredictRequest(BaseModel):
    texts: Annotated[
        List[Annotated[str, Field(min_length=1, max_length=5000)]],
        Field(min_length=1, max_length=100),
    ]

    @field_validator("texts", mode="after")
    @classmethod
    def no_empty_texts(cls, v: List[str]) -> List[str]:
        for txt in v:
            if not txt:
                raise ValueError("Chaque texte doit contenir au moins un caractère")
        return v


class PredictionItem(BaseModel):
    text_preview: str
    proba_negative: float
    label: str

    model_config = ConfigDict(protected_namespaces=())


class PredictResponse(BaseModel):
    model_version: str
    decision_threshold: float
    predictions: List[PredictionItem]

    model_config = ConfigDict(protected_namespaces=())


class HealthResponse(BaseModel):
    status: str
    model_version: str
    decision_threshold: float

    model_config = ConfigDict(protected_namespaces=())


class InsightItem(BaseModel):
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
    """Renvoie l'état de l'API, la version du modèle et le seuil de décision appliqué."""
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
    """Prédit la polarité d'une liste de textes en utilisant la convention de décision unique."""
    model, version = model_info
    texts = payload.texts

    # Calcul de la probabilité négative via le module décision (source unique).
    try:
        proba_negative = decision.negative_proba(model, texts)
    except Exception as exc:  # NON VERIFIE
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
    dernière date disponible pour cet *app_id*."""
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
    """Point d'entrée minimal pour lancer le serveur API."""
    host = os.getenv("REVIEWPULSE_API_HOST", "0.0.0.0")
    port = int(os.getenv("REVIEWPULSE_API_PORT", "8000"))
    uvicorn.run("reviewpulse.api:app", host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
