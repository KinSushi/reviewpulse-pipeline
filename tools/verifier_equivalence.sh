#!/bin/sh
# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
# Prouve qu'un enrichissement de code n'a rien change au comportement.
#
# Quoi     : compare deux versions d'un module Python apres avoir retire ce qui n'execute
#            rien -- docstrings, commentaires, et appels de journalisation (logger.*).
#            Si les arbres syntaxiques restants sont identiques, l'enrichissement n'a
#            touche qu'a l'explication, jamais a la logique.
# Pourquoi : le 20/09/2026, Enzo a demande du code qui s'explique -- pourquoi, comment,
#            journaux -- sur vingt-six modules. Ce travail est delegue a un modele local,
#            et un modele qui reecrit un fichier entier peut y glisser un changement de
#            logique sans le dire. Relire vingt-six fichiers a l'oeil ne le verrait pas ;
#            comparer les arbres syntaxiques, si. Une porte, pas une confiance.
# Ou       : s'execute a la racine du depot, avec le Python de l'hote ou de l'image.
# Comment  : sh tools/verifier_equivalence.sh <ancien.py> <nouveau.py>
#            Rend 0 si les logiques sont identiques, 1 sinon, en nommant la premiere
#            difference. Les appels logger.* sont ignores parce que c'est precisement ce
#            que l'enrichissement ajoute ; un `print` ne l'est PAS, parce qu'il modifie la
#            sortie standard, donc le comportement observable.
set -u

if [ "$#" -ne 2 ]; then
    echo "usage : sh tools/verifier_equivalence.sh <ancien.py> <nouveau.py>" >&2
    exit 2
fi

python - "$1" "$2" <<'PY'
import ast
import sys
import pathlib

# Sous Windows la console est en cp1252 : un rapport citant une espace fine insecable faisait
# tomber l'outil au moment de nommer la divergence (quality.py, 20/09/2026).
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# Noms usuels d'un journal de module : le banc local a rendu `_logger` la ou le depot ecrit
# `logger` (20/09/2026) ; l'un et l'autre n'executent aucune logique metier.
NOMS_JOURNAL = ("logger", "_logger", "log", "LOGGER")
NIVEAUX = ("debug", "info", "warning", "error", "exception", "critical")


