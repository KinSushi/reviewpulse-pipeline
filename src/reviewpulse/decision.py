"""reviewpulse.decision
======================

Ce module centralise la *convention de décision* utilisée par le projet.
Le 16/09/2026, deux inversions successives du seuil de décision ont été
observées : d’abord dans ``train.py`` puis dans ``score.py``,
ce qui entraînait plus de 95 % d’avis prédits négatifs alors que seuls 4 %
étaient réellement négatifs.  
Pour éviter toute nouvelle incohérence, la logique de calcul du
probabilité négative, du seuil et de la conversion en étiquette est
maintenue ici, unique source de vérité.  

La convention d’étiquetage est :
- ``LABEL_NEGATIVE = 0``  (avis négatif, ``voted_up`` = ``False``)
- ``LABEL_POSITIVE = 1``  (avis positif, ``voted_up`` = ``True``)

Les fonctions suivantes utilisent ces constantes et le paramètre
``config.DEFAULT_DECISION_THRESHOLD`` afin d’assurer une cohérence
entre les modules *train*, *score* et l’API.
"""

from __future__ import annotations

import numpy as np
from typing import Any, Sequence

from reviewpulse import config

# --------------------------------------------------------------------------- #
# Constantes d'étiquetage
# --------------------------------------------------------------------------- #
LABEL_NEGATIVE: int = 0
"""Valeur d’étiquette correspondant à un avis négatif."""

LABEL_POSITIVE: int = 1
"""Valeur d’étiquette correspondant à un avis positif."""

__all__ = [
    "LABEL_NEGATIVE",
    "LABEL_POSITIVE",
    "negative_proba",
    "model_threshold",
    "predict_labels",
    "label_name",
]

# --------------------------------------------------------------------------- #
# Fonctions utilitaires
# --------------------------------------------------------------------------- #
def negative_proba(model: Any, texts: Sequence[str]) -> np.ndarray:
    """Renvoie les probabilités de la classe négative (``0``) pour chaque texte.

    Le modèle doit implémenter ``predict_proba`` et posséder l’attribut
    ``classes_``.  On ne suppose pas que la colonne 0 du tableau retourné
    corresponde à la classe ``0`` ; on recherche explicitement l’indice
    de cette classe dans ``model.classes_``.

    Parameters
    ----------
    model: Any
        Modèle entraîné compatible scikit‑learn.
    texts: Sequence[str]
        Textes à évaluer.

    Returns
    -------
    np.ndarray
        Tableau unidimensionnel de probabilités (float64) de la classe
        négative, dans le même ordre que ``texts``.
    """
    # ``predict_proba`` accepte n’importe quel itérable de textes.
    proba = model.predict_proba(list(texts))
    try:
        idx_negative = list(model.classes_).index(LABEL_NEGATIVE)
    except ValueError as exc:
        raise ValueError(
            "Le modèle ne contient pas la classe négative (0)."
        ) from exc
    return proba[:, idx_negative]


def model_threshold(model: Any) -> float:
    """Retourne le seuil de décision associé au modèle.

    Si le modèle possède l’attribut ``decision_threshold_`` (défini lors
    de l’entraînement), on l’utilise ; sinon on se rabat sur la valeur
    par défaut définie dans la configuration.

    Parameters
    ----------
    model: Any
        Modèle entraîné.

    Returns
    -------
    float
        Seuil de décision.
    """
    return getattr(model, "decision_threshold_", config.DEFAULT_DECISION_THRESHOLD)


def predict_labels(proba_negative: np.ndarray, threshold: float) -> np.ndarray:
    """Convertit des probabilités négatives en étiquettes selon le seuil.

    Un avis est classé **négatif** si sa probabilité négative est supérieure
    ou égale au seuil, sinon il est **positif**.

    Parameters
    ----------
    proba_negative: np.ndarray
        Probabilités de la classe négative (float64).
    threshold: float
        Seuil de décision.

    Returns
    -------
    np.ndarray
        Tableau d’étiquettes (int64) contenant ``LABEL_NEGATIVE`` ou
        ``LABEL_POSITIVE``.
    """
    proba_arr = np.asarray(proba_negative, dtype=np.float64)
    labels = np.where(proba_arr >= threshold, LABEL_NEGATIVE, LABEL_POSITIVE)
    return labels.astype(np.int64)


def label_name(label: int) -> str:
    """Retourne le nom lisible de l’étiquette.

    Parameters
    ----------
    label: int
        Valeur d’étiquette (``0`` ou ``1``).

    Returns
    -------
    str
        ``"negative"`` ou ``"positive"``.

    Raises
    ------
    ValueError
        Si ``label`` n’est ni ``LABEL_NEGATIVE`` ni ``LABEL_POSITIVE``.
    """
    if label == LABEL_NEGATIVE:
        return "negative"
    if label == LABEL_POSITIVE:
        return "positive"
    raise ValueError(f"Étiquette inconnue : {label}")
