# Script de la démonstration — 10 minutes, puis 5 minutes de questions

Présentation : `ReviewPulse_DemoDay.pptx` (9 diapositives, gabarit Jedha).
Construction : `tools/construire_slides.py` — le fichier se régénère à l'identique depuis le gabarit.

**Principe de minutage** : les diapositives servent d'appui, la démonstration en direct occupe le cœur. Si le temps manque, c'est la partie « industrialisation » qui se raccourcit, jamais la démonstration.

| Minute | Diapositive | Ce que je dis, ce que je montre |
|---|---|---|
| 0:00–0:40 | 1 — titre | Le nom, la promesse en une phrase : trier chaque matin les avis Steam négatifs d'un studio de jeu. |
| 0:40–1:00 | 2 — sommaire | Annonce du parcours, en insistant sur le fait que la démonstration sera en direct. |
| 1:00–2:00 | 3 — problématique | La personne, la décision, le coût actuel : des centaines d'avis, lus à la main ou pas du tout ; une régression repérée plusieurs jours trop tard pendant que la note baisse. **Une phrase sur ML plutôt que LLM** : la source fournit déjà l'étiquette, un modèle supervisé suffit, s'explique et ne coûte rien à servir. |
| 2:00–3:00 | 4 — les données | Source réelle, volumes, et surtout ce qui protège : zone brute inchangée, pseudonymisation, identifiants directs supprimés, idempotence prouvée par le manifeste. |
| 3:00–4:00 | 5 — la chaîne | Les six étapes et leur automatisation. Dire que la zone silver est en Iceberg et la gold en dbt, sans s'y attarder : c'est la démonstration qui prouvera que ça tourne. |
| 4:00–4:40 | 6 — le modèle | Quatre variantes mesurées, celle retenue, et pourquoi les n-grammes de caractères. Le seuil est **appris**, pas fixé à 0,5. |
| 4:40–5:30 | 7 — résultats | F1 macro, AUC, rappel. Trois faits à dire lentement : **144 tests verts**, **27 mutations sur 27 détectées, en un seul passage, en intégration continue** — un runner GitHub vierge, pas la machine du développeur, et **les hyperparamètres réglés sur mesure** : 12 points en validation croisée, `C=10.0` retenu, **promu par la barrière** qui a **refusé** le même jour un réentraînement à l'ancienne valeur. C'est la preuve que la barrière fonctionne dans les deux sens, et **deux entraînements successifs donnent le même chiffre à la seizième décimale**. Si le jury demande ce qu'apportent les mutations : deux avaient survécu, l'une montrait que la porte de qualité n'était pas prouvée bloquante, l'autre qu'un test passait pour la mauvaise raison. |
| **5:30–8:00** | **écran, pas de diapositive** | **Démonstration en direct**, dans cet ordre : 1) le tableau de bord, part négative prédite contre part réelle, courbe des quinze derniers jours ; 2) un filtre par jeu et par langue ; 3) les avis à lire en premier ; 4) **un avis tapé à la main**, sa prédiction, puis **les termes qui pèsent** ; 5) un aller-retour dans Airflow pour montrer le DAG à **neuf tâches**, porte de qualité silver et gold et déclenchement du réentraînement compris. |
| 8:00–9:20 | 8 — industrialisation | Ce qui tourne sans intervention : le DAG à neuf tâches, la dérive mesurée à chaque passage, le retour arrière outillé, les 16 contrôles de la pile, et **l'essai de charge — 300 requêtes, 0 % d'erreur, 29,3 par seconde, p99 925 ms**. Puis **nommer les manques**, un par un et sans les habiller : le dépôt n'est pas publié et la chaîne d'intégration n'a jamais tourné en ligne ; **la mesure de biais par langue et par jeu n'existe pas**, alors que l'AI Act la demande (ADR 0021) ; Kafka, le stockage objet et Terraform sont absents ; Kubernetes est écarté pour la démonstration et décrit comme cible. Dire que **chacun de ces manques est écrit dans un ADR**, avec sa raison et sa condition de retour — ce n'est pas un oubli, c'est un arbitrage. |
| — | — | **Sur le réemploi, si la question vient** : ReviewPulse est le support du **bloc AIA 4**. Pour les autres blocs, ce sont les **briques** qui circulent — l'orchestration, la porte de qualité, le registre de modèles, la réversibilité — pas le projet. Chaque bloc garde son projet imposé : Spotify, Stripe, Fraud Detection, Kayak, Getaround. **Le piège serait de prétendre que ce projet couvre les dix blocs** ; il n'en couvre qu'un, et il outille les autres. |
| 9:20–10:00 | 9 — questions | Reformuler la promesse et rendre la parole. |

## Chemin de secours

- **Si l'API Steam ne répond pas** : la chaîne rejoue sur la zone brute déjà remplie, avec `make pipeline-gele`, qui n'ingère rien. C'est précisément l'intérêt d'une zone brute inchangée.
- **Si un service ne démarre pas** : la vidéo enregistrée la veille prend le relais ; la fiche du bloc AIA l'admet explicitement.
- **Si une question porte sur un chiffre** : les preuves sont dans `docs/evidence/`, le registre des sujets ouverts dans `docs/16_registre_suivi.md`, et l'historique daté dans le journal de bord.

## Ce qu'il reste à faire avant le jour J

1. Ouvrir la présentation et vérifier qu'aucun texte ne déborde (contrôle visuel, non automatisable ici).
2. Répéter une fois en conditions réelles, chronomètre en main.
3. Enregistrer la vidéo de secours.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
