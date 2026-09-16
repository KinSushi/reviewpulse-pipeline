# Contrat de code — ReviewPulse

Référence unique pour tous les modules. `src/reviewpulse/config.py` fait foi pour les noms et les chemins : **l'importer, ne jamais recopier ses valeurs**.

## Environnement

- Python **3.11**, disposition `src/` (paquet `reviewpulse`, installé par `pip install -e .`).
- Versions figées : pandas 2.2.3 · pyarrow 17.0.0 · scikit-learn 1.5.2 · mlflow 2.17.2 · fastapi 0.115.5 · uvicorn 0.32.1 · pydantic 2.9.2 · streamlit 1.40.2 · requests 2.32.3 · pytest 8.3.4 · httpx 0.27.2 · ruff 0.8.1.
- Journalisation par `logging.getLogger(__name__)`, jamais `print` hors des `main()`.
- **Ne jamais journaliser un texte d'avis en entier ni un `steamid`.**
- Chaque module exécutable expose `main() -> int` et `if __name__ == "__main__": raise SystemExit(main())`.
- Commentaires et docstrings en français, identifiants en anglais.
- **Importer la configuration par `from reviewpulse import config` et lire `config.X` au moment de l'appel.** Les paramètres de chemin valent `None` par défaut et sont résolus dans le corps de la fonction (`raw_dir = raw_dir or config.RAW_DIR`). Jamais `from reviewpulse.config import RAW_DIR`, jamais `def f(raw_dir=config.RAW_DIR)` : les tests remplacent ces valeurs par `monkeypatch.setattr(config, ...)`.

## `config.py` — contenu de référence (à reproduire tel quel)

