# ADR 0029 — Surveillance de la latence

**Date** : 20/09/2026 · **Statut** : acceptée

## Contexte

Le chapitre « Monitoring Deployed Models » de la bibliothèque technique locale prescrit des SLI et SLO pour latence, qualite et ressources, un point d'acces `/metrics` minimal, et des journaux structures portant identifiant de requete, version du modele et duree. Le projet n'avait aucune visibilite sur la latence de l'API. A cinq jours de la soutenance, il fallait instrumenter sans toucher au contrat HTTP existant ni introduire de dependance nouvelle.

## Decision

Implementation dans `src/reviewpulse/api.py` :

1. Un registre en memoire des durees, une file bornee a **2 048** echantillons par point d'acces. Borne assumee : un service de longue duree ne doit pas voir sa memoire croitre indefiniment.
2. Un intergiciel HTTP qui mesure chaque requete avec `time.perf_counter` et emet **un journal structure par requete** — identifiant de requete, chemin, methode, code de statut, duree en millisecondes — sur une seule ligne JSON.
3. Une fonction `_percentile` sans numpy, en **interpolation lineaire de type 7**.
4. Un point d'acces **`/metrics`** rendant, par point d'acces observe : nombre, p50, p95, p99, moyenne, maximum ; plus le total des requetes depuis le demarrage et la duree de fonctionnement.
5. `/metrics` ne depend **pas** du modele : il repond meme si le champion n'est pas charge. C'est precisement le defaut de `/health`, qui declare `Depends(get_model)` et se noyait sous ses propres controles de sante (registre R55).

Le contrat HTTP des quatre points d'acces existants — `/health`, `/predict`, `/explain`, `/insights` — est **intact**. Aucune dependance nouvelle : bibliotheque standard seule.

Trois defauts corriges a l'audit :
- les imports etaient places au milieu du fichier ; `ruff` les refusait (E402) ;
- la docstring annoncait un « rang le plus proche » alors que le calcul est une interpolation ;
- le total des requetes etait deduit de files **bornees**, donc faux des la 2 049e requete. Un compteur reel a ete ajoute, et le nombre d'echantillons retenus est rendu separement.

**Le piege** : `/metrics` melange les requetes a froid et a chaud. Le premier passage d'un service fraichement demarre porte le chargement du modele : **p99 mesure a 5 874 ms au premier essai contre 925 ms a chaud**, sur le meme systeme. Un centile lu sans cette precision est trompeur, et ce chiffre-la ne doit jamais etre annonce seul.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Taux de desaccord champion/challenger | L'API ne charge que le champion ; l'exploiter demanderait un trafic miroir vers le challenger, donc une refonte. |
| Assumer l'absence par ecrit | Option perdante de la decision, rejetee par l'arbitrage fonde sur les faits. |

## Consequences

- La latence est observable par point d'acces, avec centiles et total reel.
- Aucune alerte automatique sur la latence avant la soutenance, aucune vue sur le processeur ni la memoire.
- Condition de revision, reprise de l'option perdante : au-dela de 300 requetes par jour, ou si la latence a chaud depasse 1 s, une alerte automatique devra etre ajoutee.

## Comment cette decision a ete prise

Deux familles de modeles ont redige la decision independamment et ont diverge — l'une concluait qu'il fallait instrumenter, l'autre qu'il fallait assumer l'absence par ecrit. Une troisieme famille a arbitre, avec pour consigne de s'appuyer sur les faits et non sur une preference. Elle a tranche pour l'instrumentation, en demandant de reprendre trois apports de l'option perdante. L'orchestrateur a verifie les faits et corrige trois defauts du code produit. C'est la premiere decision du projet prise ainsi.
