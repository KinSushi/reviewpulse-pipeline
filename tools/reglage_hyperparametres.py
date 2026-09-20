"""tools/reglage_hyperparametres.py
================================================

Rôle
----
Fournir un petit moteur de recherche d’hyperparamètres pour le modèle
de classification de sentiment, afin de satisfaire la consigne du *Final
Project (Demo Day)* : « Tune hyperparameters to optimize the model's
performance ».  L’outil ré‑utilise exactement la même logique de
pré‑traitement, de construction de pipeline et de séparation des jeux
de données que `src/reviewpulse/train.py` : même vecteur TF‑IDF,
même régression logistique, même ajout des avis `negative_boost` aux
ensembles d’entraînement des plis, même métrique `f1_macro`.

Fonctionnement
--------------
1. `grille()` construit une petite grille (≈ 12 points) en faisant
   varier `C`, `ngram_range` et `max_features`.  Le point actuel
   (`C=4.0, ngram_range=(2, 5), max_features=100000`) y est toujours
   présent pour permettre une comparaison directe.
2. `evaluer(parametres, X, y, plis, graine)` exécute une validation
   croisée stratifiée sur les avis *naturels* d’entraînement, ajoute à
   chaque pli les avis `negative_boost`, entraîne le pipeline avec les
   hyperparamètres fournis, puis calcule le `f1_macro` (seuil de décision
   = `config.DEFAULT_DECISION_THRESHOLD`).  Le résultat comprend la
   moyenne, l’écart‑type et la durée d’exécution.
3. `chercher(X, y, plis, graine)` parcourt la grille, journalise chaque
   appel de `evaluer` via `logger.info` et renvoie la liste des
   dictionnaires triée par `f1_macro` décroissant.
4. `rapport_markdown(resultats, point_courant, date_utc, commit)` génère
   un tableau Markdown de tous les points testés puis une lecture en
   prose : quel point gagne, de combien il dépasse le point courant et
   si cet écart dépasse l’écart‑type du point courant (condition de
   signification).  Si l’écart n’est pas significatif, le point courant
   est conservé.
5. `main()` expose une CLI (`--plis`, `--rapport`, `--graine`) qui
   charge les données nettoyées (`config.CLEAN_FILE`), lance la recherche,
   écrit le rapport et renvoie `0` en cas de succès ou `1` si le fichier
   de données est introuvable.

Aucune dépendance supplémentaire n’est introduite : scikit‑learn,
pandas et la bibliothèque standard suffisent.

"""

from __future__ import annotations

import argparse
import os
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from reviewpulse import config, decision

logger = logging.getLogger(__name__)


def _pipeline_custom(C: float, ngram_range: tuple[int, int], max_features: int) -> Pipeline:
    """Construit le pipeline TF‑IDF + LogisticRegression avec les hyperparamètres fournis.

    Args:
        C: Coefficient de régularisation du classifieur.
        ngram_range: Tuple (min, max) pour les n‑grammes de caractères.
        max_features: Nombre maximal de caractéristiques retenues.

    Returns:
        Pipeline prêt à être entraîné.
    """
    tfidf = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=ngram_range,
        min_df=2,
        max_features=max_features,
        sublinear_tf=True,
        lowercase=True,
    )
    clf = LogisticRegression(
        C=C,
        class_weight="balanced",
        max_iter=2000,
        random_state=config.RANDOM_STATE,
    )
    return Pipeline([("tfidf", tfidf), ("clf", clf)])


def grille() -> List[Dict[str, object]]:
    """Retourne la grille de recherche d’hyperparamètres.

    La grille est volontairement petite (≈ 12 points) pour rester
    exploitable sur une machine modeste.  On fait varier :

    - C : 1.0, 4.0 (point actuel), 10.0
    - ngram_range : (2, 4), (2, 5) (point actuel)
    - max_features : 50 000, 100 000 (point actuel)

    Le point actuel est toujours présent afin de pouvoir comparer les
    résultats obtenus avec la configuration déjà utilisée en production.
    """
    points = []
    for C in [1.0, 4.0, 10.0]:
        for ngram_range in [(2, 4), (2, 5)]:
            for max_feat in [50_000, 100_000]:
                points.append(
                    {
                        "C": C,
                        "ngram_range": ngram_range,
                        "max_features": max_feat,
                    }
                )
    return points


