# Discours du Demo Day — dix minutes, mot pour mot

**Ce document est le texte parlé.** Le minutage vit dans `script_10_minutes.md` ; ici, ce qu'Enzo
dit, phrase par phrase, avec le raisonnement dit à voix haute. Environ 1 400 mots : dix minutes à
un rythme de soutenance, démonstration comprise. Les indications entre crochets ne se lisent pas.

---

## 0:00 — Diapositive 1 · Titre

Bonjour. Je m'appelle Enzo, et je vais vous présenter ReviewPulse : une chaîne de données qui, chaque
matin, trie les avis négatifs laissés sur Steam pour qu'une équipe de jeu vidéo lise d'abord ceux
qui comptent.

Je vais suivre la consigne du Final Project à la lettre : le cas métier, le choix entre un modèle
classique et un LLM, la conception de la chaîne, une démonstration en direct, et ce que je
construirais ensuite. Et à chaque étape, je vous dirai non seulement ce que j'ai fait, mais pourquoi,
et comment je sais que ça marche.

## 0:40 — Diapositive 3 · Le problème métier

Le contexte. Un studio qui publie un jeu sur Steam reçoit des avis par centaines chaque jour, dans une
vingtaine de langues. Personne ne les lit tous. Résultat : quand un patch casse quelque chose, quand
un prix passe mal, la note visible sur la page du jeu baisse pendant plusieurs jours avant que
quelqu'un ne comprenne pourquoi.

L'utilisateur, c'est la personne responsable de la communauté et du *live-ops*. Sa décision, chaque
matin : quels retours négatifs remonter aux développeurs, sur quel jeu, dans quelle langue, en
priorité. Et « utile » a un sens précis que j'ai écrit dans la charte avant la première ligne de
code : un tableau de bord quotidien, la part d'avis négatifs prédite par jeu et par langue, les avis
à lire en premier, et les termes qui pèsent dans la prédiction. Avec un seuil de mise en service :
un F1 macro d'au moins 0,75, sinon le modèle ne sert pas.

Pourquoi écrire ça avant de coder ? Parce qu'une chaîne de données sans décision servie est un
exercice technique, pas un produit. La charte, c'est la boussole des trois jours.

## 1:40 — Diapositive 6 · Les données réelles

Les données sont réelles, collectées par l'API publique de Steam : plus de neuf mille lignes brutes, trois jeux,
anglais et français. Je ne les ai pas fabriquées, et c'est volontaire : la consigne dit « real data,
or the project is a toy » — et le désordre des vraies données est justement ce qui oblige les
transformations à faire un vrai travail.

Cinq étapes, testées à chaque passage. D'abord, la zone brute : chaque objet reçu de l'API est déposé
tel quel, jamais modifié. C'est une exigence non négociable de la consigne, et c'est aussi ce qui
fonde tout le reste — si la source est intacte, tout peut être rejoué. L'ingestion est idempotente :
un manifeste d'identifiants garantit qu'un second passage n'écrit aucun doublon. Ensuite le
dédoublonnage et le nettoyage du BBCode, puis la pseudonymisation, puis les contrôles bloquants,
puis Great Expectations.

Un mot sur la confidentialité, parce qu'un avis Steam porte un identifiant de joueur. Cet identifiant
est pseudonymisé par un HMAC-SHA256 salé — pas un simple hachage, parce qu'un identifiant Steam est
court et devinable, et qu'un hachage sans sel se casse par dictionnaire. Le sel est un secret
obligatoire : sans lui, la chaîne refuse de démarrer. Les identifiants directs — pseudonyme, URL de
profil, avatar — sont supprimés dès la zone propre. Et un flux complémentaire d'avis négatifs sert à
l'entraînement seulement, jamais au test : je ne veux pas mesurer le modèle sur une distribution que
j'ai moi-même gonflée.

## 3:00 — Diapositive 13 · La chaîne de bout en bout

Voici la chaîne. Ingestion idempotente depuis Steam. Zone silver en PySpark et Iceberg : chaque
écriture crée un instantané, plus de trente aujourd'hui, chacun restaurable — c'est ma réversibilité sur
les données. Zone gold en dbt et DuckDB, avec trente tests déclarés dans les contrats.

Pourquoi ces choix, et pas d'autres ? Spark pour la zone silver parce que c'est la brique du
programme, et parce que pandas reste la référence de comparaison dans mes tests : quand les deux
divergent, c'est un défaut. dbt pour la zone gold parce que c'est le seul endroit où le travail est de
la modélisation SQL, et où un contrat compte plus que du code. DuckDB plutôt qu'un entrepôt géré parce
que la démonstration ne doit dépendre d'aucun compte externe. Chaque décision de ce genre est écrite
dans un ADR — il y en a trente et une — avec la mesure qui l'a motivée et l'alternative écartée.

## 3:50 — Diapositive 14 · Le modèle, et le choix ML ou LLM

