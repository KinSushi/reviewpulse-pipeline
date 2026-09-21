# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""reviewpulse.quality
=====================

Rôle
----
Dire si la zone propre est utilisable ; lever une erreur sinon.

Place dans la chaîne
-------------------
* **Après** : appelé par :pymod:`reviewpulse.transform.main` (et par le script CLI) immédiatement après la transformation, avant l’écriture du parquet.
* **Avant** : aucune étape suivante du pipeline n’est exécutée tant que la fonction ``assert_quality`` n’a pas validé le DataFrame ; en cas d’échec le DAG Airflow s’arrête avec un code de sortie non‑nul.

Fonctionnement
--------------
1. ``_column_type_mismatch`` compare les colonnes et leurs types avec ``config.CLEAN_COLUMNS`` ; toute différence produit une erreur et interrompt les vérifications suivantes.
2. ``check_clean`` exécute successivement :
   - vérification d’ordre et de type,
   - présence d’au moins une ligne,
   - unicité et non‑nullité de ``review_id``,
   - valeurs de ``label`` limitées à {0, 1},
   - appartenance de ``language`` à ``config.LANGUAGES``,
   - appartenance de ``sample_source`` à ``config.SAMPLE_SOURCES``,
   - ``text_len`` ≥ 1,
   - absence des colonnes listées dans ``config.FORBIDDEN_CLEAN_COLUMNS``,
   - format hexadécimal 64 caractères de ``author_pseudo``,
   - part de négatifs calculée uniquement sur les lignes où ``sample_source == config.SAMPLE_NATURAL`` et comprise entre 0,5 % et 95 %.
   Les messages d’erreur sont agrégés dans une liste.
3. ``assert_quality`` appelle ``check_clean`` et lève ``DataQualityError`` contenant tous les messages si la liste n’est pas vide.
4. ``main`` lit ``config.CLEAN_FILE``, invoque ``assert_quality`` et renvoie 0 en cas de succès, 1 sinon.

Choix de conception
-------------------
* Retourner une liste d’erreurs plutôt que d’interrompre au premier problème, pour fournir un diagnostic complet (ADR 0005).
* Calculer la part de négatifs uniquement sur le flux « natural » conformément à la spécification v2 (ADR 0005 et 0007).
* Le script expose un ``main() -> int`` compatible avec la convention du projet (voir SPEC_CODE.md).

Preuves
-------
* Les contrôles sont couverts par les tests ``test_transform_quality.py`` et ``test_boost.py`` (ADR 0005).

Tests associés
--------------
* ``test_transform_quality.py`` – couvre toutes les vérifications de ``check_clean``.
* ``test_boost.py`` – confirme la prise en compte du champ ``sample_source``.
* ``test_fresh_dirs.py`` – vérifie que le répertoire de sortie est créé avant l’appel à ``main``.
* ``test_artifacts_location.py`` – s’assure que le module ne dépend pas d’un chemin codé en dur.

Quoi
----
Module de validation du DataFrame de la zone propre, bloquant en cas d’échec.

Pourquoi
--------
Le pipeline ne doit pas entraîner ni scorer sur des données corrompues, incomplètes ou mal typées. Cette porte centralise les règles de qualité afin que l’échec soit explicite et complet avant toute consommation aval.

Où
---
* Appelé par :pymod:`reviewpulse.transform.main` et par le script CLI.
* Lit ``config.CLEAN_FILE`` dans :func:`main`.
* *N’écrit aucun fichier ; renvoie un code de sortie et consigne les erreurs dans les logs.*

