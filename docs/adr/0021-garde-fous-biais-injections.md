# ADR 0021 — Garde-fous : biais et injections

**Date** : 20/09/2026 · **Statut** : acceptée

## Contexte

Le référentiel AIA 4 impose des garde‑fous contre les biais et les injections.  
Le modèle déployé est une régression logistique sur vectorisation TF‑IDF ; il ne génère pas de texte, il renvoie une classe et une probabilité. Ainsi, une injection de prompt n’a aucune influence sur le modèle.  

L’API FastAPI expose l’endpoint `/predict` qui accepte un corps JSON `{"texts": [...]}` et impose une borne : 1 ≤ nombre de textes ≤ N (N = 100 dans le code). Cette contrainte est vérifiée par la validation Pydantic et confirmée par la mutation **M12** tuée (`tests/test_api.py::test_predict_too_many_texts_422`).  

Les données d’entraînement sont des avis Steam publics en anglais et en français. L’entraînement utilise `class_weight="balanced"` pour compenser le déséquilibre global des classes, mais aucune mesure de biais par sous‑population (langue ou jeu) n’est présente dans le dépôt.  

Le projet est porté par une seule personne et soutenu le 25/09/2026.

## Decision

Nous **assumons l’absence** de garde‑fous de biais (mesure de performance différenciée par langue et par jeu) et consignons cette situation.  
Raison : le modèle ne subit aucun risque d’injection de prompt, et la mise en place immédiate de métriques de biais nécessiterait des travaux d’ingénierie (extraction, agrégation et stockage des métriques par langue et par `app_id`) qui ne sont pas prévus dans le sprint actuel.  

Condition de retour : dès que les ressources (temps de développement ou aide externe) seront disponibles, nous implémenterons :
* le calcul des métriques (ex. `f1_macro`, `recall_negative`, `precision_negative`, `roc_auc`) séparément pour chaque langue (`english`, `french`);
* le calcul des mêmes métriques séparément pour chaque jeu (`app_id`);
* l’ajout de ces métriques aux artefacts MLflow et à l’endpoint `/insights` afin de les rendre consultables.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Implémenter immédiatement les métriques de biais par langue et par jeu | Nécessite du temps de développement et des modifications du pipeline d’évaluation qui ne sont pas disponibles dans le planning actuel. |
| Ignorer totalement le problème de biais | Le référentiel AIA 4 impose explicitement des garde‑fous ; l’absence non documentée serait non conforme. |
| Modifier le modèle pour le rendre génératif afin de couvrir les injections | Le modèle est conçu comme un classifieur linéaire ; changer son type introduirait une complexité majeure et n’est pas justifié par le risque d’injection. |

## Consequences

* **Ce qui n’est pas impacté** : aucune injection de prompt ne peut affecter le classifieur linéaire ; la borne du nombre de textes par requête continue de protéger la disponibilité du service (preuve par mutation M12).  
* **Ce qui est coûté** : l’absence de mesures de biais expose le projet à un risque de discrimination non détectée entre les langues et les jeux, et constitue une non‑conformité au référentiel AIA 4 tant que la situation n’est pas rectifiée.  
* **Ce qui n’est pas coûté** : aucune dégradation des performances de prédiction, aucune surcharge de calcul, aucune modification du code existant n’est requise pour le moment.  
* **Plan d’action** : la documentation de cette absence constitue le garde‑fou administratif requis ; le retour à l’implémentation sera déclenché dès que les ressources seront allouées, conformément à la condition de retour définie ci‑dessus.  

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
