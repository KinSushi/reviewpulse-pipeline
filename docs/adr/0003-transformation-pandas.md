# ADR 0003 — Transformation en pandas

**Date** : 16/09/2026 · **Statut** : acceptée

## Contexte

L'énoncé autorise dbt, PySpark ou pandas. Le volume réel est de l'ordre de 10 000 avis (8 797 lignes brutes le 16/09/2026), quelques mégaoctets.

## Décision

pandas, avec une zone propre en un seul fichier Parquet réécrit atomiquement à chaque exécution.

## Alternatives écartées

| Option | Pourquoi écartée |
|---|---|
| PySpark | Démarrage d'une JVM pour quelques Mo : coût sans bénéfice ; reste la voie de passage à l'échelle |
| dbt | Suppose un entrepôt SQL ; la transformation principale (nettoyage de texte, HMAC) est plus lisible en Python |

## Conséquences

- Temps de transformation de l'ordre de la seconde.
- **Seuil de bascule** : au-delà d'environ 10 millions d'avis ou d'une mémoire insuffisante, passer en PySpark (lecture par partition) ou pousser le brut dans un entrepôt et transformer en dbt. Le contrat d'entrée et de sortie (`CLEAN_COLUMNS`) ne change pas.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