Limites connues
---------------
* Ne répare pas les données : il signale seulement les écarts.
* Ne valide pas le contenu sémantique du texte (langue réelle, sens de l’avis).
* La part de négatifs est calculée uniquement sur le flux naturel ; un déséquilibre dans le flux complémentaire n’est pas détecté ici.
"""

import logging
import re
from pathlib import Path

import pandas as pd

from reviewpulse import config

# Pourquoi : centraliser les logs du module pour faciliter le suivi et le filtrage.
logger = logging.getLogger(__name__)


class DataQualityError(Exception):
    """Exception levée lorsqu'une ou plusieurs vérifications de qualité échouent.

    Pourquoi :
        Centraliser les échecs de validation sous une même classe permet aux
        appelants (ex. :func:`assert_quality`, le CLI) de distinguer les
        problèmes de données des autres types d’erreurs (IO, logique).
    """


def _column_type_mismatch(df: pd.DataFrame) -> list[str]:
    """Détecte un désalignement entre les colonnes attendues et celles du DataFrame.

    Args:
        df: DataFrame à valider.

    Returns:
        Liste d’erreurs ; vide si les colonnes et leurs types correspondent à
        ``config.CLEAN_COLUMNS``.

    Pourquoi :
        Séparer cette logique simplifie ``check_clean`` et évite de poursuivre
        les contrôles de type lorsqu’un problème d’ordre/colonnes est déjà présent.
    """
    errors = []
    expected_cols = list(config.CLEAN_COLUMNS.keys())
    actual_cols = list(df.columns)

    if actual_cols != expected_cols:
        errors.append(
            f"Colonnes inattendues ou ordre incorrect. Attendu {expected_cols}, trouvé {actual_cols}"
        )
        # Si l'ordre est mauvais, on ne poursuit pas les vérifications de type
        return errors

    for col, expected_type in config.CLEAN_COLUMNS.items():
        actual_type = str(df[col].dtype)
        if actual_type != expected_type:
            errors.append(
                f"Type de colonne '{col}' incorrect : attendu '{expected_type}', trouvé '{actual_type}'"
            )
    return errors


def check_clean(df: pd.DataFrame) -> list[str]:
    """Vérifie la qualité du DataFrame nettoyé.

    Retourne la liste des messages d'erreur ; liste vide si tout est conforme.

    Args:
        df: DataFrame issu de :func:`reviewpulse.transform.clean`.

    Returns:
        list[str]: messages d’erreur accumulés.

    Pourquoi :
        Centraliser toutes les règles de validation afin que le pipeline puisse
        les invoquer en une seule étape et obtenir un rapport complet.
    """
    errors: list[str] = []

    # 1. Colonnes et types
    errors.extend(_column_type_mismatch(df))

    # 2. Au moins une ligne
    if df.shape[0] == 0:
        errors.append("Le DataFrame ne contient aucune ligne")

    # 3. review_id non nul et unique
    if "review_id" in df.columns:
        # Pourquoi : isnull() détecte les valeurs nulles, équivalent à isna().
        if df["review_id"].isnull().any():
            errors.append("review_id contient des valeurs nulles")
        # Pourquoi : is_unique utilise l'index pour vérifier l'unicité en O(n).
        if not df["review_id"].is_unique:
            errors.append("review_id n'est pas unique")

    # 4. label dans {0, 1}
    if "label" in df.columns:
        # Pourquoi : la liste [0, 1] est suffisante pour la lisibilité ; le DataFrame est petit.
        invalid_labels = df[~df["label"].isin([0, 1])]
        if not invalid_labels.empty:
            errors.append("label contient des valeurs hors de {0, 1}")

    # 5. language valide
    if "language" in df.columns:
        # Pourquoi : config.LANGUAGES est une petite liste ; la conversion en set n'apporte pas de gain notable ici.
        invalid_lang = df[~df["language"].isin(config.LANGUAGES)]
        if not invalid_lang.empty:
            errors.append(
                f"language contient des valeurs non autorisées : {invalid_lang['language'].unique().tolist()}"
            )

    # 6. sample_source valide (v2)
    if "sample_source" in df.columns:
        # Pourquoi : config.SAMPLE_SOURCES est petite ; la liste reste lisible.
        invalid_source = df[~df["sample_source"].isin(config.SAMPLE_SOURCES)]
        if not invalid_source.empty:
            errors.append(
                f"sample_source contient des valeurs non autorisées : {invalid_source['sample_source'].unique().tolist()}"
            )
    else:
        errors.append("Colonne 'sample_source' manquante")

    # 7. text_len >= 1
    if "text_len" in df.columns:
        if (df["text_len"] < 1).any():
            errors.append("text_len contient des valeurs < 1")

    # 8. Colonnes interdites
    forbidden = set(config.FORBIDDEN_CLEAN_COLUMNS)
    present_forbidden = forbidden.intersection(df.columns)
    if present_forbidden:
        errors.append(f"Colonnes interdites présentes : {sorted(present_forbidden)}")

    # 9. author_pseudo format hex 64 caractères
    if "author_pseudo" in df.columns:
        # Pourquoi : les pseudos sont générés en hexadécimal minuscule via HMAC‑SHA256.
        pattern = re.compile(r"^[0-9a-f]{64}$")
        invalid_pseudo = df[~df["author_pseudo"].astype(str).str.match(pattern)]
        if not invalid_pseudo.empty:
            errors.append("author_pseudo ne correspond pas au format hexadécimal 64 caractères")

    # 10. Part de négatifs (calculée uniquement sur les avis naturels) (v2)
    if "label" in df.columns and "sample_source" in df.columns:
        natural_df = df[df["sample_source"] == config.SAMPLE_NATURAL]
        # Pourquoi : le calcul de la part de négatifs nécessite au moins un avis naturel.
        if natural_df.empty:
            errors.append("Aucun avis naturel disponible pour le calcul de la part de négatifs")
        else:
            negative_share = (natural_df["label"] == 0).mean()
            # Pourquoi : seuils définis par l'ADR 0007 pour éviter des parts extrêmes.
            if not (0.005 <= negative_share <= 0.95):
                errors.append(
                    f"Part de négatifs hors limites (0,5 %‑95 %) : {negative_share:.2%}"
                )

    return errors


def assert_quality(df: pd.DataFrame) -> None:
    """Lève DataQualityError si le DataFrame ne satisfait pas les contrôles.

    Args:
        df: DataFrame à valider.

    Raises:
        DataQualityError: si au moins une règle de qualité échoue.

    Pourquoi :
        Fournir une fonction unique utilisable tant par le CLI que par le
        pipeline de transformation, garantissant un comportement identique.
    """
    failures = check_clean(df)
    if failures:
        message = "Échecs de qualité des données :\n" + "\n".join(failures)
        raise DataQualityError(message)


def main() -> int:
    """Charge le fichier nettoyé, vérifie la qualité et renvoie le code de sortie.

    Returns:
        int: 0 si le fichier passe toutes les vérifications, 1 sinon.

    Pourquoi :
        Point d’entrée scriptable du module, conforme à la convention du projet
        (``if __name__ == "__main__": raise SystemExit(main())``).
    """
    clean_path: Path = config.CLEAN_FILE
    try:
        df = pd.read_parquet(clean_path)
    except Exception as exc:
        # Le chemin complet peut contenir des informations sensibles ; on ne le journalise qu’en debug.
        logger.debug("Impossible de lire le fichier nettoyé %s : %s", clean_path, exc)
        return 1

    try:
        assert_quality(df)
    except DataQualityError as e:
        # L’échec de qualité est attendu dans le flux normal ; on le consigne en warning.
        logger.warning("Qualité des données non satisfaisante : %s", e)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
