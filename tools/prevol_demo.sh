#!/bin/sh
# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
# Contrôle avant vol de la démonstration : la pile est-elle PRÊTE, à chaud, et cohérente ?
#
# Quoi     : interroge la pile qui tourne comme la démonstration va le faire, dans l'ordre du
#            discours, et rend un verdict PRÊT ou PAS PRÊT en nommant ce qui manque :
#            1. les quatre services répondent (API, tableau de bord, MLflow, Airflow) ;
#            2. l'API est RÉCHAUFFÉE : le premier appel après un démarrage charge le modèle ;
#            3. la phrase tapée à la main pendant la démonstration est classée négative, en
#               moins de 100 ms une fois à chaud, et l'explication rend des termes ;
#            4. les scores servis ont été calculés par le champion EN SERVICE ;
#            5. le planificateur d'Airflow ET son interface sont vivants.
# Pourquoi : chaque contrôle porte le nom d'un défaut réellement rencontré. Le 21/09/2026 : le
#            premier appel à `/health` après un redémarrage a pris 190 s, le premier `/predict`
#            9,7 s, puis 6 ms à chaud -- une démonstration ouverte sur une pile froide commence
#            par trois minutes de silence. Le tableau de bord affichait la version 2 du modèle
#            alors que le champion était la 5 : les scores dataient d'avant la promotion. Le
#            serveur web d'Airflow était mort depuis la veille, planificateur vivant. Aucun test
#            ne voyait ces trois défauts ; ce sont des captures et une lecture d'écran qui les
#            ont trouvés. Ce script les cherche avant que le jury ne le fasse.
# Où       : sur la machine de la démonstration, pile levée (`make up`, `make airflow`).
# Comment  : sh tools/prevol_demo.sh          -- à lancer QUINZE MINUTES avant de passer.
#            Rend 0 et « PRÊT » si tout est conforme, 1 et la liste des manques sinon. Les
#            adresses se changent par REVIEWPULSE_PREVOL_API, _TABLEAU, _MLFLOW, _AIRFLOW.
set -u

python - <<'PY'
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = os.getenv("REVIEWPULSE_PREVOL_API", "http://localhost:8000")
TABLEAU = os.getenv("REVIEWPULSE_PREVOL_TABLEAU", "http://localhost:8501")
MLFLOW = os.getenv("REVIEWPULSE_PREVOL_MLFLOW", "http://localhost:5000")
AIRFLOW = os.getenv("REVIEWPULSE_PREVOL_AIRFLOW", "http://localhost:8080")
# La phrase du discours, mot pour mot : c'est elle que le jury verra taper.
PHRASE = "injouable, plein de bugs, remboursez-moi"
SEUIL_CHAUD_S = 0.100

manques = []


def appel(url, corps=None, delai=30):
    """Rend (code, json_ou_None, duree_s). Pourquoi : une seule façon d'appeler, chronométrée."""
    donnees = json.dumps(corps).encode("utf-8") if corps is not None else None
    requete = urllib.request.Request(url, data=donnees, headers={"Content-Type": "application/json"})
    debut = time.perf_counter()
    try:
        with urllib.request.urlopen(requete, timeout=delai) as reponse:
            brut = reponse.read()
            code = reponse.status
    except urllib.error.HTTPError as erreur:
        return erreur.code, None, time.perf_counter() - debut
    except Exception:
        return 0, None, time.perf_counter() - debut
    duree = time.perf_counter() - debut
    try:
        return code, json.loads(brut.decode("utf-8")), duree
    except ValueError:
        return code, None, duree


def ligne(ok, texte):
    print(("  ok      " if ok else "  MANQUE  ") + texte)
    if not ok:
        manques.append(texte)


print("1. Les services répondent")
# Pourquoi 300 s : le premier /health charge le champion depuis MLflow ; mesuré à 190 s sur disque lent.
code, sante, duree = appel(API + "/health", delai=300)
ligne(code == 200, "API /health : code %s en %.1f s" % (code, duree))
version = str((sante or {}).get("model_version", ""))
seuil = (sante or {}).get("decision_threshold")
for nom, url in (("tableau de bord", TABLEAU + "/_stcore/health"), ("MLflow", MLFLOW + "/health")):
    code, _, duree = appel(url, delai=30)
    ligne(code == 200, "%s : code %s en %.1f s" % (nom, code, duree))

print("2. L'API est réchauffée")
appel(API + "/predict", {"texts": [PHRASE]}, delai=120)
appel(API + "/explain", {"text": PHRASE}, delai=120)
code, prediction, duree = appel(API + "/predict", {"texts": [PHRASE]}, delai=30)
ligne(code == 200 and duree < SEUIL_CHAUD_S, "/predict à chaud : %.0f ms (attendu < %.0f ms)" % (duree * 1000, SEUIL_CHAUD_S * 1000))

print("3. La phrase de la démonstration")
etiquette = ((prediction or {}).get("predictions") or [{}])[0].get("label")
proba = ((prediction or {}).get("predictions") or [{}])[0].get("proba_negative")
ligne(etiquette == "negative", "« %s » -> %s (probabilité négative %s)" % (PHRASE, etiquette, None if proba is None else round(proba, 3)))
code, explication, duree = appel(API + "/explain", {"text": PHRASE}, delai=60)
termes = (explication or {}).get("terms") or []
ligne(code == 200 and len(termes) >= 5, "/explain : %d termes en %.0f ms" % (len(termes), duree * 1000))

print("4. Les scores servis viennent du champion en service")
ligne(bool(version), "champion en service : version %s, seuil %s" % (version or "?", seuil))
code, schema, _ = appel(API + "/openapi.json", delai=30)
code, resume, _ = appel(API + "/insights?app_id=1086940", delai=60)
versions_servies = sorted({str(r.get("model_version")) for r in (resume or []) if isinstance(r, dict)})
ligne(code == 200 and versions_servies == [version], "résumé quotidien : versions %s (attendu [%s])" % (versions_servies, version))

print("5. Airflow : planificateur ET interface")
code, etat, duree = appel(AIRFLOW + "/health", delai=60)
ligne(code == 200, "interface d'Airflow : code %s en %.1f s" % (code, duree))
for composant in ("metadatabase", "scheduler"):
    statut = ((etat or {}).get(composant) or {}).get("status")
    ligne(statut == "healthy", "Airflow %s : %s" % (composant, statut))

print()
if manques:
    print("PAS PRÊT -- %d manque(s) :" % len(manques))
    for m in manques:
        print("  - " + m)
    sys.exit(1)
print("PRÊT -- la pile est levée, réchauffée et cohérente. Ne redémarre plus rien avant de passer.")
sys.exit(0)
PY
