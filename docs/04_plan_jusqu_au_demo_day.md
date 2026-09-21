# Plan jusqu'au Demo Day du 25/09/2026

Les matinées (02:30–11:00, heure de Panama) sont prises par la Lead. Le plan utilise les après-midi, et cale chaque brique **après** le cours qui l'enseigne, pour pouvoir la défendre.

| Jour | Cours du matin | Après-midi — ReviewPulse | Preuve à garder |
|---|---|---|---|
| **Mer 16/09** | Iceberg & Lakehouse | Cadrage, charte, architecture v1, contrat de code, génération du squelette, schémas | Ce dossier `docs/` |
| **Jeu 17/09** | Introduction à Airflow | Ingestion réelle sur les 3 jeux, zone brute, idempotence vérifiée (deux passages) | Capture du second passage : 0 nouvel avis |
| **Ven 18/09** | Airflow & orchestration | Transformation + contrôles qualité ; DAG quotidien testé dans Airflow | Capture du DAG vert dans l'interface Airflow |
| **Sam 19/09** | — | *Réservé au bloc 6 du CDSD (plan du 12/09)* | — |
| **Dim 20/09** | — | Entraînement + MLflow + promotion `champion` ; premier chiffre de qualité | Capture MLflow : runs comparés, alias |
| **Lun 21/09** | Great Expectations | Ajouter une suite **Great Expectations** sur la zone propre, en plus des contrôles maison | Rapport GX (Data Docs) |
| **Mar 22/09** | GitHub Actions | Dépôt public, `ci.yml` vert, `pipeline.yml` planifié, secret `REVIEWPULSE_SALT` configuré | Badge CI, run planifié réussi |
| **Mer 23/09** | Final Project (encadré) | API + tableau de bord en Docker Compose ; répétition de la démo | Vidéo de la démo complète (**livrable AIA 4**) |
| **Jeu 24/09** | Final Project (encadré) | Slides sur le gabarit Jedha, script de 10 minutes, questions probables ; **gel du code le soir** | Tag `v1.0-demoday`, empreinte du commit |
| **Ven 25/09** | **🎙️ Demo Day** | Demander l'enregistrement ; archiver les questions du jury | Enregistrement, notes |

## Le chemin de secours

Si la démo en direct échoue, elle se fait sur la vidéo enregistrée le 23/09. La fiche AIA l'admet explicitement : « captures d'écran ou vidéo ».

Si l'API Steam ne répond pas le jour J, le pipeline tourne sur la zone brute déjà remplie : c'est précisément l'intérêt de la conserver inchangée.

## La démo de 10 minutes, en une ligne par minute

1. Le problème : la ou le community manager et ses centaines d'avis quotidiens.
2. Pourquoi ML et pas LLM, en une phrase.
3. Architecture globale (schéma 01).
4. Ingestion en direct : un second passage n'écrit rien (idempotence).
5. Zone propre : pseudonymisation et contrôle qualité qui bloque (schémas 02 et 07).
6. DAG Airflow qui tourne seul (schéma 03).
7. MLflow : runs, chiffre de qualité, alias `champion` (schéma 04).
8. Tableau de bord, puis test d'un avis en direct via l'API.
9. CI/CD et monitoring (schémas 05 et 10).
10. Et après : modèle profond branché dans la même chaîne (schéma 09).

## À obtenir de Jedha avant le 23/09

- Présentation seul ou en équipe ; heure de passage.
- Les trois questions de `03_matrice_reemploi_blocs.md`.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
