#!/bin/sh
# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
# Verifie que la documentation se tient : chaque document numerote est cite par le README,
# et aucun lien relatif ne pointe dans le vide.
#
# Quoi     : deux controles, rendus 1 si l un echoue.
# Pourquoi : le 20/09/2026, six documents ne figuraient pas au README, dont les trois que la
#            consigne du Demo Day exige nommement. Un livrable absent de la porte d entree
#            n existe pas pour qui ouvre le depot.
# Ou       : s execute a la racine du depot.
# Comment  : sh tools/verifier_documentation.sh
set -u

code=0

for f in docs/[0-9][0-9]_*.md; do
    [ -e "$f" ] || continue
    if ! grep -q "$f" README.md; then
        echo "MANQUE AU README : $f"
        code=1
    fi
done

morts=$(python - <<'PY'
import pathlib, re
morts = []
for md in list(pathlib.Path(".").glob("*.md")) + list(pathlib.Path("docs").rglob("*.md")):
    for cible in re.findall(r"]\(([^)#][^)]*)\)", md.read_text(encoding="utf-8")):
        if cible.startswith(("http", "mailto")):
            continue
        c = cible.split("#")[0]
        if not c:
            continue
        if not (md.parent / c).exists() and not pathlib.Path(c).exists():
            morts.append("%s -> %s" % (md, c))
for m in morts:
    print("LIEN MORT :", m)
print("total", len(morts))
PY
)
echo "$morts"
echo "$morts" | grep -q "^total 0$" || code=1

# Aucune signature d outil, nulle part : ni dans un fichier suivi, ni dans un message de commit.
# Regle d Enzo, posee le 19/09/2026 et repetee le 20/09. Les motifs sont assembles a l execution
# pour que ce script ne porte pas lui-meme ce qu il interdit.
signatures=$(python - <<'PY'
import re, subprocess, pathlib
mots = [chr(67)+"laude", chr(65)+"nthropic", chr(67)+"o-"+chr(65)+"uthored-"+chr(66)+"y", chr(71)+"enerated with"]
motif = re.compile("|".join(mots), re.I)
import shutil
touches = []
# Sans git (image de developpement), on parcourt l arbre ; avec git, la liste des suivis.
if shutil.which("git"):
    fichiers = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split()
else:
    racines = ["README.md", "docs", "src", "tests", "tools", "dags", "dashboard", "dbt", "docker", ".github"]
    fichiers = []
    for r in racines:
        p = pathlib.Path(r)
        if p.is_file():
            fichiers.append(str(p))
        elif p.is_dir():
            fichiers += [str(q) for q in p.rglob("*") if q.is_file() and ".git" not in q.parts]
for f in fichiers:
    # Une presentation est une archive : une signature logee dans ses proprietes ou dans une
    # diapositive echapperait a une lecture de texte. On ouvre l archive et on lit ses parties.
    if f.lower().endswith((".pptx", ".docx", ".xlsx")):
        try:
            import zipfile
            z = zipfile.ZipFile(f)
            t = " ".join(z.read(n).decode("utf-8", errors="ignore") for n in z.namelist() if n.endswith((".xml", ".rels")))
        except Exception:
            continue
        if motif.search(t):
            touches.append("FICHIER : " + f)
        continue
    try:
        t = pathlib.Path(f).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if motif.search(t):
        touches.append("FICHIER : " + f)
if shutil.which("git"):
    journal = subprocess.run(["git", "log", "--format=%B"], capture_output=True, text=True, errors="ignore").stdout
    if motif.search(journal):
        touches.append("HISTORIQUE : au moins un message de commit")
else:
    print("(git absent : historique non verifie ici, il l est par la CI)")
for t in touches:
    print("SIGNATURE D OUTIL -", t)
print("total", len(touches))
PY
)
echo "$signatures"
echo "$signatures" | grep -q "^total 0$" || code=1

if [ "$code" -eq 0 ]; then
    echo "Documentation : chaque document numerote est cite, aucun lien mort, aucune signature d outil."
fi
exit "$code"
