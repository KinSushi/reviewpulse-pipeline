# Justifications des décisions d'architecture

*Date UTC* : 2026-09-19T20:26:21Z
*Commit* : f3e06ce

| ADR | titre | code | questions | diapositives |
|-----|-------|------|-----------|--------------|
| 0001 | Cas métier : avis Steam, API publique | 4 | 3 | 1 |
| 0002 | Zone brute inchangée, idempotence par manifeste | 6 | 5 | 1 |
| 0003 | Transformation en pandas | 4 | 2 | 1 |
| 0004 | Pseudonymisation HMAC salée, sel obligatoire | 8 | 4 | 3 |
| 0005 | Contrôles qualité bloquants | 7 | 3 | 2 |
| 0006 | Modèle ML sur n-grammes de caractères | 4 | 3 | 2 |
| 0007 | Avis négatifs complémentaires et seuil appris | 9 | 4 | 2 |
| 0008 | Barrière de promotion et alias MLflow | 8 | 4 | 4 |
| 0009 | Convention de décision centralisée | 5 | 2 | 1 |
| 0010 | Emplacement des artefacts et des écritures | 4 | 2 | 1 |
| 0011 | Airflow et GitHub Actions | 6 | 3 | 1 |
| 0012 | Déploiement Docker Compose | 4 | 2 | 1 |
| 0013 | Pile du programme Lead et environnements séparés | 12 | 4 | 3 |
| 0014 | Zone silver en PySpark et Iceberg, pandas comme référence | 7 | 1 | 3 |
| 0015 | Surveillance de la dérive | 4 | 1 | 3 |
| 0016 | Déploiement progressif champion / challenger | 5 | 2 | 2 |
| 0017 | Airflow sur PostgreSQL | 6 | 1 | 2 |
| 0018 | Reproductibilite : empreintes, tracabilite, sauvegarde | 7 | 2 | 2 |
| 0019 | Explicabilite par contribution lineaire exacte | 4 | 1 | 2 |
| 0020 | Porte de qualite etendue aux zones silver et gold | 4 | 2 | 3 |

## Totaux

* Citations dans le code : 118
* Citations dans les questions‑réponses : 51
* Citations dans les diapositives : 40
