# ADR 0028 — Gestion du backlog sans sprints

**Date** : 20/09/2026 · **Statut** : acceptée

## Contexte

Le projet ReviewPulse est porté par une seule personne.  
Il n’y a ni équipe, ni client externe, ni parties prenantes à synchroniser.  
Le dépôt contient :

* Un backlog (`docs/10_backlog.md`).  
* Un registre de suivi (`docs/16_registre_suivi.md`) où chaque ligne comporte : identifiant, sujet, source, priorité, état, critère de fin, preuve, prochaine action.  

Règle du registre : un sujet n’est fermé que lorsque son critère de fin est satisfait **et** vérifié par une preuve stockée sur disque.  

Exemples réels de fermeture :  
* R10 fermé par l’exécution du DAG montrant 4 suites de qualité, 29 attentes, zéro échec.  
* R11 fermé par un PSI mesuré à 0,0399 (seuil = 0,2).  

Exemple de non‑fermeture : un chiffre annoncé dont le journal n’existait plus a été remis en cause et le sujet rouvert.  

Le projet possède un jalon unique et immuable : le 25/09/2026.

## Decision

Un sprint sert avant tout à :

* **Coordonner plusieurs personnes** (planification, synchronisation).  
* **Négocier un engagement collectif** (définir une capacité, un objectif partagé).  

Ces deux fonctions sont sans objet pour un projet solo.  
Les cérémonies (planification, revue, rétrospective) n’apportent aucune valeur ajoutée supplémentaire à la méthode déjà en place : le registre assure la traçabilité de chaque sujet jusqu’à la preuve concrète.

Par conséquent, la méthode réellement employée est conservée : le backlog est piloté par le registre de suivi, dont la cadence est dictée par la fermeture des sujets selon leurs critères de fin et leurs preuves. Aucun calendrier de sprint ni aucune cérémonie ne sont planifiés.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Adopter un cadre de sprint (calendrier, cérémonies, vélocité) | Les fonctions principales du sprint (coordination d’équipe, engagement collectif) sont inutiles pour un projet à une seule personne ; cela introduirait une surcharge administrative sans bénéfice mesurable. |
| Mélanger sprint et registre (sprint pour planifier, registre pour clôture) | La double structure créerait une redondance : le registre suffit déjà à garantir la traçabilité et la preuve de chaque sujet, tandis que le sprint n’apporterait aucune métrique de vélocité pertinente. |

## Consequences

* **Ce que le registre tient mieux qu’un sprint**  
  - Traçabilité exacte d’un engagement jusqu’à la preuve sur disque.  
  - Garantie que la fermeture d’un sujet repose sur un critère vérifiable, pas sur une simple intention.  

* **Ce que le registre tient moins bien qu’un sprint**  
  - Absence de mesure de vélocité (nombre de points ou de sujets fermés par période).  
  - Aucun engagement temporel explicite sur un lot de travail (pas de date de « début / fin » de sprint).  

* **Impact opérationnel**  
  - Le travail continue à être planifié et suivi via le backlog et le registre, en fonction de la disponibilité du développeur.  
  - La décision restera valable tant que le projet reste monopersonnel.  

* **Quand la décision devra être revue**  
  - Dès l’arrivée d’une deuxième personne (ou plus) impliquée dans le développement, la coordination et l’engagement collectif deviendront pertinents. À ce moment‑là, l’introduction d’un cadre de sprint pourra être ré‑évaluée.  

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
