# ADR 0016 — Déploiement progressif champion / challenger

**Date** : 18/09/2026 · **Statut** : proposée

## Contexte

Actuellement, la promotion d’un challenger au statut de champion est binaire : dès que le challenger franchit la barrière définie dans l’ADR 0008, il devient le modèle servi à 100 % du trafic `/predict`.
Le programme AIA 4 impose un déploiement progressif (tests A/B ou canari) afin de comparer en production les performances du challenger et du champion avant toute bascule définitive.

## Décision

- Introduire une part configurable du trafic `/predict` qui sera servie par le modèle **challenger**.
- La proportion est lue dans la variable d’environnement `REVIEWPULSE_CHALLENGER_TRAFFIC` (float : 0 → 1). Valeur par défaut : `0` (aucun trafic challenger).
- Le routage est déterministe : pour chaque requête, on calcule un hash (ex. SHA-256) de l’identifiant de requête (`request_id` fourni dans le header `X-Request-ID` ou, à défaut, d’un hash du corps). Les huit premiers octets du hash, ramenés dans l'intervalle [0, 1) par division par 2^64, sont comparés à la valeur de `REVIEWPULSE_CHALLENGER_TRAFFIC` ; le même appel reçoit toujours le même modèle.
- La réponse `/predict` inclut le champ `model_version` ainsi qu’un nouveau champ `served_by` indiquant `champion` ou `challenger`.
- L’alias `champion` continue d’être utilisé par le code existant (`score.py`, tableaux de bord) ; le challenger est chargé via l’alias `challenger` mais n’est jamais exposé comme `champion` tant que la proportion n’est pas égale à 1.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Bascule binaire conservée | Contredit l’exigence de déploiement progressif et empêche la comparaison en production. |
| Ombre (challenger score sans répondre) | Ne fournit pas de données d’impact réel sur le trafic réel, limite la mesure de la latence et du comportement client. |
| Passerelle externe (service de routage) | Complexité supplémentaire, dépendance à une infrastructure tierce non justifiée pour un simple pourcentage de trafic. |

## Conséquences

- **Implémentation** : le service devra charger simultanément les deux modèles (`champion` et `challenger`) en mémoire, augmentant l’utilisation du CPU/VRAM.
- **Mesure** : les logs et les tableaux de bord devront distinguer les deux versions afin de comparer les métriques (F1, latence, taux d’erreur) en temps réel.
- **Pas de retour arrière automatique** : si le challenger montre une régression, aucune bascule automatique n’est prévue ; il faut réduire `REVIEWPULSE_CHALLENGER_TRAFFIC` ou ré-promouvoir le champion via l’ADR 0008.
- **Compatibilité** : les clients existants continuent de recevoir `model_version` et `decision_threshold` comme auparavant ; le nouveau champ `served_by` est optionnel pour les clients qui ne le lisent pas.

## Preuves

- Décision **proposée**, aucune implémentation ni mesure à ce jour.
- Aucun test automatisé ou métrique de production disponible pour valider le comportement.