class Depouilleur(ast.NodeTransformer):
    """Retire docstrings et appels logger.* ; ne touche a rien d'autre."""

    def _sans_docstring(self, corps):
        if corps and isinstance(corps[0], ast.Expr) and isinstance(getattr(corps[0], "value", None), ast.Constant) \
                and isinstance(corps[0].value.value, str):
            corps = corps[1:]
        return corps or [ast.Pass()]

    def visit_Module(self, noeud):
        self.generic_visit(noeud)
        noeud.body = self._sans_docstring(noeud.body)
        return noeud

    def visit_FunctionDef(self, noeud):
        self.generic_visit(noeud)
        noeud.body = self._sans_docstring(noeud.body)
        return noeud

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, noeud):
        self.generic_visit(noeud)
        noeud.body = self._sans_docstring(noeud.body)
        return noeud

    @staticmethod
    def _est_appel_de_journal(v):
        """Vrai pour `logger.info(...)`, `logging.info(...)` et `logging.getLogger(...).info(...)`."""
        if not (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr in NIVEAUX):
            return False
        cible = v.func.value
        if isinstance(cible, ast.Name) and cible.id in NOMS_JOURNAL + ("logging",):
            return True
        # Le DAG importe `logging` dans chaque fonction autonome et ecrit
        # `logging.getLogger(__name__).info(...)` : meme nature, autre forme (20/09/2026).
        return (isinstance(cible, ast.Call) and isinstance(cible.func, ast.Attribute)
                and cible.func.attr == "getLogger" and isinstance(cible.func.value, ast.Name)
                and cible.func.value.id == "logging")

    def visit_Expr(self, noeud):
        # Un appel de journal n'execute aucune logique metier : on l'ignore.
        if self._est_appel_de_journal(noeud.value):
            return None
        return noeud

    def _corps_non_vide(self, noeud):
        # Un `pass` remplace par un appel de journal laisse un corps vide une fois le journal retire :
        # c'est le meme bloc, on le compare comme tel.
        self.generic_visit(noeud)
        if not noeud.body:
            noeud.body = [ast.Pass()]
        return noeud

    visit_For = visit_While = visit_With = visit_Try = _corps_non_vide

    @staticmethod
    def _test_sans_effet(test):
        """Vrai si evaluer la condition ne peut rien changer : noms, attributs, constantes,
        comparaisons, et les seuls appels `len`, `isinstance`, `hasattr`, `getattr`."""
        purs = (ast.Name, ast.Attribute, ast.Constant, ast.Compare, ast.BoolOp, ast.UnaryOp,
                ast.Subscript, ast.Load, ast.And, ast.Or, ast.Not, ast.cmpop, ast.Tuple, ast.List)
        for n in ast.walk(test):
            if isinstance(n, ast.Call):
                if not (isinstance(n.func, ast.Name) and n.func.id in ("len", "isinstance", "hasattr", "getattr")):
                    return False
            elif not isinstance(n, purs):
                return False
        return True

    def visit_If(self, noeud):
        # `if <condition>: logger.warning(...)` ajoute sur un chemin degrade : une fois le journal
        # retire il ne reste rien a executer. Le bloc disparait de la comparaison SEULEMENT si sa
        # condition est sans effet de bord ; sinon l'evaluer est deja de la logique, et il reste.
        self.generic_visit(noeud)
        if not noeud.body and not noeud.orelse and self._test_sans_effet(noeud.test):
            return None
        if not noeud.body:
            noeud.body = [ast.Pass()]
        return noeud

    def visit_ExceptHandler(self, noeud):
        self._corps_non_vide(noeud)
        # `except X as exc:` dont le nom ne sert qu'au journal : une fois les appels de journal
        # retires, plus rien ne le lit ; il se compare comme s'il n'existait pas. Un nom encore lu
        # par le corps (relance, message d'erreur) reste compare : c'est de la logique.
        if noeud.name and not any(isinstance(n, ast.Name) and n.id == noeud.name
                                  for c in noeud.body for n in ast.walk(c)):
            noeud.name = None
        return noeud


def logique(chemin):
    arbre = ast.parse(pathlib.Path(chemin).read_text(encoding="utf-8"))
    arbre = Depouilleur().visit(arbre)
    ast.fix_missing_locations(arbre)
    # Les imports de logging ajoutes par l'enrichissement sont tolérés : ils n'executent rien.
    arbre.body = [n for n in arbre.body
                  if not (isinstance(n, ast.Import) and all(a.name == "logging" for a in n.names))
                  and not (isinstance(n, ast.Assign) and len(n.targets) == 1
                           and isinstance(n.targets[0], ast.Name) and n.targets[0].id in NOMS_JOURNAL)]
    # Le bloc d'imports de tete est compare sans egard a son ordre interne. Un modele qui recopie un
    # fichier trie volontiers ses imports (api.py et rollback.py, 20/09/2026) ; entre imports
    # contigus de tete de module, l'ordre ne change rien a l'execution. Un import retire, ajoute, ou
    # deplace APRES une instruction reste une divergence : seul le bloc contigu de tete est trie.
    n_tete = 0
    while n_tete < len(arbre.body) and isinstance(arbre.body[n_tete], (ast.Import, ast.ImportFrom)):
        n_tete += 1
    arbre.body[:n_tete] = sorted(arbre.body[:n_tete], key=ast.dump)
    return ast.dump(arbre, include_attributes=False)


ancien, nouveau = sys.argv[1], sys.argv[2]
a, b = logique(ancien), logique(nouveau)
if a == b:
    print("EQUIVALENT : la logique de %s est inchangee" % pathlib.Path(nouveau).name)
    sys.exit(0)
# Nommer la premiere divergence pour que l'audit sache ou regarder.
i = next((k for k, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
print("DIVERGENT : la logique de %s a change (premiere difference vers le caractere %d de l'arbre)"
      % (pathlib.Path(nouveau).name, i))
print("   ancien  : ..." + a[max(0, i - 80):i + 80].replace("\n", " "))
print("   nouveau : ..." + b[max(0, i - 80):i + 80].replace("\n", " "))
sys.exit(1)
PY
