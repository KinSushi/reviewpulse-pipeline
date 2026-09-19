# Dossier de gouvernance des données – Bloc AIA 1 – Spotify (pilote ReviewPulse)

## 1. Politique de gouvernance (tâche 1)

**a. Prescription pour Spotify**  
Définir une politique couvrant la qualité, la sécurité, la conformité, la vie privée, l’accessibilité et l’intégration. La politique doit être applicable à des opérations mondiales. Elle doit être révisable régulièrement. Elle doit pouvoir être étendue à de nouveaux jeux de données ou à de nouvelles régions. Elle doit prévoir des mécanismes de contrôle d’accès, de chiffrement, de journalisation et de suivi des changements. Elle doit inclure une clause de révision annuelle ou en cas d’incident majeur.

**b. Sur le pilote ReviewPulse**  
*Qualité* – Contrôles bloquants avant écriture de la zone propre (ADR 0005). Utilisation de Great Expectations sur la zone propre. 43 tests dbt sur la zone gold. Contrats dbt dans `_staging.yml` et `_marts.yml`.  
*Sécurité* – Zone brute immuable. Ingestion idempotente par curseur et manifeste d’identifiants (ADR 0002). Le sel `REVIEWPULSE_SALT` est stocké comme secret obligatoire.  
*Conformité* – Base légale retenue : intérêt légitime, RGPD article 6.1.f. AI Act : risque minimal, consigne dans la charte et la Model Card.  
*Vie privée* – Pseudonymisation HMAC‑SHA256 avec sel obligatoire (ADR 0004). Suppression des champs `personaname`, `profile_url`, `avatar`, `steamid` dès la zone propre. Tableau de bord ne montre aucune information d’auteur et tronque les textes à 200 caractères.  
*Accessibilité* – Aucun dispositif d’accessibilité décrit dans le pilote.  
*Intégration* – Traçabilité via MLflow : chaque run porte l’étiquette `code_commit` et l’empreinte du jeu de données (SHA‑256 condensé, nombre de lignes, bornes de dates, comptes par flux).  
*Manquant* – Rien dans le pilote ne répond aux exigences d’accessibilité, de catalogue de données, de RBAC/ABAC, de journal des accès, ni à un processus de révision formel de la politique.

## 2. Rôles et responsabilités (tâche 2)

**a. Prescription pour Spotify**  
Définir des Data Stewards par jeu de données. Nommer un DPO. Instaurer une ligne de remontée claire. Créer un comité de gouvernance réunissant les départements clés (ingestion, data engineering, conformité, produit, juridique). Formaliser un RACI. Identifier les Data Owners. Documenter les responsabilités de chaque rôle.

**b. Sur le pilote ReviewPulse**  
Aucun rôle formel n’est nommé. Le projet est porté par une seule personne. Aucun Data Owner, Data Steward ou DPO n’est désigné. Aucun comité de gouvernance n’est constitué. Le tableau ci‑dessous résume les rôles identifiés dans le pilote.

| Rôle | Responsabilité | Titulaire sur le pilote |
|------|----------------|------------------------|
| Responsable du projet | Coordination globale, décision technique | Unique développeur du projet |
| Responsable de la pseudonymisation | Application du HMAC‑SHA256, gestion du sel | Unique développeur du projet |
| Responsable de la qualité | Définition et exécution des contrôles Great Expectations, dbt tests | Unique développeur du projet |
| Responsable de la traçabilité | Étiquetage des runs MLflow, conservation des empreintes | Unique développeur du projet |
| Responsable de la réversibilité | Gestion des snapshots Iceberg, alias MLflow | Unique développeur du projet |

Manquants : RACI formel, Data Stewards, DPO, comité de gouvernance, lignes de remontée documentées.

## 3. Plan de mise en œuvre (tâche 3)

**a. Prescription pour Spotify**  
Décomposer le déploiement en étapes : analyse des besoins, conception de la politique, mise en place du catalogue, définition des rôles, implémentation technique, phase pilote, évaluation, généralisation. Fixer des jalons mesurables. Allouer les ressources humaines et techniques. Définir des indicateurs de succès (qualité, conformité, adoption). Conduire le changement avec communication, formation et documentation. Prévoir une phase pilote sur un département ou une région avant le déploiement global.

**b. Sur le pilote ReviewPulse**  
Le pilote couvre déjà plusieurs étapes : ingestion, transformation, contrôle qualité, traçabilité, réversibilité, surveillance, restitution. Aucun jalon formel n’est documenté. Aucun indicateur de gouvernance n’est collecté. Aucun plan de communication ou de formation n’est décrit. Aucun calendrier d’audit n’est prévu. Le tableau suivant propose des indicateurs à construire.

