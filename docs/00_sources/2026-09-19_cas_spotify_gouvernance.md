# Cas Spotify — exigences relevées, 19/09/2026

**Statut** : lu. Le blocage du registre R08 est levé.

**Source** : huit PDF du parcours Lead, dossier `06_crawl_detaille/files/` du corpus
`D:\JEDHA_JULIE\99_TEMP_DO_NOT_SEND\PHASE2_PACKS_BY_PARCOURS\03_lead_data_analysis\…`.
Texte extrait le 19/09/2026 dans un conteneur `python:3.11-slim` avec `pypdf` — rien n'a été
installé sur la machine. Les textes extraits restent hors du dépôt (document de cours) ;
seules les exigences sont relevées ici.

**Piège vérifié, et correction d'une note antérieure** : chaque document existe en double, et
l'une des deux copies est une page d'erreur HTML renommée en `.pdf`. Le critère de
sélection est **l'en-tête `%PDF-`**, pas la taille : pour `Data_governance_role_template`,
le fichier HTML pèse 28 733 octets et le vrai PDF 12 460.

| Document | Pages | Caractères extraits |
|---|---|---|
| `business_case.pdf` | 8 | 24 120 |
| `pilot_template.pdf` | 4 | 6 154 |
| `Organizational_models.pdf` | 34 | 6 051 |
| `executive-qa-guide.pdf` | 4 | 5 924 |
| `governance-principles-guide.pdf` | 2 | 3 440 |
| `tech-tools-overview.pdf` | 2 | 3 229 |
| `Data_governance_role_template.pdf` | 1 | 1 852 |
| `Data_maturity_assessment_template.pdf` | 1 | 289 |

## Le cas

Spotify, plus de 450 millions d'utilisateurs actifs dont 200 millions d'abonnés payants,
présent dans plus de 180 pays. Quatre problèmes énoncés : **silos de données** entre
marketing, produit, curation et ingénierie ; **conformité réglementaire** (RGPD, CCPA, PDPA) ;
**qualité des données**, dont dépend le moteur de recommandation ; **vie privée** des
utilisateurs. S'y ajoute l'**accessibilité** : des données cloisonnées ralentissent chaque
nouvelle fonctionnalité.

## Les quatre objectifs énoncés

1. Améliorer la qualité des données : processus et outils normalisés, nettoyage, validation,
   surveillance continue.
2. Garantir la conformité : consentement, demandes des personnes concernées, notification
   des violations.
3. Protéger la vie privée : minimisation, transparence, contrôle rendu à l'utilisateur.
4. Améliorer l'accessibilité et l'intégration : casser les silos sans perdre la sécurité.

## Les six tâches attendues — ce sont les livrables

1. **Politique de gouvernance** : qualité, sécurité, conformité, vie privée, accessibilité et
   intégration. Adaptée aux opérations mondiales, révisable, extensible.
2. **Rôles et responsabilités** : Data Stewards par jeu de données, rôle du DPO, redevabilité
   sur la qualité et la conformité, ligne de remontée claire, **comité de gouvernance**
   réunissant les départements clés.
3. **Plan de mise en œuvre** : étapes, jalons, ressources, **indicateurs de réussite**, et une
   **phase pilote** sur un département ou une région avant la généralisation. Stratégie de
   communication et conduite du changement.
4. **Initiative qualité** : nettoyage, validation, normalisation, outils de surveillance,
   formation. Priorité aux jeux de données qui touchent l'expérience utilisateur.
5. **Conformité et vie privée** : politiques à jour, consentement explicite, anonymisation,
   **audits réguliers** des pratiques.
6. **Présentation au comité de direction** : cadre, plan, résultats attendus, valeur métier.
   Concise, visuelle, tournée vers les préoccupations des dirigeants.

## Rôles nommés dans le cas

**DPO** (stratégie de protection, point de contact du régulateur, audits, violations,
demandes des personnes concernées), **Data Stewards**, équipes marketing, produit, ingénierie.

## Risques énoncés, et la parade demandée

Résistance au changement, coordination d'équipes mondiales, tension entre gouvernance et
agilité. Parade attendue : **approche par phases**, pilote d'abord, conduite du changement,
parties prenantes engagées tôt.

## Ce que cela change pour ReviewPulse

ReviewPulse sert de **pilote** au sens de la tâche 3 : un périmètre restreint, réel, où le cadre
se démontre au lieu de se décrire. Le dossier AIA 1 doit donc articuler les six livrables
ci-dessus avec ce qui existe déjà et qui est **mesuré** : pseudonymisation (ADR 0004),
contrôles bloquants (ADR 0005), contrats dbt, registre AI Act de la charte, journal d'audit
par `code_commit` et empreinte du jeu de données, et la matrice de réversibilité.
Ce qui manque reste nommé comme manquant : RACI, catalogue, RBAC/ABAC, procédure
d'incident, indicateurs de gouvernance, audits.
