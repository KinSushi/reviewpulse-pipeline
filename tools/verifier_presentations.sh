#!/bin/sh
# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
# Refuse une présentation que PowerPoint ne pourra pas ouvrir.
#
# Quoi     : ouvre chaque fichier `.pptx` suivi par le dépôt (ou ceux passés en argument) et exige
#            que CHAQUE partie XML de l'archive soit bien formée, que chaque diapositive listée ait
#            sa relation et sa partie, et qu'aucune entrée de l'archive ne soit en double.
# Pourquoi : le 21/09/2026, à quatre jours de la soutenance, PowerPoint a refusé d'ouvrir le support
#            du Demo Day -- « PowerPoint could not open the file ». Trois diapositives portaient du
#            XML mal formé : le constructeur repérait les zones de texte par `<a:t[^>]*>`, qui
#            attrape aussi `<a:tailEnd .../>`, la pointe de flèche des formes, et écrasait tout
#            jusqu'au `</a:t>` suivant. python-pptx relisait le fichier sans broncher et aucun
#            contrôle ne l'ouvrait : il n'a été trouvé qu'en demandant à PowerPoint lui-même. Un
#            support qui ne s'ouvre pas le jour J ne se rattrape pas ; il se vérifie avant.
# Où       : à la racine du dépôt ; appelé par la campagne de preuves, la CI et `make presentations`.
# Comment  : sh tools/verifier_presentations.sh [fichier.pptx ...]
#            Rend 0 si chaque présentation est saine, 1 sinon, en nommant fichier, partie et erreur.
#            Ce contrôle est nécessaire, pas suffisant : l'ouverture réelle dans PowerPoint reste à
#            faire une fois avant la soutenance.
set -u

python - "$@" <<'PY'
import collections
import pathlib
import posixpath
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REL = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}


def presentations(arguments):
    if arguments:
        return [pathlib.Path(a) for a in arguments]
    if shutil.which("git"):
        sortie = subprocess.run(["git", "ls-files", "-z", "*.pptx"], capture_output=True).stdout.decode("utf-8", errors="replace")
        return [pathlib.Path(f) for f in sortie.split(chr(0)) if f]
    return sorted(pathlib.Path("docs").rglob("*.pptx"))


fautes = []
fichiers = presentations(sys.argv[1:])
for fichier in fichiers:
    try:
        archive = zipfile.ZipFile(fichier)
    except (OSError, zipfile.BadZipFile) as erreur:
        fautes.append("%s : archive illisible -- %s" % (fichier.as_posix(), erreur))
        continue
    noms = archive.namelist()
    for nom, combien in collections.Counter(noms).items():
        if combien > 1:
            fautes.append("%s : entree en double -- %s" % (fichier.as_posix(), nom))
    for nom in noms:
        if nom.endswith((".xml", ".rels")):
            try:
                ET.fromstring(archive.read(nom))
            except ET.ParseError as erreur:
                fautes.append("%s : XML mal forme dans %s -- %s" % (fichier.as_posix(), nom, erreur))
    try:
        listees = re.findall(r'<p:sldId [^>]*r:id="([^"]+)"', archive.read("ppt/presentation.xml").decode("utf-8"))
        relations = {r.get("Id"): r.get("Target") for r in ET.fromstring(archive.read("ppt/_rels/presentation.xml.rels")).findall("r:Relationship", REL)}
        for rid in listees:
            cible = relations.get(rid)
            if cible is None or posixpath.normpath(posixpath.join("ppt", cible)) not in noms:
                fautes.append("%s : diapositive listee sans partie -- %s" % (fichier.as_posix(), rid))
    except (KeyError, ET.ParseError) as erreur:
        fautes.append("%s : presentation.xml ou ses relations illisibles -- %s" % (fichier.as_posix(), erreur))

for faute in fautes:
    print("PRESENTATION : " + faute)
print("Presentations : %d fichier(s) ouvert(s), %d defaut(s)." % (len(fichiers), len(fautes)))
sys.exit(1 if fautes else 0)
PY
