# ADR 0026 — Tracing des explications

**Date** : 20/09/2026 · **Statut** : acceptée

## Contexte

Le référentiel AIA 4 classe le *tracing* parmi les moyens d’explicabilité.  
Dans ReviewPulse, les explications sont générées à la volée par les fonctions
`global_terms`, `local_contributions` et `explain_batch` du module
`src/reviewpulse/explain.py`.  
Elles ne sont jamais persistées : chaque affichage du tableau de bord
recalcule les contributions à partir du modèle et du texte.  
Le modèle en production est identifié par l’alias `champion` du registre
MLflow (voir ADR 0018) et chaque run MLflow porte les métadonnées
`code_commit` et l’empreinte du jeu de données.  
Une mutation de test, M21, inverse le signe des coefficients de la classe
négative et est détectée par le test
`tests/test_explain.py::test_somme_contributions_égale_decision_function`.

## Decision

Le terme *tracing* recouvre deux notions distinctes :

| Notion | Description |
|---|---|
| Tracing d’**exécution** | Enregistrement des appels, latences et flux d’exécution (ex. OpenTelemetry). |
| Tracing de **décision** | Enregistrement de *quelle* explication a été fournie pour *quel* avis, avec la version du modèle utilisée et le moment de la génération. |

Pour un projet qui doit rendre des comptes sur ses prédictions, le tracing de décision est le seul qui répond aux exigences de traçabilité réglementaire : il permet de prouver quelle logique a conduit à chaque décision et de la reproduire si nécessaire. Le tracing d’exécution, bien qu’utile pour le monitoring technique, ne fournit aucune information sur le raisonnement de la prédiction.

**Nous décidons de mettre en place un tracing de décision**.  
Lors de chaque appel de l’API `/explain` (ou lors du rendu du tableau de bord),
les informations suivantes seront enregistrées :

* `review_id` : identifiant de l’avis (ou du lot d’avis) concerné.
* `model_version` : alias `champion` ou identifiant de run MLflow (inclut `code_commit`).
* `contributions` : liste des paires `(terme, contribution)` retournées par
  `local_contributions` (ou `explain_batch` pour un lot).
* `timestamp` : horodatage ISO du moment de la génération.

Ces métadonnées seront stockées dans le **metadata store** de MLflow,
associées au run correspondant, afin d’être consultables via l’interface
MLflow ou via une requête interne.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Aucun tracing de décision | Impossible de prouver rétroactivement la logique d’une prédiction, non conforme aux exigences d’audit. |
| Tracing d’exécution uniquement (OpenTelemetry) | Fournit des métriques techniques mais aucune visibilité sur le raisonnement de la décision. |
| Persistance des explications dans une base séparée sans lien modèle | Redondant avec le métastore MLflow déjà disponible et risque de désynchronisation avec les versions de modèle. |

## Consequences

* **Traçabilité** : chaque explication est désormais liée à une version de modèle et à un horodatage, satisfaisant les exigences de responsabilité.
* **Reconstruction** : grâce aux métadonnées `code_commit` et à l’empreinte du jeu de données, il est possible de reconstituer le modèle exact (`champion` à ce commit) et, en disposant du texte original, de recalculer les contributions. La reconstruction s’arrête si le texte original n’est pas conservé ; le tracing de décision ne stocke pas le texte lui‑même, uniquement les contributions.
* **Impact sur la charge** : l’ajout d’un enregistrement MLflow est léger comparé aux appels de calcul déjà effectués.
* **Maintenance** : la logique de persistance repose sur les fonctions existantes du module `explain.py`; aucune nouvelle dépendance n’est introduite.
* **Audit** : les équipes de conformité peuvent interroger le store MLflow pour obtenir, pour tout avis, la version du modèle, les contributions et le moment de la génération, sans devoir recomposer l’ensemble du pipeline.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
