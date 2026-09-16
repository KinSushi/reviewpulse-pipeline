# Rapport de tests forward
*Date UTC* : 2026-09-16T21:06:49Z
*Commit* : 0ace6a4+travail-en-cours

## URLs testées
- **API** : `http://host.docker.internal:8000`
- **Dashboard** : `http://host.docker.internal:8501`
- **MLflow** : `http://host.docker.internal:5000`
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
| F1 | PASS | natural: 6005 lignes / 6005 ids ; negative_boost: 2797 lignes / 2797 ids |
| F2 | PASS | aucune erreur |
| F3 | PASS | aucune colonne interdite détectée |
| F4 | PASS | 1086940/english=1.209, 1086940/french=0.975, 1903340/english=0.986, 1903340/french=0.838, 2622380/english=0.797, 2622380/french=0.837 |
| F5 | PASS | n_reviews=5959 |
| F6 | PASS | toutes version=2 |

**Total PASS** : 12

**Total FAIL** : 0
