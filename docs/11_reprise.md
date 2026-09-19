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
| Disque de Docker Desktop (partagé entre projets) | cible `D:\DockerDesktop` — **bascule en cours**, voir §3 |
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
| DAG à **9 tâches** | exécuté le 19/09, aucune erreur d'import | `airflow tasks list reviewpulse_daily` |
| Dockerfiles réordonnés, image unique `reviewpulse-app` | **écrits, jamais construits** | commit `b5f92be` |
| Images Docker | **toutes supprimées par Enzo** (16/09 soir) | à reconstruire |
| Volume `mlflow_data` (registre, champion v2) | probablement supprimé avec le reste : **à vérifier** ; sinon réentraîner (`make jobs`) | — |

### Travail du 18/09, sans Docker — **écrit, jamais exécuté**

| Élément | Fichier | Contrôle statique effectué |
|---|---|---|
| Carte des modules complétée (lakehouse, spark_silver, expectations, gold, explain, drift) | `docs/06_carte_des_modules.md` | affirmations vérifiées dans le code |
| CI : Java 17 et `JAVA_TOOL_OPTIONS` | `.github/workflows/ci.yml` | analyse YAML : Java avant les dépendances |
| Mutations M14, M15, M16 (Spark, Iceberg) | `tests/reverse/mutations.json` | ancre unique, code muté syntaxiquement valide |
| Contrôles F7 et F8 (tables Iceberg) | `tools/forward_test.py` | fonctions existantes, inscrits dans la liste |
| Model Card | `docs/12_model_card.md` | aucun chiffre étranger aux sources |
| Note d'orientation technologique | `docs/13_note_orientation.md` | chiffres et ADR vérifiés |
| Plan de monitoring | `docs/14_plan_monitoring.md` | noms de modules et de colonnes vérifiés |
| Explicabilité | `src/reviewpulse/explain.py`, `tests/test_explain.py` | compile ; deux défauts corrigés |
| Dérive | `src/reviewpulse/drift.py`, `tests/test_drift.py` | compile ; colonnes et `config` vérifiés |
| ADR 0015 et 0016 (proposées) | `docs/adr/` | inscrites au registre |

**Pour reprendre, dans l'ordre :** lire `19_known_good.md` — le dernier état sain est `KG-2026-09-19-g` —, puis `16_registre_suivi.md`, puis le plan unique. Les chiffres attendus y sont : **125 tests**, **26 mutations sur 26**, **16 contrôles**, **9 tâches** au DAG, et une charge à 0 % d'erreur et p99 925 ms. La campagne se relance par `make campagne`, en montant `/tmp` en mémoire (`--tmpfs /tmp:size=3g`), sans quoi le journal du disque virtuel devient le goulot. Tout écart se traite comme un défaut réel, jamais comme un test à ajuster.

Derniers commits : `2677865`, `aa19cd6`, `67b9b28`, `642bfa3`, `0f0ca64`, `40f8a36`, `823a0a1`, `a1fd98f`. Aucune mention d'outil dans l'historique (contrôle : `git log --format=%B | grep -ci claude` doit valoir 0).

## 3. Ce qui bloque, et qui le débloque

1. **Bascule du disque Docker vers D:** (Enzo, dans Docker Desktop). À 20:39, les deux copies du disque (C: et D:) existaient, Docker était arrêté, et le réglage n'était pas enregistré. Critère de fin : Docker démarre depuis `D:\DockerDesktop`, puis l'original de C: disparaît.
   Constat de 21:45 : la copie sur D: a disparu (il ne reste que des dossiers `DockerDesktop\` vides) ; l'unique exemplaire de `docker_data.vhdx` (63,7 Go) est sur C:, attaché à Windows comme disque virtuel (disque 5, vmwp/vmmem depuis 21:39) ; `wsl --shutdown` ne le libère pas ; `Dismount-VHD` demande une console administrateur. Dans `settings-store.json`, `WslEngineEnabled` vaut `false` : à réactiver avant de relancer Docker.
   Constat de 22:00 : l'ancien disque est supprimé (C: à 64,5 Go libres). Docker tourne en **mode Hyper-V** (`WslEngineEnabled=false`, disque neuf de 44 Mo dans `C:\ProgramData\DockerDesktop\vm-data`, propriétaire Administrateurs). Le déplacement vers `D:\DockerDesktop` échoue (« owners mismatch ») parce que Docker crée `D:\DockerDesktop\DockerDesktop` au nom de `dibac`. Remède : réactiver le moteur WSL 2, puis refaire le déplacement.
   Constat du 17/09 : sans Docker, la passerelle `localhost:4000` et donc `nexus_agent.py` sont hors service. Recours : l'Ollama natif (`%LOCALAPPDATA%\Programs\Ollama\ollama.exe serve`, port 11434, version 0.34.1), appelé directement par `/api/generate`, avec `think:false` et `temperature` 0,2 ; `deepseek-v4-flash:cloud` répond proprement, `glm-5.3:cloud` laisse passer sa réflexion dans la réponse. Ses 77 modèles occupent **584 Go sur C:** (`%USERPROFILE%\.ollama\models`) ; `D:\ollama\models` existe mais est vide.
   Constat du 17/09 au soir : Docker 29.8.0 est reparti et la passerelle 4000 répond (le banc gratuit est de nouveau utilisable), mais **le disque Docker est sur C:** (`C:\ProgramData\DockerDesktop\vm-data\DockerDesktop.vhdx`, 2,45 Go ; C: 79 Go libres) et le backend est Hyper-V. Décision de l'opérateur : déplacement reporté tant que l'icacls parcourt D: (registre local-llm-docker T-20260917-003). **Ne rien reconstruire tant que le disque est sur C:.** En Hyper-V, le montage de `D:\ReviewPulse_work\data` sous `/data` exige le moteur WSL 2 ou D: déclaré en partage de fichiers.
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
