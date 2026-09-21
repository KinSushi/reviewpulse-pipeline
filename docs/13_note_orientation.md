# Note d'orientation technologique — ReviewPulse

## 1. Objet et méthode
Cette note décrit les choix technologiques réellement testés dans le projet ReviewPulse.
Chaque option a été mise en œuvre, mesurée (performance, qualité, conformité) puis consignée dans un **ADR** numéroté. Une option n’est retenue qu’après essai mesuré.

## 2. Solutions essayées et tranchées

| Sujet | Options essayées | Ce qui a été mesuré | Décision (ADR) |
|---|---|---|---|
| Représentation du texte du modèle | *Mots* 1-2 grammes – C=1 ; *Mots* 1-2 grammes – C=4 ; *Caractères* 2-5 grammes – C=4 (retenue) ; combinaison mots + caractères | F1 macro : 0,735 → 0,756 → 0,759 → 0,760 ; rappel négatif : 0,611 → 0,556 → 0,639 → 0,574 ; AUC : 0,920 → 0,923 → 0,923 → 0,931 | ADR 0006 |
| Modèle classique ou LLM | Modèle linéaire TF-IDF + LogReg (classique) ; LLM (non implémenté) ; réseau profond (prévu pour bloc 4) | Performance du modèle linéaire (F1 macro 0,759, rappel 0,639, AUC 0,923) ; aucune mesure pour LLM ou réseau profond | ADR 0006 |
| Traitement pandas ou Spark | pandas (transformation) ; PySpark (zone silver) | Sur 8 231 lignes (16/09/2026) : pandas 1,7 s, Spark 7,8 s — Spark est plus lent à ce volume, à cause du démarrage de la JVM ; `spark_silver.main()` s'exécute en 5,3 s ; équivalence stricte des résultats vérifiée | pandas → ADR 0003 ; Spark → ADR 0014 |
| Format de table | Parquet (zone clean) ; Iceberg (zone silver) | Parquet utilisé pour les données propres ; Iceberg écrit des instantanés versionnés, aucune différence fonctionnelle observée | Parquet → ADR 0003 ; Iceberg → ADR 0014 |
| Entrepôt analytique | DuckDB via dbt-duckdb ; alternatives (Snowflake, Delta Lake) | Compatibilité avec le pipeline, aucune mesure de performance supplémentaire | ADR 0013 |
| Ingestion | `ingest.py` avec curseur API Steam et manifeste d’idempotence | Idempotence vérifiée : aucun doublon après réexécution ; gestion des 429/5xx | ADR 0002 |
| Environnement Python d’Airflow | Environnement unique (conflits) ; séparation via `ExternalPythonOperator` (environnement dédié) | Conflits résolus, exécutions réussies sous Airflow 2.10.3 | ADR 0013 |

## 3. Recommandations sur la latence
- **Ce qui est en place** : aucune mesure de latence n’a été enregistrée dans les livrables.
- **Ce qui reste à faire** : instrumenter les étapes d’ingestion, de transformation et de scoring (temps d’exécution, latence API) et définir des seuils d’acceptabilité.

## 4. Recommandations sur la sécurité
- **En place**
  - Pseudonymisation HMAC-SHA256 avec sel obligatoire (`REVIEWPULSE_SALT`) – ADR 0004.
  - Suppression des champs d’identification directe (`personaname`, `profile_url`, `avatar`).
  - Zone brute conservée 30 jours, accès restreint.
  - Sel fourni par la variable d’environnement `REVIEWPULSE_SALT`, jamais écrit dans le dépôt.
- **À faire**
  - Secret `REVIEWPULSE_SALT` à créer sur le dépôt distant, pour la chaîne d’intégration continue (décision d’Enzo).
  - Rotation périodique du sel et mise à jour des pseudonymes.
  - Chiffrement des données au repos (lac S3-compatible).
  - Journalisation d’accès aux zones brute et propre.
  - Revue de conformité RGPD détaillée (base légale, registre d’activité).

## 5. Veille à poursuivre
- **Détection de thèmes par LLM** – pour enrichir les insights du tableau de bord.
- **Scalabilité Spark** – validation du seuil « ≈ 10 millions d’avis » (ADR 0003).
- **Gestion managée d’Airflow** – passer d’une instance standalone à un service cloud.
- **Gestion centralisée des secrets** – intégration d’un vault ou d’AWS Secrets Manager.
- **Optimisation du stockage** – évaluation de formats colonnes (Parquet vs Iceberg) à grande échelle.
- **À compléter : citations de la bibliothèque KOS et des sources de veille externes**

## 6. Ce que la note n'affirme pas
- Mesures précises de latence et de débit du pipeline.
- Coût d’infrastructure (CPU, mémoire, stockage).
- Résilience aux pannes réseau ou aux interruptions de services externes.
- Analyse détaillée de la conformité juridique au-delà des principes généraux.

*Note rédigée le 18/09/2026*

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
