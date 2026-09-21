# Conformité aux consignes du Demo Day — état au 21/09/2026

Référence : énoncé *Build a Data Pipeline That Feeds an AI Model*, parcours `lead-data-v2`, relu
intégralement sur Julie le 20/09/2026 et versé mot pour mot dans
[`00_sources/2026-09-20_julie_demo_day_v2_pipeline.md`](00_sources/2026-09-20_julie_demo_day_v2_pipeline.md).

**Légende.** ✅ tenu, preuve nommée · ⛔ dépend d'Enzo, pas du code · ⚠ écart assumé, à dire si la question vient.

## Les cinq exigences non négociables

| # | Exigence, mot pour mot | Réponse de ReviewPulse | Preuve | État |
|---|---|---|---|---|
| 1 | « solve a real business case with **real data you found** » | Priorisation des avis négatifs Steam pour une équipe *community & live-ops* ; API publique des avis Steam, 3 jeux, anglais et français | [`01_charte.md`](01_charte.md) ; `config.STEAM_URL` ; 9 410 lignes brutes réelles comptées le 20/09/2026, et le DAG en ajoute chaque jour | ✅ |
| 2 | « land the data **raw and unchanged** in a first storage zone **before anything touches it** » | JSONL, une ligne = l'objet reçu, partitionné par jeu, langue et date ; **idempotence** par manifeste d'identifiants et écriture atomique | 69 fichiers, 9 410 lignes, 12 manifestes (comptés le 20/09/2026) ; `test_ingest.py` (ligne relue = objet reçu) ; second passage réel : 0 nouvel avis ; ADR 0002 | ✅ |
| 3 | « transform […] with **dbt, PySpark, or pandas**, protected by **at least one data quality test** » | PySpark vers une zone silver **Iceberg**, dbt vers une zone gold DuckDB ; Great Expectations en **portes bloquantes** sur les trois zones | 4 suites, 29 attentes, 0 échec ([`evidence/dag_execution_reelle.md`](evidence/dag_execution_reelle.md)) ; 30 tests dbt déclarés ; mutations M17, M23, M24 tuées ; ADR 0005, 0014, 0020 | ✅ |
| 4 | « an **AI step** that consumes the pipeline output: an ML model tracked with **MLflow** » | TF-IDF caractères + régression logistique ; serveur MLflow, alias `champion` et `challenger`, **barrière de promotion** | champion version 5, F1 macro **0,8027** ; promotion **et** refus constatés le même jour ; ADR 0006, 0008 | ✅ |
| 5 | « At least one part of the chain must **run on its own** » | DAG Airflow quotidien (**9 tâches**) et hebdomadaire ; workflow GitHub Actions planifié | DAG exécuté en réel le 20/09 puis le 21/09 avec le code premium : 8 tâches vertes, 1 sautée par conception, et l'exécution **planifiée** qui s'est lancée seule juste après ; [`pipeline.yml`](../.github/workflows/pipeline.yml) exécuté sur un runner vierge : 5 798 avis collectés, modèle entraîné et promu ; ADR 0011 | ✅ |

**Les cinq sont tenues.** « Everything else, the domain, the model type, the tools, is your call. »

## Les livrables, jour par jour

| Jour | Livrable demandé | État |
|---|---|---|
| J1 | Charte d'une page : utilisateur, décision, coût, « utile », **hors périmètre**, **propriétaire des données**, **champs personnels et protection** | ✅ [`01_charte.md`](01_charte.md) couvre les sept rubriques |
| J1 | Une phrase ML ou LLM | ✅ dans la charte, reprise dans le README et le discours |
| J1 | Diagramme d'architecture v1 | ✅ [`diagrams/png/01_architecture_globale.png`](diagrams/png/01_architecture_globale.png) et neuf autres schémas |
| J1 | Ingestion qui remplit la zone brute depuis la source vivante | ✅ |
| J2 | Une exécution de bout en bout, source → sortie IA | ✅ ingestion → silver → porte de qualité → score → dérive → gold → porte de qualité, dans Airflow et dans GitHub Actions |
| J2 | **Un chiffre de qualité défendable** | ✅ F1 macro **0,8027** sur un test 100 % naturel tenu à l'écart ; cinq variantes comparées ([`evidence/reglage_hyperparametres.md`](evidence/reglage_hyperparametres.md), ADR 0006 et 0007) |
| J2 (facultatif) | FastAPI ou Streamlit, Docker | ✅ les trois : `docker compose` complet (MLflow, API, tableau de bord, Airflow sur PostgreSQL) ; test automatisé de la pile déployée : **16 contrôles sur 16**, rejoué le 21/09 sur la pile redémarrée avec le code premium |
| J3 | **Le dépôt** | ✅ public, intégration continue verte : 144 tests, 27 mutations sur 27 tuées en un seul passage |
| J3 | **Le diagramme** | ✅ dix schémas, sources Mermaid versionnées |
| J3 | **La présentation** : 10 min, démonstration en direct, puis 5 min de questions — cas métier, choix ML ou LLM, conception de la chaîne, **« what you would build next »** | ✅ [`presentation/ReviewPulse_DemoDay.pptx`](presentation/ReviewPulse_DemoDay.pptx) sur le gabarit Jedha ; [discours mot pour mot](presentation/discours_demo_day.md) ; [minutage](presentation/script_10_minutes.md) ; la dernière diapositive et la minute 8:00–9:20 nomment les manques un par un |
| J3 | **La démonstration qui marche** | ✅ la pile tourne et répond · ⛔ **répétition chronométrée : Enzo** (R05) |

