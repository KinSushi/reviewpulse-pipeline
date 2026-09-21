# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""tests/test_reverse_gaps.py
================================

Ce module de tests comble les lacunes révélées par le mécanisme de tests inverses
(« reverse »). Les mutations **M06**, **M07** et **M11** du fichier
``tests/reverse/mutations.json`` n’étaient pas détectées :

* **M06** – désactivation du contrôle qualité bloquant dans ``transform.main``.
* **M07** – suppression de la barrière de promotion du modèle dans ``train``.
* **M11** – calcul de la part de négatifs sur l’ensemble des flux au lieu du
  flux naturel uniquement.

Les trois tests ci‑dessous reproduisent les scénarios qui auraient dû faire
échouer ces mutations.
"""

import json

import pytest
import pandas as pd

from reviewpulse import config, quality, score, train, transform


def test_transform_quality_blocking_M06(data_env, review_factory):
    """
    M06 – contrôle qualité bloquant désactivé.

    On crée 10 avis *positifs* (``voted_up=True``) dans le flux naturel.
    La proportion de négatifs naturels est donc 0 % < 0,5 % (minimum attendu).
    ``transform.main`` doit échouer (code 1) et ne doit pas créer le fichier
    ``config.CLEAN_FILE``.
    """
    # Construction du chemin de partition attendu par ``transform.load_raw``.
    raw_path = (
        config.RAW_DIR
        / "app_id=1"
        / "language=english"
        / "dt=2026-09-16"
        / "batch_x.jsonl"
    )
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    # Écriture de 10 avis distincts, tous positifs.
    with raw_path.open("w", encoding="utf-8") as f:
        for i in range(10):
            rev = review_factory(
                rid=i,
                voted_up=True,
                text=f"Excellent game {i}",
            )
            f.write(json.dumps(rev) + "\n")

    # Exécution du pipeline de transformation.
    exit_code = transform.main()

    assert exit_code == 1, "Le pipeline doit échouer à cause du contrôle qualité"
    assert not config.CLEAN_FILE.exists(), "Aucun fichier clean ne doit être créé"


def test_train_promotion_barrier_M07(data_env, labelled_frame, monkeypatch):
    """
    M07 – barrière de promotion supprimée.

    On élève artificiellement le seuil ``F1_MACRO_MIN`` au-dessus de 1
    (impossible à atteindre). Le modèle ne doit donc pas être promu.
    De plus, aucune version champion ne doit exister, ce qui provoque une
    exception lors de l’appel à ``score.load_champion``.
    """
    # Forcer le seuil de promotion à une valeur impossible.
    monkeypatch.setattr(config, "F1_MACRO_MIN", 1.01, raising=False)

    # Entraînement et log du modèle.
    result = train.train_and_log(
        labelled_frame,
        tracking_uri=config.MLFLOW_TRACKING_URI,
    )

    assert result["promoted"] is False, "Le modèle ne doit pas être promu"

    # Aucun champion ne doit être enregistré ; la fonction doit lever.
    with pytest.raises(Exception):
        score.load_champion(tracking_uri=config.MLFLOW_TRACKING_URI)


def test_negative_share_natural_only_M11(data_env, labelled_frame):
    """
    M11 – part de négatifs calculée sur le flux naturel uniquement.

    On crée un DataFrame où le flux naturel ne contient aucun avis négatif
    (``label=1`` partout). On ajoute ensuite 40 avis négatifs provenant du
    flux ``negative_boost``. La fonction ``quality.check_clean`` doit signaler
    que la part de négatifs naturels est hors limites, même si le flux
    complémentaire contient des négatifs.
    """
    # Flux naturel : tous les labels à 1.
    df_nat = labelled_frame.copy()
    df_nat["label"] = 1

    # Flux boost : 40 copies avec label=0 et source ``negative_boost``.
    df_boost = labelled_frame.copy()
    df_boost["label"] = 0
    df_boost["review_id"] = df_boost["review_id"] + "_b"
    df_boost["sample_source"] = "negative_boost"

    # Concaténation et réinitialisation de l'index.
    frame = pd.concat([df_nat, df_boost], ignore_index=True)

    # Vérification du contrôle qualité.
    messages = quality.check_clean(frame)

    assert len(messages) >= 1, "Au moins un message d’erreur doit être retourné"
    # On s’assure que le message porte bien sur la part de négatifs naturels.
    assert any(
        "Part de négatifs" in msg for msg in messages
    ), "Le message doit concerner la part de négatifs naturels"
