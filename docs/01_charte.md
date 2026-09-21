# ReviewPulse — charte du projet (une page)

> Livrable J1 exigé par l'énoncé Jedha *Build a Data Pipeline That Feeds an AI Model*.

**L'utilisateur.** La ou le responsable *community & live-ops* d'un studio de jeu vidéo qui publie sur Steam.

**La décision.** Chaque matin : quels retours négatifs remonter à l'équipe de développement, sur quel jeu, dans quelle langue, et avec quelle priorité.

**Le coût actuel.** Les avis arrivent par centaines chaque jour, dans une vingtaine de langues. Ils sont lus à la main ou pas du tout. Une régression, un crash après un patch ou un problème de prix est repéré avec plusieurs jours de retard, alors que la note Steam, visible sur la page du jeu, baisse déjà. *Hypothèse de chiffrage, à présenter comme telle : 1 h 30 de lecture par jour par jeu suivi.*

**Ce que « utile » veut dire.** Un tableau de bord quotidien qui donne, par jeu et par langue, la part d'avis négatifs prédite, l'évolution sur 7 jours, les avis négatifs les plus probables à lire en premier, et les termes qui pèsent dans la prédiction. **Seuil de mise en service : F1 macro ≥ 0,75** sur un jeu de test tenu à l'écart (barrière de promotion automatique dans MLflow). **Objectif : 0,80.**

*Pourquoi ce seuil, mesuré le 16/09/2026 sur 5 974 avis réels (9 % de négatifs) :* le premier modèle (mots, 1-2 grammes) obtient 0,735 et n'a **pas** été promu par la barrière, alors fixée à 0,80. Quatre variantes comparées plafonnent entre 0,756 et 0,766 (AUC 0,92 à 0,93). La variante retenue, n-grammes de caractères, atteint **F1 macro 0,759, rappel des négatifs 0,639, AUC 0,923**. L'écart restant tient au faible nombre d'avis négatifs : l'étape suivante collecte des négatifs en plus (`review_type=negative`) pour l'entraînement, en gardant l'évaluation sur la distribution naturelle.

**ML ou LLM, en une phrase.** Le besoin est de **classer** des textes courts avec une étiquette déjà fournie par la source (`voted_up`) : un modèle supervisé classique (TF-IDF + régression logistique) suffit, se réentraîne en quelques secondes, s'explique terme par terme et ne coûte rien à servir.

**La donnée et son propriétaire.** Source : API publique des avis Steam (`store.steampowered.com/appreviews/<appid>?json=1`), sans clé, mise à jour en continu, pagination par curseur. Propriétaire : Valve et les auteurs des avis. Usage limité à l'analyse agrégée, sans republication des textes. **Conditions d'utilisation Steam à relire et à citer dans le dossier.**

**Données personnelles et protection.**

| Champ reçu | Nature | Traitement |
|---|---|---|
| `author.steamid` | identifiant personnel | conservé en zone brute (accès restreint), **pseudonymisé par HMAC-SHA256 salé** en zone propre |
| `author.personaname`, `profile_url`, `avatar` | identifiants directs | **supprimés** dès la zone propre |
| `review` (texte) | peut contenir des données personnelles | conservé pour le modèle ; jamais affiché en entier sur le tableau de bord public |
| `playtime_*`, `num_games_owned` | comportement | conservés, agrégés à l'affichage |

Durée de conservation de la zone brute : 30 jours. Base légale à discuter : intérêt légitime (RGPD, art. 6.1.f). Registre AI Act : système à risque minimal (classement de sentiment, sans décision sur des personnes).

**Hors périmètre, écrit.** Réponses automatiques aux joueurs · langues autres que l'anglais et le français · détection de thèmes par LLM (piste « J+1 ») · modèle profond (réservé au bloc 4 du CDSD, en octobre, dans la même chaîne).

**Livrables.** Dépôt GitHub · diagramme d'architecture · une exécution de bout en bout avec un chiffre de qualité · démo en direct de 10 minutes.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
