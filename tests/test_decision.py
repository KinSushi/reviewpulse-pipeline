# tests/test_decision.py
"""
Tests unitaires du module ``decision`` et de son intégration avec le pipeline
d’entraînement et de scoring.

Les fixtures ``data_env`` et ``labelled_frame`` proviennent de ``tests/conftest.py``.
Elles préparent un environnement de données isolé et un DataFrame équilibré
conforme à ``config.CLEAN_COLUMNS``.
"""

import numpy as np
import pandas as pd

from reviewpulse import config, decision, score, train


def test_predict_labels_seuil():
    """
    Vérifie que :func:`decision.predict_labels` applique correctement le
    seuil de décision : les probabilités supérieures ou égales au seuil donnent
    l’étiquette négative (0), sinon positive (1).
    """
    proba = np.array([0.9, 0.1, 0.75])
    seuil = 0.75
    attendu = np.array([0, 1, 0])
    resultat = decision.predict_labels(proba, seuil)
    np.testing.assert_array_equal(resultat, attendu)


def test_label_name():
    """
    Vérifie la correspondance entre les constantes d’étiquette et leurs libellés.
    """
    assert decision.label_name(0) == "negative"
    assert decision.label_name(1) == "positive"


def test_model_threshold_fallback():
    """
    Un modèle ne possédant pas l’attribut ``decision_threshold_`` doit
    renvoyer la valeur par défaut définie dans ``config.DEFAULT_DECISION_THRESHOLD``.
    """
    class DummyModel:
        pass

    dummy = DummyModel()
    assert decision.model_threshold(dummy) == config.DEFAULT_DECISION_THRESHOLD


def test_negative_proba_avec_classes_mélangées():
    """
    La fonction :func:`decision.negative_proba` doit identifier la colonne
    correspondant à la classe 0 même si ``model.classes_`` n’est pas triée.
    """
    class FakeModel:
        # L’ordre des classes est [1, 0] → l’indice de la classe 0 est 1
        classes_ = np.array([1, 0])

        def predict_proba(self, texts):
            # Retourne une probabilité de 0.2 pour la classe 1 et 0.8 pour la classe 0
            return np.array([[0.2, 0.8]])

    model = FakeModel()
    proba = decision.negative_proba(model, ["quelque texte"])
    np.testing.assert_array_almost_equal(proba, np.array([0.8]))


def test_end_to_end_training_and_scoring(data_env, labelled_frame):
    """
    Test de bout en bout :

    1. Entraîner et logger le modèle avec ``train.train_and_log``.
    2. Charger le modèle champion via ``score.load_champion``.
    3. Scorer deux avis dont le texte est clairement négatif ou positif.
    4. Vérifier que les prédictions correspondent aux attentes.
    """
    # 1. Entraînement et enregistrement du modèle
    train.train_and_log(
        labelled_frame,
        tracking_uri=config.MLFLOW_TRACKING_URI,
        register=True,
    )

    # 2. Chargement du modèle champion
    model, version = score.load_champion(tracking_uri=config.MLFLOW_TRACKING_URI)

    # 3. Construction d’un petit DataFrame contenant les deux textes test
    df_test = pd.DataFrame(
        {
            "review_text": [
                "crash bug refund broken boring",   # texte négatif
                "great fun amazing love excellent",  # texte positif
            ]
        }
    )

    # 4. Scoring
    scored = score.score(df_test, model, version)

    # Extraction des prédictions
    pred = scored["pred_label"].tolist()
    # 0 = négatif, 1 = positif selon la convention
    assert pred[0] == 0, "Le texte négatif doit être prédit comme 0"
    assert pred[1] == 1, "Le texte positif doit être prédit comme 1"


def test_balance_pred_label_share(data_env, labelled_frame):
    """
    Sur le jeu complet ``labelled_frame`` (équilibré à 50 %/50 %),
    la proportion de prédictions négatives doit rester raisonnablement
    centrée (entre 30 % et 70 %).
    """
    # Entraînement et enregistrement du modèle
    train.train_and_log(
        labelled_frame,
        tracking_uri=config.MLFLOW_TRACKING_URI,
        register=True,
    )
    model, version = score.load_champion(tracking_uri=config.MLFLOW_TRACKING_URI)

    # Scoring du jeu complet
    scored = score.score(labelled_frame, model, version)

    # Calcul de la part de prédictions négatives
    prop_negative = (scored["pred_label"] == 0).mean()
    assert 0.3 <= prop_negative <= 0.7, (
        f"La part de prédictions négatives ({prop_negative:.2f}) n'est pas "
        "dans l'intervalle attendu [0.3, 0.7]."
    )