| Indicateur | Ce qu’il mesure | Mode d’obtention |
|------------|----------------|------------------|
| Taux de succès des contrôles Great Expectations | Pourcentage de lots qui passent les contrôles bloquants | Extraction des logs d’exécution |
| Nombre de snapshots Iceberg disponibles | Couverture de la réversibilité des données silver | Commande `make snapshots` |
| Temps moyen de rollback d’un modèle | Rapidité de restauration d’une version précédente | Mesure du temps entre déclenchement et mise en service |
| Couverture des tests dbt | Exhaustivité des tests de transformation | Comptage des tests dans le répertoire dbt |
| % de runs MLflow correctement étiquetés | Qualité de la traçabilité | Analyse des métadonnées des runs |
| À construire — Indicateur de conformité RGPD | Respect des exigences légales | À définir, collecte de preuves d’anonymisation |
| À construire — Indicateur d’accessibilité | Conformité aux standards d’accessibilité | Audit manuel ou automatisé |

Manquants : plan détaillé avec jalons, ressources allouées, indicateurs de gouvernance existants, communication, formation, calendrier d’audit.

## 4. Initiative qualité (tâche 4)

**a. Prescription pour Spotify**  
Mettre en place un processus de nettoyage, validation et normalisation des données. Déployer des outils de surveillance continue (profilage, alertes). Prioriser les jeux de données impactant l’expérience utilisateur. Former les équipes aux bonnes pratiques de qualité. Documenter les procédures.

**b. Sur le pilote ReviewPulse**  
Nettoyage : suppression des champs identifiants dans la zone propre. Validation : contrôles bloquants (ADR 0005), Great Expectations, 43 tests dbt. Normalisation : transformation en zone propre, pseudonymisation stable. Surveillance : PSI sur le flux naturel, alerte écrite dans un fichier daté hors du journal Airflow, déclenchement de réentraînement. Aucun outil de profilage ou tableau de bord dédié à la qualité n’est mentionné. Aucun indicateur de qualité agrégé n’est présenté. Aucun programme de formation n’est décrit.

## 5. Conformité et vie privée (tâche 5)

**a. Prescription pour Spotify**  
Maintenir des politiques à jour (RGPD, CCPA, PDPA). Obtenir le consentement explicite des utilisateurs. Anonymiser ou pseudonymiser les données personnelles. Réaliser des audits réguliers. Documenter les bases légales. Mettre en place un registre des traitements. Gérer les demandes d’accès et d’effacement.

**b. Sur le pilote ReviewPulse**  
Base légale : intérêt légitime, RGPD article 6.1.f. Pseudonymisation HMAC‑SHA256 avec sel obligatoire (ADR 0004). Suppression des champs d’identification. Aucun consentement explicite n’est collecté (les données proviennent d’une API publique). Aucun audit formel n’est programmé. Aucun registre des traitements n’est présenté. Aucun processus de gestion des demandes d’accès ou d’effacement n’est décrit. Manquants : procédure d’incident écrite, calendrier d’audits, journal des accès, mécanisme de consentement.

## 6. Présentation au comité de direction (tâche 6)

**a. Prescription pour Spotify**  
Préparer une présentation synthétique : cadre de gouvernance, plan de mise en œuvre, résultats attendus, valeur métier. Insister sur la réduction des silos, la conformité légale, l’amélioration de la qualité des recommandations, la protection de la vie privée. Proposer un ROI estimé. Définir les prochains jalons.

**b. Sur le pilote ReviewPulse**  
Le pilote montre déjà : zone brute immuable (9 271 lignes brutes), pseudonymisation, contrôles qualité, traçabilité, réversibilité, surveillance, restitution sans informations d’auteur. Aucun document de présentation au comité n’est fourni. Aucun ROI ou métrique de valeur métier n’est calculé. Aucun plan de généralisation n’est exposé. Manquants : support de présentation, estimation d’impact, feuille de route vers la généralisation.

## Ce que ce dossier ne démontre pas

- RACI formel et catalogue de données.  
- RBAC/ABAC ou journal des accès.  
- Procédure d’incident écrite et calendrier d’audits.  
- Indicateurs de gouvernance opérationnels (hors ceux listés comme à construire).  
- Structure de comité de gouvernance avec membres désignés.  
- Processus de consentement explicite des utilisateurs.  
- Mesures d’accessibilité conformes aux standards.  
- Documentation de formation et de conduite du changement.  
- Analyse de ROI ou de valeur métier pour le comité de direction.  