def evaluer(
    parametres: Dict[str, object],
    X: pd.Series,
    y: pd.Series,
    boost_df: pd.DataFrame,
    plis: int,
    graine: int,
) -> Dict[str, object]:
    """Évalue un jeu d’hyperparamètres par validation croisée stratifiée.

    Le score utilisé est le **F1 macro** calculé avec le seuil de décision
    `config.DEFAULT_DECISION_THRESHOLD`.  La fonction renvoie un dictionnaire
    contenant les hyperparamètres, la moyenne et l’écart‑type du F1 macro
    sur les plis, ainsi que la durée d’exécution en secondes.
    """
    start = time.time()
    skf = StratifiedKFold(n_splits=plis, shuffle=True, random_state=graine)
    scores: List[float] = []

    for train_idx, val_idx in skf.split(X, y):
        # Entraînement du pli : avis naturels + boost
        X_train_fold = pd.concat([X.iloc[train_idx], boost_df["review_text"]])
        y_train_fold = pd.concat([y.iloc[train_idx], boost_df["label"]])

        pipeline = _pipeline_custom(
            C=parametres["C"],
            ngram_range=parametres["ngram_range"],
            max_features=parametres["max_features"],
        )
        pipeline.fit(X_train_fold, y_train_fold)

        # Validation sur les avis naturels uniquement
        X_val = X.iloc[val_idx]
        y_val = y.iloc[val_idx]
        proba_val = decision.negative_proba(pipeline, X_val)
        preds = decision.predict_labels(proba_val, config.DEFAULT_DECISION_THRESHOLD)
        scores.append(f1_score(y_val, preds, average="macro"))

    duration = time.time() - start
    mean_f1 = sum(scores) / len(scores)
    std_f1 = (sum((s - mean_f1) ** 2 for s in scores) / len(scores)) ** 0.5

    result = {
        "C": parametres["C"],
        "ngram_range": parametres["ngram_range"],
        "max_features": parametres["max_features"],
        "f1_mean": mean_f1,
        "f1_std": std_f1,
        "duration_s": duration,
    }
    return result


def chercher(
    X: pd.Series,
    y: pd.Series,
    boost_df: pd.DataFrame,
    plis: int,
    graine: int,
) -> List[Dict[str, object]]:
    """Parcourt la grille, journalise chaque évaluation et renvoie les résultats triés."""
    resultats: List[Dict[str, object]] = []
    for params in grille():
        logger.info(
            "Évaluation du point C=%s, ngram_range=%s, max_features=%s",
            params["C"],
            params["ngram_range"],
            params["max_features"],
        )
        res = evaluer(params, X, y, boost_df, plis, graine)
        resultats.append(res)
        logger.info(
            "Résultat : f1_mean=%.4f, f1_std=%.4f, durée=%.1fs",
            res["f1_mean"],
            res["f1_std"],
            res["duration_s"],
        )
    # Tri décroissant sur le f1 moyen
    resultats.sort(key=lambda d: d["f1_mean"], reverse=True)
    return resultats


