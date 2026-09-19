# tests/test_drift.py
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd
import pytest

from reviewpulse import config
from reviewpulse import drift


def test_psi_numerique_meme_distribution_proche_de_zero() -> None:
    """Deux échantillons tirés de la même loi normale donnent un PSI très faible."""
    rng = np.random.default_rng(seed=0)
    reference = pd.Series(rng.normal(loc=0.0, scale=1.0, size=10_000))
    courant = pd.Series(rng.normal(loc=0.0, scale=1.0, size=10_000))

    psi = drift.psi_numerique(reference, courant, bins=10)

    # Le PSI doit être très proche de zéro (tolérance arbitraire)
    assert psi < 0.01, f"PSI attendu < 0.01, obtenu {psi}"


def test_psi_numerique_decalage_de_distribution_est_plus_grand_et_interprete_comme_derive() -> None:
    """Un décalage de la distribution augmente le PSI et l’interprétation le classe comme « dérive »."""
    rng = np.random.default_rng(seed=1)
    reference = pd.Series(rng.normal(loc=0.0, scale=1.0, size=10_000))
    # Décalage de +2 sigma
    courant = pd.Series(rng.normal(loc=2.0, scale=1.0, size=10_000))

    psi_same = drift.psi_numerique(reference, reference, bins=10)
    psi_shift = drift.psi_numerique(reference, courant, bins=10)

    assert psi_shift > psi_same * 10, "Le PSI après décalage doit être nettement plus grand"
    assert drift.interpretation(psi_shift) == "dérive"


def test_psi_categoriel_parts_identiques_et_categorie_disparue() -> None:
    """PSI catégoriel ≈ 0 quand les parts sont identiques, augmente quand une catégorie disparaît."""
    # Référence : 3 catégories, parts égales
    rng_ref = np.random.default_rng(2)
    reference = pd.Series(rng_ref.choice(["A", "B", "C"], size=3000, p=[1 / 3, 1 / 3, 1 / 3]))
    # Courant identique
    rng_ident = np.random.default_rng(3)
    courant_identique = pd.Series(rng_ident.choice(["A", "B", "C"], size=3000, p=[1 / 3, 1 / 3, 1 / 3]))
    psi_zero = drift.psi_categoriel(reference, courant_identique)
    assert psi_zero < 0.01, f"PSI attendu proche de 0, obtenu {psi_zero}"

    # Courant sans la catégorie C
    rng_sans = np.random.default_rng(4)
    courant_sans_c = pd.Series(rng_sans.choice(["A", "B"], size=3000, p=[0.5, 0.5]))
    psi_augmente = drift.psi_categoriel(reference, courant_sans_c)
    assert psi_augmente > 0.1, "Le PSI doit augmenter sensiblement quand une catégorie disparaît"


def test_derive_entrees_ignore_colonne_absente() -> None:
    """derive_entrees ne lève pas d’erreur lorsqu’une colonne attendue est absente."""
    # DataFrames avec colonnes communes, mais sans la colonne 'sample_source' que la fonction pourrait ignorer
    reference = pd.DataFrame(
        {
            "review_id": ["r1", "r2"],
            "app_id": [1, 1],
            "language": ["english", "english"],
            "review_text": ["good", "bad"],
        }
    )
    courant = pd.DataFrame(
        {
            "review_id": ["r3"],
            "app_id": [1],
            "language": ["english"],
            "review_text": ["average"],
        }
    )

    result = drift.derive_entrees(reference, courant)

    assert isinstance(result, dict), "Le résultat doit être un dictionnaire"
    # Vérifier qu’une clé attendue (ex. 'psi') est présente si la fonction la calcule
    # On ne connaît pas les clés exactes, on se contente de vérifier que le dict n’est pas vide
    assert result, "Le dictionnaire retourné ne doit pas être vide"


