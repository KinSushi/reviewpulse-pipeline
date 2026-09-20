# Source primaire — page de certification AIA (RNCP41993) sur Julie

**Lue le** 20/09/2026, dans le navigateur intégré, session d'Enzo.
**Adresse** : `https://app.jedha.co/certifications/rncp41993`
**Pourquoi cette lecture** : le sujet R09 du registre bloquait trois présentations sur six,
faute d'accès aux énoncés. La session était en réalité déjà ouverte.

**Ce que cette page corrige dans nos documents** — voir `docs/08_exigences_par_bloc.md` :
nous affirmions un temps de *lecture du dossier par le jury* avant chaque soutenance
(15, 20, 20 et 25 minutes selon le bloc). **Il n'existe pas.** La page ne donne que
présentation et questions-réponses, et le total annoncé — **1 h 25** — vaut exactement
30 + 20 + 20 + 15 minutes : la somme ne laisse aucune place à une lecture.
Conséquence directe : la présentation du bloc 4 avait été calibrée sur l'idée que le jury
avait déjà lu le dossier. C'est faux.

---

## Texte intégral de la page, tel que lu

### Format de l'examen — durées officielles

| Bloc | Présentation | Questions / réponses | Total |
|---|---|---|---|
| 1 — Gouvernance | 15 min | 15 min | 30 min |
| 2 — Architecture de données | 5 min | 15 min | 20 min |
| 3 — Pipelines de données | 5 min | 15 min | 20 min |
| 4 — Industrialisation et déploiement | 5 min | 10 min | 15 min |

Durée annoncée de la certification : **1 h 25**, soit exactement 30 + 20 + 20 + 15.

> « Le support de présentation obligatoire doit contenir un nombre de slides adaptées à la durée
> de la soutenance et au temps consacré au développement de chacune des slides. »

> « La fonctionnalité des éléments produits doit être démontrée en direct pendant la
> présentation ou par le biais de captures d'écran ou d'une vidéo. »

### Projets et livrables, par bloc

| Bloc | Projet imposé | Livrables attendus |
|---|---|---|
| 1 | Lead Data Science / IA — Data Gouvernance (**projet Spotify**) | le plan de gouvernance (document bureautique) ; la présentation du plan résumé |
| 2 | Lead Data Science / IA — **From SQL to NoSQL** (projet Stripe) | un plan du ou des pipelines construits ; s'il y a lieu, le code de déploiement (Terraform, Python…) **hébergé sur GitHub** ; une **capture vidéo du pipeline en production** |
| 3 | Lead Data Science / IA — **Workflow Orchestration** (projet Automatic Fraud Detection) | un plan de l'infrastructure ; s'il y a lieu, le code de déploiement **hébergé sur GitHub** ; une **capture vidéo de l'infrastructure en production** |
| 4 | Lead Data Science / IA — **Final Project** | une présentation de la solution d'IA répondant au cahier des charges ; le code de développement **hébergé sur GitHub** ; le code de déploiement **incluant le pipeline d'intégration et de déploiement continus** ; une **capture vidéo de la solution fonctionnant en production** |

**Ce que cela impose à ReviewPulse**, qui est le support déclaré du bloc 4 : les quatre livrables
ci-dessus sont exigés, pas optionnels. Le dépôt GitHub (registre R01) et la vidéo (registre R03)
en font partie.

### Compétences attestées, bloc par bloc

**Bloc 1 — gouvernance** : analyser les usages et identifier les risques (sécurité, biais,
confidentialité) ; définir les rôles (Data Owners, Data Stewards) et la matrice RACI ; standards
de qualité, traçabilité, interopérabilité (Data Contracts, catalogues) ; politique de sécurité et
gestion des accès (RBAC, ABAC, anonymisation) ; RGPD et AI Act ; sensibilisation, inclusion et
accessibilité ; pilotage par KPI, audits, amélioration continue ; veille réglementaire et
technologique.

**Bloc 2 — infrastructure** : spécifications techniques (CPU/GPU, stockage, réseau) ; architecture
logique et physique évolutive ; arbitrage Cloud / On-Premise / Hybride et IaaS / PaaS / Serverless ;
Infrastructure as Code (Terraform) ; Data Lake, bases vectorielles, conteneurs ; résilience et haute
disponibilité (scalabilité, failover) ; sécurité (IAM, chiffrement, gestion des secrets) ;
efficience (FinOps / GreenOps) ; documentation et coordination des équipes.

**Bloc 3 — pipelines** : flux batch, streaming, ETL/ELT ; transformations (nettoyage, feature
engineering) ; industrialisation et orchestration (Airflow) ; qualité des données (tests,
anomalies) ; sécurité et conformité (RGPD, chiffrement) ; supervision des performances et des
coûts ; traçabilité (data lineage) et pilotage en mode agile.

**Bloc 4 — industrialisation** : cycle de vie des modèles (CI/CD/CT, MLOps, LLMOps) ; architecture
de déploiement (temps réel, batch, edge) ; stratégies de déploiement (A/B testing, Canary) ;
monitoring (Data Drift, performance) ; pilotage des coûts et de la performance (FinOps) ;
explicabilité et gestion des risques (biais, hallucinations) ; supervision des équipes et qualité
technique ; documentation (Model Cards, architecture) ; veille technologique continue.

### Évolutions du RNCP41993 par rapport au RNCP38777

Passage à un rôle d'**architecte** : concevoir et piloter des systèmes, pas seulement des modèles ;
intégration de l'IA générative, du MLOps, du LLMOps et du PromptOps ; forte dimension gouvernance
et IA responsable (AI Act, risques, explicabilité) ; maîtrise des environnements cloud, scalables
et industrialisés (IaC, sécurité, FinOps).
