#!/bin/sh
# Applique un lot d'enrichissements de code, un module a la fois, derriere la porte
# d'equivalence -- jamais sans elle.
#
# Quoi     : lit le JSONL rendu par le banc, extrait pour chaque tache le fichier complet entre
#            <<<CREER>>> et <<<FIN>>>, le compare au fichier courant par
#            tools/verifier_equivalence.sh, et ne remplace l'original QUE si la logique est
#            identique. Chaque original remplace est d'abord copie en quarantaine, date.
# Pourquoi : l'enrichissement (docstrings, journaux, commentaires) est produit par un modele
#            local qui reecrit des fichiers entiers. Sans porte, une divergence de logique
#            passerait avec l'explication. Avec la porte, elle est nommee et refusee. Et sans
#            copie prealable, un remplacement serait irreversible : regle d'Enzo, rien ne se
#            supprime, tout se deplace avec une trace.
# Ou       : s'execute a la racine du depot.
# Comment  : sh tools/appliquer_enrichissement.sh <sortie.jsonl>
#            Cinq portes : syntaxe, citations, non-appauvrissement, equivalence, quarantaine.
#            Rend 0 si chaque tache a ete appliquee ou refusee proprement, 1 si une extraction
#            a echoue. Le lint et les tests se passent ensuite, sur la vague entiere.
# Piege    : sous Git Bash, `/tmp` n'est pas le meme dossier pour le shell et pour le Python
#            natif de Windows -- Python ecrivait dans D:/tmp, le shell cherchait dans son propre
#            /tmp, et chaque candidat etait refuse comme « Python invalide » sans l'etre
#            (20/09/2026). Le dossier de travail est donc cree par mktemp et converti en chemin
#            Windows par cygpath quand il existe, pour que les deux mondes voient le meme fichier.
set -u

if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
    echo "usage : sh tools/appliquer_enrichissement.sh <sortie.jsonl>" >&2
    exit 2
fi

JSONL="$1"
QUARANTAINE="/d/ReviewPulse_work/quarantaine/$(date +%Y%m%d)"
mkdir -p "${QUARANTAINE}"
JOURNAL="/d/ReviewPulse_work/quarantaine/JOURNAL.md"
code=0
TRAVAIL="$(mktemp -d)"
if command -v cygpath >/dev/null 2>&1; then
    TRAVAIL="$(cygpath -m "${TRAVAIL}")"
fi
PLAN="${TRAVAIL}/enrichissement_plan.txt"

