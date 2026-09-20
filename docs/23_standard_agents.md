# Standard de production — ce que tout agent délégué doit respecter

**Date** : 20/09/2026. **Statut** : source de vérité, pas une recommandation.

Ce document existe parce qu'un standard qu'on ne transmet pas n'est pas un standard. Jusqu'au
20/09/2026, chaque tâche envoyée au banc gratuit partait **sans aucune consigne de projet** :
les modèles travaillaient « à leur manière », et l'audit rattrapait ensuite. Il rattrapait
souvent — mais rattraper coûte plus cher que prescrire.

La version courte et machine de ce document vit dans `tools/standard_agent.txt`. Elle est
passée à chaque délégation par `--systeme`, ce qui rend l'héritage **mécanique** plutôt que
déclaratif.

## Le principe

Aucun agent n'a un standard inférieur à celui de l'orchestrateur. La chaîne d'héritage est :

> orchestrateur → standard de référence → sous-tâche → agent → implémentation → tests →
> audit → intégration.

Un agent qui reçoit une sous-tâche hérite des contraintes du projet, des conventions de code,
des règles d'architecture, de test, de documentation, de sécurité et de réversibilité, ainsi
que des critères de validation.

## Ce que le projet exige, et pourquoi il l'exige

Chaque règle ci-dessous est née d'un défaut réellement rencontré. Elles ne sont pas des
généralités de style.

| Règle | Le défaut qui l'a produite |
|---|---|
| **Aucun chiffre inventé.** Un chiffre absent des sources s'écrit « à mesurer » | Le 19/09, à température 0,7, le banc a rendu un document dont **toutes** les mesures étaient inventées |
| **Aucun nom de fichier, de fonction ou d'ADR inventé** | Un ADR affirmait « déploiement sur Kubernetes documenté (ADR 0012) » alors que l'ADR 0012 **écarte** Kubernetes |
| **Les imports vont en tête de fichier** | Un `import os` manquant a tué un outil **après sept minutes de calcul** ; des imports au milieu d'un fichier sont refusés par `ruff` (E402) |
| **Une ancre se recopie depuis le disque, jamais de mémoire** | La typographie française emploie des espaces fines insécables (U+202F) : `ADR 0005` n'est pas `ADR 0005` |
| **Un état dérivé ne remplace pas un état réel** | Un compteur « total depuis le démarrage » déduit de files **bornées** était faux dès la 2 049ᵉ requête |
| **Une docstring décrit ce que le code fait** | Une docstring annonçait un « rang le plus proche » là où le calcul interpole |
| **Un contrat public ne change pas sans raison écrite** | Les quatre points d'accès de l'API sont vérifiés par le test de la pile déployée |
| **Un témoin accompagne chaque test** | Une porte qui n'a jamais refusé ne prouve rien ; deux mutations ont survécu parce qu'un test passait pour la mauvaise raison |
| **Aucune dépendance nouvelle sans justification** | `confluent-kafka` était déclaré et jamais importé ; il alourdissait chaque image et faisait échouer `pip check` |
| **Dire ce que le travail n'établit pas** | Un passage vert ne prouve pas qu'une porte **refuse** ; il faut l'écrire |

## Ce qui est refusé, et ne sera pas fusionné

Du pseudo-code présenté comme terminé. Un bouchon sans justification écrite. Un contournement
temporaire laissé en place. La duplication d'une fonctionnalité existante. Du code qui compile
mais ne s'importe pas, qui s'importe mais ne s'exécute pas, ou qui s'exécute en produisant un
état incorrect. Une correction locale qui crée une régression ailleurs. Un `TODO` silencieux
qui masque une fonctionnalité inachevée.

## Ce que l'agent doit rendre

Le contenu demandé, dans le format demandé, et **rien d'autre**. Quand une information manque,
le dire explicitement plutôt que de la supposer : une incertitude signalée coûte une
vérification, une invention coûte la crédibilité du livrable devant un jury.

## Ce que l'orchestrateur fait ensuite

Il n'accepte pas un résultat parce qu'il « paraît bon ». Il l'audite mécaniquement contre le
code réel : existence des fichiers et des fonctions cités, chiffres non fournis, `ruff`,
compilation, tests, et retours de la machine. Les contrôles employés à ce jour vivent dans
`tools/verifier_briques.py`, `tools/verifier_justifications.py`,
`tools/verifier_documentation.sh` et la phase de lint de `tools/campagne_preuves.sh`.