La consigne demande de choisir entre un modèle classique et un LLM en une phrase. La mienne : classer
un avis en positif ou négatif est une tâche de tri supervisée, sur un signal textuel court, déjà
étiqueté par la plateforme elle-même. Un classifieur linéaire la résout, s'explique terme par terme,
se réentraîne en quelques secondes, et ne coûte rien à servir. Un LLM ajouterait de la latence, un
coût, et une approximation — pour un problème qui n'en a pas besoin.

J'ai d'abord mesuré des variantes : des mots, F1 macro 0,735, refusé par la barrière ; des n-grammes
de caractères, robustes aux fautes et à l'argot des joueurs ; un flux d'avis négatifs en plus ; un
réglage en validation croisée : 0,803. Puis la vraie question — un autre modèle ferait-il mieux ?
Je l'ai mesuré : neuf candidats, les mêmes plis, et la règle de décision écrite avant de lire les
résultats. La régression logistique arrive première ; la SVM linéaire fait jeu égal mais perd
l'explication exacte ; XGBoost et la forêt aléatoire sont à 0,73 et 0,72, pour un entraînement
jusqu'à vingt-trois fois plus cher. Et le seuil de décision n'est pas 0,5 : il est appris, à 0,775.

## 4:40 — Diapositive 15 · Résultats et preuves

Sur un test cent pour cent naturel, tenu à l'écart : F1 macro 0,803, AUC 0,940, rappel des négatifs
0,650. Le rappel, c'est le chiffre qui compte pour l'utilisateur : la part des vrais avis négatifs
qu'on retrouve.

Mais un chiffre seul ne vaut rien. Voici comment je sais que ça marche. Cent quarante-neuf tests
automatisés, verts. Vingt-huit tests inverses : j'injecte un défaut volontaire — je supprime la
pseudonymisation, j'inverse la convention de décision, je retire la barrière de promotion — et je
vérifie qu'un test nommé le détecte. Vingt-huit sur vingt-huit, en un seul passage, sur un runner
d'intégration continue, pas sur ma machine. Deux entraînements successifs donnent le même F1 à la
seizième décimale : le code est déterministe, la seule source de variation est l'ingestion en direct.
Et la barrière de promotion a été éprouvée dans les deux sens le même jour : elle a promu un modèle
meilleur et refusé un modèle moins bon.

## 5:30 — Démonstration en direct [écran, pas de diapositive]

Passons à l'écran. [Tableau de bord.] Voici la part d'avis négatifs prédite, contre la part réelle,
par jeu et par langue, sur les quinze derniers jours. [Filtre.] Je filtre sur un jeu, une langue.
[Liste.] Voici les avis à lire en premier, classés par probabilité. [Saisie.] Je tape un avis à la
main — « injouable, plein de bugs, remboursez-moi » — la prédiction arrive en moins de cent
millisecondes, et voici les termes qui pèsent : ce sont les coefficients exacts du modèle, pas une
approximation. [Airflow.] Et voici le DAG quotidien : neuf tâches, ingestion, silver, porte de
qualité, score, dérive, gold, porte de qualité sur silver et gold, puis la branche de réentraînement,
qui ne se déclenche que si la dérive dépasse le seuil. Elle a été évaluée hier, et elle a décidé de ne
pas se déclencher — le PSI était à 0,04 pour un seuil de 0,2.

## 8:00 — Diapositive 17 · Industrialisation, et ce que je construirais ensuite

Ce qui tourne sans moi : le DAG quotidien, la dérive mesurée à chaque passage avec une alerte écrite
hors du journal, le retour arrière outillé — un alias MLflow pour le modèle, un instantané Iceberg
pour les données — seize contrôles sur la pile déployée, et un essai de charge : trois cents requêtes,
zéro erreur, p99 à 925 millisecondes. Un chiffre que je donne avec sa nuance : le premier appel à
froid prend plusieurs secondes, parce qu'il charge le modèle. Annoncer l'un sans l'autre serait
trompeur.

Ce que je construirais ensuite — et je le dis comme un manque, pas comme un plan : la mesure de biais
par langue et par jeu, que l'AI Act demande et que je n'ai pas ; Kafka pour du temps réel, un
stockage objet, Terraform ; Kubernetes, que j'ai écarté pour la démonstration et décrit comme cible.
Chacun de ces manques est écrit dans un ADR, avec sa raison et la condition à laquelle il changerait.
Ce ne sont pas des oublis, ce sont des arbitrages.

Et une dernière chose sur le réemploi. Ce projet couvre un bloc de certification — le quatrième de
l'Architecte IA. Pour les autres, ce sont les briques qui circulent : l'orchestration, la porte de
qualité, le registre de modèles, la réversibilité. Chaque bloc garde son propre projet. Le piège
serait de prétendre qu'un projet couvre tout ; il n'en couvre qu'un, et il outille les autres.

## 9:20 — Diapositive 18 · Questions

Je résume la promesse : chaque matin, les avis négatifs qui comptent, triés, avec la raison — et une
chaîne dont chaque pièce a été mise en défaut volontairement pour prouver qu'elle tient. Je suis prêt
pour vos questions.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
