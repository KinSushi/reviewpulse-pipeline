"""reviewpulse
================

Rôle
----
Fournit le point d’entrée du paquet *reviewpulse* en exposant la configuration
partagée et la version du projet. Aucun code métier n’est implémenté ici ; le
module se contente d’importer le sous‑module :pymod:`reviewpulse.config` afin
de garantir un accès unique et centralisé aux constantes d’environnement.

Place dans la chaîne
--------------------
*Avant* : aucun module ne dépend de ``reviewpulse.__init__`` ; il est chargé
automatiquement par l’interpréteur lors de la première importation du paquet.
*Après* : tous les modules du projet importent la configuration via
``from reviewpulse import config`` et utilisent ``config.X`` au moment de l’appel.
Le module expose également ``__all__`` et ``__version__`` pour les outils
externes (pip, documentation, tests).

Fonctionnement
--------------
1. Le module est importé : le code d’initialisation exécute l’instruction
   ``from . import config``.
2. L’import déclenche l’exécution de :pymod:`reviewpulse.config`, qui lit les
   variables d’environnement et initialise les constantes (chemins, paramètres
   MLflow, etc.) conformément au contrat de code.
3. ``__all__`` limite l’export public à ``["config"]`` ; ainsi, ``import *`` ne
   révèle que le sous‑module de configuration.
4. ``__version__`` expose la version du paquet, mise à jour lors de chaque
   release.

Choix de conception
--------------------
- **Import du sous‑module au niveau du package**  
  *Choix* : ``from . import config`` au lieu d’un import conditionnel ou d’une
  fonction d’accès.  
  *Alternative écartée* : charger la configuration à la demande (ex. via une
  fonction ``get_config``) – aurait introduit une latence supplémentaire et
  complexifié les tests qui patchent directement les attributs du module.

- **Export limité via ``__all__``**  
  *Choix* : ne publier que ``config`` afin d’éviter les fuites d’implémentation.  
  *Alternative écartée* : exposer d’autres symboles (ex. ``__version__``) dans
  ``__all__`` – inutile pour les usages internes et pouvait créer des conflits
  d’import.

- **Version statique dans le code**  
  *Choix* : définir ``__version__ = "0.1.0"`` directement.  
  *Alternative écartée* : le récupérer dynamiquement depuis ``importlib.metadata`` –
  dépendance supplémentaire non requise pour le projet et compliquait la
  reproductibilité des tests.

Garanties
---------
- Le sous‑module :pymod:`reviewpulse.config` est importé exactement une fois,
  garantissant que les constantes d’environnement sont évaluées au même moment
  pour tous les modules.
- ``__all__`` assure que seules les références publiques prévues sont
  exportées.
- ``__version__`` reste immuable pendant l’exécution du processus Python.

Tests associés
--------------
Aucun test ne cible directement ce module ; il est néanmoins couvert indirectement
par l’ensemble des tests qui importent ``reviewpulse`` (ex. ``test_fresh_dirs.py``,
``test_artifacts_location.py``). Aucun fichier de test dédié n’est requis.
"""

# Import du sous‑module de configuration selon la convention du projet
from . import config

__all__ = ["config"]
__version__ = "0.1.0"
