# Questions probables du jury — réponses et preuves

Chaque réponse renvoie à une preuve consultable. Les chiffres sont ceux du 16/09/2026.

---

## Cas métier et données

**Pourquoi ce sujet ?**
Une équipe community & live-ops reçoit des centaines d'avis par jour en plusieurs langues et repère les problèmes avec retard. L'étiquette `voted_up` est fournie par l'auteur lui-même : la qualité se mesure sans annotation. → `01_charte.md`, ADR 0001.

**Ces données sont-elles « réelles et sales » comme l'exige l'énoncé ?**
Oui : flux mis à jour en continu, BBCode, textes vides, doublons entre passages, plus de vingt langues, 9 % seulement d'avis négatifs. → ADR 0001, `transform.py`.

**Avez-vous le droit de les utiliser ?**
API publique sans clé ; usage analytique agrégé, sans republication des textes ; les conditions d'utilisation de Steam sont à citer dans le dossier. Données personnelles traitées selon l'ADR 0004.

**Qui possède la donnée ?**
Valve et les auteurs des avis. → Charte.

## Architecture et pipeline

**Montrez-moi que la zone brute est inchangée.**
Une ligne = l'objet reçu, écrit par `json.dumps` ; le test `test_ingest.py` relit chaque ligne et la compare à l'objet reçu. → ADR 0002.

**Que se passe-t-il si je relance l'ingestion deux fois ?**
Rien de nouveau n'est écrit : 6 000 avis puis 0 le 16/09. Le contrôle F1 du test réel vérifie, **par flux et sur tous les fichiers**, autant de lignes que d'identifiants distincts (6 005 / 6 005 et 2 797 / 2 797). → `evidence/forward_test.md`.

**Et si le programme s'arrête au milieu ?**
Manifeste puis lot sont écrits dans des fichiers temporaires puis renommés : aucun avis brut n'existe sans être référencé. → ADR 0002.

**Pourquoi pandas et pas Spark ?**
Quelques milliers de lignes, quelques Mo : Spark coûterait une JVM pour rien. Seuil de bascule écrit : environ 10 millions d'avis. → ADR 0003.

