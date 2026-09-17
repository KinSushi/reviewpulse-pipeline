# Reprise de session — à lire en premier

Mise à jour : 16/09/2026, 20:45 (heure de Paris). Ce fichier permet de reprendre le travail après un redémarrage de l'outil, sans rien reconstituer de mémoire. L'historique détaillé est dans `09_journal_de_bord.md`, le travail restant dans `10_backlog.md`.

## 1. Où sont les choses (tout est sur D:)

| Élément | Emplacement |
|---|---|
| Dépôt git (branche de travail `plateforme-v3`) | `D:\ReviewPulse_work\ReviewPulse` |
| Lac de données (bronze, silver Iceberg, gold DuckDB, rapports) | `D:\ReviewPulse_work\data`, monté sous `/data` par `docker-compose.override.yml` (fichier local, non versionné) |
| Sel de pseudonymisation de test (secret : ne jamais l'afficher) | `D:\ReviewPulse_work\session_scratch\salt.secret` |
| Scripts de travail (`lot_run.py`, `ast_equiv.py`, `probe_gold.sh`, image de dev `devimg/`) | `D:\ReviewPulse_work\session_scratch` |
| Archives (sauvegardes du banc, ancien lac, journaux de construction) | `D:\ReviewPulse_work\archives_2026-09-16` |
| Disque de Docker Desktop (partagé entre projets) | cible `D:\Program Files\DockerDesktopWSL` — **bascule en cours**, voir §3 |
| Ancien dossier `C:\Users\dibac\OneDrive\Bureau\Jedha_Exercices\Data_Lead\ReviewPulse` | 82 doublons OneDrive à supprimer par Enzo ; **ne plus y travailler** |

Règle d'Enzo : **rien de ReviewPulse sur C:** (ni build, ni cache, ni temporaire). Les dépendances s'installent seulement dans les images Docker ; les tests tournent dans des conteneurs.

## 2. État vérifié

| Élément | État | Preuve |
|---|---|---|
| Chaîne ingest → Spark/Iceberg → GE → MLflow → score → API → tableau de bord | fonctionne | `evidence/forward_test.md` (12/12) |
| Tests | 62 verts (54 + 4 Spark + 4 dbt) | journal, 16/09 |
| Tests inverses | 13/13 avec témoin (avant Spark et dbt) | `evidence/reverse_tests.md` |
| DAG Airflow quotidien (4 tâches) | succès avec Spark (exécution `spark_v3`) | journal, 17/09 00:26 UTC |
| Gold dbt-duckdb | 43/43 sur données réelles | journal |
| DAG à 5 tâches (avec `gold`) | **écrit, jamais exécuté** | — |
| Dockerfiles réordonnés, image unique `reviewpulse-app` | **écrits, jamais construits** | commit `b5f92be` |
| Images Docker | **toutes supprimées par Enzo** (16/09 soir) | à reconstruire |
| Volume `mlflow_data` (registre, champion v2) | probablement supprimé avec le reste : **à vérifier** ; sinon réentraîner (`make jobs`) | — |

Derniers commits : `7756b65`, `b5f92be`, `a1fa346`. Aucune mention d'outil dans l'historique (contrôle : `git log --format=%B | grep -ci claude` doit valoir 0).

## 3. Ce qui bloque, et qui le débloque

1. **Bascule du disque Docker vers D:** (Enzo, dans Docker Desktop). À 20:39, les deux copies du disque (C: et D:) existaient, Docker était arrêté, et le réglage n'était pas enregistré. Critère de fin : Docker démarre depuis `D:\Program Files\DockerDesktopWSL`, puis l'original de C: disparaît.
2. **Coordination** avec la session `local-llm-docker` (passerelle LiteLLM sur `localhost:4000`) : ne rien lancer sur Docker avant qu'elle ait confirmé que C: est libéré et que sa pile est revenue.
3. Enzo : supprimer le dépôt GitHub `KinSushi/reviewpulse` (il contient d'anciens commits avec mention d'outil) ; valider le seuil F1 ≥ 0,75 ; autoriser le secret `REVIEWPULSE_SALT` sur le futur dépôt.

## 4. Reprise, dans l'ordre

```bash
cd /d/ReviewPulse_work/ReviewPulse
export REVIEWPULSE_SALT=$(cat /d/ReviewPulse_work/session_scratch/salt.secret)
```

1. Vérifier que Docker tourne depuis D: et que C: a de la place.
2. `docker compose build api` (image `reviewpulse-app`), puis `docker compose --profile airflow build airflow`. Reconstruire aussi l'image de dev : `docker build -t reviewpulse-dev /d/ReviewPulse_work/session_scratch/devimg`.
3. `docker compose up -d mlflow api dashboard`, puis `docker compose --profile jobs run --rm pipeline` (ingest → spark → gx → train → score → gold).
4. Airflow : `docker compose --profile airflow up -d airflow`, **attendre environ 2 minutes** (sinon SQLite « database is locked » et arrêt du scheduler), déclencher `reviewpulse_daily`, viser 5/5, puis remettre le DAG en pause.
5. Tests dans l'image de dev (copie jetable, jamais le dépôt monté en écriture) ; tests inverses et test de stack à rafraîchir (`make reverse`, `make forward`) ; mettre à jour `docs/evidence/`.
6. Commit sans mention d'outil, puis la suite du backlog : CI (Java, Spark, dbt), mutations Spark/Iceberg, documentation de `score.py`, F7/F8, puis le Sprint 2.

## 5. Règles de travail (non négociables)

- **Le banc gratuit écrit le code** : `python C:/local-llm-docker/scripts/nexus_agent.py --lot … --sortie …`, puis `nexus_creer.py [--remplacer]`. Réponses encadrées par `<<<CREER>>>` / `<<<FIN>>>`. Un hook bloque l'écriture directe des `.py` et des tests. Spécifications en JSON et `lot_run.py` dans `session_scratch`. **Ne jamais modifier `C:\local-llm-docker`** ; signaler ses problèmes à NEXUS.
- Le rendu du banc est un signal, pas une preuve : il invente des colonnes, des macros et des affirmations, et « ajuste » les données des tests. Tout se vérifie en exécution réelle ; doc seule → contrôle AST (`ast_equiv.py`).
- Un test doit vérifier l'**effet réel**, et un **témoin** doit prouver qu'il échoue sans le correctif.
- `robocopy /MOVE` ne supprime pas les fichiers déjà identiques : ajouter `/IS /IT`.
- Ne jamais lire le fichier d'environnement local ; ne jamais faire apparaître le sel dans une commande.
- Aucun `Co-Authored-By` ni mention d'outil dans les commits et PR.
- Suppressions, publication GitHub, secrets : décisions d'Enzo.
- Tout fait nouveau va dans `09_journal_de_bord.md` avec sa source ; tout travail restant dans `10_backlog.md`.
