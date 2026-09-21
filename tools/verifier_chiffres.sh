#!/bin/sh
# Refuse qu'un document tourne vers le jury contredise le depot, ou annonce comme restant un
# travail fait.
#
# Quoi     : compte dans le depot ce qui se compte -- les mutations de `tests/reverse/mutations.json`,
#            les decisions de `docs/adr/` -- puis relit les documents que le jury ouvrira. Deux refus :
#            - CHIFFRE : le document ecrit « N mutations », « N ADR » ou « N decisions » avec un N
#                        qui n'est pas celui du depot ;
#            - OUVERT  : le document porte une case non cochee ou un etat « a faire ».
# Pourquoi : le 21/09/2026, Enzo a lu le depot sur GitHub et l'a juge « tres insuffisant ». Le
#            README annoncait 26 mutations quand le depot en comptait 27, et « douze decisions »
#            quand il y en avait 29 ; la grille de conformite du 16/09 laissait ouvertes des cases
#            pour du travail fait depuis des jours. Aucun test ne lisait ces pages. Un document
#            perime fait paraitre inacheve un projet qui ne l'est pas -- et personne ne le voit de
#            l'interieur.
# Temoin   : rejoue sur le README du commit 9f0aabd (20/09/2026), le controle rend 1 et nomme
#            « 26 mutations » et « Douze decisions d'architecture » ; sur la grille de conformite du
#            meme commit, sept lignes OUVERT. Sur l'arbre courant : 18 documents relus, 0 contradiction.
# Ou       : a la racine du depot ; appele par la campagne de preuves, par la CI et `make chiffres`.
# Comment  : sh tools/verifier_chiffres.sh
#            Rend 0 si aucun document ne contredit le depot, 1 sinon, en nommant fichier, ligne et
#            motif. Les documents d'HISTOIRE (journal de bord, points de reprise, registre, backlog,
#            sources, preuves datees) ne sont pas relus : un ancien total y est un fait date.
set -u

python - <<'PY'
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Documents que le jury ouvrira : ils decrivent l'etat present, jamais l'histoire.
FACADE = [
    "README.md",
    "docs/01_charte.md", "docs/02_architecture.md", "docs/05_conformite_demo_day.md",
    "docs/06_carte_des_modules.md", "docs/07_questions_jury.md", "docs/12_model_card.md",
    "docs/13_note_orientation.md", "docs/14_plan_monitoring.md", "docs/15_reversibilite.md",
    "docs/17_gouvernance.md", "docs/20_rapport_donnees.md", "docs/21_guide_api.md",
    "docs/22_runbook_deploiement.md", "docs/23_standard_agents.md",
    "docs/presentation/discours_demo_day.md", "docs/presentation/script_10_minutes.md",
    "docs/presentation/demo_day.json",
]

mutations = len(json.loads(pathlib.Path("tests/reverse/mutations.json").read_text(encoding="utf-8")))
decisions = len([p for p in pathlib.Path("docs/adr").glob("[0-9][0-9][0-9][0-9]-*.md")])

EN_LETTRES = {
    "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15, "seize": 16, "vingt": 20,
    "vingt-quatre": 24, "vingt-six": 26, "vingt-sept": 27, "vingt-huit": 28, "vingt-neuf": 29,
    "trente": 30,
}
NOMBRE = r"([0-9]+|" + "|".join(sorted(EN_LETTRES, key=len, reverse=True)) + r")"
# « 27 mutations », « vingt-sept mutations sur vingt-sept » ; « 29 ADR », « vingt-neuf decisions ».
MOTIF_MUTATIONS = re.compile(NOMBRE + r" (?:tests inverses|mutations)", re.IGNORECASE)
MOTIF_DECISIONS = re.compile(NOMBRE + r" (?:ADR|d[ée]cisions (?:d'architecture|sont [ée]crites|[ée]crites))", re.IGNORECASE)
MOTIF_OUVERT = re.compile(r"^\s*- \[ \]|⬜|🟡")
# Une phrase qui raconte un etat passe cite legitimement un ancien total.
HISTOIRE = re.compile(r"[0-9]{2}/[0-9]{2}(?:/[0-9]{4})?|la veille|avant |hier|à l'époque", re.IGNORECASE)


def valeur(texte):
    texte = texte.lower()
    return int(texte) if texte.isdigit() else EN_LETTRES[texte]


fautes = []
for nom in FACADE:
    chemin = pathlib.Path(nom)
    if not chemin.exists():
        continue
    for numero, ligne in enumerate(chemin.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if MOTIF_OUVERT.search(ligne) and "Légende" not in ligne and "États" not in ligne:
            fautes.append("%s:%d OUVERT : une case ou un etat « a faire » dans un document tourne vers le jury" % (nom, numero))
        for motif, attendu, quoi in ((MOTIF_MUTATIONS, mutations, "mutations"), (MOTIF_DECISIONS, decisions, "decisions d'architecture")):
            for trouve in motif.finditer(ligne):
                n = valeur(trouve.group(1))
                # Un total plus petit que celui du depot, dans une phrase datee, est de l'histoire.
                if n != attendu and not (n < attendu and HISTOIRE.search(ligne)):
                    fautes.append("%s:%d CHIFFRE : « %s » alors que le depot compte %d %s" % (nom, numero, trouve.group(0), attendu, quoi))

for faute in fautes:
    print(faute)
print("Chiffres : %d mutations et %d decisions dans le depot ; %d document(s) relu(s), %d contradiction(s)."
      % (mutations, decisions, sum(1 for n in FACADE if pathlib.Path(n).exists()), len(fautes)))
sys.exit(1 if fautes else 0)
PY
