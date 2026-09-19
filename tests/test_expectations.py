"""tests/test_expectations.py
Rôle
    Vérifie le comportement de la suite Great Expectations définie dans
    ``reviewpulse.expectations``.
Place dans la chaîne
    Après la transformation des données (module ``transform``) et avant le
    scoring. Les tests garantissent que les attentes déclaratives détectent
    correctement les écarts de qualité.
Fonctionnement
    * Le cadre de test utilise les fixtures partagées ``data_env`` et
      ``labelled_frame`` définies dans ``tests/conftest.py``.
    * Chaque scénario négatif travaille sur une copie de ``labelled_frame``,
      introduit une anomalie ciblée, puis appelle ``expectations.validate``.
    * Le scénario positif s’assure que le DataFrame de référence passe
      toutes les attentes.
    * ``build_data_docs`` doit créer un répertoire contenant le fichier
      ``index.html``.
Choix de conception
    * Aucun import inutile – seules les dépendances nécessaires sont importées.
    * Les assertions utilisent les messages d’erreur pour faciliter le
      débogage en cas d’échec.
    * Les attentes attendues sont comparées aux valeurs du champ
      ``expectation`` retournées par ``validate``.
Tests associés
    * ``test_expectations_positive`` – cas de succès complet.
    * ``test_expectations_duplicate_review_id`` – doublon de ``review_id``.
    * ``test_expectations_author_pseudo_regex`` – pseudo de longueur invalide.
    * ``test_expectations_missing_text_len`` – colonne obligatoire manquante.
    * ``test_expectations_weighted_vote_score_range`` – valeur hors limites.
    * ``test_build_data_docs`` – génération du rapport HTML.
"""

from reviewpulse import expectations


def test_expectations_positive(labelled_frame, data_env):
    """Le DataFrame de référence doit satisfaire toutes les attentes."""
    result = expectations.validate(labelled_frame)
    assert result["success"], f"Échec inattendu : {result.get('failed')}"
    assert not result.get("failed"), "Des attentes ont échoué dans le cas positif"


def test_expectations_duplicate_review_id(labelled_frame, data_env):
    """Un doublon de ``review_id`` doit déclencher l'attente d'unicité."""
    df = labelled_frame.copy()
    # Dupliquer l'identifiant du deuxième enregistrement dans le premier
    df.iloc[0, df.columns.get_loc("review_id")] = df.iloc[1]["review_id"]
    result = expectations.validate(df)
    assert not result["success"], "L'attente d'unicité n'a pas échoué"
    failed_expectations = [f["expectation"] for f in result["failed"]]
    assert "expect_column_values_to_be_unique" in failed_expectations


def test_expectations_author_pseudo_regex(labelled_frame, data_env):
    """Un ``author_pseudo`` de longueur incorrecte doit déclencher le regex."""
    df = labelled_frame.copy()
    df.at[0, "author_pseudo"] = "a" * 10  # 10 caractères au lieu de 64
    result = expectations.validate(df)
    assert not result["success"], "L'attente de regex n'a pas échoué"
    failed_expectations = [f["expectation"] for f in result["failed"]]
    assert "expect_column_values_to_match_regex" in failed_expectations


def test_expectations_missing_text_len(labelled_frame, data_env):
    """L'absence de la colonne ``text_len`` doit déclencher l'attente de structure."""
    df = labelled_frame.drop(columns=["text_len"])
    result = expectations.validate(df)
    assert not result["success"], "L'attente de correspondance de colonnes n'a pas échoué"
    failed_expectations = [f["expectation"] for f in result["failed"]]
    assert "expect_table_columns_to_match_ordered_list" in failed_expectations


def test_expectations_weighted_vote_score_range(labelled_frame, data_env):
    """Une valeur ``weighted_vote_score`` hors de l'intervalle [0, 1] doit échouer."""
    df = labelled_frame.copy()
    df.at[0, "weighted_vote_score"] = 2.0  # valeur invalide
    result = expectations.validate(df)
    assert not result["success"], "L'attente de bornes n'a pas échoué"
    failed_expectations = [f["expectation"] for f in result["failed"]]
    assert "expect_column_values_to_be_between" in failed_expectations


def test_build_data_docs(labelled_frame, data_env, tmp_path):
    """La génération des Data Docs doit créer un fichier ``index.html``."""
    project_dir = tmp_path / "gx"
    index_path = expectations.build_data_docs(labelled_frame, project_dir=project_dir)
    assert index_path.is_file(), "Le fichier index.html n'existe pas"
    assert index_path.name == "index.html", "Le fichier attendu doit s'appeler index.html"


def test_main_rend_zero_sur_une_zone_propre_conforme(labelled_frame, data_env):
    """Le main doit rendre 0 quand la zone propre est conforme."""
    from reviewpulse import config
    # S'assurer que le répertoire parent existe
    config.CLEAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Écriture du DataFrame de référence
    labelled_frame.to_parquet(config.CLEAN_FILE)
    # Exécution du point d'entrée
    result = expectations.main()
    assert result == 0, f"Le code de sortie attendu était 0, obtenu {result}"


def test_main_rend_un_sur_une_zone_propre_non_conforme(labelled_frame, data_env):
    """Le main doit rendre 1 quand la zone propre ne satisfait pas les attentes."""
    from reviewpulse import config
    # Copie et corruption du DataFrame
    df_invalid = labelled_frame.copy()
    df_invalid.at[0, "author_pseudo"] = "a" * 10  # longueur invalide
    # S'assurer que le répertoire parent existe
    config.CLEAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Écriture du DataFrame corrompu
    df_invalid.to_parquet(config.CLEAN_FILE)
    # Exécution du point d'entrée
    result = expectations.main()
    assert result == 1, f"Le code de sortie attendu était 1, obtenu {result}"
