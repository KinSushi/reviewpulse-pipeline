# ADR 0022 — Gestion des secrets, chiffrement en transit et audit

**Date** : 20/09/2026 · **Statut** : acceptée

## Contexte

Les référentiels AIA 2 et AIA 3 imposent :
- Un coffre à secrets (ex. Vault, AWS Secrets Manager) ;
- Le chiffrement des communications en transit ;
- Des journaux d’audit des accès aux données.

Dans le dépôt :
- Un seul secret existe : `REVIEWPULSE_SALT`, un sel de 64 caractères utilisé pour la pseudonymisation HMAC‑SHA256 des identifiants Steam.  
- Ce secret est fourni uniquement via une variable d’environnement ; il n’est jamais présent dans le dépôt (`.gitignore` exclut `.env`). Aucun fichier de clé n’est versionné.  
- L’application refuse de démarrer si la variable est absente ou vide ; elle est donc obligatoire.  
- La seule liaison sortante est l’API Steam, déjà protégée par HTTPS. Tous les autres services (API, MLflow, PostgreSQL, Airflow, tableau de bord) communiquent sur le réseau Docker privé d’une seule machine.  
- Aucun journal d’audit des accès aux données n’est produit ; seuls les logs d’exécution d’Airflow existent.  
- Le projet est développé et exploité par une seule personne, sur une seule machine, et soutenu le 25/09/2026.

## Decision

1. **Coffre à secrets** – Aucun coffre n’est déployé. Pour un unique secret, stocké localement et accessible uniquement à l’utilisateur unique, un gestionnaire externe n’apporte pas de valeur ajoutée.  
   - **Condition de mise en place** : le projet devra disposer de plusieurs environnements (ex. développement, pré‑production, production) ou de plusieurs porteurs (ex. équipe, machines), ou devra mettre en place une rotation régulière du sel. Dans ces cas, un coffre à secrets sera introduit.

2. **Gestion actuelle du secret** – Le secret est traité comme une variable d’environnement obligatoire, non versionnée, et le démarrage de l’application échoue si elle est absente. Cette contrainte constitue déjà une forme de contrôle d’accès au secret.

3. **Chiffrement en transit** – Le trafic sortant vers Steam est déjà chiffré (HTTPS). Le trafic interne entre conteneurs circule en clair sur le réseau Docker privé.  
   - **Ce qui serait nécessaire** : mise en place de TLS mutuel entre les services (ex. Docker Compose avec `tls` ou utilisation d’un service mesh tel que Istio) ou utilisation de réseaux overlay chiffrés.  
   - **Raison de l’absence** : le contexte actuel (une seule machine, un seul utilisateur) ne justifie pas la complexité et la surcharge opérationnelle d’un tel chiffrement.

4. **Journaux d’audit** – Aucun journal d’audit des accès aux données n’est présent.  
   - **Ce qui serait nécessaire** : instrumentation des services (API, MLflow, PostgreSQL, Airflow) pour enregistrer : qui (identité ou processus) a lu ou écrit quelles données, à quel moment, avec quel résultat.  
   - **Décision** : l’absence est acceptée tant que le projet reste mono‑utilisateur et mono‑machine. Un dispositif d’audit sera introduit dès que le projet évoluera vers plusieurs utilisateurs ou plusieurs machines.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Déployer un coffre à secrets (Vault, AWS Secrets Manager) | Sur‑dimensionné pour un seul secret, une seule machine et un seul utilisateur ; aucune rotation prévue. |
| Chiffrer le trafic interne (TLS mutuel, service mesh) | Complexité opérationnelle non justifiée dans un environnement mono‑machine ; le risque de compromission du réseau privé est jugé faible. |
| Implémenter des journaux d’audit détaillés dès maintenant | Pas de besoin immédiat de traçabilité d’accès dans un contexte mono‑utilisateur ; surcharge de stockage et de configuration. |

## Consequences

- Le projet continue d’utiliser `REVIEWPULSE_SALT` comme variable d’environnement obligatoire, non versionnée, garantissant que le secret ne fuit pas dans le dépôt.  
- Aucun coffre à secrets n’est provisionné tant que le projet reste mono‑environnement et mono‑utilisateur.  
- Le trafic interne reste en clair ; le risque est limité à la machine locale. Une évolution vers plusieurs machines nécessitera la mise en place de TLS interne.  
- L’absence de journaux d’audit signifie qu’il n’y a pas de traçabilité des lectures/écritures de données ; cela devra être ajouté dès que le projet supportera plusieurs acteurs ou sera exposé à des exigences de conformité.  
- La décision sera réévaluée dès que l’une des conditions suivantes sera remplie : ajout d’un deuxième environnement, multiplication des utilisateurs, besoin de rotation du sel, ou exigences réglementaires imposant l’audit.  
