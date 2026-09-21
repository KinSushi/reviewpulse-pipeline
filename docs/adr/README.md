# Registre des décisions d'architecture (ADR)

Chaque décision structurante du projet est écrite ici, **avec la mesure ou le constat qui l'a motivée**. Format : contexte, décision, alternatives écartées, conséquences, preuves. Les dates sont celles de la décision. **28 décisions** au 20/09/2026.

| N° | Décision | Statut |
|---|---|---|
| [0001](0001-cas-metier-et-source.md) | Cas métier : avis Steam, API publique | Acceptée |
| [0002](0002-zone-brute-et-idempotence.md) | Zone brute inchangée, idempotence par manifeste | Acceptée |
| [0003](0003-transformation-pandas.md) | Transformation en pandas | Acceptée |
| [0004](0004-pseudonymisation.md) | Pseudonymisation HMAC salée, sel obligatoire | Acceptée |
| [0005](0005-controles-qualite-bloquants.md) | Contrôles qualité bloquants | Acceptée |
| [0006](0006-modele-ml-caracteres.md) | Modèle ML sur n-grammes de caractères | Acceptée |
| [0007](0007-flux-negatif-et-seuil.md) | Avis négatifs complémentaires et seuil appris | Acceptée |
| [0008](0008-promotion-champion.md) | Barrière de promotion et alias MLflow | Acceptée |
| [0009](0009-convention-de-decision.md) | Convention de décision centralisée | Acceptée |
| [0010](0010-artefacts-et-ecritures.md) | Emplacement des artefacts et des écritures | Acceptée |
| [0011](0011-orchestration.md) | Airflow et GitHub Actions | Acceptée |
| [0012](0012-deploiement-conteneurs.md) | Déploiement Docker Compose | Acceptée |
| [0013](0013-pile-du-programme-et-environnements.md) | Pile du programme Lead, MLflow 3, environnements séparés dans Airflow | Acceptée |
| [0014](0014-spark-iceberg-silver.md) | Zone silver en PySpark et Iceberg, pandas comme référence | Acceptée |
| [0015](0015-surveillance-de-la-derive.md) | Surveillance de la dérive : indice de stabilité de population et écart de parts prédites | Acceptée, révisée le 19/09 |
| [0016](0016-deploiement-progressif.md) | Déploiement progressif champion / challenger | Proposée |
| [0017](0017-airflow-postgresql.md) | Airflow sur PostgreSQL : le planificateur survit à l'accès concurrent | Acceptée |
| [0018](0018-reproductibilite-empreintes.md) | Reproductibilité : empreintes d'images et de jeu de données, traçabilité, sauvegarde du registre | Acceptée |
| [0019](0019-explicabilite-lineaire.md) | Explicabilité par contribution linéaire exacte, plutôt que SHAP ou LIME | Acceptée |
| [0020](0020-qualite-silver-gold.md) | Porte de qualité étendue aux zones silver et gold | Acceptée |
| [0021](0021-garde-fous-biais-injections.md) | Garde-fous : injection sans objet sur un classifieur linéaire, mesure de biais assumée absente | Acceptée |
| [0022](0022-secrets-chiffrement-audit.md) | Secrets, chiffrement en transit et journaux d'audit : ce qui est tenu, ce qui est assumé | Acceptée |
| [0023](0023-finops-greenops.md) | FinOps et GreenOps : ce qui est mesurable avec l'existant, et ce qui ne l'est pas | Acceptée |
| [0024](0024-base-de-documents-nosql.md) | Base de documents NoSQL : la zone brute est déjà une collection de documents | Acceptée |
| [0025](0025-modelisation-etoile-scd2.md) | Modélisation en étoile et SCD2 sur des faits immuables | Acceptée |
| [0026](0026-tracing-explicabilite.md) | Tracing : tracer les décisions plutôt que les appels | Acceptée |
| [0027](0027-briques-de-reemploi.md) | Briques de réemploi : MinIO, Kafka, Terraform, déploiement public, arbitrées une par une | Acceptée |
| [0028](0028-conduite-du-backlog.md) | Conduite du backlog : un registre à critère de fin et à preuve, plutôt que des sprints | Acceptée |
| [0029](0029-surveillance-de-la-latence.md) | Surveillance de la latence : `/metrics` en mémoire, décidé par arbitrage entre trois familles de modèles | Acceptée |
| [0030](0030-choix-de-la-famille-de-modele.md) | Régression logistique plutôt qu'une autre famille : neuf candidats mesurés, règle écrite avant les résultats | Acceptée |
| [0031](0031-strategie-de-branches.md) | Une seule ligne principale, alimentée par une branche de travail validée en CI ; avance rapide seulement | Acceptée |

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
