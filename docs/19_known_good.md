# Points de reprise — KNOWN_GOOD

Ce fichier existe pour qu'on n'ait **jamais** à reconstruire l'état du projet de mémoire.
Chaque entrée dit ce qui était sain, ce qui le prouvait, et comment y revenir.

**Règle** : un état n'est `KNOWN_GOOD` que si compilation, imports, exécution, test avant,
test inverse et non-régression ont été vérifiés **et datés**. Si un seul de ces éléments est
inconnu, l'état est `PARTIELLEMENT_VALIDE`, `BLOQUE` ou `EN_ECHEC` — jamais `KNOWN_GOOD`.

---

## KG-2026-09-19-a — `KNOWN_GOOD`

**Commit** : `b44a5d2` · **Date** : 19/09/2026, 17 h.

| Preuve | Résultat | Quand |
|---|---|---|
| Compilation (`compileall`) | verte | 19/09 |
| Batterie complète, copie neuve | **90 tests verts**, 53 min | 19/09 |
| Test de la stack déployée | **16 contrôles sur 16** | 19/09 |
| Tests inverses | 16 mutations sur 16, sur l'arbre du 18/09 | 18/09 |
| DAG Airflow | 8 tâches listées, aucune erreur d'import | 19/09 |
| Retour arrière du modèle | champion 2 → 1 → 2, vérifié à chaque pas | 19/09 |
| Restauration MLflow | archive restaurée dans un volume d'essai, versions 1 à 4 et alias retrouvés | 19/09 |

**Ce qui le constitue** : tout le dépôt à ce commit, plus le lac sur `D:\ReviewPulse_work\data`
(hors dépôt, intact depuis le 16/09) et les images `reviewpulse-app`, `reviewpulse-airflow`,
`reviewpulse-dev`.

**Comment y revenir** : `git checkout b44a5d2`. Le lac n'est pas versionné : il n'est pas à
restaurer, il n'a pas bougé. Les images se reconstruisent depuis le dépôt.

**Risque connu à cette date** : les tests inverses dataient de l'arbre du 18/09, avec 16
mutations et non 26.

---

## KG-2026-09-19-b — `PARTIELLEMENT_VALIDE`

**Commit** : `116c486` · **Date** : 19/09/2026, 18 h 45.

**Pourquoi pas `KNOWN_GOOD`** : depuis `b44a5d2`, quatre lots de tests ont été ajoutés et
vérifiés **isolément**, mais **aucune batterie complète n'a rendu son résultat** sur cet arbre,
et la campagne des 26 mutations tourne encore. Tant qu'elle n'a pas rendu, cet état ne peut pas
être déclaré sain.

| Preuve | Résultat | Quand |
|---|---|---|
| Compilation | verte sur chaque fichier touché | 19/09 |
| Imports | vérifiés module par module | 19/09 |
| `tests/test_expectations_lake.py` | 7 verts | 19/09 |
| `tests/test_verifier_justifications.py` | 9 verts | 19/09 |
| `tests/test_verifier_briques.py` | 9 verts | 19/09 |
| `tests/test_drift.py` | 11 verts | 19/09 |
| `make justifications` | code 0 — 20 ADR sur 20 cités dans le code **et** dans les questions | 19/09 |
| `make briques` | code 0 — 73 briques classées, chaque manque porte un sujet | 19/09 |
| Porte silver et gold, données réelles | 28 attentes vertes, témoin rouge sur données faussées | 19/09 |
| **Batterie complète** | **non rendue** | — |
| **26 mutations** | **en cours** | — |

**Ce qui manque pour passer `KNOWN_GOOD`** : la batterie complète verte et les 26 mutations
détectées sur cet arbre. La campagne est lancée ; son résultat conditionne l'étiquette.

**En cas d'échec** : revenir à `KG-2026-09-19-a` (`git checkout b44a5d2`), qui est prouvé sain.

---

## Comment se servir de ce fichier

1. Après une compaction, un changement de modèle ou une interruption : lire **ce fichier
   d'abord**, puis `16_registre_suivi.md`, puis le plan unique.
2. Avant une opération risquée : identifier le dernier `KNOWN_GOOD` et vérifier qu'il est
   réellement restaurable.
3. Ne jamais écraser une entrée : en ajouter une. L'historique des états sert au diagnostic.
