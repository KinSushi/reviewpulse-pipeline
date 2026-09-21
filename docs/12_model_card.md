# Model Card — ReviewPulse

## 1. Identité
- **Nom du modèle** : `reviewpulse-sentiment` (`config.MODEL_NAME`), enregistré dans le registre MLflow.
- **Version** : la version courante est celle que porte l'alias `champion` dans le registre ; le registre a été perdu avec le volume Docker le 16/09/2026 et sera reconstitué au prochain entraînement.
- **Alias dans le registre** : `challenger` (version candidate) et `champion` (version en service).
- **Date de création** : 16/09/2026 (mesures de référence citées ci-dessous).
- **Responsable** : Enzo.
- **Dépôt** : dépôt git local, branche `plateforme-v3` ; la mise en ligne du dépôt public reste à faire (décision d'Enzo).

## 2. Usage prévu
- **Décision servie** : chaque matin, sélectionner les avis Steam négatifs à remonter à l’équipe de développement, par jeu et par langue, avec une priorité.
- **Utilisateur visé** : le·la responsable *community & live-ops* d’un studio de jeu vidéo publiant sur Steam.
- **Ce que le modèle ne doit pas servir à faire** : aucune modération automatisée, aucune prise de décision affectant directement les joueurs, aucune diffusion d’avis en texte intégral, aucune utilisation hors du cadre d’analyse agrégée.

## 3. Données
- **Source** : API publique des avis Steam (`store.steampowered.com/appreviews`).
- **Volumes** : 6 000 avis naturels (3 jeux × anglais et français) ; 2 797 avis négatifs complémentaires bruts, 2 254 après dédoublonnage.
- **Flux** :
  - *Flux naturel* – avis collectés sans filtre, utilisés pour l’entraînement et le test.
  - *Flux complémentaire* – avis négatifs (`review_type=negative`), utilisés **uniquement** pour l’entraînement.
- **Langues** : anglais et français uniquement.
- **Pseudonymisation** : `author.steamid` est transformé en pseudonyme HMAC-SHA256 avec un sel obligatoire ; les champs `author.personaname`, `profile_url` et `avatar` sont supprimés dès la zone propre.
- **Ce qui est supprimé** : identifiants directs (`steamid`) et informations de profil, conformément à l’ADR 0004.

## 4. Modèle
- **Représentation du texte** : TF-IDF caractères (`analyzer="char_wb"`, n-grammes 2-5, `min_df=2`, `max_features=100 000`, `sublinear_tf=True`).
- **Algorithme** : régression logistique (`C=10.0`, `class_weight="balanced"`, `max_iter=2000`). `C=10.0` depuis le 20/09/2026, retenu sur mesure : recherche à 12 points, validation croisée à 5 plis, F1 macro 0,7517 contre 0,7437 pour `C=4.0`. La **barrière de promotion a promu** ce modèle (version 5, F1 macro 0,8027) et **refusé** le même jour un modèle réentraîné à `C=4.0` (version 6, 0,7997). Réserve inscrite : l'écart entraînement-test passe de 0,118 à 0,153. Voir `docs/evidence/reglage_hyperparametres.md`.
- **Fonction de coût** : entropie croisée binaire (perte logistique), minimisée par L-BFGS. Les classes sont repondérées par `class_weight="balanced"` : chaque classe pèse en raison inverse de son effectif, ce qui compense les 9 % d'avis négatifs sans modifier les données. La régularisation est de type L2, d'intensité `C=10.0` (voir ci-dessus).
- **Seuil de décision** : **0,775** pour la version 5 en service (0,75 pour les versions 1 à 4). Choisi par validation croisée à 5 plis sur les données d’entraînement naturelles (ADR 0007). Le seuil est stocké dans l’attribut `decision_threshold_` du modèle : il voyage avec lui.
- **Pourquoi cette famille de modèles** : neuf candidats de cinq familles ont été mesurés le 21/09/2026 sur les mêmes plis et le même protocole (ADR 0030, `docs/evidence/comparaison_modeles.md`). La régression logistique arrive première (F1 macro hors plis 0,8116) ; la SVM linéaire est à égalité statistique (0,8072, écart inférieur à l'écart-type des plis de 0,017) mais perd l'explication exacte ; XGBoost (0,7345), le gradient boosting sur SVD (0,7360) et la forêt aléatoire (0,7189) sont à quatre ou cinq écarts-types derrière, XGBoost coûtant 23 fois l'entraînement. La règle de décision a été écrite avant de lire les résultats. Aucun transformeur n'a été mesuré.

## 5. Évaluation
- **Protocole** : jeu de test 100 % naturel, tenu à l’écart, stratifié.
- **Métriques du champion en service** (version 5, mesurées le 20/09/2026) :
  - F1 macro = **0,8027** (barrière de promotion ≥ 0,75).
  - AUC classe négative = 0,940.
  - Rappel négatif = 0,650.
  - Précision négative = 0,633.
- **Historique** : 0,807 de F1 macro le 16/09/2026 sur le premier registre (AUC 0,948, rappel 0,639, précision 0,657) ; 0,797 le 19/09 sur un jeu élargi par l'ingestion ; chaque run porte l'empreinte de son jeu de données (ADR 0018).
- **Barrière de promotion** : F1 macro ≥ 0,75 et strictement supérieur au champion en place (ADR 0008).

## 6. Limites et risques connus
- **Déséquilibre des classes** : seulement 9 % des avis sont négatifs.
- **Couverture linguistique** : limité à l’anglais et au français ; les avis dans d’autres langues ne sont pas traités.
- **Biais possibles** : biais lié aux trois jeux étudiés, aux langues supportées et à la proportion de négatifs.
- **Ce qui n’est pas mesuré** : nuance de sentiment, détection de harcèlement, impact sur la satisfaction globale des joueurs.

## 7. Considérations éthiques et données personnelles
- Rétention de la zone brute : 30 jours (`config.RAW_RETENTION_DAYS`), accès restreint ; la zone propre ne contient que le pseudonyme.
- La pseudonymisation suit l’ADR 0004. La base légale envisagée est l’intérêt légitime (RGPD, art. 6.1.f) : elle reste **à valider par le DPO**, et la donnée pseudonymisée demeure une donnée personnelle (RGPD, considérant 26 et art. 4.5).
- Registre AI Act : système à risque minimal (classement de sentiment, sans décision portant sur des personnes), d’après la charte.
- Aucun texte d’avis n’est affiché en entier sur le tableau de bord public.
- Le modèle ne prend pas de décision automatisée sur les joueurs.

## 8. Suivi en production
- **Journalisé** : paramètres, métriques (F1, AUC, rappel, précision, seuil) et artefacts (`top_terms.json`) dans MLflow ; résultats des tests automatisés (62 verts au 17/09/2026 : 54, plus 4 Spark et 4 dbt) ; contrôles de la stack déployée (12 / 12).
- **À mettre en place** : suivi de dérive de données, alertes sur la performance du modèle, validation du ré-entraînement hebdomadaire (existant dans le DAG mais non vérifié), tableau de bord de santé du modèle.

## 9. Traçabilité
- **Documents à consulter** :
  - ADR 0004 – Pseudonymisation HMAC salée.
  - ADR 0006 – Modèle ML sur n-grammes de caractères.
  - ADR 0007 – Avis négatifs complémentaires et seuil appris.
  - ADR 0008 – Barrière de promotion et alias MLflow.
  - ADR 0009 – Convention de décision centralisée.
  - Charte du projet (`docs/01_charte.md`).
  - README (`README.md`).

*Les mesures citées datent du 16/09/2026.*

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
