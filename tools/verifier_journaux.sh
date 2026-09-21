#!/bin/sh
# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
# Refuse un appel de journal qui ecrirait une donnee, ou qui formate sa chaine trop tot.
#
# Quoi     : parcourt l'arbre syntaxique des fichiers Python donnes (par defaut : src, dags,
#            dashboard) et examine chaque appel de journal -- `logger.info(...)`,
#            `logging.info(...)`, `logging.getLogger(...).info(...)`. Deux refus :
#            - FUITE    : un argument est une donnee issue de personnes ou un secret, passe tel
#                         quel -- le texte d'un avis, un identifiant Steam, le sel, une ligne, un
#                         DataFrame entier. `len(df)` passe ; `df` ne passe pas.
#            - F-STRING : la chaine est formatee avant l'appel ; le journal perd son formatage
#                         paresseux, et la chaine est construite meme quand le niveau est coupe.
# Pourquoi : le 21/09/2026, l'enrichissement du code a multiplie les appels de journal, et un
#            rendu du tableau de bord passait deux DataFrames entiers a `logger.warning`. Les
#            relecteurs, eux, criaient a la fuite sur des journaux qui n'ecrivaient que des
#            comptes. Ni la confiance ni la relecture ne tranchent : un controle d'arbre, si. La
#            charte promet qu'aucun identifiant ni texte d'avis ne sort de la zone propre ; un
#            journal est une sortie.
# Ou       : a la racine du depot ; appele par la campagne de preuves et par la CI.
# Comment  : sh tools/verifier_journaux.sh [fichier_ou_dossier ...]
#            Rend 0 si aucun appel n'est fautif, 1 sinon, en nommant fichier, ligne et motif.
set -u

python - "$@" <<'PY'
import ast
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NIVEAUX = ("debug", "info", "warning", "error", "exception", "critical")
NOMS_JOURNAL = ("logger", "_logger", "log", "LOGGER", "logging")
# Noms qui portent une donnee issue de personnes, un secret, ou un jeu de donnees entier.
RISQUES = {
    "review_text", "text", "texts", "texte", "textes", "steamid", "author", "author_id",
    "personaname", "profile_url", "avatar", "salt", "sel", "row", "rows", "payload", "body",
    "df", "df_clean", "df_scored", "clean_df", "scored", "scored_df", "summary_df", "natural",
}


def est_appel_de_journal(noeud):
    if not (isinstance(noeud, ast.Call) and isinstance(noeud.func, ast.Attribute) and noeud.func.attr in NIVEAUX):
        return False
    cible = noeud.func.value
    if isinstance(cible, ast.Name):
        return cible.id in NOMS_JOURNAL
    return (isinstance(cible, ast.Call) and isinstance(cible.func, ast.Attribute)
            and cible.func.attr == "getLogger")


def risque(argument):
    """Rend le nom fautif si l'argument livre une donnee telle quelle, sinon None."""
    if isinstance(argument, ast.Name) and argument.id in RISQUES:
        return argument.id
    if isinstance(argument, ast.Attribute) and argument.attr in RISQUES:
        return argument.attr
    if isinstance(argument, ast.Subscript) and isinstance(argument.slice, ast.Constant) \
            and argument.slice.value in RISQUES:
        return str(argument.slice.value)
    # str(row), repr(df) : la donnee sort quand meme. len(df), type(df) : non.
    if isinstance(argument, ast.Call) and isinstance(argument.func, ast.Name) \
            and argument.func.id in ("str", "repr", "format") and argument.args:
        return risque(argument.args[0])
    return None


def fichiers(cibles):
    for cible in cibles or ["src", "dags", "dashboard"]:
        chemin = pathlib.Path(cible)
        if chemin.is_dir():
            yield from sorted(chemin.rglob("*.py"))
        elif chemin.suffix == ".py":
            yield chemin


fautes, appels = [], 0
for chemin in fichiers(sys.argv[1:]):
    arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    for noeud in ast.walk(arbre):
        if not est_appel_de_journal(noeud):
            continue
        appels += 1
        if noeud.args and isinstance(noeud.args[0], ast.JoinedStr):
            fautes.append("%s:%d F-STRING : la chaine est formatee avant l'appel" % (chemin.as_posix(), noeud.lineno))
        for argument in list(noeud.args[1:]) + [k.value for k in noeud.keywords]:
            nom = risque(argument)
            if nom:
                fautes.append("%s:%d FUITE : `%s` est passe tel quel au journal" % (chemin.as_posix(), noeud.lineno, nom))

for faute in fautes:
    print(faute)
print("Journaux : %d appel(s) examine(s), %d fautif(s)." % (appels, len(fautes)))
sys.exit(1 if fautes else 0)
PY