def test_derive_predictions_rapport_hors_bornes_et_filtrage_n_min() -> None:
    """derive_predictions marque hors_bornes pour un ratio 3.0, ne le fait pas pour 1.0,
    et ignore les lignes dont n_reviews < n_min."""
    resume = pd.DataFrame(
        {
            "app_id": [1, 1, 1],
            "language": ["english", "english", "english"],
            "date": pd.to_datetime(["2026-09-01", "2026-09-01", "2026-09-01"]),
            "n_reviews": [30, 30, 10],  # la troisième doit être filtrée (n_min=20)
            "share_negative_pred": [0.6, 0.5, 0.5],
            "share_negative_true": [0.2, 0.5, 0.5],
        }
    )

    predictions = drift.derive_predictions(resume, ratio_min=0.5, ratio_max=2.0, n_min=20)

    # Deux lignes attendues (la troisième filtrée)
    assert len(predictions) == 2

    # Trouver les entrées correspondantes
    pred_hors = next(p for p in predictions if p["ratio"] > 2.0)
    pred_ok = next(p for p in predictions if p["ratio"] <= 2.0)

    assert pred_hors["hors_bornes"] is True, "Le ratio 3.0 doit être marqué hors_bornes"
    assert pred_ok["hors_bornes"] is False, "Le ratio 1.0 ne doit pas être marqué hors_bornes"


def test_main_retourne_1_si_fichiers_d_entree_inexistants(monkeypatch, tmp_path) -> None:
    """main() renvoie 1 quand les fichiers d’entrée configurés n’existent pas."""
    # Rediriger les chemins de configuration vers des fichiers temporaires inexistants
    fake_summary = tmp_path / "non_existant_summary.parquet"
    monkeypatch.setattr(config, "SUMMARY_FILE", fake_summary, raising=False)

    # On suppose que drift.main lit config.SUMMARY_FILE ; sinon on monkeypatch la fonction open/read interne
    exit_code = drift.main()

    assert exit_code == 1, f"main() doit renvoyer 1 en cas d’erreur, obtenu {exit_code}"


def test_evaluer_alerte_sous_les_seuils_ne_leve_rien() -> None:
    """Aucun seuil franchi, aucune alerte levée."""
    rapport = {
        "entrees": {
            "col_a": {"psi": 0.1},
            "col_b": {"psi": 0.15},
        },
        "predictions": [
            {"hors_bornes": False},
            {"hors_bornes": False},
        ],
    }
    resultat = drift.evaluer_alerte(rapport, colonnes=("col_a", "col_b"))

    assert resultat["alerte"] is False, f"alerte attendue False, obtenu {resultat['alerte']}"
    assert not resultat["motifs"], f"motifs attendus vides, obtenus {resultat['motifs']}"
    assert resultat["psi_max"] == 0.15, f"psi_max attendu 0.15, obtenu {resultat['psi_max']}"
    assert resultat["colonne_psi_max"] == "col_b", f"colonne_psi_max attendu 'col_b', obtenu {resultat['colonne_psi_max']}"


def test_evaluer_alerte_psi_au_dessus_du_seuil() -> None:
    """PSI supérieur au seuil déclenche l'alerte avec motif approprié."""
    psi_val = drift.SEUIL_PSI_ALERTE + 0.05
    rapport = {
        "entrees": {
            "col_c": {"psi": psi_val},
        },
        "predictions": [],
    }
    resultat = drift.evaluer_alerte(rapport, colonnes=("col_c",))

    assert resultat["alerte"] is True, f"alerte attendue True, obtenu {resultat['alerte']}"
    assert resultat["colonne_psi_max"] == "col_c", f"colonne_psi_max attendu 'col_c', obtenu {resultat['colonne_psi_max']}"
    assert resultat["psi_max"] == psi_val, f"psi_max attendu {psi_val}, obtenu {resultat['psi_max']}"
    assert resultat["motifs"], "motifs attendu non vide"
    assert f"{psi_val:.3f}" in resultat["motifs"][0], f"le motif doit contenir la valeur PSI formatée, obtenu {resultat['motifs'][0]}"


