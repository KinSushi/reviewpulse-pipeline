# Conformité aux consignes du Demo Day — état au 20/09/2026

Référence : énoncé *Build a Data Pipeline That Feeds an AI Model*, relevé sur Julie le 16/09
(`00_sources/2026-09-16_sources_primaires.md`) et **relu intégralement le 20/09**
(`00_sources/2026-09-20_julie_demo_day_v2_pipeline.md`).

## Deux consignes, et pourquoi le projet répond aux deux

Il existe **deux** énoncés de Final Project sur Julie, et ils ne demandent pas la même chose.

| | Parcours | Titre | Durée | Ce qu'il met en avant |
|---|---|---|---|---|
| **v2** | `lead-data-v2` — **Data Lead** | *Build a Data Pipeline That Feeds an AI Model* | 840 min | **la chaîne** : « The model is the easy part […] The grade and the real-world value come from the chain around it » |
| **v1** | `dse-lead` — Data Sc. & Eng. Lead | *Project Overview* | 1 200 min | **le cycle de vie du modèle** : « Tune hyperparameters », rapport de données, documentation d'API |

**C'est v2 qui prime** pour le Demo Day du 25/09/2026 : c'est le parcours inscrit, et la charte
du projet la cite nommément depuis le 16/09. Mais Enzo a demandé que le projet **couvre les
deux**, et c'est le cas — les exigences de v1 ont été comblées le 20/09 sans rien retirer à v2 :

| Exigence propre à **v1** | État | Preuve |
|---|---|---|
| « Tune hyperparameters » | tenue | `docs/evidence/reglage_hyperparametres.md` — 12 points, `C=10.0` promu par la barrière |
| Rapport jeu de données et prétraitement | tenue | `docs/20_rapport_donnees.md` |
| Documentation de l'API | tenue | `docs/21_guide_api.md` |
| Surveillance de la **latence** | tenue | point d'accès `/metrics`, ADR 0029 |
| Instructions pour exécuter et déployer | tenue | `docs/22_runbook_deploiement.md` |

**La tension à connaître** : v1 exige de régler les hyperparamètres, v2 dit de **ne pas** y
passer le projet. Les deux sont satisfaites — le réglage est fait et mesuré — mais **la
présentation suit v2** : la chaîne d'abord, le modèle comme une boîte du schéma. Si le jury
interroge le réglage, la réponse existe et tient en deux phrases.

**Exigence de contenu, souvent oubliée** : v2 demande que la présentation dise
**« what you would build next »**. C'est la dernière diapositive et la minute 8:00–9:20 du
script, qui nomment les manques un par un.

**Écart assumé** : v2 prévoit des **équipes de deux ou trois**. Le projet est porté par une
seule personne. Ce n'est pas un manque à combler, c'est un fait à dire si la question vient.

### Réponse directe : le projet sert-il les deux versions ?

**Oui pour tout ce qui dépend du code, vérifié par commande le 20/09/2026 :**

| Exigence v2 | Contrôle passé | Résultat |
|---|---|---|
| 1 — données réelles trouvées | `config.STEAM_URL` | `https://store.steampowered.com/appreviews/{app_id}` |
| 2 — zone brute inchangée, idempotente | comptage de la zone brute et du manifeste | **69 fichiers, 9 410 lignes**, 12 manifestes d'état |
| 3 — transformation + test de qualité | présence des quatre modules | `spark_silver.py`, `dbt_project.yml`, `expectations.py`, `expectations_lake.py` |
| 4 — étape d'IA suivie par MLflow | occurrences dans `train.py` | 33 |
| 5 — une partie s'exécute seule | DAG et workflows | 2 DAG, 2 workflows GitHub Actions |

**Non pour trois livrables, et ce sont les mêmes pour les deux versions.** Ils ne dépendent pas
du code :

