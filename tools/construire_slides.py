#!/usr/bin/env python3
"""
Script autonome de création d'une présentation PowerPoint à partir d'un gabarit,
défini par un fichier de spécification JSON.

Le fichier de spécification décrit :
- le chemin du gabarit (« gabarit »)
- le chemin de sortie (« sortie »)
- la liste des diapositives à conserver (« slides_gardees »)
- les remplacements de texte par diapositive et indice de run (« remplacements »)

Le script lit la spécification, filtre les diapositives, applique les
remplacements et reconstruit le fichier .pptx en conservant le thème,
les mises en page et les images. Aucun parsing XML complet n'est utilisé,
seules les expressions régulières de la bibliothèque standard.
"""

import argparse
import json
import logging
import re
import sys
import zipfile
from pathlib import Path
from typing import Dict, List

# --------------------------------------------------------------------------- #
# Fonctions utilitaires (inchangées)
# --------------------------------------------------------------------------- #

def echappe_xml(texte: str) -> str:
    """Échappe les caractères réservés dans XML."""
    return (
        texte.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

def remplacer_runs(xml: str, remplacements: Dict[int, str]) -> str:
    """
    Remplace le texte des balises <a:t> selon le dictionnaire ``remplacements``.
    ``remplacements`` : {indice_du_run : nouveau_texte}
    """
    def repl(match):
        nonlocal index
        opening, contenu, closing = match.groups()
        if index in remplacements:
            nouveau = remplacements[index]
            # échappement
            nouveau_escaped = echappe_xml(nouveau)
            # ajout de xml:space si besoin
            if nouveau.startswith(" ") or nouveau.endswith(" "):
                if "xml:space" not in opening:
                    opening = opening.rstrip(">") + ' xml:space="preserve">'
            result = f"{opening}{nouveau_escaped}{closing}"
        else:
            result = match.group(0)
        index += 1
        return result

    index = 0
    pattern = re.compile(r'(<a:t[^>]*>)(.*?)(</a:t>)', re.DOTALL)
    return pattern.sub(repl, xml)

def extraire_sldid_entries(presentation_xml: str) -> Dict[str, str]:
    """
    Retourne un dictionnaire rId -> balise <p:sldId .../> extraite de
    <p:sldIdLst>.
    """
    lst_match = re.search(r'(<p:sldIdLst[^>]*>)(.*?)(</p:sldIdLst>)', presentation_xml, re.DOTALL)
    if not lst_match:
        return {}
    contenu = lst_match.group(2)
    entries = {}
    for m in re.finditer(r'(<p:sldId[^>]*r:id="([^"]+)"[^>]*/>)', contenu):
        full_tag, rid = m.groups()
        entries[rid] = full_tag
    return entries

def reconstruire_sldid_lst(rids_ordonnes: List[str], entries: Dict[str, str]) -> str:
    """
    Construit le texte complet de <p:sldIdLst> contenant uniquement les
    rId fournis, dans l'ordre indiqué.
    """
    lignes = [entries[rid] for rid in rids_ordonnes if rid in entries]
    inner = "\n".join(lignes)
    return f"<p:sldIdLst>{inner}</p:sldIdLst>"

def filtrer_relations(rels_xml: str, slides_gardes: set) -> str:
    """
    Supprime les <Relationship ... Target="slides/slideX.xml"/> dont X n'est
    pas dans ``slides_gardes``.
    """
    def keep(match):
        target = match.group(2)
        m = re.search(r'slides/slide(\d+)\.xml', target)
        if m and int(m.group(1)) not in slides_gardes:
            return ""  # suppression
        return match.group(0)

    pattern = re.compile(r'(<Relationship[^>]*Target="([^"]+)"[^>]*/>)')
    return pattern.sub(keep, rels_xml)

def filtrer_content_types(ct_xml: str, slides_gardes: set) -> str:
    """
    Supprime les <Override PartName="/ppt/slides/slideX.xml".../> dont X n'est
    pas conservé.
    """
    def keep(match):
        part = match.group(1)
        m = re.search(r'/ppt/slides/slide(\d+)\.xml', part)
        if m and int(m.group(1)) not in slides_gardes:
            return ""  # suppression
        return match.group(0)

    pattern = re.compile(r'(<Override[^>]*PartName="([^"]+)"[^>]*/>)')
    return pattern.sub(keep, ct_xml)

# --------------------------------------------------------------------------- #
# Chargement de la spécification
# --------------------------------------------------------------------------- #

def charger_specification(chemin: Path) -> dict:
    """
    Charge le fichier JSON de spécification et renvoie un dictionnaire normalisé.

    Le JSON doit contenir les clés suivantes (obligatoires) :
        - "gabarit" : chemin du fichier .pptx source
        - "sortie"  : chemin du fichier .pptx à créer
        - "slides_gardees" : liste de numéros de diapositives (1‑based)
        - "remplacements" : dictionnaire de remplacements
          { "num_slide": { "indice_run": "texte" } }

    Les clés numériques du JSON sont des chaînes ; elles sont converties en int.
    Lève ``ValueError`` avec un message explicite en français si :
        * une clé obligatoire manque,
        * la liste ``slides_gardees`` est vide,
        * un numéro de diapositive présent dans ``remplacements`` n'est pas
          dans ``slides_gardees``.
    """
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"Impossible de lire le fichier de spécification : {e}")

    # Vérification des clés obligatoires
    for key in ("gabarit", "sortie", "slides_gardees", "remplacements"):
        if key not in data:
            raise ValueError(f"Clé obligatoire manquante dans la spécification : « {key} »")

    # Normalisation des chemins
    data["gabarit"] = Path(data["gabarit"])
    data["sortie"] = Path(data["sortie"])

    # Normalisation des listes et dictionnaires numériques
    slides_gardees = data["slides_gardees"]
    if not isinstance(slides_gardees, list) or not slides_gardees:
        raise ValueError("« slides_gardees » doit être une liste non vide de numéros de diapositives.")
    data["slides_gardees"] = [int(s) for s in slides_gardees]

    # Remplacements : conversion des clés de chaîne en int
    remplacements_raw = data["remplacements"]
    remplacements: Dict[int, Dict[int, str]] = {}
    for slide_str, inner in remplacements_raw.items():
        try:
            slide_num = int(slide_str)
        except ValueError:
            raise ValueError(f"Clé de diapositive non numérique dans « remplacements » : {slide_str}")
        if not isinstance(inner, dict):
            raise ValueError(f"Valeur attendue comme dictionnaire pour la diapositive {slide_str}")
        inner_dict: Dict[int, str] = {}
        for run_str, texte in inner.items():
            try:
                run_idx = int(run_str)
            except ValueError:
                raise ValueError(f"Clé d'indice de run non numérique dans la diapositive {slide_str} : {run_str}")
            inner_dict[run_idx] = texte
        remplacements[slide_num] = inner_dict
    data["remplacements"] = remplacements

    # Vérification de cohérence entre remplacements et slides_gardees
    slides_set = set(data["slides_gardees"])
    for slide_num in remplacements.keys():
        if slide_num not in slides_set:
            raise ValueError(
                f"Diapositive {slide_num} présente dans « remplacements » mais absente de « slides_gardees »."
            )

    return data