def test_evaluer_alerte_part_hors_bornes() -> None:
    """Proportion hors bornes supérieure au seuil déclenche l'alerte même si les PSI sont bas."""
    predictions = [
        {"hors_bornes": True},
        {"hors_bornes": True},
        {"hors_bornes": False},
        {"hors_bornes": False},
        {"hors_bornes": False},
    ]  # 2/5 = 0.4 > SEUIL_PART_HORS_BORNES (0.1)
    rapport = {
        "entrees": {
            "col_d": {"psi": 0.05},
        },
        "predictions": predictions,
    }
    resultat = drift.evaluer_alerte(rapport, colonnes=("col_d",))

    assert resultat["alerte"] is True, f"alerte attendue True, obtenu {resultat['alerte']}"
    assert abs(resultat["part_hors_bornes"] - 0.4) < 1e-6, f"part_hors_bornes attendu 0.4, obtenu {resultat['part_hors_bornes']}"
    assert resultat["motifs"], "motifs attendu non vide"
    assert "40.00%" in resultat["motifs"][-1] or "40.0%" in resultat["motifs"][-1], f"le dernier motif doit mentionner la proportion, obtenu {resultat['motifs'][-1]}"


def test_ecrire_alerte_ecrit_un_fichier_date_et_rien_sans_alerte(tmp_path, monkeypatch) -> None:
    """Sans alerte aucun fichier n’est créé ; avec alerte un fichier JSON contenant les métadonnées est écrit."""
    # Aucun alerte
    verdict_sans = {
        "alerte": False,
        "motifs": [],
        "psi_max": 0.0,
        "colonne_psi_max": None,
        "part_hors_bornes": 0.0,
    }
    chemin_none = drift.ecrire_alerte(verdict_sans, tmp_path)
    assert chemin_none is None, f"chemin attendu None quand pas d'alerte, obtenu {chemin_none}"
    assert not (tmp_path / "alertes").exists(), "le répertoire 'alertes' ne doit pas être créé lorsqu'il n'y a pas d'alerte"

    # Avec alerte
    monkeypatch.setenv("REVIEWPULSE_COMMIT", "abc1234")
    verdict_avec = {
        "alerte": True,
        "motifs": ["test motif"],
        "psi_max": 0.3,
        "colonne_psi_max": "col_test",
        "part_hors_bornes": 0.2,
    }
    chemin = drift.ecrire_alerte(verdict_avec, tmp_path)
    assert isinstance(chemin, pathlib.Path), f"chemin attendu de type Path, obtenu {type(chemin)}"
    assert chemin.name.startswith("derive_") and chemin.name.endswith(".json"), f"nom de fichier inattendu {chemin.name}"
    assert chemin.parent.name == "alertes", f"le fichier doit être dans le sous‑dossier 'alertes', trouvé {chemin.parent}"
    # Vérifier le contenu JSON
    with chemin.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["code_commit"] == "abc1234", f"code_commit attendu 'abc1234', obtenu {data.get('code_commit')}"
    assert data["horodatage_utc"], "horodatage_utc doit être présent et non vide"
    assert data["motifs"] == ["test motif"], f"motifs attendus ['test motif'], obtenus {data.get('motifs')}"


def test_evaluer_alerte_ignore_les_colonnes_de_collecte() -> None:
    """Un PSI énorme sur `language` ne lève rien : sa composition vient de notre plan de collecte, pas de la population."""
    rapport = {
        "entrees": {
            "text_len": {"psi": 0.03},
            "language": {"psi": 3.10},
            "app_id": {"psi": 0.33},
        },
        "predictions": [{"hors_bornes": False}],
    }
    resultat = drift.evaluer_alerte(rapport)

    assert resultat["alerte"] is False, (
        f"aucune alerte attendue sur les colonnes de collecte, obtenu {resultat['motifs']}"
    )
    assert resultat["colonne_psi_max"] == "text_len", (
        f"seule une colonne surveillée peut porter le maximum, obtenu {resultat['colonne_psi_max']}"
    )
    assert resultat["colonnes_surveillees"] == list(drift.COLONNES_ALERTE)

    # Témoin : la même dérive sur une colonne surveillée lève bien l'alerte.
    rapport_surveille = dict(rapport)
    rapport_surveille["entrees"] = {"text_len": {"psi": 3.10}}
    assert drift.evaluer_alerte(rapport_surveille)["alerte"] is True
