# Vérification des briques techniques

*Date UTC* : 2026-09-20T07:52:40Z
*Commit* : 0726697

## Répartition par état

* Presente : 39
* Partielle : 42
* Absente : 54

## Termes exigés non classés

Aucun problème.

## Briques sans sujet ouvert

Aucun problème.

## Sujets référencés inconnus

Aucun problème.

## Briques non présentes

| Brique | État | Preuve ou sujet |
|---|---|---|
| API de paiements en temps réel | absente | R17 |
| CDC | absente | R17 |
| CPU/GPU | absente | R34 |
| Data Lake et bases vectorielles | absente | R17 |
| Dead Letter Queues | absente | R17 |
| FinOps | absente | R34 |
| FinOps des pipelines | absente | R34 |
| FinOps précis | absente | R34 |
| FinOps, GreenOps | absente | R34 |
| IAM/RBAC | absente | R08 |
| IaC reproductible et idempotente | absente | R17 |
| KPI | absente | R08 |
| Kafka | absente | R17 |
| NoSQL DocumentDB | absente | R29 |
| OLTP, OLAP et NoSQL | absente | R29 |
| PCI-DSS | absente | R08 |
| PaaS, IaaS ou serverless | absente | R17 |
| RACI | absente | R08 |
| RBAC/ABAC | absente | R08 |
| SCD2 | absente | R35 |
| Terraform | absente | R17 |
| URL | absente | R17 |
| accessibilité et handicap | absente | R08 |
| allocation CPU et mémoire | absente | R17 |
| architectures logique et physique | absente | R17 |
| auto-scaling | absente | R17 |
| auto-scaling et failover | absente | R17 |
| besoins CPU/GPU justifiés | absente | R17 |
| catalogue | absente | R08 |
| chiffrement et segmentation | absente | R32 |
| code de déploiement (Terraform…) sur GitHub | absente | R17 |
| code sur GitHub | absente | R01 |
| coffre à secrets | absente | R32 |
| continuité | absente | R17 |
| contrats d'interface | absente | R17 |
| dimensionnement du stockage | absente | R17 |
| démonstration de résilience | absente | R39 |
| déploiement progressif (A/B, Canary) | absente | R31 |
| failover | absente | R17 |
| garde-fous | absente | R33 |
| garde-fous (biais, injections) | absente | R33 |
| journaux d'audit | absente | R32 |
| mises à jour sans interruption | absente | R17 |
| modules et versioning | absente | R17 |
| notification e-mail | absente | R11 |
| plan d'infrastructure (diagramme) | absente | R17 |
| soutenabilité | absente | R34 |
| souveraineté | absente | R17 |
| vidéo | absente | R03 |
| vidéo de l'infrastructure en production | absente | R03 |
| vidéo de la solution en production | absente | R03 |
| vidéo du pipeline en production | absente | R03 |
| vidéo exigée | absente | R03 |
| évolutivité | absente | R17 |
| AI Act | partielle | risque minimal consigné ; classification argumentée absente, R08 |
| CI/CD/CT | partielle | workflows écrits, jamais exécutés en ligne ; R01 |
| CI/CD/CT sans intervention manuelle | partielle | `ci.yml` et `pipeline.yml` écrits ; jamais exécutés en ligne, R01 |
| Data Contracts | partielle | contrats dbt ; au sens gouvernance, R08 |
| Data Owners et Stewards | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| KPI de gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| Notification | partielle | alerte de dérive en fichier daté ; canal externe absent, R11 |
| RGPD, AI Act, ISO | partielle | RGPD et AI Act écrits ; ISO absente, R08 |
| `terraform plan`, linters, scan de sécurité | partielle | `ruff` en CI ; Terraform absent, R17 |
| alertes de SLA | partielle | `_alert_on_sla_miss` écrit dans le journal Airflow ; canal externe absent, R11 |
| amélioration continue | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| arbitrage batch, streaming ou ELT selon la fraîcheur requise | partielle | le lot quotidien est justifié dans `docs/02_architecture.md` ; le streaming reste absent, R17 |
| audits | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| backlog en sprints | partielle | `10_backlog.md` et le registre ; aucun sprint, R36 |
| batch, streaming ou ELT | partielle | batch seul, aucun flux ; R17 |
| cartographie des systèmes d'IA | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| chiffrement en transit | partielle | seule l'API Steam est en HTTPS ; R32 |
| choix temps réel, lots ou edge | partielle | le lot quotidien est justifié dans `docs/02_architecture.md` ; le temps réel reste absent, R17 |
| cloud, on-premise ou hybride | partielle | arbitrage écrit (ADR 0012) ; cible cloud non réalisée, R17 |
| coordination | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| documentation accessible | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| détection de dérive avec alerte | partielle | `drift.py` et `ecrire_alerte` écrits et branchés ; exécution réelle du DAG à prouver, R11 |
| explicabilité (SHAP, LIME, tracing) | partielle | contribution linéaire exacte (ADR 0019) ; aucun tracing, R37 |
| gestion des incidents | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| gestion des secrets | partielle | sel obligatoire hors du dépôt ; aucun coffre, R32 |
| interopérabilité | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| médaillon batch et streaming | partielle | médaillon en place, aucun flux ; R17 |
| optimisation | partielle | `lru_cache` sur le champion ; aucune mesure de ressources, R34 |
| optimisation (cache, quantification, élagage) | partielle | `lru_cache` sur le chargement du champion ; quantification et élagage sans objet pour une régression logistique, à assumer par écrit, R34 |
| parties prenantes | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| plateforme | partielle | ReviewPulse est la brique commune ; briques manquantes, R17 |
| politique de sécurité | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| priorisation | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| privacy by design | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| risques (sécurité, biais, confidentialité) | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| réentraînement automatique en cas de baisse | partielle | branche `derive_gate` vers `declencher_reentrainement` ; exécution réelle à prouver, R11 |
| sensibilisation | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| sources, flux et sensibilités | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| supervision des équipes et cahier des charges | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| traçabilité | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| veille réglementaire et technologique | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| éthique et biais | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
