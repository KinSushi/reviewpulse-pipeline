# Rapport de tests forward
*Date UTC* : 2026-09-19T14:49:38Z
*Commit* : 62cff6b

## URLs testées
- **API** : `http://api:8000`
- **Dashboard** : `http://dashboard:8501`
- **MLflow** : `http://mlflow:5000`
- **Data directory** : `/data`

## Résultats des contrôles
| Contrôle | Statut | Détail |
|----------|--------|--------|
| A1 | PASS | model_version=2, decision_threshold=0.75 |
| A2 | PASS | labels=['negative', 'negative', 'positive', 'positive'] |
| A3 | PASS | reçu 422 comme attendu |
| A4 | PASS | 14 éléments |
| D1 | PASS | OK |
| M1 | PASS | champion=2 servi=2 |
| F1 | PASS | natural: 6434 lignes / 6434 ids ; negative_boost: 2837 lignes / 2837 ids |
| F2 | PASS | aucune erreur |
| F3 | PASS | aucune colonne interdite détectée |
| F4 | PASS | 1086940/english=1.066, 1086940/french=1.024, 1903340/english=0.914, 1903340/french=0.842, 2622380/english=0.761, 2622380/french=0.866 |
| F5 | PASS | n_reviews=6386 |
| F6 | PASS | toutes version=2 |
| F7 | PASS | 8640 lignes = 8640 lignes |
| F8 | PASS | 19 instantané(s), dernier id=4729758044397567047 |
| F9 | PASS | 786 lignes |
| F10 | PASS | 8640 lignes au total, dont 6386 naturelles |

**Total PASS** : 16

**Total FAIL** : 0
