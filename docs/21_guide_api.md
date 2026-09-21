# Guide d’API – ReviewPulse

## À quoi sert cette API
Cette API expose le modèle de classification de texte « champion » afin de :
1. obtenir des prédictions de polarité pour des avis,  
2. expliquer une décision individuelle,  
3. fournir des indicateurs agrégés d’avis, et  
4. vérifier la disponibilité du service.

## Comment la lever
```bash
python -m reviewpulse.api
```
Le serveur démarre par défaut sur **http://0.0.0.0:8000** (hôte configurable via `REVIEWPULSE_API_HOST`, port via `REVIEWPULSE_API_PORT`).  
FastAPI génère automatiquement la documentation interactive accessible à :

- Swagger UI : `http://0.0.0.0:8000/docs`
- ReDoc : `http://0.0.0.0:8000/redoc`

## Points d’accès

### `GET /health`
- **Méthode & chemin** : `GET /health`
- **Entrées** : aucune (le modèle est injecté via la dépendance `get_model`).
- **Sortie** (`HealthResponse`) :
  - `status` : `str` – toujours `"ok"` si le service répond.
  - `model_version` : `str` – identifiant de version du modèle chargé.
  - `decision_threshold` : `float` – seuil de décision (0.5 dans le code).
- **Exemple d’appel**  
  ```bash
  curl -X GET "http://0.0.0.0:8000/health"
  ```
  **Réponse** (200) :
  ```json
  {
    "status": "ok",
    "model_version": "1.2.3",
    "decision_threshold": 0.5
  }
  ```
- **Codes d’erreur**  
  - `503` : « Modèle indisponible » – levé par la dépendance `get_model` si le modèle ne peut pas être chargé.

---

### `POST /predict`
- **Méthode & chemin** : `POST /predict`
- **Entrées** (`PredictRequest`) :
  - `texts` : `List[str]`  
    - Nombre de textes : **1 ≤ len ≤ 100**  
    - Longueur de chaque texte : **1 ≤ len ≤ 5000** caractères  
    - Aucun texte ne doit être vide (validation supplémentaire).
- **Sortie** (`PredictResponse`) :
  - `model_version` : `str`
  - `decision_threshold` : `float`
  - `predictions` : `List[PredictionItem]` où chaque item contient :
    - `text_preview` : `str` – les 80 premiers caractères du texte fourni.
    - `proba_negative` : `float` – probabilité que le texte soit négatif.
    - `label` : `str` – `"negative"` ou `"positive"` selon le seuil.
- **Exemple d’appel**  
  ```bash
  curl -X POST "http://0.0.0.0:8000/predict" \
       -H "Content-Type: application/json" \
       -d '{
             "texts": [
               "Ce jeu est fantastique, je le recommande à tous !",
               "Terrible expérience, le serveur plante constamment."
             ]
           }'
  ```
  **Réponse** (200) :
  ```json
  {
    "model_version": "1.2.3",
    "decision_threshold": 0.5,
    "predictions": [
      {
        "text_preview": "Ce jeu est fantastique, je le recommande à tous !",
        "proba_negative": 0.02,
        "label": "positive"
      },
      {
        "text_preview": "Terrible expérience, le serveur plante constamment.",
        "proba_negative": 0.87,
        "label": "negative"
      }
    ]
  }
  ```
- **Codes d’erreur**  
  - `400` : validation Pydantic (ex. trop de textes, texte trop long, texte vide).  
  - `500` : « Model prediction failed » – levé si le calcul des probabilités échoue.  
  - `503` : « Modèle indisponible » – si le modèle ne peut pas être chargé.

---

### `POST /explain`
- **Méthode & chemin** : `POST /explain`
- **Entrées** (`ExplainRequest`) :
  - `text` : `str` – **1 ≤ len ≤ 5000** caractères.  
  - `n` : `int` – nombre maximal de contributions locales : **1 ≤ n ≤ 50**, valeur par défaut = 10.
- **Sortie** (`ExplainResponse`) :
  - `model_version` : `str`
  - `terms` : `List[TermContribution]` où chaque contribution locale contient :
    - `terme` : `str`
    - `contribution` : `float`
  - `global_negative` : `List[TermCoeff]` (10 termes les plus influents pour la classe négative) :
    - `terme` : `str`
    - `coefficient` : `float`
  - `global_positive` : `List[TermCoeff]` (10 termes les plus influents pour la classe positive) :
    - `terme` : `str`
    - `coefficient` : `float`
