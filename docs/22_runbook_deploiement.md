# Runbook de déploiement – ReviewPulse

## À qui s'adresse ce document
Ce document s’adresse à toute personne qui doit reprendre le projet ReviewPulse sans en connaître le code ni l’infrastructure.  
Il décrit, pas à pas, le déploiement complet sur une machine locale.

## Prérequis
- Docker Compose installé (version compatible avec le fichier `docker-compose.yml`).  
- Aucun composant n’est installé sur la machine hôte : tout tourne dans les images Docker décrites.  
- Variable d’environnement `REVIEWPULSE_SALT` exportée dans le shell **avant** tout appel à `docker compose`. La chaîne doit contenir exactement 64 caractères ; la vérification se fait avec `echo ${#REVIEWPULSE_SALT}` (résultat = 64).  
- Port 8000, 8501, 5000, 8080 libres sur l’hôte.  
- Disque USB externe monté et accessible ; le répertoire `./data` doit être présent.

## Lever la pile, de zéro
1. **Exporter le secret**  
   ```bash
   export REVIEWPULSE_SALT=$(cat <chemin_vers_le_fichier_salt>)
   echo ${#REVIEWPULSE_SALT}   # doit afficher 64
   ```
2. **Démarrer les services de base** (MLflow, API, Dashboard)  
   ```bash
   docker compose up -d mlflow api dashboard   # surtout PAS --build : voir « Quand ça ne marche pas »
   ```
   - **mlflow** : devient sain après **≈ 170 s** (max ≈ 580 s). Le health‑check passe quand `http://localhost:5000/health` renvoie `200`.  
   - **api** : devient sain après **≈ 3 min** (chargement du modèle champion depuis MLflow). Le health‑check passe quand `http://localhost:8000/health` renvoie `200`.  
   - **dashboard** : devient sain après **≈ 30 s**. Le health‑check passe quand `http://localhost:8501/_stcore/health` renvoie `200`.

3. **Démarrer PostgreSQL (Airflow DB)**  
   ```bash
   docker compose --profile airflow up -d airflow-db
   ```
   - Le service passe sain après **> 11 min** (phase `syncing data directory (fsync)`). Le health‑check passe quand `docker compose exec airflow-db pg_isready -U airflow` renvoie `accepting connections`.

4. **Démarrer Airflow** (scheduler, webserver)  
   ```bash
   docker compose --profile airflow up -d airflow
   ```
   - Attendre que le conteneur `airflow` signale `healthy` (≈ 2 min). L’UI est accessible sur `http://localhost:8080`.

## Vérifier que ça marche
| Service | Commande de contrôle | Réponse attendue |
|---------|----------------------|------------------|
| MLflow  | `curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health` | `200` |
| API     | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health` | `200` |
| Dashboard | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/_stcore/health` | `200` |
| PostgreSQL (Airflow DB) | `docker compose exec airflow-db pg_isready -U airflow` | `accepting connections` |
| Airflow | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health` | `200` (ou page HTML de connexion) |

## Faire tourner la chaîne
1. **Lancer le job pipeline** (ingestion → spark → expectations → train → score → gold)  
   ```bash
   docker compose --profile jobs run -d --name rp-pipeline pipeline   # jamais --rm : voir plus bas
   ```
   - Les logs du conteneur apparaissent avec `docker logs <nom_du_conteneur>` (ex. `reviewpulse-pipeline-1`).  
2. **Déclencher le DAG quotidien**  
   ```bash
   airflow dags trigger reviewpulse_daily -r <identifiant>
   ```
3. **Suivre l’état des tâches**  
   ```bash
   airflow tasks states-for-dag-run reviewpulse_daily <identifiant>
   ```
   - Huit tâches affichent `success`.  
   - La tâche `declencher_reentrainement` apparaît `skipped`. **Signification** : la dérive n’a pas dépassé le seuil, donc le ré‑entraînement n’est pas requis (comportement attendu).  
4. **Lire les journaux d’une tâche** (exemple : `train`)  
   ```bash
   docker logs $(docker ps -q -f "name=airflow") | grep train
   ```

## Revenir en arrière
- **Modèle** : l’alias `champion` pointe vers la version servie. Pour revenir à la version N :  
  ```bash
  python -m reviewpulse.rollback --vers N
  ```
  Cette commande ne copie pas les artefacts ; elle ne fait que ré‑affecter l’alias.  
- **Données** : un instantané Iceberg peut être restauré avec la cible `snapshots` du Makefile :  
  ```bash
  make snapshots TABLE=silver.reviews SNAPSHOT=<id>
  ```
  Le retour en arrière se fait donc par bascule d’alias, pas par recopie de fichiers.

## Quand ça ne marche pas
| Symptôme | Cause mesurée | Action corrective |
|----------|---------------|-------------------|
| `docker compose up --build` ne se termine jamais | L'**écriture** de l'image se bloque à `exporting layers` sur le disque externe, **sans erreur** : deux constructions complètes perdues le 20/09/2026, toutes étapes en cache et `pip check` compris. Sujet R46 | **Ne jamais passer `--build`** sur cette machine. Le code du paquet est déjà monté en lecture seule dans le conteneur Airflow (`docker-compose.yml`), donc un changement de code ne demande **aucune** reconstruction |
| Une commande `docker run --rm` ne rend jamais la main | Le conteneur **s'exécute bel et bien** — sa sortie est dans `docker logs` — mais le **retrait de sa couche** se bloque sur le disque externe. Le client reste suspendu et laisse un conteneur derrière lui : dix-neuf en ont été retirés le 20/09/2026, un par tentative | Lancer en détaché, `-d` avec un `--name` fixe, puis lire `docker logs <nom>`. Un échec ne laisse alors **qu'un** conteneur, réutilisable |
| Vérification du statut d’un pipeline renvoie toujours 0 | Lecture de `$?` après un tuyau | Ne pas utiliser `$?` après un pipe ; récupérer le code de la première commande séparément |
| Script `.sh` échoue avec `set: Illegal option -` | Fins de ligne CRLF (script créé sous Windows) | S’assurer que le fichier possède l’attribut `eol=lf` via `.gitattributes` ou convertir avec `dos2unix` |
| Service `mlflow` reste « unhealthy » pendant > 180 s | Temps de migration initiale (170 s‑580 s) | Attendre le `start_period` (180 s) avant de conclure à une panne |
| Service `api` reste « unhealthy » pendant > 420 s | Chargement du champion depuis MLflow (plusieurs minutes) | Attendre le `start_period` (420 s) avant d’intervenir |
| Service `airflow-db` reste « unhealthy » pendant > 600 s | `syncing data directory (fsync)` > 11 min après arrêt brutal | Attendre le `start_period` (600 s) avant de redémarrer le service |

## Ce que ce runbook ne couvre pas
- Déploiement sur plusieurs machines ou dans un environnement cloud.  
- Mise à l’échelle horizontale (replication de services, load‑balancing).  
- Procédure de bascule sans interruption (blue‑green, canary).  
- Gestion du disque USB externe au niveau du système d’exploitation.  
- Intégration continue / déploiement continu (CI/CD) externe au dépôt.  
- Monitoring avancé (alertes, tableaux de bord externes).  

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
