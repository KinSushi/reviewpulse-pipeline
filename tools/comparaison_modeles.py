"""tools/comparaison_modeles.py
================================

Rôle
----
Banc de comparaison de familles de modèles pour le projet ReviewPulse.
L'outil évalue plusieurs candidats selon le protocole exact de
`src/reviewpulse/train.py` (mêmes données, mêmes plis, même convention de
décision) et produit un rapport Markdown vérifiable.

Place dans la chaîne
--------------------
Hors DAG principal.  Appelé à la main pour répondre à la question du jury :
« ne peut-on pas obtenir un meilleur score avec un autre modèle ? ».

Quoi
----
Comparer le modèle en service (TF-IDF sur n-grammes de caractères +
régression logistique) à d'autres familles de modèles : SVM linéaire
calibré, SGD avec perte modified_huber, Bayes naïf complémentaire,
régression ridge calibrée, gradient boosting sur SVD, régression logistique
sur mots, forêt aléatoire et XGBoost.

Pourquoi
--------
Le projet a comparé des variantes d'un même modèle (mots contre
caractères, régularisation, hyperparamètres) mais jamais d'autres familles.
Un jury demandera si une famille différente ne serait pas meilleure.  La
réponse doit être une mesure, pas une opinion.

Où
--
- Lit : `config.CLEAN_FILE`, `config.SAMPLE_NATURAL`,
  `config.SAMPLE_NEGATIVE_BOOST`, `config.THRESHOLD_GRID`,
  `config.RANDOM_STATE`, `config.DEFAULT_DECISION_THRESHOLD`.
- Appelle : `train.build_pipeline()`, `decision.negative_proba()`,
  `decision.predict_labels()`.
- Écrit : rapport Markdown dans `docs/evidence/comparaison_modeles.md`
  par défaut.

Comment
-------
1. Chargement des données nettoyées ; séparation des avis naturels (X, y)
   et des avis complémentaires (`boost_df`).
2. Calcul unique des plis de validation croisée stratifiée.
3. Pour chaque candidat, construction d'un pipeline neuf par pli,
   entraînement sur naturels d'entraînement + boost, probabilités négatives
   hors pli via `decision.negative_proba`.
4. Recherche du seuil optimal sur les probabilités hors pli dans
   `config.THRESHOLD_GRID` avec `decision.predict_labels`.
5. Calcul du F1 macro hors pli, de l'AUC de la classe négative, du rappel
   et de la précision négatifs au seuil retenu.
6. Mesure de la durée d'entraînement moyenne par pli et de la latence de
   prédiction pour 1 000 avis.
7. Génération d'un rapport Markdown trié par F1 macro décroissant.

Choix de conception
-------------------
- **Mêmes plis pour tous les candidats** : la liste des indices de plis est
  calculée une seule fois avant la boucle des candidats.  Cela garantit que
  la comparaison n'est pas biaisée par un tirage différent.
- **Protocole identique à `train.py`** : boost ajouté à l'entraînement de
  chaque pli, jamais à la validation ; seuil appris sur les probabilités
  hors pli ; métriques au seuil retenu.
- **Fabriques sans argument** : chaque candidat fournit une fonction qui
  rend un pipeline neuf, évitant tout état partagé entre plis.
- **TF-IDF du projet réutilisé** : `train.build_pipeline().steps[0]` fournit
  l'étape `("tfidf", vectoriseur)` neuf, sans recopier les hyperparamètres.
- **Calibration sigmoïde pour SVM et Ridge** : ces modèles n'ont pas de
  `predict_proba` natif ; `CalibratedClassifierCV` fournit les probabilités
  exigées par la convention `decision.negative_proba`.
- **XGBoost optionnel** : import dans un bloc `try/except` en tête de
  fichier ; si le paquet est absent, le candidat est listé comme
  « non mesuré » sans faire échouer l'outil.
- **Poids par échantillon pour XGBoost** : XGBoost n'accepte pas
  `class_weight` ; on passe `clf__sample_weight=compute_sample_weight(...)`.
- **Rapport généré à partir des chiffres** : la section « Lecture » ne
  contient que des constats calculés (meilleur candidat, écart au témoin,
  comparaison à l'écart-type des plis du témoin).

Limites connues
---------------
- Le banc ne mesure pas les modèles de type transformeur ni les
  plongements de phrases ; ces familles nécessitent de télécharger des
  modèles de plusieurs centaines de Mo que l'image du projet n'embarque
  pas.
- Le seuil est cherché dans `config.THRESHOLD_GRID` uniquement ; un optimum
  entre deux valeurs de la grille peut être manqué.
- La latence est mesurée sur le dernier pli, avec un échantillon tronqué
  ou répété à 1 000 lignes ; ce n'est pas une mesure de production sous
  charge.
- XGBoost est optionnel ; son absence ne constitue pas un échec du banc.
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, RidgeClassifier, SGDClassifier
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.utils.class_weight import compute_sample_weight

# Import optionnel de xgboost.  Le banc doit continuer si le paquet est absent.
try:
    import xgboost
except ImportError:
    xgboost = None

from reviewpulse import config, decision, train

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Description d'un candidat
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Candidat:
    """Description figée d'un candidat au banc de comparaison.

    Pourquoi : regrouper dans une seule structure le nom, la fabrique de
    pipeline, la famille, et les deux indicateurs booléens nécessaires au
    protocole (explication exacte et poids par échantillon).
    """

    nom: str
    fabrique: Callable[[], Pipeline]
    explication_exacte: bool
    poids_par_echantillon: bool
    famille: str


# --------------------------------------------------------------------------- #
# Fabriques de candidats
# --------------------------------------------------------------------------- #
def _etape_tfidf_projet() -> tuple[str, TfidfVectorizer]:
    """Renvoie l'étape TF-IDF du pipeline en service, neuve.

    Pourquoi : reprendre exactement la vectorisation du projet sans
    recopier ses hyperparamètres dans chaque candidat.
    """
    return train.build_pipeline().steps[0]


def _logreg_regression() -> LogisticRegression:
    """Renvoie la régression logistique du modèle en service, neuve.

    Pourquoi : plusieurs candidats réutilisent le même classifieur que
    `build_pipeline()` ; cette fonction évite la duplication.
    """
    return LogisticRegression(
        C=10.0,
        class_weight="balanced",
        max_iter=2000,
        random_state=config.RANDOM_STATE,
    )


def _fabrique_logreg_caracteres() -> Pipeline:
    """Fabrique le modèle en service (témoin)."""
    return train.build_pipeline()


def _fabrique_svm_lineaire() -> Pipeline:
    """Fabrique un SVM linéaire calibré sur la même TF-IDF."""
    tfidf_name, tfidf = _etape_tfidf_projet()
    clf = CalibratedClassifierCV(
        LinearSVC(
            C=1.0,
            class_weight="balanced",
            random_state=config.RANDOM_STATE,
        ),
        method="sigmoid",
        cv=3,
    )
    return Pipeline([(tfidf_name, tfidf), ("clf", clf)])


def _fabrique_sgd_modified_huber() -> Pipeline:
    """Fabrique un SGD avec perte modified_huber sur la même TF-IDF."""
    tfidf_name, tfidf = _etape_tfidf_projet()
    clf = SGDClassifier(
        loss="modified_huber",
        class_weight="balanced",
        max_iter=2000,
        tol=1e-4,
        random_state=config.RANDOM_STATE,
    )
    return Pipeline([(tfidf_name, tfidf), ("clf", clf)])


def _fabrique_bayes_naif_complementaire() -> Pipeline:
    """Fabrique un Bayes naïf complémentaire sur la même TF-IDF."""
    tfidf_name, tfidf = _etape_tfidf_projet()
    clf = ComplementNB(alpha=0.3)
    return Pipeline([(tfidf_name, tfidf), ("clf", clf)])


def _fabrique_ridge() -> Pipeline:
    """Fabrique une régression ridge calibrée sur la même TF-IDF."""
    tfidf_name, tfidf = _etape_tfidf_projet()
    clf = CalibratedClassifierCV(
        RidgeClassifier(
            class_weight="balanced",
            random_state=config.RANDOM_STATE,
        ),
        method="sigmoid",
        cv=3,
    )
    return Pipeline([(tfidf_name, tfidf), ("clf", clf)])


def _fabrique_gradient_boosting_sur_svd() -> Pipeline:
    """Fabrique un gradient boosting sur SVD après la même TF-IDF."""
    tfidf_name, tfidf = _etape_tfidf_projet()
    svd = TruncatedSVD(n_components=200, random_state=config.RANDOM_STATE)
    clf = HistGradientBoostingClassifier(
        class_weight="balanced",
        max_iter=200,
        random_state=config.RANDOM_STATE,
    )
    return Pipeline([(tfidf_name, tfidf), ("svd", svd), ("clf", clf)])


def _fabrique_logreg_mots() -> Pipeline:
    """Fabrique une régression logistique sur des n-grammes de mots."""
    tfidf = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=2,
        sublinear_tf=True,
        lowercase=True,
    )
    clf = _logreg_regression()
    return Pipeline([("tfidf", tfidf), ("clf", clf)])


def _fabrique_foret_aleatoire() -> Pipeline:
    """Fabrique une forêt aléatoire sur la même TF-IDF."""
    tfidf_name, tfidf = _etape_tfidf_projet()
    clf = RandomForestClassifier(
        n_estimators=300,
        max_features="sqrt",
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=config.RANDOM_STATE,
    )
    return Pipeline([(tfidf_name, tfidf), ("clf", clf)])


def _fabrique_xgboost() -> Pipeline:
    """Fabrique un XGBoost sur la même TF-IDF."""
    tfidf_name, tfidf = _etape_tfidf_projet()
    clf = xgboost.XGBClassifier(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.3,
        tree_method="hist",
        eval_metric="logloss",
        n_jobs=-1,
        random_state=config.RANDOM_STATE,
    )
    return Pipeline([(tfidf_name, tfidf), ("clf", clf)])


def candidats() -> List[Candidat]:
    """Liste l'ensemble des candidats du banc.

    Pourquoi : centraliser la définition des candidats pour que la CLI
    `--seulement` puisse filtrer sur les noms déclarés ici.

    Returns:
        Liste des descriptions de candidats.
    """
    return [
        Candidat(
            nom="logreg_caracteres",
            fabrique=_fabrique_logreg_caracteres,
            explication_exacte=True,
            poids_par_echantillon=False,
            famille="lineaire",
        ),
        Candidat(
            nom="svm_lineaire",
            fabrique=_fabrique_svm_lineaire,
            explication_exacte=False,
            poids_par_echantillon=False,
            famille="marge",
        ),
        Candidat(
            nom="sgd_modified_huber",
            fabrique=_fabrique_sgd_modified_huber,
            explication_exacte=True,
            poids_par_echantillon=False,
            famille="lineaire",
        ),
        Candidat(
            nom="bayes_naif_complementaire",
            fabrique=_fabrique_bayes_naif_complementaire,
            explication_exacte=True,
            poids_par_echantillon=False,
            famille="bayesien",
        ),
        Candidat(
            nom="ridge",
            fabrique=_fabrique_ridge,
            explication_exacte=False,
            poids_par_echantillon=False,
            famille="lineaire",
        ),
        Candidat(
            nom="gradient_boosting_sur_svd",
            fabrique=_fabrique_gradient_boosting_sur_svd,
            explication_exacte=False,
            poids_par_echantillon=False,
            famille="arbres",
        ),
        Candidat(
            nom="logreg_mots",
            fabrique=_fabrique_logreg_mots,
            explication_exacte=True,
            poids_par_echantillon=False,
            famille="lineaire",
        ),
        Candidat(
            nom="foret_aleatoire",
            fabrique=_fabrique_foret_aleatoire,
            explication_exacte=False,
            poids_par_echantillon=False,
            famille="arbres",
        ),
        Candidat(
            nom="xgboost",
            fabrique=_fabrique_xgboost,
            explication_exacte=False,
            poids_par_echantillon=True,
            famille="arbres",
        ),
    ]


# --------------------------------------------------------------------------- #
# Protocole de mesure
# --------------------------------------------------------------------------- #
def _mesurer_latence(pipeline: Pipeline, X_val: pd.Series) -> float:
    """Mesure la latence de prédiction pour 1 000 avis en millisecondes.

    Pourquoi : la latence doit être comparable entre candidats ; on
    normalise l'entrée à exactement 1 000 lignes.

    Args:
        pipeline: Pipeline entraîné du dernier pli.
        X_val: Série de textes du dernier pli de validation.

    Returns:
        Durée moyenne d'une prédiction sur 1 000 avis, en millisecondes.
    """
    n = 1000
    if len(X_val) >= n:
        X_bench = X_val.iloc[:n]
    else:
        # Pourquoi : répéter les lignes jusqu'à atteindre 1 000 si le pli est
        # plus petit, afin de conserver une taille fixe de référence.
        repeats = (n // len(X_val)) + 1
        X_bench = pd.concat([X_val] * repeats, ignore_index=True).iloc[:n]

    start = time.perf_counter()
    decision.negative_proba(pipeline, X_bench)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return float(elapsed_ms)


def _evaluer_candidat(
    candidat: Candidat,
    X: pd.Series,
    y: pd.Series,
    boost_df: pd.DataFrame,
    plis: List[tuple[np.ndarray, np.ndarray]],
) -> dict:
    """Évalue un candidat selon le protocole de validation croisée du projet.

    Pourquoi : appliquer exactement la même méthodologie à chaque
    candidat pour que la comparaison soit honnête.

    Args:
        candidat: Description du candidat (fabrique, nom, etc.).
        X: Textes des avis naturels.
        y: Étiquettes des avis naturels.
        boost_df: Avis complémentaires ajoutés à l'entraînement de chaque pli.
        plis: Liste des couples (indices_entraînement, indices_validation)
            calculés une seule fois pour tous les candidats.

    Returns:
        Dictionnaire des métriques et mesures pour le candidat.
    """
    oof_proba = pd.Series(index=X.index, dtype="float64")
    durees_entrainement: List[float] = []
    dernier_pipeline: Pipeline | None = None
    dernier_X_val: pd.Series | None = None

    for train_idx, val_idx in plis:
        X_train_fold = pd.concat([X.iloc[train_idx], boost_df["review_text"]])
        y_train_fold = pd.concat([y.iloc[train_idx], boost_df["label"]])

        pipeline = candidat.fabrique()

        fit_kwargs: dict = {}
        if candidat.poids_par_echantillon:
            # Pourquoi : XGBoost n'accepte pas class_weight ; on compense le
            # déséquilibre par des poids par échantillon sur l'ensemble d'entraînement.
            fit_kwargs["clf__sample_weight"] = compute_sample_weight(
                "balanced", y_train_fold
            )

        start_fit = time.perf_counter()
        pipeline.fit(X_train_fold, y_train_fold, **fit_kwargs)
        durees_entrainement.append(time.perf_counter() - start_fit)

        proba_val = decision.negative_proba(pipeline, X.iloc[val_idx])
        oof_proba.iloc[val_idx] = proba_val

        dernier_pipeline = pipeline
        dernier_X_val = X.iloc[val_idx]

    # Recherche du seuil optimal sur les probabilités hors pli
    best_thr = config.DEFAULT_DECISION_THRESHOLD
    best_f1 = -1.0
    for thr in config.THRESHOLD_GRID:
        preds_thr = decision.predict_labels(oof_proba, thr)
        f1_thr = f1_score(y, preds_thr, average="macro")
        if f1_thr > best_f1 or (
            abs(f1_thr - best_f1) < 1e-9 and abs(thr - 0.5) < abs(best_thr - 0.5)
        ):
            best_f1 = f1_thr
            best_thr = thr

    # Pourquoi : l'écart-type par pli doit se mesurer au même seuil que le F1
    # publié, sinon on comparerait un écart à une dispersion mesurée ailleurs.
    f1_par_pli: List[float] = []
    for _, val_idx in plis:
        f1_par_pli.append(
            float(
                f1_score(
                    y.iloc[val_idx],
                    decision.predict_labels(oof_proba.iloc[val_idx], best_thr),
                    average="macro",
                )
            )
        )

    preds_final = decision.predict_labels(oof_proba, best_thr)
    f1_macro = float(f1_score(y, preds_final, average="macro"))
    recall_neg = float(recall_score(y, preds_final, pos_label=0))
    precision_neg = float(precision_score(y, preds_final, pos_label=0))
    auc_neg = float(roc_auc_score((y == 0).astype(int), oof_proba))

    mean_train_s = float(sum(durees_entrainement) / len(durees_entrainement))
    latence_ms = (
        _mesurer_latence(dernier_pipeline, dernier_X_val)
        if dernier_pipeline is not None and dernier_X_val is not None
        else float("nan")
    )

    return {
        "nom": candidat.nom,
        "f1_macro": f1_macro,
        "seuil": float(best_thr),
        "auc": auc_neg,
        "recall_negatif": recall_neg,
        "precision_negatif": precision_neg,
        "entrainement_par_pli_s": mean_train_s,
        "latence_1000_ms": latence_ms,
        "famille": candidat.famille,
        "explication_exacte": candidat.explication_exacte,
        "f1_par_pli": f1_par_pli,
    }


# --------------------------------------------------------------------------- #
# Rapport Markdown
# --------------------------------------------------------------------------- #
def _ligne_tableau(r: dict) -> str:
    """Formate une ligne du tableau de comparaison.

    Pourquoi : centraliser le formatage pour garantir la cohérence des
    arrondis et des séparateurs.
    """
    explication = "oui" if r["explication_exacte"] else "non"
    return (
        f"| {r['nom']} | {r['f1_macro']:.4f} | {r['seuil']:.3f} | {r['auc']:.4f} | "
        f"{r['recall_negatif']:.4f} | {r['precision_negatif']:.4f} | "
        f"{r['entrainement_par_pli_s']:.2f} | {r['latence_1000_ms']:.2f} | "
        f"{r['famille']} | {explication} |"
    )


def _generer_rapport(
    resultats: List[dict],
    date_utc: str,
    commit: str,
    n_natural: int,
    n_boost: int,
    part_negative: float,
) -> str:
    """Génère le rapport Markdown complet.

    Pourquoi : produire une trace vérifiable qui ne contient que des
    constats calculés à partir des mesures.

    Args:
        resultats: Résultats triés par F1 macro décroissant.
        date_utc: Horodatage ISO 8601 en UTC.
        commit: Identifiant de commit (ou "inconnu").
        n_natural: Nombre d'avis naturels.
        n_boost: Nombre d'avis complémentaires.
        part_negative: Part d'avis négatifs parmi les naturels.

    Returns:
        Contenu du rapport Markdown.
    """
    témoin = next(r for r in resultats if r["nom"] == "logreg_caracteres")
    meilleur = resultats[0]

    lines = [
        "# Banc de comparaison des familles de modèles",
        "",
        f"*Date :* {date_utc}",
        f"*Commit :* {commit}",
        "",
        "## Données",
        "",
        f"- Avis naturels : {n_natural}",
        f"- Avis complémentaires : {n_boost}",
        f"- Part d'avis négatifs : {part_negative:.4f}",
        "",
        "## Protocole",
        "",
        "1. Données : avis `sample_source == SAMPLE_NATURAL` pour X et y ; autres avis pour `boost_df`, ajoutés à l'entraînement de chaque pli uniquement.",
        "2. Validation croisée stratifiée à 5 plis, même graine et mêmes plis pour tous les candidats.",
        "3. Probabilités négatives hors pli via `decision.negative_proba`.",
        "4. Seuil optimal dans `config.THRESHOLD_GRID` maximisant le F1 macro hors pli ; métriques au seuil retenu.",
        "5. Durée moyenne d'entraînement par pli et latence de prédiction pour 1 000 avis (dernier pli).",
        "",
        "## Tableau comparatif",
        "",
        "| Candidat | F1 macro hors plis | Seuil | AUC | Rappel négatifs | Précision négatifs | Entraînement par pli (s) | Latence 1 000 avis (ms) | Famille | Explication exacte |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for r in resultats:
        lines.append(_ligne_tableau(r))

    ecart = meilleur["f1_macro"] - témoin["f1_macro"]
    std_temoin = float(np.std(témoin["f1_par_pli"], ddof=0))
    ecart_inferieur_std = abs(ecart) < std_temoin

    lines.extend(
        [
            "",
            "## Lecture",
            "",
            f"Le meilleur candidat est **{meilleur['nom']}** avec un F1 macro hors plis de {meilleur['f1_macro']:.4f}.",
            f"Écart au modèle en service (logreg_caracteres, F1 = {témoin['f1_macro']:.4f}) : {ecart:+.4f}.",
        ]
    )

    if ecart_inferieur_std:
        lines.append(
            "Cet écart est inférieur à l'erreur type des plis du modèle en service "
            f"({std_temoin:.4f}) ; il n'est pas interprétable comme un gain significatif."
        )
    else:
        lines.append(
            "Cet écart atteint ou dépasse l'erreur type des plis du modèle en service "
            f"({std_temoin:.4f})."
        )

    if témoin["nom"] != meilleur["nom"]:
        lines.append(
            f"Le modèle en service n'est pas le meilleur candidat mesuré ici ; "
            f"**{meilleur['nom']}** le devance."
        )
    else:
        lines.append("Le modèle en service reste le meilleur candidat mesuré ici.")

    # Avertissement si le témoin s'écarte de la valeur attendue
    if abs(témoin["f1_macro"] - 0.80) > 0.03:
        lines.extend(
            [
                "",
                "## Attention",
                "",
                f"Le modèle en service (logreg_caracteres) affiche un F1 macro hors plis de {témoin['f1_macro']:.4f}, "
                "soit un écart supérieur à 0,03 par rapport à 0,80. Le banc ne reproduit pas le protocole attendu."
            ]
        )

    lines.extend(
        [
            "",
            "## Ce que ce banc ne mesure pas",
            "",
            "Aucun modèle de type transformeur ni plongement de phrases n'est évalué. "
            "Il faudrait télécharger un modèle de plusieurs centaines de Mo, et l'image du projet ne l'embarque pas. "
            "C'est le candidat suivant si un meilleur score devenait nécessaire.",
        ]
    )

    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def main() -> int:
    """Point d'entrée du banc de comparaison des familles de modèles.

    Pourquoi : fournir une CLI autonome, hors DAG, pour comparer les
    familles de modèles sur le protocole du projet.

    Returns:
        0 en cas de succès, 1 si le fichier de données est introuvable.
    """
    parser = argparse.ArgumentParser(
        description="Banc de comparaison de familles de modèles pour ReviewPulse."
    )
    parser.add_argument(
        "--sortie",
        type=Path,
        default=Path("docs/evidence/comparaison_modeles.md"),
        help="Chemin du rapport Markdown de sortie (défaut : docs/evidence/comparaison_modeles.md).",
    )
    parser.add_argument(
        "--plis",
        type=int,
        default=5,
        help="Nombre de plis de validation croisée (défaut : 5).",
    )
    parser.add_argument(
        "--seulement",
        nargs="+",
        default=None,
        help="Noms des candidats à évaluer (défaut : tous).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if not config.CLEAN_FILE.exists():
        logger.error("Fichier de données nettoyées introuvable : %s", config.CLEAN_FILE)
        return 1

    df = pd.read_parquet(config.CLEAN_FILE)
    logger.info("Données lues depuis %s : %d lignes", config.CLEAN_FILE, len(df))

    # Garantir la présence de la colonne sample_source
    # Pourquoi : les anciennes versions de la zone propre peuvent ne pas
    # porter cette colonne ; on la remplit sans changer le flux naturel.
    if "sample_source" not in df.columns:
        df["sample_source"] = config.SAMPLE_NATURAL

    natural_df = df[df["sample_source"] == config.SAMPLE_NATURAL]
    boost_df = df[df["sample_source"] == config.SAMPLE_NEGATIVE_BOOST]

    X = natural_df["review_text"].astype("string")
    y = natural_df["label"]

    n_natural = int(len(X))
    n_boost = int(len(boost_df))
    part_negative = float((y == 0).mean())

    logger.info(
        "Banc lancé sur %d avis naturels et %d avis complémentaires, %d plis",
        n_natural,
        n_boost,
        args.plis,
    )

    # Calcul unique des plis pour tous les candidats
    # Pourquoi : la comparaison n'est honnête que si chaque candidat voit les
    # mêmes indices d'entraînement et de validation.
    skf = StratifiedKFold(
        n_splits=args.plis, shuffle=True, random_state=config.RANDOM_STATE
    )
    plis = list(skf.split(X, y))

    tous_les_candidats = candidats()
    noms_autorises = set(args.seulement) if args.seulement else None

    resultats: List[dict] = []
    for candidat in tous_les_candidats:
        if candidat.nom == "xgboost" and xgboost is None:
            logger.info(
                "Candidat %s non évalué : paquet xgboost absent de l'environnement",
                candidat.nom,
            )
            resultats.append(
                {
                    "nom": candidat.nom,
                    "f1_macro": float("nan"),
                    "seuil": float("nan"),
                    "auc": float("nan"),
                    "recall_negatif": float("nan"),
                    "precision_negatif": float("nan"),
                    "entrainement_par_pli_s": float("nan"),
                    "latence_1000_ms": float("nan"),
                    "famille": candidat.famille,
                    "explication_exacte": candidat.explication_exacte,
                    "f1_par_pli": [],
                    "absent": True,
                }
            )
            continue

        if noms_autorises is not None and candidat.nom not in noms_autorises:
            continue

        logger.info("Évaluation du candidat %s", candidat.nom)
        res = _evaluer_candidat(candidat, X, y, boost_df, plis)
        res["absent"] = False
        resultats.append(res)
        logger.info(
            "Candidat %s : f1_macro=%.4f, seuil=%.3f, auc=%.4f, "
            "rappel_neg=%.4f, precision_neg=%.4f, train_pli=%.2fs, latence=%.2fms",
            res["nom"],
            res["f1_macro"],
            res["seuil"],
            res["auc"],
            res["recall_negatif"],
            res["precision_negatif"],
            res["entrainement_par_pli_s"],
            res["latence_1000_ms"],
        )

    # Tri décroissant par F1 macro ; les candidats non mesurés restent en fin
    # de tableau grâce à la valeur NaN.
    resultats.sort(key=lambda d: d["f1_macro"], reverse=True)

    date_utc = datetime.now(timezone.utc).isoformat()
    commit = os.getenv("REVIEWPULSE_COMMIT", "inconnu")
    markdown = _generer_rapport(
        resultats, date_utc, commit, n_natural, n_boost, part_negative
    )

    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    # Pourquoi : écriture en octets avec fins de ligne LF pour un rendu
    # identique quel que soit l'OS.
    args.sortie.write_bytes(markdown.encode("utf-8"))
    logger.info("Rapport écrit dans %s", args.sortie)

    # Affichage d'un résumé d'une ligne par candidat
    for r in resultats:
        if r.get("absent"):
            print(f"{r['nom']} | non mesuré : paquet absent de l'environnement")
        else:
            print(
                f"{r['nom']} | F1={r['f1_macro']:.4f} | seuil={r['seuil']:.3f} | "
                f"AUC={r['auc']:.4f} | famille={r['famille']}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
