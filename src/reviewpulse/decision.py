"""reviewpulse.decision
======================

Rôle
----
Définit la convention de décision unique du projet : `LABEL_NEGATIVE = 0`,
`LABEL_POSITIVE = 1` et la règle « probabilité négative ≥ seuil → négatif ».

Place dans la chaîne
--------------------
Appelé par les modules `train`, `score`, `api` et le tableau de bord
(`dashboard/app.py`).

Quoi
----
Centralise la conversion des probabilités du modèle en étiquettes binaires
(0 = négatif, 1 = positif) et fournit l’accès au seuil de décision.

Pourquoi
--------
La convention a été inversée deux fois le 16/09/2026 (F1 = 0 à l’entraînement ;
95 % de négatifs prédits pour 4 % réels au score). Ce module évite que la
règle de décision soit réimplémentée ou interprétée différemment dans chaque
consommateur. ADR 0009.

Où
--
Appelé par `train`, `score`, `api` et `dashboard/app.py`. Lit `model.classes_`
et, le cas échéant, `model.decision_threshold_` ; écrit uniquement en mémoire
via les valeurs de retour.

Comment
-------
`negative_proba` appelle `predict_proba` sur le modèle et extrait la colonne
de la classe négative en cherchant son indice dans `model.classes_`.
`model_threshold` renvoie l’attribut du modèle s’il existe, sinon le seuil par
défaut de la configuration. `predict_labels` applique le critère
`proba_negative >= threshold` et retourne `LABEL_NEGATIVE` ou
`LABEL_POSITIVE`. `label_name` traduit les deux étiquettes en chaînes et refuse
toute valeur inconnue.

Choix de conception
-------------------
`negative_proba` lit `model.classes_` pour identifier l’indice de la classe
négative au lieu de supposer que la première colonne correspond à cette
classe.  Décision documentée dans l’ADR 0009 (Convention de décision
centralisée).

Preuves
-------
* ADR 0009 (16/09/2026) : aucune comparaison au seuil n’est implémentée
hors de ce module.  
* Tests : `test_decision.py` (incluant un test de bout en bout) et
`test_api.py` valident le comportement.

Tests associés
--------------
`test_decision.py`, `test_api.py`

Limites connues
---------------
Ne choisit pas le seuil (celui-ci est appris dans `train`) ; ne valide pas la
présence de `predict_proba` avant l’appel ; ne gère pas plus de deux classes ;
ne fournit ni explicabilité ni calibration des probabilités.
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Any, Sequence

from reviewpulse import config

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Constantes d'étiquetage
# --------------------------------------------------------------------------- #
# Pourquoi : 0/1 est la convention binaire retenue pour tout le projet ; toute
# autre valeur obligerait chaque consommateur à traduire l'étiquette.
LABEL_NEGATIVE: int = 0
"""Valeur d’étiquette correspondant à un avis négatif."""

# Pourquoi : 1 est l'étiquette complémentaire de 0 ; garder les deux constantes
# côte à côte interdit toute divergence dans les modules appelants.
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
    # Pourquoi : ``predict_proba`` accepte une liste mais pas forcément une
    # ``Sequence`` générique ; on normalise sans copier les chaînes.
    proba = model.predict_proba(list(texts))
    logger.debug("predict_proba retourne %d lignes", len(proba))
    # Pourquoi : ``model.classes_`` peut être un tableau numpy ; ``list`` expose
    # ``.index`` pour trouver la position de la classe négative.
    try:
        idx_negative = list(model.classes_).index(LABEL_NEGATIVE)
    except ValueError as exc:
        logger.exception("classe négative %d absente de model.classes_", LABEL_NEGATIVE)
        raise ValueError(
            "Le modèle ne contient pas la classe négative (0)."
        ) from exc
    logger.debug("classe négative trouvée à l'indice %d", idx_negative)
    # Pourquoi : on ne retient qu'une seule colonne pour alléger la suite et
    # éviter toute ambiguïté sur l'ordre des classes.
    return proba[:, idx_negative]


def model_threshold(model: Any) -> float:
    """Obtenir le seuil de décision associé au modèle.

    Si le modèle possède l’attribut ``decision_threshold_``, il est utilisé ;
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
    # Pourquoi : le seuil voyage avec le modèle quand il est entraîné, mais un
    # modèle hérité ou externe peut n'avoir que la valeur par défaut.
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
    # Pourquoi : on force le type flottant 64 bits pour garantir la comparaison
    # au seuil même si l'entrée est d'un sous-type entier ou flottant.
    proba_arr = np.asarray(proba_negative, dtype=np.float64)
    # Pourquoi : la règle métier est ``proba_negative >= threshold -> négatif`` ;
    # l'alternative ``>`` écarterait les avis exactement sur le seuil.
    labels = np.where(proba_arr >= threshold, LABEL_NEGATIVE, LABEL_POSITIVE)
    logger.debug("%d probabilités seuillées au seuil %.3f", len(proba_arr), threshold)
    # Pourquoi : les étiquettes doivent rester des entiers 64 bits pour être
    # comparables aux constantes et compatibles avec les métriques scikit-learn.
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
    # Pourquoi : la fonction refuse par défaut (fail-closed) : toute valeur non
    # reconnue lève une erreur plutôt que de renvoyer une chaîne ambiguë.
    if label == LABEL_NEGATIVE:
        return "negative"
    if label == LABEL_POSITIVE:
        return "positive"
    logger.error("étiquette inconnue reçue : %d", label)
    raise ValueError(f"Étiquette inconnue : {label}")