Constantes : `DATA_DIR = Path(os.getenv("REVIEWPULSE_DATA_DIR", "data"))`, `RAW_DIR`, `CLEAN_DIR`, `SCORED_DIR`, `STATE_DIR` (sous-dossiers `raw`, `clean`, `scored`, `state`), `CLEAN_FILE = CLEAN_DIR / "reviews.parquet"`, `SCORED_FILE = SCORED_DIR / "reviews_scored.parquet"`, `SUMMARY_FILE = SCORED_DIR / "daily_summary.parquet"`, `APP_IDS` (liste d'entiers lue dans `REVIEWPULSE_APP_IDS`, défaut `"1903340,1086940,2622380"`), `LANGUAGES = ["english", "french"]`, `STEAM_URL = "https://store.steampowered.com/appreviews/{app_id}"`, `PAGE_SIZE = 100`, `MAX_PAGES` (env `REVIEWPULSE_MAX_PAGES`, défaut 20), `HTTP_TIMEOUT_S = 20`, `HTTP_MAX_RETRIES = 4`, `MLFLOW_TRACKING_URI` (env, défaut `"sqlite:///data/mlflow.db"`), `MLFLOW_EXPERIMENT = "reviewpulse"`, `MODEL_NAME = "reviewpulse-sentiment"`, `ALIAS_CHAMPION = "champion"`, `ALIAS_CHALLENGER = "challenger"`, `RAW_RETENTION_DAYS = 30`, `F1_MACRO_MIN = 0.75`, `RANDOM_STATE = 42`, `FORBIDDEN_CLEAN_COLUMNS = ["steamid", "personaname", "profile_url", "avatar"]`, et :

```python
CLEAN_COLUMNS = {
    "review_id": "string", "app_id": "int64", "language": "string",
    "review_text": "string", "label": "int64",
    "created_at": "datetime64[ns, UTC]", "updated_at": "datetime64[ns, UTC]",
    "votes_up": "int64", "weighted_vote_score": "float64",
    "playtime_at_review_min": "int64", "author_pseudo": "string", "text_len": "int64",
}
```

Fonction `salt() -> bytes` : lit `REVIEWPULSE_SALT`, lève `RuntimeError` si absent ou vide. **Aucune valeur par défaut.**

Les types `"string"` désignent le type pandas `string` (`df[col].astype("string")`) ; la comparaison des types se fait sur `str(df[col].dtype)`.

## `tests/conftest.py` — fixtures partagées

- `data_env(tmp_path, monkeypatch)` : crée l'arborescence sous `tmp_path / "data"`, remplace dans `reviewpulse.config` **toutes** les constantes de chemin (`DATA_DIR`, `RAW_DIR`, `CLEAN_DIR`, `SCORED_DIR`, `STATE_DIR`, `ARTIFACT_DIR`, `CLEAN_FILE`, `SCORED_FILE`, `SUMMARY_FILE`), fixe `config.MLFLOW_TRACKING_URI` à `f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"`, définit la variable d'environnement `REVIEWPULSE_SALT="test-salt"`, et renvoie `tmp_path / "data"`.
- `make_review(rid, voted_up=True, text="great game", steamid="7656119800000000", created=1_780_000_000, updated=None, playtime=120)` : fonction (exposée par la fixture `review_factory`) qui renvoie un dict au format de l'API Steam, `author` complet compris (`steamid`, `personaname`, `profile_url`, `avatar`, `playtime_at_review`), `votes_up=0`, `weighted_vote_score="0.5"`, `language="english"`.
- `FakeResponse(status_code, payload)` avec `.status_code` et `.json()` ; `FakeSession(pages)` : `.get(url, params=None, timeout=None)` renvoie la réponse suivante de la liste (ou `{}` si la liste est épuisée) et enregistre `{"url": ..., "params": ..., "timeout": ...}` dans `.calls`. Exposées par la fixture `fake_session_cls` (renvoie la classe).
- `labelled_frame(n=200)` : fixture qui renvoie un DataFrame conforme à `CLEAN_COLUMNS`, moitié positive (textes composés de « great fun amazing love excellent … ») et moitié négative (« crash bug refund boring broken … »), avec variations aléatoires à graine fixe, `author_pseudo` sur 64 caractères hexadécimaux.

## Évolution v2 — flux complémentaire d'avis négatifs (prime sur les sections suivantes)

*Décision du 16/09/2026, mesurée sur le même test naturel (1 192 avis, 108 négatifs) : F1 macro 0,750 → 0,798, AUC 0,896 → 0,928. Voir ADR 0006.*

- **config** : `SAMPLE_NATURAL = "natural"`, `SAMPLE_NEGATIVE_BOOST = "negative_boost"`, `SAMPLE_SOURCES = [SAMPLE_NATURAL, SAMPLE_NEGATIVE_BOOST]`, `BOOST_MAX_PAGES` (env `REVIEWPULSE_BOOST_MAX_PAGES`, défaut 5), `THRESHOLD_GRID = [round(0.30 + 0.025 * i, 3) for i in range(21)]` (0,30 à 0,80), `DEFAULT_DECISION_THRESHOLD = 0.5`. `CLEAN_COLUMNS` gagne une 13e colonne, en dernier : `"sample_source": "string"`.
- **ingest** : `ingest_app(..., sample_source=config.SAMPLE_NATURAL)` (valeur résolue dans le corps si `None`). Pour `negative_boost`, la requête ajoute `review_type=negative`. **Compatibilité ascendante obligatoire** (des données réelles existent déjà) : le flux `natural` garde EXACTEMENT le chemin `RAW_DIR/app_id=.../language=.../dt=.../batch_....jsonl` et le manifeste `STATE_DIR/seen_<app_id>_<language>.txt` ; seul le flux `negative_boost` utilise `RAW_DIR/sample=negative_boost/app_id=.../...` et `STATE_DIR/seen_negative_boost_<app_id>_<language>.txt`. `fetch_page` reçoit un paramètre `review_type="all"`. `main()` collecte d'abord le flux naturel (`MAX_PAGES`), puis le flux `negative_boost` (`BOOST_MAX_PAGES`), pour chaque jeu et chaque langue.
- **transform** : `load_raw` ajoute `sample_source` lu dans la partition `sample=` (valeur `natural` si la partition est absente, pour compatibilité). `clean` accepte un brut sans colonne `sample_source` (et sans `language_partition`) : `sample_source` vaut alors `natural`. Au dédoublonnage, **un avis présent dans les deux flux est conservé comme `natural`** (tri par priorité natural, puis `timestamp_updated` décroissant).
- **quality** : contrôle supplémentaire `sample_source ∈ SAMPLE_SOURCES`. La part de négatifs se calcule **sur les lignes `natural` seulement** ; s'il n'y en a aucune, c'est un échec.
- **train** :
  1. le test (20 %, stratifié) est tiré **uniquement** des lignes `natural` ;
  2. l'entraînement = le reste des lignes `natural` + **toutes** les lignes `negative_boost` ;
  3. seuil de décision : prédictions hors-plis (`StratifiedKFold(5, shuffle=True, random_state)`) calculées **sur les lignes naturelles d'entraînement**, les lignes `negative_boost` étant ajoutées à l'entraînement de chaque pli et jamais évaluées ; on retient dans `THRESHOLD_GRID` le seuil qui maximise le F1 macro hors-plis (à égalité, le plus proche de 0,5) ; `f1_cv_mean` = F1 macro hors-plis à ce seuil ;
  4. le modèle final est entraîné sur tout l'entraînement ; on fixe `pipeline.decision_threshold_ = seuil` (attribut conservé par la sérialisation) ;
  5. prédiction négative si `proba_negative >= seuil` ; toutes les métriques de test sont calculées à ce seuil ;
  6. journaliser en paramètres `decision_threshold`, `n_boost`, et en métriques `n_train`, `n_test`, `negative_share` (du test naturel) ; poser le tag de version `decision_threshold`.
- **score** : `threshold = getattr(model, "decision_threshold_", config.DEFAULT_DECISION_THRESHOLD)` ; `pred_label = 0 si proba_negative >= threshold sinon 1` ; colonne `decision_threshold` ajoutée. `summarize` **n'agrège que les lignes `natural`**.
- **api** : même règle de seuil ; `/health` renvoie aussi `decision_threshold`.
- **tableau de bord** : n'affiche que les lignes `natural` ; montre le seuil en vigueur.
- **conftest** : `labelled_frame` ajoute `sample_source="natural"` ; `make_review` inchangé.

## Convention de décision — `decision.py` (source unique de vérité)

*Constat du 16/09/2026 : la convention a été inversée deux fois, dans `train.py` puis dans `score.py` (95 % d'avis prédits négatifs pour 4 % réels). Elle ne doit plus exister qu'à un seul endroit.*

- `LABEL_NEGATIVE = 0`, `LABEL_POSITIVE = 1` (étiquette Steam : `voted_up` vrai → 1).
- `negative_proba(model, texts) -> np.ndarray` : `model.predict_proba(list(texts))[:, index de la classe 0 dans model.classes_]` (ne jamais supposer que la colonne 0 est la classe 0).
- `model_threshold(model) -> float` : `getattr(model, "decision_threshold_", config.DEFAULT_DECISION_THRESHOLD)`.
- `predict_labels(proba_negative, threshold) -> np.ndarray[int64]` : `LABEL_NEGATIVE` si `proba_negative >= threshold`, sinon `LABEL_POSITIVE`.
- `label_name(label) -> str` : `"negative"` ou `"positive"`.
- `train`, `score` et `api` n'écrivent **aucune** comparaison au seuil eux-mêmes : ils appellent ces fonctions.
- `/predict` renvoie aussi `decision_threshold`.
- Le tableau de bord calcule la part négative prédite comme la moyenne de `pred_label == LABEL_NEGATIVE`, la part réelle comme la moyenne de `label == LABEL_NEGATIVE`, et trace la courbe à partir de `SUMMARY_FILE` (colonne `share_negative_pred`).

## Source

`GET https://store.steampowered.com/appreviews/{app_id}` avec `json=1`, `filter=recent`, `language=<english|french>`, `purchase_type=all`, `num_per_page=100`, `cursor=<curseur>` (premier appel : `*`). Réponse : `{"success": 1, "query_summary": {...}, "reviews": [...], "cursor": "..."}`.

Un objet `review` contient notamment : `recommendationid` (str), `author` (objet : `steamid`, `personaname`, `profile_url`, `avatar`, `num_games_owned`, `num_reviews`, `playtime_forever`, `playtime_at_review`, …), `language`, `review` (texte), `timestamp_created` (epoch s), `timestamp_updated` (epoch s), `voted_up` (bool), `votes_up` (int), `weighted_vote_score` (str ou nombre).

## Zone brute — `ingest.py`

- Fichier : `RAW_DIR/app_id=<id>/language=<lang>/dt=<YYYY-MM-DD>/batch_<YYYYmmddTHHMMSSZ>.jsonl`.
- **Une ligne = l'objet `review` exactement tel que reçu** (`json.dumps(obj, ensure_ascii=False)`), sans ajout ni retrait.
- Manifeste d'idempotence : `STATE_DIR/seen_<app_id>_<language>.txt`, un `recommendationid` par ligne. Seuls les avis absents du manifeste sont écrits ; le manifeste est mis à jour **après** l'écriture réussie du lot (écriture dans un fichier temporaire puis `os.replace`). Aucun nouvel avis → aucun fichier créé.
- Pagination : s'arrêter quand une page ne contient aucun nouvel avis, quand la liste est vide, quand le curseur se répète, ou à `MAX_PAGES`.
- HTTP : `requests.Session`, `timeout=HTTP_TIMEOUT_S`, jusqu'à `HTTP_MAX_RETRIES` nouvelles tentatives sur 429 et 5xx avec attente exponentielle (1, 2, 4, 8 s ; attente injectable pour les tests), `success != 1` → `RuntimeError`.
- API : `fetch_page(session, app_id, language, cursor) -> dict` · `ingest_app(app_id, language, session=None, max_pages=MAX_PAGES, now=None) -> int` (nombre de nouveaux avis) · `main()`.

## Zone propre — `transform.py`

- `load_raw(raw_dir=RAW_DIR) -> pd.DataFrame` : lit tous les `*.jsonl`, ajoute `app_id` et `language_partition` depuis le chemin.
- `clean(raw: pd.DataFrame, salt: bytes) -> pd.DataFrame` qui renvoie **exactement** les colonnes et types de `config.CLEAN_COLUMNS`, dans cet ordre :
  - `review_id` = `recommendationid` ; dédoublonnage en gardant le plus grand `timestamp_updated` ;
  - `review_text` : suppression des balises BBCode (`[b]`, `[/spoiler]`, `[url=…]`, etc., motif `\[/?[a-zA-Z*]+(=[^\]]*)?\]`), espaces multiples réduits, `strip()` ; lignes au texte vide supprimées ;
  - `label` = 1 si `voted_up` vrai, sinon 0 ;
  - `created_at`, `updated_at` en UTC depuis les epochs ;
  - `weighted_vote_score` converti en float, `votes_up` en int ;
  - `playtime_at_review_min` = `author.playtime_at_review` (0 si absent) ;
  - `author_pseudo` = `hmac.new(salt, steamid.encode(), hashlib.sha256).hexdigest()` ;
  - `language` = langue de la partition ; `text_len` = longueur du texte nettoyé ;
  - aucune colonne de `FORBIDDEN_CLEAN_COLUMNS`.
- `write_clean(df, path=CLEAN_FILE) -> Path` : Parquet, écriture atomique.
- `purge_raw(raw_dir=RAW_DIR, retention_days=RAW_RETENTION_DAYS, today=None) -> int` : supprime les partitions `dt=` plus anciennes.
- `main()` : `load_raw` → `clean(config.salt())` → `quality.assert_quality` (**bloquant**) → `write_clean` → `purge_raw`.

## Qualité — `quality.py`

- `class DataQualityError(Exception)`.
- `check_clean(df) -> list[str]` : renvoie la liste des échecs, vide si tout va bien. Contrôles : colonnes et types conformes à `CLEAN_COLUMNS` · au moins une ligne · `review_id` non nul et unique · `label` dans {0, 1} · `language` dans `LANGUAGES` · `text_len >= 1` · aucune colonne interdite · `author_pseudo` conforme à `^[0-9a-f]{64}$` · part de négatifs entre 0,5 % et 95 %.
- `assert_quality(df) -> None` : lève `DataQualityError` avec tous les échecs.
- `main()` : lit `CLEAN_FILE`, contrôle, code 0 ou 1.

## Modèle — `train.py`

- `build_pipeline() -> sklearn.pipeline.Pipeline` : `TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, max_features=100000, sublinear_tf=True, lowercase=True)` puis `LogisticRegression(C=4.0, class_weight="balanced", max_iter=2000, random_state=RANDOM_STATE)`. *Choix mesuré le 16/09 sur données réelles, voir la charte.*
- **Emplacement des artefacts.** `config.ARTIFACT_DIR = DATA_DIR / "mlartifacts"`. Si l'URI de suivi commence par `sqlite:` ou `file:`, l'expérience est créée (si elle n'existe pas) avec `artifact_location=Path(config.ARTIFACT_DIR).resolve().as_uri()`, puis sélectionnée par `mlflow.set_experiment`. Avec un serveur `http(s)`, on laisse le serveur gérer les artefacts. *Constat du 16/09 : sans cela, le modèle part dans `./mlruns` du dossier courant et devient introuvable pour l'API.*
- `roc_auc` se calcule pour la classe négative : `roc_auc_score((y_test == 0).astype(int), proba_negative)`.
- Enregistrement : `mlflow.sklearn.log_model(..., registered_model_name=MODEL_NAME)` et version lue dans `model_info.registered_model_version`. **Ne jamais utiliser `get_latest_versions`** (obsolète). Pas d'`input_example` (le chemin pyfunc passe un DataFrame au vectoriseur) ; signature seule.
- Chaque `main()` configure `logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")`.
- `train_and_log(df, tracking_uri=MLFLOW_TRACKING_URI, register=True) -> dict` :
  - découpage stratifié 80/20, `random_state=RANDOM_STATE` ;
  - validation croisée `StratifiedKFold(5)` sur l'entraînement, F1 macro moyen et écart-type ;
  - métriques de test : `f1_macro`, `recall_negative`, `precision_negative`, `roc_auc` (probabilité de la classe 0), `n_train`, `n_test`, `negative_share` ;
  - `mlflow.log_params`, `mlflow.log_metrics`, artefact `top_terms.json` (20 termes les plus négatifs et 20 plus positifs d'après les coefficients) ;
  - `mlflow.sklearn.log_model(..., artifact_path="model", signature=..., input_example=...)` ;
  - si `register` : enregistrement sous `MODEL_NAME`, alias `challenger` sur la nouvelle version ; alias `champion` si `f1_macro >= F1_MACRO_MIN` **et** (aucun champion ou `f1_macro` supérieur à celui du champion, lu dans les métriques de son run) ;
  - renvoie un dict avec les métriques, `run_id`, `model_version` (ou `None`) et `promoted` (bool).
- L'entrée du modèle est la colonne `review_text` (série de chaînes) ; la cible est `label`.
- `main()` : lit `CLEAN_FILE`, entraîne, affiche les métriques.

## Score — `score.py`

- `load_champion(tracking_uri=MLFLOW_TRACKING_URI) -> tuple[model, str]` : `mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@{ALIAS_CHAMPION}")` et la version via `MlflowClient().get_model_version_by_alias`.
- `score(df, model, model_version) -> pd.DataFrame` : ajoute `proba_negative` (probabilité de la classe 0), `pred_label` (1 si `proba_negative < 0.5`, sinon 0), `model_version`, `scored_at` (UTC).
- `summarize(scored) -> pd.DataFrame` : par `app_id`, `language`, `date` (jour de `created_at`) : `n_reviews`, `share_negative_pred`, `share_negative_true`, `model_version`.
- `main()` : écrit `SCORED_FILE` et `SUMMARY_FILE` (écriture atomique).

## API — `api.py` (FastAPI)

- `app = FastAPI(title="ReviewPulse API")`.
- Dépendance `get_model()` qui renvoie `(model, version)` ; chargée une fois et mise en cache ; remplaçable dans les tests par `app.dependency_overrides`.
- `GET /health` → `{"status": "ok", "model_version": str}`.
- `POST /predict`, corps `{"texts": [str]}` : de 1 à 100 textes, chacun de 1 à 5 000 caractères (validation Pydantic, sinon 422). Réponse : `{"model_version": str, "predictions": [{"text_preview": 80 premiers caractères, "proba_negative": float, "label": "negative" | "positive"}]}`.
- `GET /insights?app_id=<int>&days=<int, 1..90, défaut 7>` : lit `SUMMARY_FILE`, filtre sur `app_id` et sur les `days` derniers jours **comptés depuis la dernière date disponible pour ce jeu** (une démo rejouée doit fonctionner), renvoie **directement une liste** de lignes (dates en ISO). 404 si le fichier est absent.
- `model_version` est toujours une **chaîne**, dans l'API comme dans le dict renvoyé par `train_and_log`.
- Garde-fous : aucune journalisation du texte ; seuil de décision 0,5 documenté.
- Si le modèle champion ne peut pas être chargé, `get_model` lève `HTTPException(503, "Modèle indisponible")` et journalise la cause ; une nouvelle tentative a lieu à l'appel suivant (le cache ne retient que les succès).

## Tableau de bord — `dashboard/app.py` (Streamlit)

Lit `SCORED_FILE` et `SUMMARY_FILE`. Filtres : jeu, langue. Indicateurs : nombre d'avis, part négative prédite, part négative réelle, version du modèle. Courbe de la part négative prédite par jour. Tableau des 20 avis les plus probablement négatifs : date, langue, `proba_negative`, texte tronqué à 200 caractères, **aucune information d'auteur**. Zone « Tester un avis » qui appelle `POST {REVIEWPULSE_API_URL}/predict` (défaut `http://localhost:8000`). Message clair si les fichiers n'existent pas encore.

## Orchestration — `dags/reviewpulse_daily.py` (Airflow 2.10)

- DAG `reviewpulse_daily` : `schedule="0 6 * * *"`, `catchup=False`, `retries=2`, `retry_delay=5 min`, tâches `PythonOperator` : `ingest` → `transform_and_check` → `score`.
- DAG `reviewpulse_weekly_train` : `schedule="0 7 * * 1"`, tâche `train`, puis `score`.
- Les fonctions appelées sont les `main()` des modules ; un code non nul lève `AirflowException`.

## Tests — `tests/`

Aucun accès réseau : `requests.Session` remplacée par un faux objet. Chaque test utilise `tmp_path` et `monkeypatch` pour rediriger `config.DATA_DIR`, `RAW_DIR`, `CLEAN_DIR`, `SCORED_DIR`, `STATE_DIR` et les fichiers dérivés. MLflow pointe vers `sqlite:///<tmp_path>/mlflow.db`.
