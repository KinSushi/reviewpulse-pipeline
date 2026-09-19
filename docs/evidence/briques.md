# Vérification des briques techniques

*Date UTC* : 2026-09-19T23:20:53Z
*Commit* : eeca3e6

## Répartition par état

* Presente : 28
* Partielle : 16
* Absente : 30

## Termes exigés non classés

Aucun problème.

## Briques sans sujet ouvert

Aucun problème.

## Sujets référencés inconnus

Aucun problème.

## Briques non présentes

| Brique | État | Preuve ou sujet |
|---|---|---|
| , NoSQL DocumentDB, pipeline | absente | R29 |
| API de paiements en temps réel | absente | R17 |
| CDC | absente | R17 |
| CPU/GPU | absente | R34 |
| Dead Letter Queues | absente | R17 |
| FinOps | absente | R34 |
| FinOps, GreenOps | absente | R34 |
| IAM/RBAC | absente | R08 |
| IaC reproductible et idempotente | absente | R17 |
| KPI | absente | R08 |
| Kafka | absente | R17 |
| OLTP, OLAP et NoSQL | absente | R29 |
| PCI-DSS | absente | R08 |
| PaaS, IaaS ou serverless | absente | R17 |
| RACI | absente | R08 |
| RBAC/ABAC | absente | R08 |
| SCD2 | absente | R35 |
| Terraform | absente | R17 |
| URL | absente | R17 |
| accessibilité et handicap | absente | R08 |
| auto-scaling | absente | R17 |
| catalogue | absente | R08 |
| coffre à secrets | absente | R32 |
| démonstration de résilience | absente | R39 |
| déploiement progressif (A/B, Canary) | absente | R31 |
| failover | absente | R17 |
| garde-fous | absente | R33 |
| notification e-mail | absente | R11 |
| vidéo | absente | R03 |
| vidéo exigée | absente | R03 |
| AI Act | partielle | risque minimal consigné ; classification argumentée absente, R08 |
| CI/CD/CT | partielle | workflows écrits, jamais exécutés en ligne ; R01 |
| Data Contracts | partielle | contrats dbt ; au sens gouvernance, R08 |
| Notification | partielle | alerte de dérive en fichier daté ; canal externe absent, R11 |
| RGPD, AI Act, ISO | partielle | RGPD et AI Act écrits ; ISO absente, R08 |
| `terraform plan`, linters, scan de sécurité | partielle | `ruff` en CI ; Terraform absent, R17 |
| alertes de SLA | partielle | `_alert_on_sla_miss` écrit dans le journal Airflow ; canal externe absent, R11 |
| backlog en sprints | partielle | `10_backlog.md` et le registre ; aucun sprint, R36 |
| batch, streaming ou ELT | partielle | batch seul, aucun flux ; R17 |
| chiffrement en transit | partielle | seule l'API Steam est en HTTPS ; R32 |
| cloud, on-premise ou hybride | partielle | arbitrage écrit (ADR 0012) ; cible cloud non réalisée, R17 |
| explicabilité (SHAP, LIME, tracing) | partielle | contribution linéaire exacte (ADR 0019) ; aucun tracing, R37 |
| gestion des secrets | partielle | sel obligatoire hors du dépôt ; aucun coffre, R32 |
| médaillon batch et streaming | partielle | médaillon en place, aucun flux ; R17 |
| optimisation | partielle | `lru_cache` sur le champion ; aucune mesure de ressources, R34 |
| plateforme | partielle | ReviewPulse est la brique commune ; briques manquantes, R17 |
