#!/usr/bin/env python3
"""
Script autonome de création d'une présentation PowerPoint à partir d'un gabarit.

Il conserve uniquement les diapositives indiquées, met à jour le texte
selon le dictionnaire ``REMPLACEMENTS`` et préserve le thème, les
mises en page et les images (logo Jedha).

Fonctionnalités implémentées avec la bibliothèque standard uniquement :
- zipfile, pathlib, re
- Manipulation XML par expressions régulières (pas de parser complet)

Auteur : souvenir d'entraînement (NON VÉRIFIÉ)
"""

import re
import zipfile
from pathlib import Path
from typing import Dict

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

TEMPLATE_PATH = Path(
    r"C:\Users\dibac\OneDrive\Bureau\Jedha_Exercices\Data_Essentiels\Projet_Final\Template DemoDay Slides - projet Telco.pptx"
)
SORTIE_PATH = Path(
    r"D:\ReviewPulse_work\ReviewPulse\docs\presentation\ReviewPulse_DemoDay.pptx"
)

# Diapositives à conserver (numéros 1‑based) dans l'ordre souhaité
SLIDES_GARDES = [1, 2, 3, 6, 13, 14, 15, 17, 18]

# Remplacements de texte par slide et par indice de run
REMPLACEMENTS: Dict[int, Dict[int, str]] = {
    1: {0: "Bootcamp Data Lead — Demo Day", 1: "ReviewPulse", 2: " : les avis Steam négatifs triés chaque matin"},
    2: {1: "Projet individuel :", 2: "Enzo", 4: "", 6: "", 8: "", 10: "Sommaire",
        12: "Problème métier et décision servie", 14: "Les données réelles", 15: "La chaîne de bout en bout",
        17: "Le modèle et sa preuve", 18: "Démonstration ", 19: "en direct", 21: "Industrialisation et suite"},
    3: {0: "Problématique", 2: "Problème métier",
        3: "Des centaines d'avis chaque jour, lus à la main ou pas du tout.",
        4: "Objectif métier :", 6: "Remonter chaque matin les avis négatifs qui comptent, par jeu et par langue",
        7: "Cible", 8: "Responsable community et live-ops ", 9: "Équipe de développement",
        10: "Besoin", 11: "Repérer une régression avant que la note Steam ne baisse ",
        12: "ex. : part négative prédite par jeu, avis à lire en premier"},
    6: {0: "2.   Les données", 2: "API publique des avis Steam",
        3: "9 054 lignes brutes — 3 jeux, anglais et français",
        4: "Traitement en 5 étapes, testé à chaque passage",
        5: " 1. ", 6: "Zone brute inchangée", 7: "2. Dédoublonnage ", 8: "et nettoyage du BBCode",
        9: "3. Pseudonymisation HMAC", 10: "4. Contrôles bloquants", 11: "5. Great Expectations",
        12: "Confidentialité :", 14: "steamid", 15: " ", 16: "→ pseudonymisé (HMAC salé)",
        17: "personaname, profile_url, avatar : identifiants directs", 18: " → ",
        19: "supprimés dès la zone propre ", 20: "Flux complémentaire", 21: " d'avis négatifs ",
        22: "→ entraînement seulement", 23: "Idempotence : un second passage n'écrit aucun doublon ",
        24: "(manifeste)", 25: "Zone silver Iceberg ", 26: "→ 9 instantanés versionnés ", 27: ""},
    13: {0: "La chaîne de bout en bout", 2: "Six étapes, une seule chaîne",
         3: "Ingestion idempotente depuis l'API Steam", 4: "Zone silver : ", 5: "PySpark et Iceberg",
         6: "Zone gold : ", 7: "dbt et DuckDB, 43 tests verts"},
    14: {0: "4. Le modèle", 2: "4 v", 3: "ariantes mesurées",
         4: "Mots, 1 à 2 grammes : F1 macro 0,735", 5: "Mots, régularisation ajustée : 0,756",
         6: "Caractères, 2 à 5 grammes ", 7: "(0,759 puis 0,797) ", 8: "→ retenu",
         9: "Pourquoi les n-grammes de caractères ?", 10: "Robustes aux fautes et aux variantes d'écriture",
         11: "Entraînement en quelques secondes, explicable terme par terme",
         12: "Seuil de décision appris, et non fixé à 0,5", 13: ""},
    15: {0: "5. Résultats mesurés ", 2: "Modèle retenu : ",
         3: "TF-IDF sur caractères et régression logistique, ", 4: "class_weight='balanced'",
         5: "Seuil appris par validation croisée : ", 6: "0,75",
         7: " — barrière de promotion F1 macro ≥ 0,75.",
         8: "Sur un test 100 % naturel tenu à l'écart :",
         9: "F1 macro : ", 10: "0,797", 11: " (0,807 le 16/09, sur un jeu plus petit)",
         12: "AUC : ", 13: "0,931", 14: " ; rappel des négatifs 0,634",
         15: "Tests : ", 16: "73 verts", 17: " ; 16 mutations sur 16 détectées",
         18: "Deux entraînements successifs donnent ", 19: "le même F1", 20: " à la seizième décimale.",
         21: "Un modèle à métriques égales n'est pas promu : la barrière l'a refusé en conditions réelles.",
         22: "R", 23: "ésultats et p", 24: "reuves "},
    17: {0: "6. Industrialisation et suite", 2: "Ce qui tourne sans intervention",
         3: "DAG Airflow quotidien : 6 tâches sur 6, base PostgreSQL",
         4: "Test de la stack déployée : 14 contrôles sur 14",
         5: "Dérive des données et des prédictions mesurée à chaque passage",
         6: "Retour arrière outillé : l'alias champion revient sur une version antérieure",
         7: "Prochaines étapes", 8: "Alerte hors journal et réentraînement déclenché par la dérive",
         9: "Restauration d'un instantané Iceberg, images épinglées par empreinte",
         10: "Kafka pour le temps réel, stockage objet compatible S3",
         11: "Publication du dépôt et chaîne d'intégration verte",
         12: "Ce que le projet sert au-delà", 13: "Socle réemployable pour les blocs AIA et CDSD"},
    18: {0: "Questions ?"},
}

