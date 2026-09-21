# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""reviewpulse
================

Rôle
----
Fournit le point d'entrée du paquet *reviewpulse* en exposant la configuration
partagée et la version du projet. Aucun code métier n'est implémenté ici ; le
module se contente d'importer le sous‑module :pymod:`reviewpulse.config` afin
de garantir un accès unique et centralisé aux constantes d'environnement.

Place dans la chaîne
--------------------
*Avant* : aucun module ne dépend de ``reviewpulse.__init__`` ; il est chargé
automatiquement par l'interpréteur lors de la première importation du paquet.
*Après* : tous les modules du projet importent la configuration via
``from reviewpulse import config`` et utilisent ``config.X`` au moment de l'appel.
Le module expose également ``__all__`` et ``__version__`` pour les outils
externes (pip, documentation, tests).

Fonctionnement
--------------
1. Le module est importé : le code d'initialisation exécute l'instruction
   ``from . import config``.
2. L'import déclenche l'exécution de :pymod:`reviewpulse.config`, qui lit les
   variables d'environnement et initialise les constantes (chemins, paramètres
   MLflow, etc.) conformément au contrat de code.
3. ``__all__`` limite l'export public à ``["config"]`` ; ainsi, ``import *`` ne
   révèle que le sous‑module de configuration.
4. ``__version__`` expose la version du paquet, mise à jour lors de chaque
   release.

Choix de conception
--------------------
- **Import du sous‑module au niveau du package**  
  *Choix* : ``from . import config`` au lieu d'un import conditionnel ou d'une
  fonction d'accès.  
  *Alternative écartée* : charger la configuration à la demande (ex. via une
  fonction ``get_config``) – aurait introduit une latence supplémentaire et
  complexifié les tests qui patchent directement les attributs du module.

- **Export limité via ``__all__``**  
  *Choix* : ne publier que ``config`` afin d'éviter les fuites d'implémentation.  
  *Alternative écartée* : exposer d'autres symboles (ex. ``__version__``) dans
  ``__all__`` – inutile pour les usages internes et pouvait créer des conflits
  d'import.

- **Version statique dans le code**  
  *Choix* : définir ``__version__ = "0.1.0"`` directement.  
  *Alternative écartée* : le récupérer dynamiquement depuis ``importlib.metadata`` –
  dépendance supplémentaire non requise pour le projet et compliquait la
  reproductibilité des tests.

Pourquoi
--------
Ce module existe pour éviter la duplication des imports de configuration dans
chaque sous‑module du paquet. Sans ce point d'entrée centralisé, chaque module
devrait importer ``reviewpulse.config`` individuellement, ce qui augmenterait le
risque d'incohérence si la logique d'import changeait. Il évite également que
des symboles internes ne soient exposés accidentellement via ``import *``.

Garanties
---------
- Le sous‑module :pymod:`reviewpulse.config` est importé exactement une fois,
  garantissant que les constantes d'environnement sont évaluées au même moment
  pour tous les modules.
- ``__all__`` assure que seules les références publiques prévues sont
  exportées.
- ``__version__`` reste immuable pendant l'exécution du processus Python.

Limites connues
---------------
- Ce module ne valide pas la configuration : si :pymod:`reviewpulse.config`
  échoue à l'import (variables d'environnement manquantes, sel absent), l'erreur
  est levée immédiatement sans message personnalisé.
- Ce module ne fournit aucun mécanisme de rechargement à chaud : une fois
  importé, ``config`` reste figé jusqu'à la fin du processus.
- Ce module ne garantit pas que ``config`` est valide : il expose le sous‑module
  tel quel, la validation relève des modules qui l'utilisent.

Tests associés
--------------
Aucun test ne cible directement ce module ; il est néanmoins couvert indirectement
par l'ensemble des tests qui importent ``reviewpulse`` (ex. ``test_fresh_dirs.py``,
``test_artifacts_location.py``). Aucun fichier de test dédié n'est requis.
"""

# Pourquoi : import relatif explicite pour garantir que config est chargé une
# seule fois au premier import du paquet, conformément à la convention du projet.
# Comment : l'instruction déclenche l'exécution de reviewpulse.config qui lit
# les variables d'environnement et initialise les constantes.
from . import config

# Pourquoi : __all__ limite l'export public pour éviter les fuites d'implémentation.
# Alternative écartée : exposer __version__ ou d'autres symboles – inutile pour
# les usages internes et source potentielle de conflits d'import.
__all__ = ["config"]

# Pourquoi : version statique définie directement dans le code pour garantir la
# reproductibilité des tests sans dépendance à importlib.metadata.
# Alternative écartée : récupération dynamique via importlib.metadata – dépendance
# supplémentaire non requise et complexité accrue pour les tests.
__version__ = "0.1.0"
