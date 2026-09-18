# Rapport de tests forward
*Date UTC* : 2026-09-18T13:21:33Z
*Commit* : inconnu

## URLs testées
- **API** : `http://api:8000`
- **Dashboard** : `http://dashboard:8501`
- **MLflow** : `http://mlflow:5000`
- **Data directory** : `/data`

## Résultats des contrôles
| Contrôle | Statut | Détail |
|----------|--------|--------|
| A1 | PASS | model_version=1, decision_threshold=0.75 |
| A2 | PASS | labels=['negative', 'negative', 'positive', 'positive'] |
| A3 | PASS | reçu 422 comme attendu |
| A4 | PASS | 13 éléments |
| D1 | PASS | OK |
| M1 | PASS | champion=1 servi=1 |
| F1 | PASS | natural: 6239 lignes / 6239 ids ; negative_boost: 2815 lignes / 2815 ids |
| F2 | PASS | aucune erreur |
| F3 | PASS | aucune colonne interdite détectée |
| F4 | PASS | 1086940/english=1.093, 1086940/french=1.025, 1903340/english=0.946, 1903340/french=0.868, 2622380/english=0.775, 2622380/french=0.866 |
| F5 | PASS | n_reviews=6192 |
| F6 | PASS | toutes version=1 |
| F7 | PASS | 8447 lignes = 8447 lignes |
| F8 | PASS | 9 instantané(s), dernier id=1910635972352722239 |

**Total PASS** : 14

**Total FAIL** : 0
