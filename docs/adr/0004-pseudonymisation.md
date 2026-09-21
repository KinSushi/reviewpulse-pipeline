# ADR 0004 — Pseudonymisation HMAC salée, sel obligatoire

**Date** : 16/09/2026 · **Statut** : acceptée

## Contexte

L'API renvoie `steamid` (identifiant stable), `personaname`, `profile_url` et `avatar`. Le modèle n'en a pas besoin ; l'analyse par auteur (un joueur qui poste plusieurs fois) peut en avoir besoin.

## Décision

- Zone propre : `author_pseudo = HMAC-SHA256(sel, steamid)` ; suppression de `personaname`, `profile_url`, `avatar` et `steamid`.
- Le sel est un **secret obligatoire** (`REVIEWPULSE_SALT`), **sans valeur par défaut** ; `config.salt()` refuse un sel absent ou vide.
- Le contrôle est fait **dans l'application**, pas dans Docker Compose.
- Zone brute : conservée telle que reçue (ADR 0002), accès restreint, rétention 30 jours.
- Tableau de bord : aucune information d'auteur ; texte tronqué à 200 caractères.

## Alternatives écartées

| Option | Pourquoi écartée |
|---|---|
| Hachage SHA-256 simple | Réversible par dictionnaire : les `steamid` sont des entiers sur 17 chiffres, énumérables |
| Suppression pure de `steamid` | Perd l'analyse par auteur sans gain de confidentialité par rapport au HMAC |
| Contrôle du sel dans Compose (`${VAR:?}`) | Essayé le 16/09/2026 : bloquait aussi `docker compose ps` et `down` |

## Conséquences

- Pseudonymes stables tant que le sel est conservé : le sel se range dans un gestionnaire de secrets (secret GitHub en CI).
- Changer de sel rend les anciens pseudonymes non comparables : c'est aussi un moyen de rotation.

## Preuves

- 16/09/2026 : job lancé **sans sel** → code de sortie 1, message explicite, **zone propre non modifiée** (date de modification identique).
- Tests : `test_transform_quality.py` (pseudonyme sur 64 hexadécimaux, stable, colonnes interdites absentes, sel absent refusé) ; contrôle F3 de `tools/forward_test.py`.
- Référence : RGPD, considérant 26 et article 4.5 (la donnée pseudonymisée reste une donnée personnelle) ; base légale envisagée : intérêt légitime (art. 6.1.f), à valider par le DPO.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
