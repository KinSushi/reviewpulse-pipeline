"""dashboard/app.py
Rôle
----
Restitution pour la ou le community manager.

Place dans la chaîne
--------------------
Exécuté après le module `score` (et en même temps que `api`). Ne produit pas de sortie persistante.

Choix de conception
-------------------
* Avis naturels seulement.  
* Aucune information d'auteur affichée.  
* Texte tronqué à 200 caractères.  
* Parts négatives calculées sur les étiquettes (pas sur les probabilités).  
* URL de l'API lue dans la variable d’environnement `REVIEWPULSE_API_URL` (dans Docker, `localhost` désigne le conteneur du tableau de bord).  
* Appel direct à `main()` ; un `SystemExit` bloquerait le moteur de test Streamlit.

Preuves
-------
Défauts observés dans le navigateur le 16/09/2026 et corrigés : affichage erroné de la part réelle (affichée comme part positive) et plantage lié aux dates du résumé.

Tests associés
--------------
`test_dashboard.py` : exécution réelle du script avec `AppTest`.
"""

import os
import requests
import pandas as pd
import streamlit as st
from reviewpulse import config, decision

def _load_scored() -> pd.DataFrame | None:
    """Charge le fichier de scores produit par le module `score.py`.

    Retourne
    -------
    pd.DataFrame | None
        DataFrame contenant les avis annotés et scorés, ou ``None`` si le
        fichier n’est pas encore présent.

    Pourquoi
    -------
    Le tableau de bord doit pouvoir démarrer même si le pipeline n’a pas encore
    produit le parquet ; renvoyer ``None`` permet d’afficher un message d’attente
    sans interrompre l’exécution.
    """
    try:
        return pd.read_parquet(config.SCORED_FILE)
    except FileNotFoundError:
        return None

def _load_summary() -> pd.DataFrame | None:
    """Charge le résumé quotidien produit par le module `score.py`.

    Retourne
    -------
    pd.DataFrame | None
        DataFrame agrégé par jour, jeu et langue, ou ``None`` si le fichier
        n’est pas encore présent.

    Pourquoi
    -------
    Le même raisonnement que pour ``_load_scored`` : le tableau de bord doit
    rester fonctionnel pendant la génération des artefacts.
    """
    try:
        return pd.read_parquet(config.SUMMARY_FILE)
    except FileNotFoundError:
        return None

def _format_date(dt: pd.Timestamp) -> str:
    """Convertit un timestamp en date ISO (UTC).

    Parameters
    ----------
    dt : pd.Timestamp
        Timestamp issu de la colonne ``created_at`` du DataFrame.

    Returns
    -------
    str
        Date au format ``YYYY‑MM‑DD`` en UTC.

    Pourquoi
    -------
    Le tableau de bord affiche uniquement la date, pas l’heure, afin de
    simplifier la lecture et d’uniformiser le format avec le résumé quotidien.
    """
    return dt.tz_convert("UTC").date().isoformat()

def _truncate(text: str, length: int = 200) -> str:
    """Tronque le texte à *length* caractères en ajoutant une ellipse si besoin.

    Parameters
    ----------
    text : str
        Texte complet de l’avis.
    length : int, optional
        Longueur maximale souhaitée (défaut : 200).

    Returns
    -------
    str
        Texte tronqué ou identique si sa longueur est inférieure à *length*.

    Pourquoi
    -------
    Limite l’exposition de données personnelles tout en conservant une
    indication du contenu de l’avis.
    """
    return (text[:length] + "…") if len(text) > length else text

