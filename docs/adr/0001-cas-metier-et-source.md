# ADR 0001 — Cas métier : avis Steam, API publique

**Date** : 16/09/2026 · **Statut** : acceptée

## Contexte

L'énoncé Jedha impose un cas métier réel, des données réelles « qui se mettent à jour, ont des trous et obligent à transformer », et un usage légal. Le sujet est libre.

## Décision

Aider une équipe *community & live-ops* à lire en priorité les avis négatifs, à partir de l'API publique `store.steampowered.com/appreviews/<appid>?json=1`, sur trois jeux (1903340, 1086940, 2622380) en anglais et en français.

## Alternatives écartées

| Option | Pourquoi écartée |
|---|---|
| Jeux de données Kaggle ou Hugging Face | Figés : pas de flux, donc pas d'idempotence ni d'orchestration à démontrer |
| Collecte par scraping (Trustpilot, Google Play) | Conditions d'utilisation plus restrictives ; fragilité du HTML |
| Données bancaires synthétiques du Demo Day Fullstack | Déjà présentées pour le bloc 6 du CDSD ; l'énoncé exige des données trouvées, réelles |
| Actualités RSS avec un LLM | Pas d'étiquette disponible : la qualité ne se mesurerait qu'avec une grille manuelle |

## Conséquences

- Étiquette gratuite et fiable : `voted_up` (l'auteur dit lui-même s'il recommande).
- Données personnelles présentes (`steamid`, pseudonyme, profil, avatar) : voir ADR 0004.
- Tâche = **analyse de sentiment sur un produit**, exactement le thème imposé du bloc 4 du CDSD : la chaîne est réemployable en octobre.
- Déséquilibre fort (9 % de négatifs) : voir ADR 0006 et 0007.

## Preuves

Relevé du 16/09/2026 : l'API répond sans clé ; 23 172 à 504 467 avis par jeu et par langue ; noms des jeux non vérifiés (la route `appdetails` n'a pas renvoyé de JSON).

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
