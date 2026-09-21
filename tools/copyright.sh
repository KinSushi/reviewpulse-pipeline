#!/bin/sh
# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
# Appose la mention de droit d'auteur sur chaque fichier du depot, ou verifie qu'elle y est.
#
# Quoi     : deux modes. `apposer` ecrit la mention dans chaque fichier suivi qui peut la porter,
#            dans la syntaxe de commentaire de son type ; `verifier` rend 1 et nomme chaque fichier
#            qui ne la porte pas. La mention vit a UN seul endroit : la variable MENTION ci-dessous.
# Pourquoi : demande d'Enzo du 21/09/2026 -- la mention « partout ». Apposee a la main, elle
#            manquerait au premier fichier cree ensuite ; verifiee en integration continue, elle
#            reste vraie. L'apposition est mecanique et n'ajoute que des commentaires : aucune
#            ligne de logique ne bouge, et c'est verifiable (compilation, `ruff`, `sh -n`).
# Ou       : a la racine du depot ; `make copyright` appose, la CI et la campagne verifient.
# Comment  : sh tools/copyright.sh apposer      -- idempotent : un fichier deja marque est saute
#            sh tools/copyright.sh verifier     -- 0 si tout fichier concerne porte la mention
# Ne portent PAS la mention, et pourquoi :
#            - les fichiers JSON : le format n'admet aucun commentaire ;
#            - les images, presentations et journaux : binaires ou produits par une machine ;
#            - `docs/00_sources/` : ce sont les consignes de Jedha, relevees mot pour mot -- la
#              mention d'un autre auteur n'a rien a y faire ;
#            - `tools/standard_agent.txt` : ce texte est transmis tel quel a des modeles.
#            `docs/evidence/` la recoit a l'apposition mais n'est pas verifie : ces rapports sont
#            reecrits par les outils qui les produisent.
set -u

if [ "$#" -ne 1 ] || { [ "$1" != "apposer" ] && [ "$1" != "verifier" ]; }; then
    echo "usage : sh tools/copyright.sh apposer|verifier" >&2
    exit 2
fi

python - "$1" <<'PY'
import pathlib
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MENTION = "Copyright " + chr(169) + " 2026 " + chr(183) + " Auteur " + chr(8212) + " KinSushi " + chr(183) + " Enzo " + chr(183) + " Sovralys LLC"
LF = chr(10)

DIESE = {".py", ".sh", ".yml", ".yaml", ".toml", ".cfg", ".ini"}
NOMS_DIESE = {"Makefile", "Dockerfile", ".env.example", ".gitignore", ".dockerignore", ".gitattributes"}
EXCLUS = ("docs/00_sources/",)
NON_VERIFIES = ("docs/evidence/",)


def style(chemin):
    """Rend la facon d'ecrire la mention dans ce fichier, ou None s'il ne doit pas la porter."""
    nom, suffixe = chemin.name, chemin.suffix.lower()
    posix = chemin.as_posix()
    if any(posix.startswith(e) for e in EXCLUS) or posix == "tools/standard_agent.txt":
        return None
    if suffixe == ".md":
        return "pied"
    if suffixe in DIESE or nom in NOMS_DIESE or nom.startswith("Dockerfile") or suffixe == ".dockerfile":
        return "diese"
    if suffixe == ".txt" and nom.startswith("requirements"):
        return "diese"
    if suffixe == ".sql":
        return "tirets"
    if suffixe == ".js":
        return "barres"
    if suffixe == ".mmd":
        return "mermaid"
    return None


def suivis():
    if shutil.which("git"):
        sortie = subprocess.run(["git", "ls-files", "-z"], capture_output=True).stdout.decode("utf-8", errors="replace")
        return [pathlib.Path(f) for f in sortie.split(chr(0)) if f]
    racines = ["README.md", "Makefile", "docs", "src", "tests", "tools", "dags", "dashboard", "dbt", "docker", ".github"]
    fichiers = []
    for r in racines:
        p = pathlib.Path(r)
        fichiers += [p] if p.is_file() else [q for q in p.rglob("*") if q.is_file()]
    return fichiers


def apposer(chemin, facon):
    texte = chemin.read_bytes().decode("utf-8").replace(chr(13) + LF, LF)
    if facon == "pied":
        nouveau = texte.rstrip(LF) + LF + LF + "---" + LF + LF + "*" + MENTION + "*" + LF
    elif facon == "mermaid":
        nouveau = texte.rstrip(LF) + LF + "%% " + MENTION + LF
    else:
        prefixe = {"diese": "# ", "tirets": "-- ", "barres": "// "}[facon]
        lignes = texte.split(LF)
        # Pourquoi : un shebang, un codage declare ou une directive de Dockerfile doivent rester en
        # premiere ligne, sinon l'interpreteur ne les lit plus.
        rang = 0
        while rang < len(lignes) and (lignes[rang].startswith("#!") or "coding" in lignes[rang][:30]
                                      or lignes[rang].startswith("# syntax=") or lignes[rang].startswith("# escape=")):
            rang += 1
        lignes.insert(rang, prefixe + MENTION)
        nouveau = LF.join(lignes)
    chemin.write_bytes(nouveau.encode("utf-8"))


mode = sys.argv[1]
marques, sautes, manquants = 0, 0, []
for chemin in suivis():
    facon = style(chemin)
    if facon is None or not chemin.exists():
        continue
    try:
        porte = MENTION in chemin.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        continue
    if mode == "apposer":
        if porte:
            sautes += 1
        else:
            apposer(chemin, facon)
            marques += 1
    elif not porte and not any(chemin.as_posix().startswith(n) for n in NON_VERIFIES):
        manquants.append(chemin.as_posix())

if mode == "apposer":
    print("Mention apposee sur %d fichier(s) ; %d la portaient deja." % (marques, sautes))
    sys.exit(0)
for m in manquants:
    print("SANS MENTION : " + m)
print("Droit d'auteur : %d fichier(s) sans la mention." % len(manquants))
sys.exit(1 if manquants else 0)
PY