- **Exemple d’appel**  
  ```bash
  curl -X POST "http://0.0.0.0:8000/explain" \
       -H "Content-Type: application/json" \
       -d '{
             "text": "Le gameplay est moyen mais les graphismes sont superbes.",
             "n": 5
           }'
  ```
  **Réponse** (200) :
  ```json
  {
    "model_version": "1.2.3",
    "terms": [
      {"terme": "graphismes", "contribution": -0.12},
      {"terme": "superbes", "contribution": -0.08},
      {"terme": "moyen", "contribution": 0.05},
      {"terme": "gameplay", "contribution": 0.03},
      {"terme": "mais", "contribution": 0.01}
    ],
    "global_negative": [
      {"terme": "bug", "coefficient": 0.45},
      {"terme": "lag", "coefficient": 0.38}
      /* … 8 autres termes … */
    ],
    "global_positive": [
      {"terme": "excellent", "coefficient": -0.52},
      {"terme": "fantastique", "coefficient": -0.47}
      /* … 8 autres termes … */
    ]
  }
  ```
- **Codes d’erreur**  
  - `400` : validation Pydantic (texte trop long, `n` hors limites).  
  - `503` : « Modèle indisponible » – si le modèle ne peut pas être chargé.

---

### `GET /insights`
- **Méthode & chemin** : `GET /insights`
- **Paramètres de requête** :
  - `app_id` : `int` – **obligatoire** (identifiant Steam de l’application).  
  - `days` : `int` – nombre de jours à remonter : **1 ≤ days ≤ 90**, défaut = 7.
- **Sortie** (`list[InsightItem]`) – tableau d’objets :
  - `app_id` : `int`
  - `language` : `str` (`"english"` ou `"french"` selon les données)
  - `date` : `str` – date ISO `YYYY-MM-DD`
  - `n_reviews` : `int` – nombre d’avis ce jour‑là
  - `share_negative_pred` : `float` – part des avis prédits négatifs
  - `share_negative_true` : `float` – part des avis réellement négatifs
  - `model_version` : `str`
- **Exemple d’appel**  
  ```bash
  curl -X GET "http://0.0.0.0:8000/insights?app_id=570&days=3"
  ```
  **Réponse** (200) :
  ```json
  [
    {
      "app_id": 570,
      "language": "english",
      "date": "2026-09-18",
      "n_reviews": 124,
      "share_negative_pred": 0.27,
      "share_negative_true": 0.30,
      "model_version": "1.2.3"
    },
    {
      "app_id": 570,
      "language": "english",
      "date": "2026-09-19",
      "n_reviews": 138,
      "share_negative_pred": 0.22,
      "share_negative_true": 0.25,
      "model_version": "1.2.3"
    },
    {
      "app_id": 570,
      "language": "english",
      "date": "2026-09-20",
      "n_reviews": 150,
      "share_negative_pred": 0.20,
      "share_negative_true": 0.18,
      "model_version": "1.2.3"
    }
  ]
  ```
  (Si aucune donnée n’est disponible, la réponse est `[]`.)
- **Codes d’erreur**  
  - `404` : « Summary file not found » – le fichier `config.SUMMARY_FILE` n’existe pas.  
  - `500` : « Failed to read summary file » – lecture du parquet échouée.  

## Bornes, et pourquoi elles existent
Les limites imposées sur les entrées évitent qu’une requête unique surcharge le service :

| Champ                | Minimum | Maximum | Unité |
|----------------------|---------|---------|-------|
| `texts` (liste)      | 1       | 100     | éléments |
| Longueur d’un texte  | 1       | 5 000   | caractères |
| `n` (explain)        | 1       | 50      | contributions locales |
| `days` (insights)    | 1       | 90      | jours |

Ces contraintes sont codées dans les modèles Pydantic et les paramètres FastAPI ; elles sont vérifiées avant toute exécution de logique métier.

## Ce que l’API ne fait pas
- **Authentification** : aucune vérification d’identité ou de jeton n’est implémentée.  
- **Limitation de débit** : aucun rate‑limiting n’est appliqué.  
- **Versionnement d’URL** : les chemins restent fixes (`/health`, `/predict`, `/explain`, `/insights`).  
- **Journalisation des avis** : les textes soumis ne sont jamais enregistrés, seules les exceptions sont loggées.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
