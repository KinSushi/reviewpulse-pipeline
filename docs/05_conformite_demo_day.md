# Conformité aux consignes du Demo Day — état au 16/09/2026

Référence : énoncé *Build a Data Pipeline That Feeds an AI Model*, relevé sur Julie le 16/09 (`00_sources/2026-09-16_sources_primaires.md`).

**Légende.** ✅ vérifié par exécution le 16/09 · 🟡 écrit, pas encore exécuté dans son environnement cible · ⬜ à faire · ⚠ écart ou risque.

## Les cinq exigences non négociables

| # | Exigence de l'énoncé | Réponse de ReviewPulse | Preuve | État |
|---|---|---|---|---|
| 1 | Cas métier réel, données réelles trouvées | Priorisation des avis négatifs Steam pour une équipe community & live-ops ; API publique des avis Steam | `01_charte.md` ; 6 000 avis réels collectés sur 3 jeux × 2 langues | ✅ |
| 2 | Données déposées **brutes et inchangées** dans une première zone | JSONL, une ligne = l'objet reçu, partitionné par jeu, langue et date | Test `test_ingest` (ligne relue = objet reçu) ; exécution réelle : 6 fichiers, 6 000 lignes | ✅ |
| 2b | Dépôt **idempotent** (exigence J1) | Manifeste des identifiants, écriture atomique | Second passage réel : **0 nouvel avis**, 6 000 identifiants uniques pour 6 000 lignes ; tests `test_fresh_dirs` | ✅ |
| 3 | Transformation en jeu propre avec dbt, PySpark **ou pandas** | pandas : dédoublonnage, BBCode, types, pseudonymisation | Exécution réelle : 5 974 lignes propres ; types contrôlés | ✅ |
| 3b | **Au moins un test de qualité** | 9 contrôles **bloquants** avant écriture de la zone propre | `quality.py`, tests dédiés | ✅ |
| 4 | Étape d'IA qui consomme la sortie, **ML suivi avec MLflow** | Régression logistique sur n-grammes de caractères, registre MLflow, alias `champion` / `challenger`, barrière de promotion | Run réel : F1 macro **0,753 à 0,759**, AUC **0,897 à 0,923** selon l'échantillon ; promotion automatique vérifiée | ✅ |
| 5 | Une partie de la chaîne **s'exécute seule** | DAG Airflow quotidien + workflow GitHub Actions planifié | `dags/reviewpulse_daily.py` (syntaxe vérifiée) ; `.github/workflows/pipeline.yml` | 🟡 à exécuter dans Airflow (cours du 17-18/09) et sur GitHub (22/09) |

## Les livrables par jour

| Jour | Livrable demandé | État |
|---|---|---|
| J1 | Charte d'une page : utilisateur, décision, coût, « utile », **hors périmètre**, **propriétaire des données**, **champs personnels et protection** | ✅ `01_charte.md` couvre les sept rubriques |
| J1 | Une phrase ML ou LLM | ✅ dans la charte |
| J1 | Diagramme d'architecture v1 | ✅ `diagrams/png/01_architecture_globale.png` + 9 autres |
| J1 | Ingestion qui remplit la zone brute depuis la source vivante | ✅ |
| J2 | Une exécution de bout en bout, source → sortie IA | ✅ ingestion → propre → modèle → score → API, dans deux conteneurs distincts |
| J2 | **Un chiffre de qualité défendable** | ✅ F1 macro sur test tenu à l'écart + validation croisée 5 plis (0,750 ± 0,018) ; comparaison de 4 variantes |
| J2 (facultatif) | FastAPI ou Streamlit, Docker | 🟡 API vérifiée en conteneur (`/health`, `/predict`, `/insights`, 422, 503) ; tableau de bord et `docker compose` complet **pas encore lancés** |
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

1. **Précision des avis négatifs : 0,50.** Un avis signalé sur deux est en réalité positif. Pour un outil de *priorisation de lecture*, c'est acceptable (le coût d'une lecture inutile est faible) ; le rappel (0,62–0,64) est la métrique qui compte.
2. **F1 proche de la barrière (0,75).** Un jour défavorable, la nouvelle version n'est pas promue et l'ancienne reste en service : c'est le garde-fou voulu.
3. **Seuil de promotion revu de 0,80 à 0,75** après mesure. La décision et ses chiffres sont tracés dans la charte.
4. **Great Expectations** n'est pas encore utilisé (contrôles maison) : prévu après le cours du 21/09.
5. **Le pipeline tourne en local ou sur GitHub**, pas dans un cloud public : la fiche AIA l'admet (« dans le cloud ou on-premise »).

## Ce qui reste avant le 25/09

- [ ] Lancer `docker compose` complet (MLflow serveur, API, tableau de bord) et l'Airflow du profil `airflow`.
- [ ] Publier le dépôt sur GitHub (KinSushi), secret `REVIEWPULSE_SALT`, premier run planifié vert.
- [ ] Ajouter la suite Great Expectations.
- [ ] Slides sur le gabarit Jedha (ou `Template DemoDay Slides - projet Telco.pptx` déjà sur le disque), script de 10 min, vidéo de secours.
- [ ] Faire confirmer par Jedha : passage seul ou en équipe, heure, réemploi pour l'AIA 4.
