# tests/test_explain.py
"""
Tests unitaires du module ``explain``.

Les tests construisent un petit pipeline scikit‑learn
(`TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3))` + `LogisticRegression`)
entraîné sur une dizaine de phrases françaises.  Aucun accès disque, aucun
réseau, aucune dépendance externe au projet.
"""

import numpy as np
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from reviewpulse import decision
from reviewpulse.explain import (
    global_terms,
    local_contributions,
    explain_batch,
)


@pytest.fixture(scope="module")
def tiny_model():
    """Entraîne un pipeline très simple sur des exemples français."""
    # Textes et étiquettes (0 = négatif, 1 = positif)
    textes = [
        "mauvais service, très lent",          # négatif
        "produit cassé, rien ne fonctionne",     # négatif
        "décevant, je ne recommande pas",       # négatif
        "horrible, très mauvaise qualité",      # négatif
        "terrible expérience, je suis fâché",   # négatif
        "excellent produit, très satisfait",    # positif
        "service rapide et agréable",           # positif
        "j'adore ce produit, super",           # positif
        "parfait, je recommande vivement",      # positif
        "qualité exceptionnelle, très bon",    # positif
    ]
    labels = [
        decision.LABEL_NEGATIVE,
        decision.LABEL_NEGATIVE,
        decision.LABEL_NEGATIVE,
        decision.LABEL_NEGATIVE,
        decision.LABEL_NEGATIVE,
        decision.LABEL_POSITIVE,
        decision.LABEL_POSITIVE,
        decision.LABEL_POSITIVE,
        decision.LABEL_POSITIVE,
        decision.LABEL_POSITIVE,
    ]

    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3)),
            ),
            ("clf", LogisticRegression(max_iter=1000, solver="lbfgs")),
        ]
    )
    pipeline.fit(textes, labels)
    return pipeline


def test_local_contributions_triées_et_limitées(tiny_model):
    """Les contributions locales sont triées par valeur absolue décroissante
    et limitées à ``n``."""
    texte = "service rapide et agréable"
    n = 5
    contrib = local_contributions(tiny_model, texte, n=n)

    # Vérifie le nombre d'éléments
    assert len(contrib) == n

    # Vérifie l'ordre décroissant de la valeur absolue
    valeurs = [c[1] for c in contrib]
    assert all(
        abs(valeurs[i]) >= abs(valeurs[i + 1]) for i in range(len(valeurs) - 1)
    ), "Les contributions ne sont pas triées par valeur absolue décroissante"


def test_terme_absent_ne_apparaît_pas(tiny_model):
    """Un terme qui n’est pas présent dans le texte ne doit jamais apparaître
    dans les contributions locales."""
    texte = "service rapide et agréable"
    contrib = local_contributions(tiny_model, texte, n=10)

    # Récupère les termes du texte après vectorisation
    vecteur = tiny_model.named_steps["tfidf"]
    indices_texte = vecteur.transform([texte]).nonzero()[1]
    termes_texte = {vecteur.get_feature_names_out()[i] for i in indices_texte}

    # Tous les termes retournés doivent appartenir à ``termes_texte``
    for terme, _ in contrib:
        assert terme in termes_texte, f"Le terme '{terme}' n'est pas présent dans le texte"


def test_somme_contributions_égale_decision_function(tiny_model):
    """La somme des contributions locales + ordonnée à l'origine doit
    correspondre (à 1e-9) à la fonction de décision du modèle pour la classe
    négative."""
    texte = "service rapide et agréable"
    n = len(tiny_model.named_steps["tfidf"].get_feature_names_out())
    contrib = local_contributions(tiny_model, texte, n=n)

    # Somme des contributions
    somme_contrib = sum(val for _, val in contrib)

    # Intercept de la classe négative (dans un modèle binaire, il s’agit de
    # l’opposé de l’intercept de la classe positive)
    intercept_neg = -tiny_model.named_steps["clf"].intercept_[0]

    # Décision du modèle pour la classe négative = -decision_function
    decision_neg = -tiny_model.decision_function([texte])[0]

    assert np.isclose(somme_contrib + intercept_neg, decision_neg, atol=1e-9)


def test_global_terms_n_et_signes(tiny_model):
    """``global_terms`` doit renvoyer exactement ``n`` termes de chaque côté,
    avec des coefficients du bon signe."""
    n = 7
    termes = global_terms(tiny_model, n=n)

    # Vérifie la présence des clés attendues
    assert set(termes.keys()) == {"negative", "positive"}

    # Chaque liste doit contenir exactement ``n`` éléments
    assert len(termes["negative"]) == n
    assert len(termes["positive"]) == n

    # Tous les coefficients doivent être strictement positifs et les termes doivent être disjoints
    for terme, coeff in termes["negative"]:
        assert coeff > 0, f"Coefficient non positif trouvé dans la liste négative : {coeff}"
    for terme, coeff in termes["positive"]:
        assert coeff > 0, f"Coefficient non positif trouvé dans la liste positive : {coeff}"
    # Vérifier que les ensembles de termes sont disjoints
    termes_neg = {terme for terme, _ in termes["negative"]}
    termes_pos = {terme for terme, _ in termes["positive"]}
    intersection = termes_neg.intersection(termes_pos)
    assert not intersection, f"Termes présents à la fois dans les listes négative et positive : {intersection}"


def test_explain_batch_cohérence_avec_local_contributions(tiny_model):
    """``explain_batch`` doit retourner le même résultat que
    ``local_contributions`` appliqué texte par texte."""
    textes = [
        "mauvais service, très lent",
        "excellent produit, très satisfait",
        "décevant, je ne recommande pas",
    ]
    n = 8
    batch_res = explain_batch(tiny_model, textes, n=n)

    # Calcul texte par texte avec ``local_contributions``
    expected = [local_contributions(tiny_model, txt, n=n) for txt in textes]

    assert batch_res == expected
