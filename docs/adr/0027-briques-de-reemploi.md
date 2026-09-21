# ADR 0027 — Briques de réemploi

**Date** : 20/09/2026 · **Statut** : acceptée

## Contexte

Le Demo Day est prévu le 25/09/2026. ReviewPulse est le support déclaré du **seul** bloc AIA 4. Les autres blocs (AIA 2, AIA 3, CDSD 1, CDSD 5) imposent des briques techniques :

- **Stockage objet compatible S3 (MinIO)** : requis par le bloc CDSD 1 et le bloc AIA 2. Le lac de données actuel repose sur du disque local avec des tables Iceberg ; le même format fonctionnerait sur un stockage objet, seul le chemin de stockage changerait.  
- **Kafka, Avro, Schema Registry, files de messages mortes** : requis par le bloc AIA 3. Aucun composant n’existe aujourd’hui ; la dépendance `confluent‑kafka` a été retirée le 19/09/2026.  
- **Terraform** : requis par le bloc AIA 2. L’outil n’est pas installé sur la machine ; aucun `validate`, `plan` ou scan de sécurité n’est disponible. Un squelette de configuration existe dans le dépôt `swiss-data-ai-engineering-lab/devops/terraform/`.  
- **Déploiement public accessible** : exigé par le bloc CDSD 5, qui attend une URL fonctionnelle le jour de la soutenance. Un workflow de publication vers un Hugging Face Space existe déjà dans un autre dépôt local.

Une démonstration de résilience (consommateur arrêté puis relancé, rattrapage du retard) n’a de sens que si Kafka est présent.

## Decision

| Brique | Décision | Raison |
|---|---|---|
| Stockage objet (MinIO) | **Assumée** | Le changement de chemin de stockage ne modifie pas le format Iceberg. Construire MinIO nécessiterait l’installation d’un serveur absent et ne profiterait qu’aux blocs CDSD 1 et AIA 2, qui ne sont pas le support déclaré. Le gain est donc limité au contexte externe. |
| Kafka, Avro, Schema Registry, DLQ | **Assumée** | Aucun composant n’est présent et la dépendance `confluent‑kafka` a été retirée. Installer Kafka impliquerait des services supplémentaires non disponibles sur la machine, alors que le bloc AIA 3 n’est pas le support déclaré. |
| Terraform | **Assumée** | L’outil n’est pas installé ; le squelette existe mais ne peut être exécuté. Construire l’infrastructure IaC ne serait pas vérifiable avant le Demo Day et ne sert qu’aux exigences du bloc AIA 2. |
| Déploiement public (URL) | **Assumée** | Un workflow de publication vers Hugging Face Space est déjà fonctionnel dans un autre dépôt. Reprendre ce workflow ne nécessite pas d’outil nouveau. La URL sera fournie le jour J en réutilisant le processus existant, sans développer de nouvelle infrastructure. |

### Analyse coût / bénéfice

- **Coût de construction maintenant** : installation de services (MinIO, Kafka, Terraform) qui ne sont pas présents, configuration, tests – dépasse largement le temps disponible (cinq jours avant le Demo Day).  
- **Bénéfice pour le seul bloc supporté (AIA 4)** : aucune de ces briques n’est requise par le bloc AIA 4, qui utilise déjà les composants déjà en place (traitement batch quotidien, stockage local).  
- **Bénéfice pour les autres blocs** : limité, car chaque bloc possède son propre projet imposé ; la réutilisation de ces briques serait une valeur ajoutée secondaire mais non indispensable à la soutenance.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Construire MinIO localement | Nécessite serveur S3 absent, dépasse le planning, bénéfice limité au bloc CDSD 1 et AIA 2. |
| Installer et configurer Kafka + Avro + Schema Registry | Aucun composant installé, dépendance retirée, temps d’intégration supérieur à la fenêtre disponible, résilience impossible sans Kafka. |
| Installer Terraform et exécuter les plans | Terraform n’est pas présent sur la machine, aucune validation possible, effort disproportionné. |
| Développer un nouveau workflow de déploiement public | Un workflow fonctionnel existe déjà (Hugging Face Space) ; recréer serait redondant et risqué. |

## Consequences

- **Assumer** ces briques signifie que ReviewPulse s’appuie sur des capacités externes qui seront fournies par les projets des autres blocs ou par des dépôts existants. Ce n’est pas une dissimulation : le choix est explicitement documenté et justifié, avec la condition que les livrables attendus des blocs concernés soient fournis séparément.  
- La **démo de résilience** ne pourra pas être réalisée, car elle dépend de Kafka qui est assumé et non présent. Le jury sera informé que la résilience sera démontrée uniquement au niveau conceptuel (exposé du design) et pourra être activée dès que Kafka sera disponible.  
- Le **déploiement public** sera réalisé en réutilisant le workflow de publication Hugging Face Space déjà existant ; aucune nouvelle infrastructure ne sera créée.  
- Aucun outil absent de la machine ne sera installé, respectant la contrainte de ne rien promettre qui ne puisse être exécuté.  
- Le focus reste sur le bloc AIA 4, support déclaré, avec les livrables déjà prévus (CI/CD, monitoring, vidéo, etc.), garantissant que la soutenance du 25/09/2026 se déroule avec les éléments déjà disponibles.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