**Où est votre test de qualité ?**
Une série de contrôles bloquants (liste exhaustive dans l'ADR 0005) avant l'écriture de la zone propre ; un échec arrête la tâche et laisse la zone précédente intacte. → ADR 0005.

**Comment savez-vous que vos tests servent à quelque chose ?**
Tests inverses : 13 défauts graves injectés dans une copie du code, **13 détectés**, chacun par un test nommé ; une mesure témoin sans défaut passe (48 tests). Le premier passage avait révélé **3 défauts non détectés** : trois tests ont été ajoutés. → `evidence/reverse_tests.md`.

## Données personnelles et conformité

**Vos données sont-elles anonymes ?**
**Non, pseudonymisées.** `steamid` est remplacé par un HMAC-SHA256 salé ; pseudonyme, profil et avatar sont supprimés. Une donnée pseudonymisée reste une donnée personnelle au sens du RGPD. → ADR 0004.

**Pourquoi un HMAC et pas un simple SHA-256 ?**
Les `steamid` sont des entiers sur 17 chiffres, énumérables : un hachage simple se renverse par dictionnaire.

**Que se passe-t-il sans sel ?**
Le job s'arrête avec un message explicite et la zone propre n'est pas modifiée (vérifié le 16/09). → ADR 0004.

**Et l'AI Act ?**
Classement de sentiment sur des avis de produits, sans décision sur des personnes : risque minimal. La transparence est assurée (seuil et version affichés).

## Modèle

**Pourquoi pas un LLM ?**
L'étiquette est fournie : une classification linéaire résout la tâche en secondes, s'explique terme par terme et ne coûte rien à servir. → ADR 0006.

**Pourquoi des n-grammes de caractères ?**
Quatre variantes mesurées ; celle-ci a le meilleur rappel des négatifs (0,639) pour un F1 équivalent, avec un seul vectoriseur, et tolère fautes et mélange de langues. → ADR 0006.

**Quel est votre chiffre de qualité ?**
F1 macro **0,807** sur un test **100 % naturel** tenu à l'écart ; 0,802 en validation croisée ; AUC 0,948 ; rappel 0,639 et précision 0,657 sur les négatifs. → README, ADR 0007.

**Comment gérez-vous le déséquilibre ?**
Pondération des classes, plus un flux d'avis négatifs réels **réservé à l'entraînement**. Le test reste naturel, sinon la mesure serait flatteuse. Gain mesuré sur le même test : F1 0,750 → 0,798. → ADR 0007.

**Comment avez-vous choisi le seuil de 0,75 ?**
Par validation croisée sur les données d'entraînement uniquement, jamais sur le test. → ADR 0007.

**Votre modèle est-il cohérent en production ?**
Pour chaque jeu et chaque langue, la part négative prédite vaut entre 0,797 et 1,209 fois la part réelle (contrôle F4, tolérance fixée à [0,5 ; 2]). → `evidence/forward_test.md`.

**Un avis sur deux signalé comme négatif est-il faux ?**
C'était le cas avant l'amélioration (précision 0,50) ; c'est maintenant environ un sur trois (0,657). Pour un outil de **priorisation de lecture**, une lecture inutile coûte peu ; le rappel compte davantage.

**Comment expliquez-vous une prédiction ?**
Modèle linéaire : les 20 termes les plus négatifs et positifs sont enregistrés à chaque entraînement (`artifacts/top_terms.json` dans MLflow).

## Industrialisation

**Que se passe-t-il si le nouveau modèle est moins bon ?**
Il n'est pas promu : la version 5, entraînée par le DAG hebdomadaire (F1 0,798), n'a pas remplacé la version 2 (F1 0,807). → ADR 0008.

**Et s'il est exactement aussi bon ?**
Pas de promotion non plus (« strictement meilleur ») : la version 3, entraînée sur les mêmes données, a donné **exactement les mêmes métriques** — preuve de reproductibilité.

**Comment revenir en arrière ?**
Déplacer l'alias `champion` vers la version précédente dans MLflow ; l'API la charge au redémarrage.

**Que se passe-t-il à la première installation, sans modèle ?**
L'API démarre et répond 503 « Modèle indisponible », puis charge le champion dès qu'il existe, sans redémarrage (constaté le 16/09). → ADR 0008.

**Qu'est-ce qui tourne tout seul ?**
Deux DAG Airflow (quotidien et hebdomadaire, une exécution à la fois, deux nouvelles tentatives) et un workflow GitHub Actions planifié indépendant de la machine locale. → ADR 0011.

**Avez-vous eu des problèmes au déploiement ?**
Oui, et ils sont documentés : modèle introuvable (artefacts relatifs au dossier courant), écriture refusée pour l'utilisateur non-root, droits différents entre Airflow et l'application, contrôle de santé du tableau de bord sur le mauvais port, URL de l'API codée en dur, inversion de la convention de décision. Chacun a sa correction et, quand c'est possible, son test. → ADR 0009, 0010, 0011, 0012.

**Comment prouvez-vous que tout marche ailleurs que sur votre poste ?**
`make up && make jobs && make evidence` : tests unitaires, tests inverses et test de la stack déployée, avec rapports datés et numéro de commit. → `evidence/`.

## Ce que vous feriez ensuite

- Suite Great Expectations avec rapport HTML (cours du 21/09).
- Suivi de dérive (distribution de `proba_negative`, part négative) avec alerte. → schéma 10.
- Détection de thèmes (bug, prix, performance) par un LLM sur les seuls avis négatifs.
- Modèle profond de sentiment et création de données, branchés dans la même chaîne (bloc 4 du CDSD). → schéma 09.
- Cible cloud : stockage objet chiffré, MLflow et Airflow managés, Terraform. → schéma 06.