## Les attendus implicites, relevés dans l'énoncé

| Attendu | État |
|---|---|
| « Real data, or the project is a toy » : une source qui se met à jour, qui a des trous, qui oblige à transformer | ✅ avis récents, textes vides, BBCode, doublons, identifiants personnels |
| Données personnelles protégées « comme dans le module gouvernance » | ✅ HMAC-SHA256 salé, suppression des identifiants directs, sel obligatoire sans valeur par défaut (ADR 0004) |
| « The model is the easy part » : la chaîne d'abord | ✅ le modèle est une boîte du schéma ; neuf tâches autour de lui |
| Pouvoir dire en une phrase pourquoi ML | ✅ |
| **Équipe de deux ou trois**, chacun explique toute la chaîne | ⚠ le projet est porté par une seule personne : un fait à dire si la question vient, pas un manque à combler |

## Deux consignes, et pourquoi le projet répond aux deux

Il existe **deux** énoncés de Final Project sur Julie. **C'est v2 qui prime** : c'est le parcours
inscrit, et la charte le cite depuis le 16/09. Enzo a demandé que le projet couvre aussi v1
(`dse-lead`, *Project Overview*, versé dans
[`00_sources/2026-09-20_julie_demo_day_project_overview.md`](00_sources/2026-09-20_julie_demo_day_project_overview.md)) :

| Exigence propre à **v1** | État | Preuve |
|---|---|---|
| « Tune hyperparameters » | ✅ | [`evidence/reglage_hyperparametres.md`](evidence/reglage_hyperparametres.md) — 12 points, `C=10.0` promu par la barrière |
| Rapport sur le jeu de données et le prétraitement | ✅ | [`20_rapport_donnees.md`](20_rapport_donnees.md) |
| Documentation de l'API | ✅ | [`21_guide_api.md`](21_guide_api.md) |
| Surveillance de la **latence** | ✅ | point d'accès `/metrics`, ADR 0029 |
| Instructions pour exécuter et déployer | ✅ | [`22_runbook_deploiement.md`](22_runbook_deploiement.md) |
| Vidéo de la solution en production | ⛔ | Enzo (R03) |

**La tension à connaître** : v1 exige de régler les hyperparamètres, v2 dit de **ne pas** y passer
le projet. Les deux sont satisfaites — le réglage est fait et mesuré — mais **la présentation suit
v2** : la chaîne d'abord. Si le jury interroge le réglage, la réponse tient en deux phrases.

## Les écarts connus, à assumer devant le jury

1. **Précision des avis négatifs : 0,633.** Environ un avis signalé sur trois est en réalité positif. Pour un outil de *priorisation de lecture*, une lecture inutile coûte peu ; le rappel (0,650) compte davantage.
2. **Seuil de promotion revu de 0,80 à 0,75** après mesure ; l'objectif de 0,80 est atteint depuis (0,8027). Histoire complète : ADR 0008.
3. **La mesure de biais par langue et par jeu manque.** L'AI Act la demande ; c'est dit sur la dernière diapositive, pas masqué (ADR 0021).
4. **Le pipeline tourne en conteneurs locaux et sur GitHub Actions**, pas dans un cloud public ; la cible est décrite (schéma 06, ADR 0012).
5. **Airflow tient dans un seul conteneur** (`standalone`, base PostgreSQL) : adapté à la démonstration, pas à la production (ADR 0011).
6. **L'essai de charge est mesuré sur une seule machine** : 300 requêtes, 0 % d'erreur, p99 925 ms à chaud, 5 874 ms au premier appel à froid. L'un ne s'annonce jamais sans l'autre.

## Ce qui reste avant le 25/09 — rien ne dépend plus du code

- ⛔ **Répétition chronométrée** de la démonstration, dix minutes (R05) — Enzo.
- ⛔ **Vidéo** de la démonstration, qui sert aussi de secours le jour J (R03) — Enzo.
- ⛔ Faire confirmer par Jedha : passage seul ou en équipe, heure de passage.
- ⛔ Suppression de l'ancien dépôt `KinSushi/reviewpulse` (R02) — Enzo.

L'état détaillé de chaque sujet, avec son critère de fin et sa preuve, vit dans
[`16_registre_suivi.md`](16_registre_suivi.md) ; le dernier état prouvé de bout en bout, dans
[`19_known_good.md`](19_known_good.md).

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
