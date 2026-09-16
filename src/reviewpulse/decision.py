"""reviewpulse.decision
======================

Rôle
----
Définit la convention de décision unique du projet : `LABEL_NEGATIVE = 0`,
`LABEL_POSITIVE = 1` et la règle « probabilité négative ≥ seuil → négatif ».

Place dans la chaîne
--------------------
Appelé par les modules `train`, `score`, `api` et le tableau de bord
(`dashboard/app.py`).

Choix de conception
-------------------
`negative_proba` lit `model.classes_` pour identifier l’indice de la classe
négative au lieu de supposer que la première colonne correspond à cette
classe.  Décision documentée dans l’ADR 0009 (Convention de décision
centralisée).

Preuves
-------
* ADR 0009 (16/09/2026) : aucune comparaison au seuil n’est implémentée
hors de ce module.  
* Tests : `test_decision.py` (incluant un test de bout en bout) et
`test_api.py` valident le comportement.

Tests associés
--------------
`test_decision.py`, `test_api.py`
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
    """Calculer les probabilités de la classe négative (``0``) pour chaque texte.

    Le modèle doit implémenter ``predict_proba`` et posséder l’attribut
    ``classes_``.  L’indice de la classe négative est recherché explicitement
    dans ``model.classes_``.

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

    Raises
    ------
    ValueError
        Si la classe négative (``0``) n’est pas présente dans ``model.classes_``.

    Pourquoi :
        Centralise le calcul de la probabilité négative.
    """
    # ``predict_proba`` accepte n’importe quel itérable de textes.
    proba = model.predict_proba(list(texts))
    # Recherche explicite de l’indice de la classe négative.
    try:
        idx_negative = list(model.classes_).index(LABEL_NEGATIVE)
    except ValueError as exc:
        raise ValueError(
            "Le modèle ne contient pas la classe négative (0)."
        ) from exc
    # Retourne uniquement la colonne correspondant à la classe négative.
    return proba[:, idx_negative]


def model_threshold(model: Any) -> float:
    """Obtenir le seuil de décision associé au modèle.

    Si le modèle possède l’attribut ``decision_threshold_``, il est utilisé ;
    sinon la valeur par défaut définie dans la configuration est renvoyée.

    Parameters
    ----------
    model: Any
        Modèle entraîné.

    Returns
    -------
    float
        Seuil de décision.

    Pourquoi :
        Assure l’utilisation d’un même seuil même si le modèle ne possède pas
        l’attribut ``decision_threshold_``.
    """
    # Fallback vers la configuration si l’attribut n’est pas présent.
    return getattr(model, "decision_threshold_", config.DEFAULT_DECISION_THRESHOLD)


def predict_labels(proba_negative: np.ndarray, threshold: float) -> np.ndarray:
    """Convertir des probabilités négatives en étiquettes selon le seuil.

    Un avis est classé **négatif** si sa probabilité négative est supérieure ou
    égale au seuil, sinon il est **positif**.

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

    Pourquoi :
        Centralise la conversion des probabilités en étiquettes.
    """
    # Normalisation du tableau d’entrée.
    proba_arr = np.asarray(proba_negative, dtype=np.float64)
    # Application du critère de décision.
    labels = np.where(proba_arr >= threshold, LABEL_NEGATIVE, LABEL_POSITIVE)
    # Retour sous forme d’entiers 64 bits, conforme aux constantes.
    return labels.astype(np.int64)


def label_name(label: int) -> str:
    """Obtenir le nom lisible d’une étiquette.

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

    Pourquoi :
        Fournit une traduction unique des étiquettes.
    """
    if label == LABEL_NEGATIVE:
        return "negative"
    if label == LABEL_POSITIVE:
        return "positive"
    raise ValueError(f"Étiquette inconnue : {label}")
