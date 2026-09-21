"""reviewpulse.explain
=====================

Ce module fournit des fonctions d’explicabilité locale et globale du
modèle de classification de sentiment utilisé dans ReviewPulse.

Utilité
-------
* **Model Card** : présenter les termes les plus influents du modèle.
* **Tableau de bord** : expliquer, pour chaque avis, quelles n‑grammes
  (caractères) ont le plus contribué à la décision négative ou positive.

Le modèle attendu est un :class:`sklearn.pipeline.Pipeline` contenant exactement
deux étapes nommées :

* ``tfidf`` : :class:`sklearn.feature_extraction.text.TfidfVectorizer`
  (analyse ``char_wb``).
* ``clf`` : :class:`sklearn.linear_model.LogisticRegression` binaire.

Les fonctions lèvent :class:`ValueError` si ces exigences ne sont pas respectées.

Aucune lecture/écriture disque, journalisation ou appel à MLflow n’est
effectué ici.

Quoi
----
Ce module fournit des fonctions d’explicabilité locale et globale pour le
modèle de classification de sentiment de ReviewPulse.

Pourquoi
--------
Le besoin métier est de présenter les termes influents (Model Card) et
d'expliquer les décisions individuelles (Tableau de bord). Cette approche
privilégie la contribution linéaire exacte (ADR 0019) plutôt que des
méthodes approximatives comme SHAP ou LIME, garantissant une
interprétabilité exacte et des performances constantes.

Ou
--
Ce module s'exécute en mémoire, sans accès disque, ni journalisation externe.

Comment
-------
Le module valide d'abord le pipeline pour s'assurer de la présence des
étapes TfidfVectorizer et LogisticRegression. Il extrait ensuite les
coefficients du classifieur, calcule les contributions locales via le
produit de la valeur TF-IDF et du coefficient, et trie les résultats par
magnitude pour identifier les traits les plus discriminants.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import logging
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from reviewpulse.decision import LABEL_NEGATIVE

logger = logging.getLogger(__name__)

__all__: List[str] = [
    "global_terms",
    "local_contributions",
    "explain_batch",
]


def _validate_model(model: Pipeline) -> Tuple[TfidfVectorizer, LogisticRegression]:
    """Vérifie que *model* possède les étapes attendues.

    Parameters
    ----------
    model: Pipeline
        Pipeline entraîné.

    Returns
    -------
    tuple
        Le vecteur TF‑IDF et le classifieur.

    Raises
    ------
    ValueError
        Si le pipeline ne contient pas les étapes ``tfidf`` et ``clf`` ou si
        les objets ne sont pas du type attendu.
    """
    logger.info("Début de la validation du modèle.")
    if not isinstance(model, Pipeline):
        raise ValueError("Le modèle doit être une instance de sklearn.pipeline.Pipeline.")
    try:
        tfidf = model.named_steps["tfidf"]
        clf = model.named_steps["clf"]
    except KeyError as exc:
        raise ValueError(
            "Le pipeline doit contenir les étapes nommées 'tfidf' et 'clf'."
        ) from exc

    if not isinstance(tfidf, TfidfVectorizer):
        raise ValueError("L'étape 'tfidf' doit être un TfidfVectorizer.")
    if not isinstance(clf, LogisticRegression):
        raise ValueError("L'étape 'clf' doit être un LogisticRegression.")
    logger.info("Validation du modèle réussie.")
    return tfidf, clf


def _negative_coefficients(clf: LogisticRegression) -> np.ndarray:
    """Renvoie le vecteur de coefficients associé à la classe négative.

    En classification binaire, ``clf.coef_[0]`` correspond aux coefficients
    de la classe ``clf.classes_[1]``.  Ainsi, si la classe négative occupe
    l’indice 1, le vecteur retourné est ``clf.coef_[0]`` tel quel ; sinon il
    faut en prendre l’opposé.

    Parameters
    ----------
    clf: LogisticRegression
        Classifieur entraîné.

    Returns
    -------
    np.ndarray
        Coefficients (float64) de la classe négative, de même forme que
        ``clf.coef_[0]``.
    """
    logger.info("Extraction des coefficients pour la classe négative.")
    # Pourquoi : L'ordre des classes dans clf.classes_ n'est pas garanti, on cherche l'index explicite.
    try:
        idx_negative = list(clf.classes_).index(LABEL_NEGATIVE)
    except ValueError as exc:
        raise ValueError(
            "Le classifieur ne contient pas la classe négative (0) dans clf.classes_."
        ) from exc

    # ``clf.coef_[0]`` porte les coefficients de ``clf.classes_[1]``.
    # Si la classe négative est à l’indice 1, on renvoie le vecteur tel quel,
    # sinon on renvoie son opposé.
    if idx_negative == 1:
        return clf.coef_[0]
    else:
        return -clf.coef_[0]


def global_terms(model: Pipeline, n: int = 20) -> Dict[str, List[Tuple[str, float]]]:
    """Retourne les *n* termes les plus influents pour chaque classe.

    Les termes sont triés par valeur absolue décroissante du coefficient
    associé à la classe correspondante.

    Parameters
    ----------
    model: Pipeline
        Pipeline entraîné contenant les étapes ``tfidf`` et ``clf``.
    n: int, optional
        Nombre de termes à retourner pour chaque classe (défaut = 20).

    Returns
    -------
    dict
        ``{"negative": [(terme, coeff), ...], "positive": [(terme, coeff), ...]}``.

    Raises
    ------
    ValueError
        Si le pipeline ne respecte pas les exigences décrites.
    """
    logger.info("Calcul des termes globaux pour %d termes.", n)
    tfidf, clf = _validate_model(model)

    terms = tfidf.get_feature_names_out()
    coeff_pos = clf.coef_[0]               # coefficients de la classe positive
    coeff_neg = _negative_coefficients(clf)  # coefficients de la classe négative

    # Comment : On filtre les coefficients positifs car ils indiquent une influence positive vers la classe cible.
    neg_pairs = [(term, coeff) for term, coeff in zip(terms, coeff_neg) if coeff > 0]
    pos_pairs = [(term, coeff) for term, coeff in zip(terms, coeff_pos) if coeff > 0]

    # Tri par valeur absolue décroissante
    neg_pairs.sort(key=lambda x: abs(x[1]), reverse=True)
    pos_pairs.sort(key=lambda x: abs(x[1]), reverse=True)

    logger.info("Terme global calculé pour %d classes.", len(neg_pairs) + len(pos_pairs))
    return {
        "negative": neg_pairs[:n],
        "positive": pos_pairs[:n],
    }


def local_contributions(
    model: Pipeline, text: str, n: int = 10
) -> List[Tuple[str, float]]:
    """Calcule les contributions locales d’un texte.

    La contribution d’un trait est le produit de sa valeur TF‑IDF par le
    coefficient de la classe négative.  Les contributions positives poussent
    vers la classe « negative », les négatives vers « positive ».

    Parameters
    ----------
    model: Pipeline
        Pipeline entraîné contenant les étapes ``tfidf`` et ``clf``.
    text: str
        Texte à expliquer.
    n: int, optional
        Nombre maximal de contributions à retourner (défaut = 10).

    Returns
    -------
    list[tuple[str, float]]
        Liste triée de ``(terme, contribution)``.

    Raises
    ------
    ValueError
        Si le pipeline ne respecte pas les exigences décrites.
    """
    logger.info("Calcul des contributions locales pour un texte.")
    tfidf, clf = _validate_model(model)

    # Vectorisation du texte (sparse)
    X = tfidf.transform([text])  # shape (1, n_features)
    if X.nnz == 0:
        return []

    coeff_neg = _negative_coefficients(clf)  # vecteur de coefficients négatifs

    # Contributions = valeur TF‑IDF * coeff négatif
    # On exploite la multiplication élément‑par‑élément sur la matrice sparse.
    # La multiplication peut retourner une matrice au format COO qui ne possède pas
    # l’attribut ``indices``. On la convertit donc en CSR (format supportant ``indices``)
    # avant d’en extraire les indices et les valeurs.
    # Comment : La conversion en CSR est nécessaire pour accéder aux indices via l'attribut .indices.
    contrib_sparse = X.multiply(coeff_neg).tocsr()

    indices = contrib_sparse.indices
    values = contrib_sparse.data
    terms = tfidf.get_feature_names_out()

    contributions = [(terms[idx], val) for idx, val in zip(indices, values)]
    contributions.sort(key=lambda x: abs(x[1]), reverse=True)

    logger.info("Contribution locale calculée pour %d termes.", len(contributions))
    return contributions[:n]


def explain_batch(
    model: Pipeline, texts: Sequence[str], n: int = 10
) -> List[List[Tuple[str, float]]]:
    """Explique un lot de textes en appliquant :func:`local_contributions`.

    La vectorisation de l’ensemble des textes n’est effectuée qu’une seule
    fois pour des raisons de performance.

    Parameters
    ----------
    model: Pipeline
        Pipeline entraîné contenant les étapes ``tfidf`` et ``clf``.
    texts: Sequence[str]
        Séquence de textes à expliquer.
    n: int, optional
        Nombre maximal de contributions retournées par texte (défaut = 10).

    Returns
    -------
    list[list[tuple[str, float]]]
        Liste où chaque élément correspond aux contributions d’un texte.

    Raises
    ------
    ValueError
        Si le pipeline ne respecte pas les exigences décrites.
    """
    logger.info("Exploration d'un lot de %d textes.", len(texts))
    tfidf, clf = _validate_model(model)

    # Vectorisation en bloc
    X = tfidf.transform(list(texts))  # shape (len(texts), n_features)
    if X.nnz == 0:
        return [[] for _ in texts]

    coeff_neg = _negative_coefficients(clf)

    # Contributions par élément (sparse multiplication)
    # La multiplication peut produire une matrice au format COO qui ne possède pas
    # l’attribut ``indices``. On la convertit en CSR pour pouvoir accéder aux indices
    # et aux valeurs de chaque ligne.
    # Comment : La conversion en CSR est nécessaire pour itérer ligne par ligne.
    contrib_matrix = X.multiply(coeff_neg).tocsr()  # même forme que X, mais valeurs = tfidf * coeff_neg

    terms = tfidf.get_feature_names_out()
    results: List[List[Tuple[str, float]]] = []

    for row_idx in range(contrib_matrix.shape[0]):
        row = contrib_matrix.getrow(row_idx)
        if row.nnz == 0:
            results.append([])
            continue
        idxs = row.indices
        vals = row.data
        contribs = [(terms[i], v) for i, v in zip(idxs, vals)]
        contribs.sort(key=lambda x: abs(x[1]), reverse=True)
        results.append(contribs[:n])

    logger.info("Lot de %d textes expliqués.", len(results))
    return results