| | Exigé par | Qui |
|---|---|---|
| Le **dépôt publié** — v2 le liste parmi les livrables du jour 3, v1 l'exige nommément | v1 **et** v2 | Enzo (R01) |
| La **vidéo** de la solution en production | v1 | Enzo (R03) |
| La **démonstration en direct**, répétée et chronométrée | v1 **et** v2 | Enzo (R05) |

**La chaîne d'intégration est prête** : `ci.yml` se déclenche sur `push:` toutes branches — le
défaut ancien, « ne se déclenche que sur `main` », est corrigé. Elle tournera sur
`plateforme-v3` dès la publication, sans autre intervention.

**Avertissement daté.** Les ✅ marqués « 16/09 » s'appuyaient sur un registre MLflow et des images **détruits le 16/09 au soir** avec le volume Docker. Tout a été reconstruit et reprouvé les 18 et 19/09, et le 19/09 au soir l'ensemble a été rejoué **le même jour sur le même arbre** : batterie **131 tests** (20/09), tests inverses **26 mutations sur 26**, test de stack **16 contrôles sur 16**, DAG quotidien à **9 tâches**, et un essai de charge à **0 % d'erreur**, 29,3 requêtes par seconde, p99 925 ms. Le détail figure au journal et dans `docs/16_registre_suivi.md`.

**Légende.** ✅ vérifié par exécution le 16/09 · 🟡 écrit, pas encore exécuté dans son environnement cible · ⬜ à faire · ⚠ écart ou risque.

## Les cinq exigences non négociables

| # | Exigence de l'énoncé | Réponse de ReviewPulse | Preuve | État |
|---|---|---|---|---|
| 1 | Cas métier réel, données réelles trouvées | Priorisation des avis négatifs Steam pour une équipe community & live-ops ; API publique des avis Steam | `01_charte.md` ; 6 000 avis réels collectés sur 3 jeux × 2 langues | ✅ |
| 2 | Données déposées **brutes et inchangées** dans une première zone | JSONL, une ligne = l'objet reçu, partitionné par jeu, langue et date | Test `test_ingest` (ligne relue = objet reçu) ; exécution réelle : 6 fichiers, 6 000 lignes | ✅ |
| 2b | Dépôt **idempotent** (exigence J1) | Manifeste des identifiants, écriture atomique | Second passage réel : **0 nouvel avis**, 6 000 identifiants uniques pour 6 000 lignes ; tests `test_fresh_dirs` | ✅ |
| 3 | Transformation en jeu propre avec dbt, PySpark **ou pandas** | pandas : dédoublonnage, BBCode, types, pseudonymisation | Exécution réelle : 5 974 lignes propres ; types contrôlés | ✅ |
| 3b | **Au moins un test de qualité** | 9 contrôles **bloquants** avant écriture de la zone propre | `quality.py`, tests dédiés | ✅ |
| 4 | Étape d'IA qui consomme la sortie, **ML suivi avec MLflow** | Régression logistique sur n-grammes de caractères, serveur MLflow, alias `champion` / `challenger`, barrière de promotion | Au 16/09 : F1 macro **0,807**, AUC 0,948, promotion et non-promotion vérifiées (versions 1 à 5). Ce registre a été **détruit avec le volume Docker le 16/09 au soir** ; il a été reconstitué le 18/09 — F1 macro **0,797**, promotion de la version 1 puis **non-promotion** d'une version à métriques égales, vérifiée à nouveau | ✅ reprouvé le 19/09 |
| 5 | Une partie de la chaîne **s'exécute seule** | DAG Airflow quotidien et hebdomadaire + workflow GitHub Actions planifié | Airflow réel : 3 exécutions quotidiennes et 1 hebdomadaire réussies ; `pipeline.yml` écrit | ✅ Airflow · 🟡 GitHub Actions (dépôt à publier) |

## Les livrables par jour

