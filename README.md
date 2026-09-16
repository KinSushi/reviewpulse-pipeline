# ReviewPulse

**Un pipeline de données qui alimente un modèle d'IA** — Final Project de la formation Data Lead (Jedha, cohorte dal-ft-18), Demo Day du 25 septembre 2026.

Chaque jour, ReviewPulse collecte les avis Steam de plusieurs jeux, les dépose bruts dans un lac de données, les nettoie et les pseudonymise, puis un modèle de sentiment suivi dans MLflow repère les avis négatifs à lire en priorité. Une API et un tableau de bord restituent le résultat à l'équipe community & live-ops.

![Architecture](docs/diagrams/png/01_architecture_globale.png)

## Résultats mesurés le 16/09/2026 (données réelles, stack Docker déployée)

| Mesure | Valeur |
|---|---|
| Avis naturels collectés | 6 000 (3 jeux × anglais et français) ; **0 nouvel avis** au passage suivant (idempotence) |
| Avis négatifs complémentaires (entraînement seulement) | 2 797 bruts → 2 254 après dédoublonnage |
| Part d'avis négatifs (distribution naturelle) | 9 % |
| **F1 macro, test 100 % naturel tenu à l'écart** | **0,807** (barrière de promotion 0,75) |
| F1 macro hors-plis (validation croisée 5 plis) | 0,802 |
| AUC classe négative | 0,948 |
| Rappel / précision des négatifs | 0,639 / 0,657 |
| Seuil de décision (choisi par validation croisée) | 0,75 |
| Cohérence métier : part négative prédite ÷ réelle, par jeu et langue | 0,79 à 1,21 |
| Tests automatisés | 45 réussis, lint propre |
| Tests en conditions réelles | API, tableau de bord (navigateur), MLflow, DAG Airflow quotidien et hebdomadaire : tous réussis |

*Avant l'ajout des avis négatifs complémentaires, le même test donnait F1 0,750 et AUC 0,896 ; le détail de la décision est dans la charte et le contrat de code.*

## Démarrer

```bash
cp .env.example .env        # puis définir REVIEWPULSE_SALT
make install                # Python 3.11
make pipeline               # ingest → transform → train → score
make api                    # http://localhost:8000/docs
make dashboard              # http://localhost:8501
```

Ou tout en conteneurs :

```bash
make up                     # MLflow :5000, API :8000, tableau de bord :8501
make jobs                   # une exécution complète de la chaîne
make airflow                # Airflow :8080, DAG reviewpulse_daily
```

## La chaîne

| Étape | Module | Ce qu'il garantit |
|---|---|---|
| Ingestion | `src/reviewpulse/ingest.py` | objets reçus écrits **inchangés** ; idempotence par manifeste ; reprise sur 429 et 5xx |
| Transformation | `src/reviewpulse/transform.py` | dédoublonnage, nettoyage, types, **pseudonymisation HMAC**, rétention 30 jours |
| Qualité | `src/reviewpulse/quality.py` | 9 contrôles **bloquants** avant la zone propre |
| Modèle | `src/reviewpulse/train.py` | TF-IDF caractères + régression logistique, MLflow, promotion automatique si F1 macro ≥ 0,75 |
| Score | `src/reviewpulse/score.py` | prédictions et résumé quotidien, version du modèle tracée |
| API | `src/reviewpulse/api.py` | `/health`, `/predict`, `/insights` ; 503 si modèle indisponible |
| Tableau de bord | `dashboard/app.py` | aucune information d'auteur affichée |
| Orchestration | `dags/reviewpulse_daily.py`, `.github/workflows/` | exécution quotidienne, réentraînement hebdomadaire, CI |

## Documentation

| Document | Contenu |
|---|---|
| [`docs/01_charte.md`](docs/01_charte.md) | Charte d'une page : utilisateur, décision, données personnelles, hors périmètre |
| [`docs/02_architecture.md`](docs/02_architecture.md) | Architecture et justification des choix |
| [`docs/03_matrice_reemploi_blocs.md`](docs/03_matrice_reemploi_blocs.md) | Ce que le projet apporte à chaque bloc CDSD et AIA |
| [`docs/04_plan_jusqu_au_demo_day.md`](docs/04_plan_jusqu_au_demo_day.md) | Calendrier et déroulé de la démo |
| [`docs/05_conformite_demo_day.md`](docs/05_conformite_demo_day.md) | Grille de conformité aux consignes |
| [`docs/SPEC_CODE.md`](docs/SPEC_CODE.md) | Contrat de code |
| [`docs/diagrams/`](docs/diagrams/) | Dix schémas (sources Mermaid, SVG, PNG) |

## Données et conformité

Source : API publique des avis Steam. Les identifiants de joueurs sont pseudonymisés dès la zone propre et les identifiants directs supprimés ; le sel est un secret obligatoire, sans valeur par défaut. Détail dans la charte et le schéma [07](docs/diagrams/png/07_gouvernance_donnees_personnelles.png).
