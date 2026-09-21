# Rapport de tests forward
*Date UTC* : 2026-09-21T09:39:08Z
*Commit* : dca4a52

## URLs testées
- **API** : `http://api:8000`
- **Dashboard** : `http://dashboard:8501`
- **MLflow** : `http://mlflow:5000`
- **Data directory** : `/data`

## Résultats des contrôles
| Contrôle | Statut | Détail |
|----------|--------|--------|
| A1 | PASS | model_version=5, decision_threshold=0.775 |
| A2 | PASS | labels=['negative', 'negative', 'positive', 'positive'] |
| A3 | PASS | reçu 422 comme attendu |
| A4 | PASS | 13 éléments |
| D1 | PASS | OK |
| M1 | PASS | champion=5 servi=5 |
| F1 | PASS | natural: 6769 lignes / 6769 ids ; negative_boost: 2868 lignes / 2868 ids |
| F2 | PASS | aucune erreur |
| F3 | PASS | aucune colonne interdite détectée |
| F4 | PASS | 1086940/english=1.092, 1086940/french=1.024, 1903340/english=0.922, 1903340/french=0.975, 2622380/english=0.857, 2622380/french=0.919 |
| F5 | PASS | n_reviews=6720 |
| F6 | PASS | toutes version=5 |
| F7 | PASS | 8974 lignes = 8974 lignes |
| F8 | PASS | 31 instantané(s), dernier id=3657012973483003646 |
| F9 | PASS | 795 lignes |
| F10 | PASS | 8974 lignes au total, dont 6720 naturelles |

**Total PASS** : 16

**Total FAIL** : 0