def rapport_markdown(
    resultats: List[Dict[str, object]],
    point_courant: Dict[str, object],
    date_utc: str,
    commit: str,
) -> str:
    """Génère le rapport Markdown à partir des résultats.

    Le texte indique :
    1. le point qui obtient le meilleur `f1_mean`;
    2. de combien il dépasse le point courant;
    3. si cet écart dépasse l’écart‑type du point courant (condition de
       signification).  Si l’écart n’est pas significatif, le texte
       précise que le point courant doit être conservé.
    """
    lines = [
        "# Rapport de réglage d’hyperparamètres",
        f"*Date :* {date_utc}",
        f"*Commit :* {commit}",
        "",
        "## Tableau des essais",
        "",
        "| C | n‑grammes | max_features | f1_mean | f1_std | durée (s) |",
        "|---|-----------|--------------|--------|-------|-----------|",
    ]

    for r in resultats:
        lines.append(
            f"| {r['C']} | {r['ngram_range']} | {r['max_features']} | "
            f"{r['f1_mean']:.4f} | {r['f1_std']:.4f} | {r['duration_s']:.1f} |"
        )

    best = resultats[0]
    diff = best["f1_mean"] - point_courant["f1_mean"]
    signif = diff > point_courant["f1_std"]

    lines.extend(
        [
            "",
            "## Analyse",
            "",
            f"Le meilleur point est **C={best['C']}, ngram_range={best['ngram_range']}, "
            f"max_features={best['max_features']}** avec un `f1_mean` de {best['f1_mean']:.4f}.",
            f"Il dépasse le point courant (C={point_courant['C']}, ngram_range={point_courant['ngram_range']}, "
            f"max_features={point_courant['max_features']}) de **{diff:.4f}** points de `f1_mean`.",
        ]
    )

    if signif:
        lines.append(
            "Cet écart est supérieur à l’écart‑type du point courant "
            f"({point_courant['f1_std']:.4f}), il est donc **significatif** et le nouveau point doit être retenu."
        )
    else:
        lines.append(
            "Cet écart n’est **pas** supérieur à l’écart‑type du point courant "
            f"({point_courant['f1_std']:.4f}); le gain n’est pas significatif et le point courant doit être conservé."
        )

    return "\n".join(lines)


def main() -> int:
    """Point d’entrée de l’outil de réglage d’hyperparamètres."""
    parser = argparse.ArgumentParser(
        description="Recherche d’hyperparamètres pour le modèle de sentiment."
    )
    parser.add_argument(
        "--plis",
        type=int,
        default=5,
        help="Nombre de plis pour la validation croisée (défaut : 5).",
    )
    parser.add_argument(
        "--rapport",
        type=Path,
        default=Path("docs/evidence/reglage_hyperparametres.md"),
        help="Chemin du fichier Markdown de sortie.",
    )
    parser.add_argument(
        "--graine",
        type=int,
        default=config.RANDOM_STATE,
        help="Graine aléatoire (défaut : celle du config).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    # Chargement des données nettoyées
    if not config.CLEAN_FILE.exists():
        logger.error("Fichier de données nettoyées introuvable : %s", config.CLEAN_FILE)
        return 1

    df = pd.read_parquet(config.CLEAN_FILE)

    # Garantir la présence de la colonne sample_source
    if "sample_source" not in df.columns:
        df["sample_source"] = config.SAMPLE_NATURAL

    natural_df = df[df["sample_source"] == config.SAMPLE_NATURAL]
    boost_df = df[df["sample_source"] == config.SAMPLE_NEGATIVE_BOOST]

    X_nat = natural_df["review_text"].astype("string")
    y_nat = natural_df["label"]

    # Recherche
    resultats = chercher(X_nat, y_nat, boost_df, args.plis, args.graine)

    # Point courant (celui présent dans la grille)
    point_courant = next(
        r
        for r in resultats
        if r["C"] == 4.0 and r["ngram_range"] == (2, 5) and r["max_features"] == 100_000
    )

    # Génération du rapport
    date_utc = datetime.now(timezone.utc).isoformat()
    commit = os.getenv("REVIEWPULSE_COMMIT", "inconnu")
    markdown = rapport_markdown(resultats, point_courant, date_utc, commit)

    args.rapport.parent.mkdir(parents=True, exist_ok=True)
    args.rapport.write_text(markdown, encoding="utf-8")
    logger.info("Rapport écrit dans %s", args.rapport)

    # Affichage d’un résumé succinct
    best = resultats[0]
    logger.info(
        "Meilleur point : C=%s, ngram_range=%s, max_features=%s, f1_mean=%.4f",
        best["C"],
        best["ngram_range"],
        best["max_features"],
        best["f1_mean"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
