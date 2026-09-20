#!/bin/sh
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

if [ "$code" -eq 0 ]; then
    echo "Documentation : chaque document numerote est cite, aucun lien mort."
fi
exit "$code"
