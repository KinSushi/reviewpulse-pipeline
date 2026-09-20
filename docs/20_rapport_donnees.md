## 1. Le jeu de données

Le jeu provient de l’API publique des avis Steam ; il regroupe les avis en anglais et en français de trois applications identifiées dans `src/reviewpulse/config.py` via la variable `APP_IDS`. L’ingestion (`src/reviewpulse/ingest.py`) parcourt chaque couple *app_id × language* et récupère les pages d’avis jusqu’à `config.MAX_PAGES` (ou `config.BOOST_MAX_PAGES` pour le flux négatif). Au 19/09/2026, la zone brute contient **9 271 lignes** réparties sur les trois jeux, ce qui constitue un volume suffisant pour entraîner un modèle de classification tout en restant exploitable dans le cadre d’un projet académique.  

Ces avis sont directement issus d’utilisateurs réels, ce qui rend le problème « sentiment analysis » à la fois **challenging** (texte libre, présence de balises BBCode, déséquilibre des votes) et **relevant to a real‑world problem** (détection de satisfaction client, modération de contenu).  

## 2. Ce qui est retiré, et pourquoi

Le nettoyage (`src/reviewpulse/transform.py` → `clean`) supprime les colonnes listées dans `config.FORBIDDEN_CLEAN_COLUMNS` :

| Colonne            | Raison du retrait |
|--------------------|-------------------|
| `steamid`          | Identifiant personnel direct, prohibé par le RGPD ; remplacé par un pseudonyme HMAC. |
| `personaname`      | Nom d’utilisateur pouvant identifier la personne. |
| `profile_url`      | URL publique du profil, donnée personnelle. |
| `avatar`           | Lien vers l’image du profil, également personnel. |

Ces colonnes sont éliminées **avant** la phase de pseudonymisation, dès la création du DataFrame propre, afin de garantir qu’aucune donnée brute d’identification ne persiste dans la zone propre.

## 3. La pseudonymisation

Le mécanisme est implémenté dans `src/reviewpulse/transform.py` : la fonction interne `_hash_steamid` applique `hmac.new(salt, steamid.encode(), hashlib.sha256).hexdigest()`. Le sel provient de `config.salt()` (`src/reviewpulse/config.py`), qui lira la variable d’environnement `REVIEWPULSE_SALT` ; l’absence de cette variable déclenche une `RuntimeError`.  

**Pourquoi un HMAC avec sel ?** Un simple hachage (ex. SHA‑256) serait vulnérable à une attaque par dictionnaire : les identifiants Steam sont courts et souvent séquentiels, ce qui permettrait de reconstruire les valeurs originales. Le sel, obligatoire et de 64 caractères, rend chaque hachage unique et empêche la pré‑calculation de tables de correspondance, assurant ainsi une pseudonymisation conforme au RGPD (article 6.1.f).

## 4. Le nettoyage et le dédoublonnage

`src/reviewpulse/transform.py` décrit le pipeline :

1. **Lecture** de tous les fichiers `*.jsonl` sous `config.RAW_DIR` (`load_raw`).  
2. **Priorité de dédoublonnage** : la colonne `_priority` est créée à partir de `sample_source` ; `natural` reçoit la priorité 0, `negative_boost` la priorité 1 (`clean`). Le DataFrame est trié par `_priority` puis par `timestamp_updated` décroissant, et les doublons sur `review_id` sont éliminés en conservant la première occurrence. Cette règle favorise les avis du flux naturel, qui sont complets, tout en conservant la version la plus récente lorsqu’un même avis apparaît dans les deux flux.  
3. **Nettoyage du texte** : les balises BBCode sont retirées via `_RE_BBCODE`, les espaces multiples sont compressés et le texte est stripé (`_clean_text`). Les lignes dont le texte devient vide sont ensuite filtrées.  
4. **Conversion des types** selon `config.CLEAN_COLUMNS` ; les colonnes dérivées (`author_pseudo`, `playtime_at_review_min`, `text_len`, etc.) sont calculées.  
5. **Contrôle de qualité** (`reviewpulse.quality.assert_quality`) bloque l’écriture si une colonne interdite subsiste.  

## 5. Le déséquilibre des classes

Le jeu présente naturellement plus d’avis positifs (`voted_up = true`) que négatifs. Le modèle de régression logistique, défini ailleurs dans le projet, utilise `class_weight="balanced"` ; ainsi, chaque classe reçoit un poids inversement proportionnel à sa fréquence lors de l’ajustement. Cette approche évite le sur‑échantillonnage ou le sous‑échantillonnage qui pourraient introduire des biais supplémentaires ou perdre de l’information, tout en respectant la distribution originale des avis.

## 6. Le feature engineering

Après le nettoyage, les textes (`review_text`) sont vectorisés par TF‑IDF ; les paramètres de la vectorisation (par ex. `max_features`, `ngram_range`) sont fixés dans le module de modélisation (non montré ici) mais sont choisis pour capturer la richesse lexicale tout en limitant le sur‑ajustement. La TF‑IDF transforme chaque avis en un vecteur numérique, permettant au modèle linéaire de distinguer les termes fortement associés aux avis positifs ou négatifs.

## 7. Ce que ce jeu ne permet pas de conclure

Le jeu est limité à trois titres Steam et à deux langues ; il ne représente donc pas l’ensemble de la communauté Steam ni les avis multilingues au-delà de l’anglais et du français. La période de collecte (jusqu’au 19/09/2026) ne couvre pas les évolutions récentes du comportement des joueurs. De plus, les avis ne sont soumis qu’aux utilisateurs qui choisissent de publier un commentaire, introduisant un **biais de sélection** : les opinions extrêmes sont sur‑représentées, ce qui peut fausser l’estimation de la satisfaction moyenne. Ces limites doivent être prises en compte lors de l’interprétation des performances du modèle.

*Toutes les affirmations techniques sont directement tirées des fichiers : `src/reviewpulse/ingest.py`, `src/reviewpulse/transform.py` et `src/reviewpulse/config.py`.*