| Jour | Livrable demandé | État |
|---|---|---|
| J1 | Charte d'une page : utilisateur, décision, coût, « utile », **hors périmètre**, **propriétaire des données**, **champs personnels et protection** | ✅ `01_charte.md` couvre les sept rubriques |
| J1 | Une phrase ML ou LLM | ✅ dans la charte |
| J1 | Diagramme d'architecture v1 | ✅ `diagrams/png/01_architecture_globale.png` + 9 autres |
| J1 | Ingestion qui remplit la zone brute depuis la source vivante | ✅ |
| J2 | Une exécution de bout en bout, source → sortie IA | ✅ ingestion → propre → modèle → score → API, dans deux conteneurs distincts |
| J2 | **Un chiffre de qualité défendable** | ✅ F1 macro 0,807 sur test 100 % naturel tenu à l'écart, 0,802 en validation croisée, variantes comparées (ADR 0006 et 0007) |
| J2 (facultatif) | FastAPI ou Streamlit, Docker | ✅ `docker compose` complet (MLflow, API, tableau de bord, Airflow **sur PostgreSQL**), services sains ; tableau de bord ouvert et parcouru le 19/09 ; test automatisé de la stack : 12 / 12 au 16/09, **14 / 14 au 18/09** |
| J3 | Démo en direct 10 min + 5 min de questions, dépôt, diagramme, présentation | ⬜ slides sur le gabarit Jedha, répétition, vidéo de secours |

## Les attendus implicites, relevés dans l'énoncé

| Attendu | État |
|---|---|
| Source qui se met à jour, qui a des trous et oblige à transformer | ✅ avis récents, textes vides, BBCode, doublons, 20+ langues |
| Données personnelles protégées « comme dans le module gouvernance » | ✅ HMAC salé, suppression des identifiants directs, sel obligatoire sans valeur par défaut |
| Chaîne complète à mi-J2 plutôt qu'un modèle parfait | ✅ la chaîne tourne déjà |
| Pouvoir dire en une phrase pourquoi ML | ✅ |
| **Équipe de 2 ou 3**, chacun explique toute la chaîne | ⚠ **à clarifier avec Jedha** : le parcours d'Enzo est individuel ; si le passage est en équipe, répartir ingestion, IA, automatisation |

## Les écarts connus, à assumer devant le jury

1. **Précision des avis négatifs : 0,657.** Environ un avis signalé sur trois est en réalité positif (contre un sur deux avant l'ADR 0007). Pour un outil de *priorisation de lecture*, une lecture inutile coûte peu ; le rappel (0,639) compte davantage.
2. **Seuil de promotion revu de 0,80 à 0,75** après mesure ; l'objectif de 0,80 est atteint depuis (0,807). Histoire complète : ADR 0008.
3. **Great Expectations** couvre désormais la zone propre (`expectations.py`) **et** les zones silver et gold (`expectations_lake.py`, 28 attentes, tâche `gx_lake` bloquante dans le DAG). ADR 0020.
4. **Le pipeline tourne en conteneurs locaux ou sur GitHub**, pas dans un cloud public : la fiche AIA l'admet (« dans le cloud ou on-premise ») ; la cible cloud est décrite (schéma 06).
5. **Airflow en mode `standalone`** (base SQLite, une tâche à la fois) : adapté à la démo, pas à la production (ADR 0011).

## Ce qui reste avant le 25/09

- [x] Lancer `docker compose` complet et Airflow ; tester en conditions réelles (16/09).
- [x] Tests inverses et test automatisé de la stack déployée (16/09).
- [ ] Publier le dépôt sur GitHub (KinSushi), secret `REVIEWPULSE_SALT`, premier run planifié vert.
- [ ] Vidéo de la démo en production (livrable AIA 4).
- [ ] Ajouter la suite Great Expectations.
- [ ] Slides sur le gabarit Jedha (ou `Template DemoDay Slides - projet Telco.pptx` déjà sur le disque), script de 10 min, vidéo de secours.
- [ ] Faire confirmer par Jedha : passage seul ou en équipe, heure, réemploi pour l'AIA 4.
