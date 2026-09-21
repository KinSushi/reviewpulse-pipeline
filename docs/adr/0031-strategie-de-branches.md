# ADR 0031 — Une seule ligne principale, alimentée par une branche de travail validée en CI

**Date** : 21/09/2026 · **Statut** : acceptée

## Contexte

L'ancien dépôt portait deux histoires **sans ancêtre commun** : une branche `main` de 2 commits et
une branche `plateforme-v3` qui portait tout le travail. Le sujet R16 demandait depuis le 19/09 de
trancher : « une seule ligne principale ». Le 20/09, le projet a été publié dans un dépôt propre,
`KinSushi/reviewpulse-pipeline`, dont la branche `main` **est** la ligne de `plateforme-v3`. Le
21/09, Enzo a confié la décision à l'orchestrateur.

## Décision

1. **Une seule ligne principale : `main`** du dépôt publié. Historique **linéaire** — 130 commits,
   aucun commit de fusion, vérifié par `git rev-list --merges --count`.
2. **Le travail se fait sur une branche de travail** (`premium-code` aujourd'hui). Chaque envoi y
   déclenche l'intégration continue : lint, portes, batterie, 27 mutations.
3. **`main` n'avance que par avance rapide** (`git merge --ff-only`) sur un commit que la CI a
   **déjà** validé sur la branche de travail. Jamais de fusion, jamais d'envoi direct non validé.
4. La branche locale `plateforme-v3` est le nom local de `main` ; elle suit `propre/main`.
5. **Gel** : l'étiquette `v1.0-demoday` sera posée le 24/09 sur le dernier commit vert.

## Ce que la mesure en dit

La nuit du 20 au 21/09, la branche de travail a connu **quatre passages rouges pour trois causes** :
un `except … as exc` devenu inutile dans un module rendu par un arbitre (`ruff` F841) ; une batterie
qui remplaçait tout le paquet par des faux dans `sys.modules` ; une assertion décalée d'un caractère.
**Aucun n'a atteint `main`.** C'est la preuve que la règle 3 sert à quelque chose : avec des envois
directs, `main` aurait été rouge quatre fois pendant qu'Enzo lisait le dépôt.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Fusionner l'ancienne `main` dans la ligne de travail (`--allow-unrelated-histories`) | Deux commits sans valeur, dont les messages portent une signature d'outil : ils violeraient la règle « aucune mention d'outil », vérifiée en CI. L'ancien dépôt est à supprimer (R02) |
| GitFlow (`develop`, branches de version) | Un seul développeur, une seule version à livrer le 25/09 : de la cérémonie sans bénéfice |
| Envois directs sur `main` | Quatre passages rouges en une nuit seraient arrivés sur la branche que le jury lit |
| Demandes de fusion avec relecture obligatoire | Personne pour relire ; la relecture est tenue par les portes mécaniques et la CI |

## Conséquences

- Les anciennes branches locales (`great-expectations`, `propre-main`, `propre-premium`,
  `premium-documentation`, l'ancienne `main`) ne sont **pas supprimées** — règle du projet : rien ne
  se supprime sans décision d'Enzo — et ne sont pas publiées dans le dépôt propre.
- Une **protection de branche** sur `main` (« exiger que la CI soit verte ») rendrait la règle 3
  mécanique côté GitHub. C'est un réglage du compte d'Enzo : il est proposé, pas imposé.
- Condition de révision : l'arrivée d'un second contributeur — la relecture par demande de fusion
  deviendrait alors la règle.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