python - "$JSONL" "$TRAVAIL" > "${PLAN}" <<'PY'
import io, json, re, sys, pathlib, tokenize
# Sous Windows, print() termine ses lignes en CRLF et le shell garde le retour chariot colle
# au chemin : on force LF a l'ecriture du plan.
sys.stdout.reconfigure(newline=chr(10), encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
travail = pathlib.Path(sys.argv[2])

# Caracteres typographiques qu'un modele remplace volontiers par leur voisin ASCII : espace fine
# insecable, espace insecable, trait d'union insecable, trait d'union, apostrophes courbes.
TYPOGRAPHIE = {
    chr(0x202F): " ", chr(0xA0): " ", chr(0x2011): "-", chr(0x2010): "-",
    chr(0x2019): "'", chr(0x2018): "'",
}


def _normaliser(texte):
    for fin, ascii_voisin in TYPOGRAPHIE.items():
        texte = texte.replace(fin, ascii_voisin)
    return texte


def _jetons_de_chaine(source):
    genres = {tokenize.STRING}
    if hasattr(tokenize, "FSTRING_MIDDLE"):
        genres.add(tokenize.FSTRING_MIDDLE)
    return [t for t in tokenize.generate_tokens(io.StringIO(source).readline) if t.type in genres]


def reparer_typographie(chemin_original, candidat):
    """Rend au candidat les espaces fines insecables des chaines de l'original.

    Pourquoi : les messages du depot suivent la typographie francaise (espace fine avant « : »).
    Un modele qui recopie un fichier remplace volontiers U+202F par une espace ordinaire ; la
    chaine change, la porte d'equivalence refuse a juste titre, et un module entier est perdu pour
    un caractere (transform.py, 20/09/2026). La reparation est mecanique : une chaine du candidat
    qui ne differe d'une chaine de l'original QUE par ses espaces insecables reprend la forme de
    l'original. Tout autre ecart reste un refus ; la porte d'equivalence juge ensuite.
    """
    try:
        original = pathlib.Path(chemin_original).read_text(encoding="utf-8")
        attendues = {}
        for t in _jetons_de_chaine(original):
            if any(c in t.string for c in TYPOGRAPHIE):
                attendues.setdefault(_normaliser(t.string), t.string)
        if not attendues:
            return candidat, 0
        lignes = candidat.split(chr(10))
        reparations = 0
        for t in reversed(_jetons_de_chaine(candidat)):
            voulu = attendues.get(_normaliser(t.string))
            if voulu is None or voulu == t.string or t.start[0] != t.end[0]:
                continue
            i = t.start[0] - 1
            if lignes[i][t.start[1]:t.end[1]] != t.string:
                continue
            lignes[i] = lignes[i][:t.start[1]] + voulu + lignes[i][t.end[1]:]
            reparations += 1
        return chr(10).join(lignes), reparations
    except (tokenize.TokenError, SyntaxError, IndentationError, OSError):
        return candidat, 0

for ligne in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines():
    # Une ligne vide ou illisible n'arrete pas le lot : le banc ecrit une ligne par tache aboutie,
    # et un fichier filtre peut n'en contenir aucune (21/09/2026).
    try:
        d = json.loads(ligne)
    except json.JSONDecodeError:
        continue
    if not isinstance(d, dict) or not d.get("texte"):
        continue
    nom = d.get("nom", "?")
    joints = d.get("fichiers_joints") or []
    cible = joints[0]["chemin"] if joints else ""
    # Extraction tolerante sur la FORME, jamais sur la preuve : le banc local ferme parfois avec
    # un second <<<CREER>>> ou une cloture de code au lieu de <<<FIN>>> (lakehouse et train, le
    # 20/09/2026). On accepte ces fermetures ; les portes qui suivent -- syntaxe, conservation,
    # equivalence -- jugent le contenu exactement comme avant.
    texte = d["texte"]
    ouverture = texte.find("<<<CREER")
    saut = texte.find(chr(10), ouverture) if ouverture >= 0 else -1
    if saut < 0 or not cible:
        print(chr(9).join(["REFUS", nom, cible, "marqueur d ouverture ou cible absents"]))
        continue
    reste = texte[saut + 1:]
    fermetures = [i for i in (reste.find("<<<FIN"), reste.find("<<<CREER")) if i >= 0]
    corps = reste[:min(fermetures)] if fermetures else reste
    # Un modele qui entoure le fichier d une cloture de code : on la retire, en tete et en queue.
    morceaux = corps.replace(chr(13), "").split(chr(10))
    if morceaux and morceaux[0].startswith("```"):
        morceaux = morceaux[1:]
    while morceaux and morceaux[-1].strip() in ("```", ""):
        morceaux = morceaux[:-1]
    corps = chr(10).join(morceaux)
    # Chemin en barres obliques : un antislash survit mal a un `read` ou a un `printf` de shell.
    tmp = travail / ("enrichi_" + nom + ".py")
    # Ecriture en octets, fins de ligne LF : sous Windows, write_text convertirait en CRLF et
    # git refuserait le fichier (.gitattributes impose eol=lf).
    LF = chr(10)
    corps = corps.replace(chr(13) + LF, LF)
    corps, reparees = reparer_typographie(cible, corps)
    if reparees:
        print("typographie : %d chaine(s) de %s rendue(s) a la forme de l'original" % (reparees, nom), file=sys.stderr)
    tmp.write_bytes((corps + (LF if not corps.endswith(LF) else '')).encode('utf-8'))
    print("CANDIDAT\t%s\t%s\t%s" % (nom, cible, tmp.as_posix()))
PY

while IFS="$(printf '\t')" read -r statut nom cible tmp; do
    case "$statut" in
        REFUS)
            echo "REFUS      ${nom} : ${tmp}"
            code=1
            ;;
        CANDIDAT)
            if [ ! -f "${cible}" ]; then
                echo "REFUS      ${nom} : cible ${cible} introuvable"
                code=1
                continue
            fi
            # Idempotence : rejouer un lot deja applique ne doit ni recopier en quarantaine ni
            # ajouter une ligne au journal.
            if cmp -s "${cible}" "${tmp}"; then
                echo "DEJA       ${nom} : le fichier courant est identique au candidat"
                continue
            fi
            # L'erreur de syntaxe est rendue : un refus muet a coute une heure le 20/09/2026.
            if erreur="$(python -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" "${tmp}" 2>&1)"; then
                :
            else
                echo "REFUS      ${nom} : le rendu n'est pas du Python valide : $(printf '%s' "${erreur}" | tail -n 1)"
                continue
            fi
            # Porte de conservation : un enrichissement n'a pas le droit de faire disparaitre une
            # citation d'ADR, de test ou de registre presente dans l'original. Le 20/09/2026, le banc
            # a reecrit la docstring de transform.py et perdu ses sections « Preuves » et « Tests ».
            if perdu="$(sh tools/citations_perdues.sh "${cible}" "${tmp}")"; then
                :
            else
                echo "REFUS      ${nom} : citations fautives -- ${perdu}"
                continue
            fi
            # Porte de non-appauvrissement : la nouvelle version ne peut pas expliquer moins que
            # celle qu'elle remplace (journaux retires, raisonnement efface, fichier fondu).
            if appauvri="$(sh tools/explication_appauvrie.sh "${cible}" "${tmp}")"; then
                :
            else
                echo "REFUS      ${nom} : explication appauvrie -- ${appauvri}"
                continue
            fi
            if sh tools/verifier_equivalence.sh "${cible}" "${tmp}" > "${TRAVAIL}/eq_${nom}.txt" 2>&1; then
                copie="${QUARANTAINE}/$(echo "${cible}" | tr '/' '_').avant_enrichissement"
                cp "${cible}" "${copie}"
                printf '| %s | `%s` | `%s` | Original avant enrichissement par le banc local ; logique prouvee identique par `verifier_equivalence.sh` | `cp` inverse |\n' \
                    "$(date +%d/%m/%Y)" "$(basename "${copie}")" "${cible}" >> "${JOURNAL}"
                cp "${tmp}" "${cible}"
                echo "APPLIQUE   ${nom} -> ${cible}"
            else
                echo "DIVERGENT  ${nom} : logique changee, NON applique"
                sed -n '2,3p' "${TRAVAIL}/eq_${nom}.txt"
            fi
            ;;
    esac
done < "${PLAN}"
echo "candidats et rapports conserves sous ${TRAVAIL}"
exit "$code"