def main() -> int:
    """Point d’entrée du tableau de bord Streamlit.

    Retourne
    -------
    int
        Code de sortie : toujours ``0`` (compatible avec la convention
        ``if __name__ == "__main__": raise SystemExit(main())``).

    Pourquoi
    -------
    Centralise toutes les étapes d’affichage afin de respecter le contrat
    d’un module exécutable exposant ``main() -> int``.
    """
    # Configuration de la page Streamlit
    st.set_page_config(page_title="ReviewPulse")
    st.title("Tableau de bord ReviewPulse")

    # Chargement paresseux des artefacts
    scored_df = _load_scored()
    summary_df = _load_summary()

    # Si l’un des fichiers n’est pas encore disponible, on informe l’utilisateur
    if scored_df is None or summary_df is None:
        st.warning(
            "Les fichiers de données ne sont pas encore disponibles. "
            "Veuillez attendre que le pipeline d’ingestion et de scoring ait terminé son exécution."
        )
        return 0

    # Filtre sur les avis « natural » uniquement (convention du projet)
    natural_mask = scored_df["sample_source"] == config.SAMPLE_NATURAL

    # Interface de sélection des filtres
    with st.sidebar:
        st.header("Filtres")
        # Liste des jeux disponibles dans le sous‑ensemble naturel
        app_ids = sorted(scored_df.loc[natural_mask, "app_id"].unique())
        selected_app = st.selectbox("Jeu (app_id)", app_ids, index=0)
        # Liste des langues disponibles dans le sous‑ensemble naturel
        languages = sorted(scored_df.loc[natural_mask, "language"].unique())
        selected_lang = st.selectbox("Langue", languages, index=0)

    # Sous‑ensemble filtré selon les sélections
    filt = (
        natural_mask
        & (scored_df["app_id"] == selected_app)
        & (scored_df["language"] == selected_lang)
    )
    df_view = scored_df.loc[filt].copy()

    # ------------------------------------------------------------------
    # Calcul des indicateurs
    # ------------------------------------------------------------------
    total_reviews = int(df_view.shape[0])

    # Part négative prédite : proportion de prédictions égales à LABEL_NEGATIVE
    pred_negative_share = (
        (df_view["pred_label"] == decision.LABEL_NEGATIVE).mean()
        if not df_view.empty
        else 0.0
    )

    # Part négative réelle : proportion d'étiquettes réelles égales à LABEL_NEGATIVE
    real_negative_share = (
        (df_view["label"] == decision.LABEL_NEGATIVE).mean()
        if not df_view.empty
        else 0.0
    )

    # Version du modèle (exemple : « v1.2.3 » ou « N/A » si aucun avis)
    model_version = str(df_view["model_version"].iloc[0]) if not df_view.empty else "N/A"

    # Seuil de décision utilisé pour la prédiction
    decision_threshold = (
        float(df_view["decision_threshold"].iloc[0])
        if not df_view.empty and "decision_threshold" in df_view.columns
        else config.DEFAULT_DECISION_THRESHOLD
    )

    # Affichage des indicateurs sous forme de métriques
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Nombre d’avis", f"{total_reviews:,}")
    col2.metric("Part négative prédite", f"{pred_negative_share:.2%}")
    col3.metric("Part négative réelle", f"{real_negative_share:.2%}")
    col4.metric("Version du modèle", model_version)
    col5.metric("Seuil de décision", f"{decision_threshold:.3f}")

    # ------------------------------------------------------------------
    # Courbe quotidienne des parts négatives (prédite et réelle)
    # ------------------------------------------------------------------
    if not df_view.empty:
        # Le résumé quotidien contient déjà les agrégations par jour.
        summary_mask = (
            (summary_df["app_id"] == selected_app)
            & (summary_df["language"] == selected_lang)
        )
        daily_summary = summary_df.loc[summary_mask].copy()

        if not daily_summary.empty:
            # S’assure que la colonne date est bien de type datetime.date.
            if not pd.api.types.is_datetime64_any_dtype(daily_summary["date"]):
                daily_summary["date"] = pd.to_datetime(daily_summary["date"]).dt.date
            else:
                daily_summary["date"] = daily_summary["date"].dt.date

            # Sélection des colonnes d’intérêt et tri chronologique
            daily = daily_summary.sort_values("date")[
                ["date", "share_negative_pred", "share_negative_true"]
            ].set_index("date")
            daily.rename(
                columns={
                    "share_negative_pred": "Part négative prédite",
                    "share_negative_true": "Part négative réelle",
                },
                inplace=True,
            )
            st.subheader("Évolution quotidienne de la part négative")
            st.line_chart(daily)

    # ------------------------------------------------------------------
    # Tableau des 20 avis les plus probablement négatifs
    # ------------------------------------------------------------------
    st.subheader("Top 20 des avis les plus probablement négatifs")
    top20 = (
        df_view.sort_values("proba_negative", ascending=False)
        .head(20)
        .copy()
    )
    top20["date"] = top20["created_at"].apply(_format_date)
    top20["texte"] = top20["review_text"].apply(_truncate)
    display_cols = ["date", "language", "proba_negative", "texte"]
    st.dataframe(top20[display_cols].reset_index(drop=True))

    # ------------------------------------------------------------------
    # Zone de test d’un avis via l’API /predict
    # ------------------------------------------------------------------
    st.subheader("Tester un avis")
    # Utilise la variable d’environnement REVIEWPULSE_API_URL si définie,
    # sinon le fallback « http://localhost:8000 » (dans Docker, localhost
    # désigne le conteneur du tableau de bord).
    api_url = st.text_input(
        "URL de l’API ReviewPulse",
        value=os.getenv('REVIEWPULSE_API_URL', 'http://localhost:8000'),
        help="Point d’entrée du service FastAPI /predict",
    )
    user_text = st.text_area(
        "Texte de l’avis à tester",
        placeholder="Entrez le texte d’un avis ici…",
        height=150,
    )
    if st.button("Envoyer pour prédiction"):
        if not user_text.strip():
            st.error("Le texte de l’avis ne peut pas être vide.")
        else:
            try:
                resp = requests.post(
                    f"{api_url.rstrip('/')}/predict",
                    json={"texts": [user_text]},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                pred = data["predictions"][0]
                label = "negative" if pred["label"] == "negative" else "positive"
                # Affiche le seuil renvoyé par l’API en plus de la probabilité.
                threshold = data.get('decision_threshold')
                st.success(
                    f"Prédiction : {label} (probabilité négative = {pred['proba_negative']:.2%}, seuil = {threshold})"
                )
            except Exception as e:
                st.error(f"Erreur lors de l’appel à l’API : {e}")

    return 0

# Streamlit exécute le script comme __main__ ; un SystemExit bloque le moteur de test AppTest (délai dépassé mesuré le 16/09/2026) et n'a pas de sens dans une application Streamlit.
main()