# --------------------------------------------------------------------------- #
# Fonctions utilitaires
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

def reconstruire_sldid_lst(rids_ordonnes: list, entries: Dict[str, str]) -> str:
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
# Corps principal
# --------------------------------------------------------------------------- #

def main() -> None:
    """Construit la présentation filtrée et affiche les informations."""
    # Création du répertoire de sortie si nécessaire
    SORTIE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Ouverture du gabarit en lecture
    with zipfile.ZipFile(TEMPLATE_PATH, "r") as zin:
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
        rids_gardes = [slide_to_rid[n] for n in SLIDES_GARDES if n in slide_to_rid]
        nouveau_sldid_lst = reconstruire_sldid_lst(rids_gardes, sldid_entries)
        pres_data_mod = re.sub(
            r'(<p:sldIdLst[^>]*>).*?(</p:sldIdLst>)',
            nouveau_sldid_lst,
            pres_data,
            flags=re.DOTALL,
        )

        # 3. Nettoyage du fichier de relations
        rels_data_mod = filtrer_relations(rels_data, set(SLIDES_GARDES))

        # 4. Nettoyage du fichier [Content_Types].xml
        ct_path = "[Content_Types].xml"
        ct_data = zin.read(ct_path).decode("utf-8")
        ct_data_mod = filtrer_content_types(ct_data, set(SLIDES_GARDES))

        # 5. Préparer le contenu des slides conservées (remplacement du texte)
        slides_mod: Dict[str, bytes] = {}
        for num in SLIDES_GARDES:
            slide_path = f"ppt/slides/slide{num}.xml"
            if slide_path not in zin.namelist():
                continue  # sécurité
            xml_raw = zin.read(slide_path).decode("utf-8")
            remap = REMPLACEMENTS.get(num, {})
            xml_new = remplacer_runs(xml_raw, remap)
            slides_mod[slide_path] = xml_new.encode("utf-8")

        # 6. Création du nouveau fichier .pptx
        with zipfile.ZipFile(SORTIE_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                name = item.filename

                # Sauter les slides non conservées
                if re.fullmatch(r'ppt/slides/slide(\d+)\.xml', name):
                    num = int(re.search(r'(\d+)', name).group(1))
                    if num not in SLIDES_GARDES:
                        continue
                    # Écrire la version modifiée
                    zout.writestr(name, slides_mod[name])
                    continue

                # Sauter les relations des slides non conservées
                if re.fullmatch(r'ppt/slides/_rels/slide(\d+)\.xml\.rels', name):
                    num = int(re.search(r'(\d+)', name).group(1))
                    if num not in SLIDES_GARDES:
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
    taille_kb = SORTIE_PATH.stat().st_size // 1024
    print(f"Fichier créé : {SORTIE_PATH}")
    print(f"Taille : {taille_kb} ko")
    print(f"Nombre de diapositives : {len(SLIDES_GARDES)}")

if __name__ == "__main__":
    main()