# --------------------------------------------------------------------------- #
# Construction de la présentation à partir d'une spécification
# --------------------------------------------------------------------------- #

def construire(spec: dict) -> Path:
    """
    Construit la présentation selon la spécification fournie.

    Retourne le chemin du fichier .pptx créé.
    """
    template_path: Path = spec["gabarit"]
    sortie_path: Path = spec["sortie"]
    slides_gardees: List[int] = spec["slides_gardees"]
    remplacements: Dict[int, Dict[int, str]] = spec["remplacements"]

    # Création du répertoire de sortie si nécessaire
    sortie_path.parent.mkdir(parents=True, exist_ok=True)

    # Ouverture du gabarit en lecture
    with zipfile.ZipFile(template_path, "r") as zin:
        # 1. Lecture du fichier de relations et construction du mapping slide → rId
        rels_path = "ppt/_rels/presentation.xml.rels"
        rels_data = zin.read(rels_path).decode("utf-8")
        slide_to_rid: Dict[int, str] = {}
        for m in re.finditer(r'<Relationship[^>]*Id="([^"]+)"[^>]*Target="slides/slide(\d+)\.xml"', rels_data):
            rid, num = m.groups()
            slide_to_rid[int(num)] = rid

        # 2. Réécriture de <p:sldIdLst> dans presentation.xml
        pres_path = "ppt/presentation.xml"
        pres_data = zin.read(pres_path).decode("utf-8")
        sldid_entries = extraire_sldid_entries(pres_data)
        rids_gardes = [slide_to_rid[n] for n in slides_gardees if n in slide_to_rid]
        nouveau_sldid_lst = reconstruire_sldid_lst(rids_gardes, sldid_entries)
        pres_data_mod = re.sub(
            r'(<p:sldIdLst[^>]*>).*?(</p:sldIdLst>)',
            nouveau_sldid_lst,
            pres_data,
            flags=re.DOTALL,
        )

        # 3. Nettoyage du fichier de relations
        rels_data_mod = filtrer_relations(rels_data, set(slides_gardees))

        # 4. Nettoyage du fichier [Content_Types].xml
        ct_path = "[Content_Types].xml"
        ct_data = zin.read(ct_path).decode("utf-8")
        ct_data_mod = filtrer_content_types(ct_data, set(slides_gardees))

        # 5. Vérification des indices de run et préparation du contenu des slides conservées
        slides_mod: Dict[str, bytes] = {}
        run_pattern = re.compile(r'(<a:t[^>]*>)(.*?)(</a:t>)', re.DOTALL)
        for num in slides_gardees:
            slide_path = f"ppt/slides/slide{num}.xml"
            if slide_path not in zin.namelist():
                continue  # sécurité
            xml_raw = zin.read(slide_path).decode("utf-8")
            # Comptage des runs dans le slide
            runs = run_pattern.findall(xml_raw)
            nb_runs = len(runs)

            remap = remplacements.get(num, {})
            # Vérification des indices
            for idx in remap.keys():
                if idx >= nb_runs:
                    raise ValueError(
                        f"Diapositive {num} : indice de run {idx} hors limites (nombre de runs disponible : {nb_runs})"
                    )
            # Journalisation
            logging.info(
                f"Diapositive {num} : {nb_runs} runs, {len(remap)} remplacements appliqués"
            )

            # Remplacement effectif
            xml_new = remplacer_runs(xml_raw, remap)
            slides_mod[slide_path] = xml_new.encode("utf-8")

        # 6. Création du nouveau fichier .pptx
        with zipfile.ZipFile(sortie_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                name = item.filename

                # Sauter les slides non conservées
                if re.fullmatch(r'ppt/slides/slide(\d+)\.xml', name):
                    num = int(re.search(r'(\d+)', name).group(1))
                    if num not in slides_gardees:
                        continue
                    # Écrire la version modifiée
                    zout.writestr(name, slides_mod[name])
                    continue

                # Sauter les relations des slides non conservées
                if re.fullmatch(r'ppt/slides/_rels/slide(\d+)\.xml\.rels', name):
                    num = int(re.search(r'(\d+)', name).group(1))
                    if num not in slides_gardees:
                        continue
                    # copier tel quel
                    zout.writestr(name, zin.read(name))
                    continue

                # Remplacer les fichiers modifiés
                if name == pres_path:
                    zout.writestr(name, pres_data_mod.encode("utf-8"))
                elif name == rels_path:
                    zout.writestr(name, rels_data_mod.encode("utf-8"))
                elif name == ct_path:
                    zout.writestr(name, ct_data_mod.encode("utf-8"))
                else:
                    # Copie directe pour tout le reste
                    zout.writestr(name, zin.read(name))

    # Affichage des informations demandées
    taille_kb = sortie_path.stat().st_size // 1024
    print(f"Fichier créé : {sortie_path}")
    print(f"Taille : {taille_kb} ko")
    print(f"Nombre de diapositives : {len(slides_gardees)}")

    return sortie_path

# --------------------------------------------------------------------------- #
# Interface en ligne de commande
# --------------------------------------------------------------------------- #

def main() -> int:
    """
    Interface en ligne de commande.

    Usage :
        python tools/construire_slides.py --spec <chemin_spec.json>

    Retourne 0 en cas de succès, 1 en cas d'erreur (fichier introuvable,
    spécification invalide, etc.).
    """
    parser = argparse.ArgumentParser(
        description="Construire une présentation PowerPoint à partir d'un gabarit et d'une spécification JSON."
    )
    parser.add_argument(
        "--spec",
        type=Path,
        help="Chemin vers le fichier de spécification JSON.",
        required=False,
    )
    args = parser.parse_args()

    if not args.spec:
        parser.print_help()
        return 1

    logging.basicConfig(level=logging.ERROR, format="%(levelname)s : %(message)s")

    try:
        spec = charger_specification(args.spec)
        construire(spec)
    except ValueError as ve:
        logging.error(str(ve))
        return 1
    except FileNotFoundError as fnfe:
        logging.error(str(fnfe))
        return 1
    except Exception as e:
        logging.error(f"Erreur inattendue : {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
