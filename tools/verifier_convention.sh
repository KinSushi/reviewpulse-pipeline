#!/bin/sh
# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
# Refuse qu'une etiquette de classe soit ecrite en dur hors du module qui la definit.
#
# Quoi     : parcourt l'arbre syntaxique du code (src, dashboard, dags, tools) et signale, hors de
#            `src/reviewpulse/decision.py` : un `pos_label=0` ou `pos_label=1` ; une comparaison
#            `== 0`, `== 1`, `!= 0`, `!= 1` sur une ligne qui parle d'etiquettes (`label`, `y`,
#            `y_...`). La longueur d'une liste (`len(...) == 0`) n'est pas une etiquette et passe.
# Pourquoi : l'ADR 0009 fait de `decision.py` la SEULE definition de la convention -- 0 pour un
#            avis negatif, 1 pour un avis positif -- apres une inversion entre deux modules trouvee
#            par le test de la pile : 95 % d'avis predits negatifs pour 4 % reels. Le 21/09/2026,
#            un balayage a pourtant trouve l'etiquette negative reecrite « 0 » a sept endroits de
#            `score.py`, `quality.py` et `train.py`. Tant que la valeur est la meme partout, rien ne
#            casse ; le jour ou la convention bouge, sept endroits se trompent en silence. Une
#            convention unique se prouve par l'absence de copies, pas par une phrase dans un ADR.
# Ou       : a la racine du depot ; appele par la campagne de preuves, la CI et `make convention`.
# Comment  : sh tools/verifier_convention.sh [fichier_ou_dossier ...]
#            Rend 0 si aucune etiquette n'est ecrite en dur, 1 sinon, en nommant fichier et ligne.
set -u

python - "$@" <<'PY'
import ast
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SOURCE_DE_VERITE = "src/reviewpulse/decision.py"
PARLE_D_ETIQUETTES = re.compile(r"label|(?<![A-Za-z0-9_])y(?:_[A-Za-z0-9_]*)?(?![A-Za-z0-9_])")


def fichiers(cibles):
    for cible in cibles or ["src", "dashboard", "dags", "tools"]:
        chemin = pathlib.Path(cible)
        if chemin.is_dir():
            yield from sorted(chemin.rglob("*.py"))
        elif chemin.suffix == ".py":
            yield chemin


def est_zero_ou_un(noeud):
    return isinstance(noeud, ast.Constant) and type(noeud.value) is int and noeud.value in (0, 1)


def est_une_longueur(noeud):
    return isinstance(noeud, ast.Call) and isinstance(noeud.func, ast.Name) and noeud.func.id == "len"


fautes = []
for chemin in fichiers(sys.argv[1:]):
    if chemin.as_posix().endswith(SOURCE_DE_VERITE):
        continue
    source = chemin.read_text(encoding="utf-8")
    lignes = source.splitlines()
    for noeud in ast.walk(ast.parse(source)):
        if isinstance(noeud, ast.keyword) and noeud.arg == "pos_label" and est_zero_ou_un(noeud.value):
            fautes.append((chemin.as_posix(), noeud.value.lineno, "pos_label ecrit en dur"))
        elif isinstance(noeud, ast.Compare) and len(noeud.ops) == 1 and isinstance(noeud.ops[0], (ast.Eq, ast.NotEq)):
            gauche, droite = noeud.left, noeud.comparators[0]
            constante, autre = (droite, gauche) if est_zero_ou_un(droite) else (gauche, droite) if est_zero_ou_un(gauche) else (None, None)
            if constante is None or est_une_longueur(autre):
                continue
            if PARLE_D_ETIQUETTES.search(lignes[noeud.lineno - 1]):
                fautes.append((chemin.as_posix(), noeud.lineno, "etiquette comparee a %d en dur" % constante.value))

for fichier, ligne, motif in sorted(set(fautes)):
    print("%s:%d CONVENTION : %s -- ecrire decision.LABEL_NEGATIVE ou decision.LABEL_POSITIVE" % (fichier, ligne, motif))
print("Convention : %d etiquette(s) ecrite(s) en dur hors de %s." % (len(set(fautes)), SOURCE_DE_VERITE))
sys.exit(1 if fautes else 0)
PY
