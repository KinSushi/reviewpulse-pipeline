# ADR 0002 — Zone brute inchangée, idempotence par manifeste

**Date** : 16/09/2026 · **Statut** : acceptée

## Contexte

L'énoncé exige un dépôt **brut et inchangé** avant toute transformation, et une ingestion **idempotente** : relancer ne crée aucun doublon. L'API renvoie les avis du plus récent au plus ancien ; deux passages successifs se recouvrent presque entièrement.

## Décision

- Une ligne JSONL = l'objet `review` **exactement tel que reçu** (`json.dumps`, sans ajout ni retrait).
- Partitionnement `app_id=…/language=…/dt=…` ; le flux complémentaire (ADR 0007) sous `sample=negative_boost/`.
- Un **manifeste** par flux, jeu et langue liste les identifiants déjà écrits ; seuls les nouveaux sont écrits.
- Ordre d'écriture : manifeste temporaire → lot temporaire → `os.replace` du lot → `os.replace` du manifeste. Aucun avis brut ne peut exister sans être référencé.
- Pagination arrêtée sur : page sans nouvel avis, page vide, curseur répété, nombre maximal de pages.

## Alternatives écartées

| Option | Pourquoi écartée |
|---|---|
| Dédoublonner seulement en aval | La zone brute grossirait sans fin ; l'énoncé demande l'idempotence à l'ingestion |
| Ajouter des métadonnées dans chaque ligne | L'objet ne serait plus « inchangé » ; les métadonnées vivent dans le chemin |
| Base de données pour le manifeste | Surdimensionné pour quelques milliers d'identifiants par flux |

## Conséquences

- Les chemins du flux naturel ne doivent **jamais** changer : des données réelles existent déjà (règle de compatibilité du contrat de code).
- Un passage interrompu se rejoue sans risque.

## Preuves

- 16/09/2026, exécution réelle : 6 000 avis au premier passage, **0** au second ; 6 000 identifiants distincts pour 6 000 lignes.
- Défaut trouvé en exécution réelle et corrigé : le dossier du manifeste n'était pas créé, le lot brut était écrit mais pas le manifeste, et le second passage réécrivait les 1 000 mêmes avis. Test de non-régression : `tests/test_fresh_dirs.py`.
- Tests : `test_ingest.py`, `test_fresh_dirs.py`, `test_boost.py`.
