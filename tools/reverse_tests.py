"""tools/reverse_tests.py
Où : module exécutable placé sous le répertoire ``tools`` du projet ReviewPulse.
Quoi : exécute la batterie de « mutations » décrites dans
``tests/reverse/mutations.json`` afin de vérifier que les tests
détectent les défauts volontairement injectés.
Comment :
- pour chaque mutation, copie les sources (``src/``, ``tests/``, ``dashboard/``,
  ``dags/``) et le fichier ``pyproject.toml`` dans un répertoire temporaire,
- s'assure que la chaîne ``avant`` apparaît exactement une fois dans le
  fichier ciblé, sinon la mutation est marquée ``OBSOLETE``,
- remplace cette occurrence par ``apres``,
- lance ``pytest`` dans la copie avec un environnement contrôlé
  (``PYTHONPATH`` pointant vers ``src`` et ``REVIEWPULSE_SALT`` fixé à
  ``reverse-salt``),
- interprète le code retour : ``non-zero`` -> ``TUEE`` (les tests ont
  détecté la mutation), ``zero`` -> ``SURVIVANTE``,
- relève le premier test qui échoue (ou « ERREUR DE COLLECTE »),
- conserve la dernière ligne de sortie de ``pytest`` comme résumé.
Pourquoi : ce script constitue le test de robustesse du jeu de tests
en s'assurant qu'une mutation introduite volontairement entraîne l'échec
des tests. Le rapport Markdown généré sert de preuve d'effet.

Le module expose ``main() -> int`` et se lance via
``if __name__ == "__main__": raise SystemExit(main())``.

Choix de conception :
- Copie du projet dans un répertoire temporaire : retenu, car chaque mutation
  modifie isolément une copie sans toucher aux sources. Alternative écartée :
  appliquer les mutations en place puis les annuler, car un échec intermédiaire
  laisserait le dépôt dans un état inconnu.
- ``REVIEWPULSE_SALT`` fixé à ``reverse-salt`` : retenu, pour rendre les tests
  reproductibles indépendamment du sel de l'environnement. Alternative écartée :
  utiliser le sel local, car il pourrait ne pas être défini dans CI.
- ``pytest -x`` : retenu, pour arrêter à la première défaillance et identifier
  le test détecteur. Alternative écartée : laisser pytest poursuivre, car le
  rapport ne retient qu'un seul test par mutation.
- Code de sortie : ``0`` si toutes les mutations sont tuées, ``1`` si au moins
  une survit ou est obsolète, ``2`` si le témoin échoue. Cela distingue un
  jeu de tests insuffisant d'une exécution invalide.

Limites connues :
- Le script ne vérifie pas que ``mutations.json`` couvre l'ensemble des
  décisions critiques ; il valide seulement que les mutations listées sont
  détectées.
- Une mutation obsolète n'indique pas forcément que le défaut simulé a
  disparu du code, seulement que la chaîne ``avant`` n'est plus présente.
- Le délai global n'est pas borné : chaque mutation dispose de son propre
  ``timeout``, mais la somme des délais peut dépasser l'horizon attendu.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

log = logging.getLogger(__name__)

Mutation = Dict[str, Any]
Result = Tuple[str, str]  # (statut, résumé pytest)


def _repo_root() -> Path:
    """Retourne le répertoire racine du dépôt (parent du répertoire ``tools``).

    Pourquoi : l'arborescence des sources est relative à la racine du dépôt,
    que le script soit lancé depuis ``tools`` ou depuis la racine.
    """
    return Path(__file__).resolve().parents[1]


def _load_mutations(path: Path) -> List[Mutation]:
    """Charge la liste des mutations depuis le fichier JSON indiqué.

    Pourquoi : centraliser le chargement permet de valider une fois pour toutes
    que le fichier contient bien une liste JSON.

    Args:
        path: chemin absolu vers ``tests/reverse/mutations.json``.

    Returns:
        liste des mutations brutes.

    Raises:
        ValueError: si le fichier JSON ne contient pas une liste.
    """
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Le fichier {path} ne contient pas une liste JSON.")
    return data  # type: ignore[return-value]


def _copy_project(temp_dir: Path) -> None:
    """Copie ``src/``, ``tests/``, ``dashboard/``, ``dags/``, ``dbt/`` et ``pyproject.toml``.

    Pourquoi : chaque mutation s'exécute dans un environnement isolé, sans
    modifier le dépôt source.

    Args:
        temp_dir: répertoire temporaire qui accueillera la copie.
    """
    root = _repo_root()
    for name in ("src", "tests", "dashboard", "dags", "dbt"):
        src = root / name
        if src.is_dir():
            dst = temp_dir / name
            shutil.copytree(src, dst, dirs_exist_ok=True)
    # pyproject.toml est à la racine du dépôt
    shutil.copy2(root / "pyproject.toml", temp_dir / "pyproject.toml")


def _apply_mutation(
    temp_dir: Path, mutation: Mutation
) -> Tuple[str, Path | None]:
    """
    Applique la mutation dans la copie du projet.

    Retourne un tuple ``(statut, chemin_fichier)`` où ``statut`` vaut
    ``"OBSOLETE"`` si la chaîne ``avant`` n'est pas trouvée exactement
    une fois, sinon ``"OK"``. ``chemin_fichier`` est le chemin absolu du
    fichier modifié (ou ``None`` en cas d'``OBSOLETE``).

    Pourquoi : une mutation n'a de sens que si la chaîne cible existe une
    seule fois ; sinon le résultat serait ambigu ou la mutation obsolète.

    Args:
        temp_dir: copie du projet où appliquer la mutation.
        mutation: dictionnaire décrivant ``fichier``, ``avant`` et ``apres``.

    Returns:
        ``("OK", chemin)`` ou ``("OBSOLETE", None)``.
    """
    rel_path = Path(mutation["fichier"])
    target = temp_dir / rel_path
    if not target.is_file():
        return "OBSOLETE", None

    before = mutation["avant"]
    after = mutation["apres"]

    content = target.read_text(encoding="utf-8")
    occurrences = content.count(before)

    if occurrences != 1:
        return "OBSOLETE", None

    new_content = content.replace(before, after, 1)
    target.write_text(new_content, encoding="utf-8")
    return "OK", target


def _run_pytest(
    temp_dir: Path,
    timeout_s: int = 3600,
    chemins: list[str] | None = None,
) -> Tuple[int, str, str]:
    """
    Lance ``pytest`` dans ``temp_dir`` avec les options requises.

    Si *chemins* est fourni, les chemins de fichiers de test sont ajoutés à la
    ligne de commande après les options habituelles. Sinon, la batterie
    complète est exécutée.

    Retourne ``(code_retour, sortie_complète, dernière_ligne_de_sortie)``.

    Pourquoi : lancer pytest dans la copie temporaire avec ``PYTHONPATH``
    redirigé garantit que les tests portent sur le code muté, pas sur les
    sources du dépôt.

    Args:
        temp_dir: copie du projet servant de répertoire de travail.
        timeout_s: durée maximale autorisée pour l'exécution, en secondes.
        chemins: chemins de tests à passer à pytest, ou ``None`` pour la
            batterie complète.

    Returns:
        triplet ``(code_retour, sortie, dernière_ligne)``.
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = str(temp_dir / "src")
    env["REVIEWPULSE_SALT"] = "reverse-salt"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-x",
        "-p",
        "no:warnings",
        "-p",
        "no:cacheprovider",
        "-rf",  # pour que la ligne FAILED apparaisse
    ]

    # Ajout des chemins de test éventuels
    if chemins:
        cmd.extend(chemins)

    try:
        proc = subprocess.run(
            cmd,
            cwd=temp_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        output = proc.stdout.strip() or proc.stderr.strip()
        returncode = proc.returncode
    except subprocess.TimeoutExpired:
        # Code de retour 124 (comme dans GNU timeout), sortie explicative en français
        output = f"Le délai de {timeout_s} secondes a été dépassé."
        returncode = 124

    # Extraction de la dernière ligne non vide de la sortie (ou du message d'erreur)
    last_line = ""
    for line in reversed(output.splitlines()):
        if line.strip():
            last_line = line.strip()
            break
    return returncode, output, last_line


def _extract_failing_test(pytest_output: str) -> str:
    """
    Extrait le nom du premier test en échec.

    - Si une ligne commence par ``FAILED ``, on renvoie le texte qui suit
      jusqu'au premier espace.
    - Si le texte contient le mot ``error`` (insensible à la casse) sans
      ligne ``FAILED ``, on renvoie ``ERREUR DE COLLECTE``.
    - Sinon, on renvoie ``-``.

    Pourquoi : le rapport ne retient qu'un seul test détecteur par mutation ;
    le premier ``FAILED`` de pytest est le plus pertinent.

    Args:
        pytest_output: sortie texte brute de pytest.

    Returns:
        nom du test, ``ERREUR DE COLLECTE`` ou ``-``.
    """
    for line in pytest_output.splitlines():
        if line.startswith("FAILED "):
            # le nom du test se trouve après "FAILED " jusqu'au premier espace
            rest = line[len("FAILED ") :].strip()
            return rest.split()[0]
    if "error" in pytest_output.lower():
        return "ERREUR DE COLLECTE"
    return "-"


def _git_short_hash(root: Path) -> str:
    """Retourne le hash court du commit courant, ou ``'inconnu'`` en cas d'échec.

    Pourquoi : le rapport doit être rattaché à une version du code, même
    quand la variable ``REVIEWPULSE_COMMIT`` n'est pas définie.

    Args:
        root: répertoire racine du dépôt.

    Returns:
        hash court git, ou la chaîne ``'inconnu'``.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "inconnu"


def _get_commit(root: Path) -> str:
    """Détermine le commit à reporter.

    Pourquoi : la CI peut fournir le commit via une variable d'environnement ;
    en local, on relève git.

    Args:
        root: répertoire racine du dépôt.

    Returns:
        identifiant de commit à inscrire dans le rapport.
    """
    env_commit = os.getenv("REVIEWPULSE_COMMIT")
    if env_commit:
        return env_commit
    return _git_short_hash(root)


def _format_markdown_report(
    witness_ok: bool,
    witness_summary: str,
    results: List[Dict[str, str]],
    total: int,
    killed: int,
    survived: int,
    obsolete: int,
    commit: str,
    date_utc: str,
) -> str:
    """Construit le texte complet du rapport Markdown.

    Pourquoi : le rapport est la preuve d'effet attendue par le jury ;
    sa structure est figée pour rester lisible dans GitHub.

    Args:
        witness_ok: ``True`` si la mesure témoin a réussi.
        witness_summary: dernière ligne de sortie du témoin.
        results: liste des résultats de mutation.
        total: nombre total de mutations exécutées.
        killed: nombre de mutations tuées.
        survived: nombre de mutations survivantes.
        obsolete: nombre de mutations obsolètes.
        commit: identifiant de version.
        date_utc: date et heure UTC du rapport.

    Returns:
        texte Markdown complet.
    """
    lines = [
        f"# Rapport de tests inverses – {date_utc}",
        "",
        f"Commit : `{commit}`",
        "",
    ]

    if witness_ok:
        lines.append(f"Témoin : {witness_summary}")
    else:
        lines.append(f"TÉMOIN EN ÉCHEC : résultats invalides – {witness_summary}")
    lines.append("")

    # Tableau des mutations
    header = "| id | défaut simulé | pourquoi c’est grave | statut | résumé pytest | test qui détecte | portée |"
    separator = "|---|---------------|----------------------|--------|---------------|-----------------|-------|"
    lines.append(header)
    lines.append(separator)
    for r in results:
        lines.append(
            f"| {r['id']} | {r['defaut_simule']} | {r['pourquoi_grave']} | {r['statut']} | {r['resume']} | {r['test_qui_detecte']} | {r.get('portee', 'batterie complète')} |"
        )
    lines.extend(
        [
            "",
            f"**Total** : {total} – **TUEES** : {killed} – **SURVIVANTES** : {survived} – **OBSOLETES** : {obsolete}",
            "",
        ]
    )
    return "\n".join(lines)


def _print_console_table(results: List[Dict[str, str]]) -> None:
    """Affiche un tableau simple en console (format Markdown).

    Pourquoi : l'opérateur voit immédiatement le résultat sans ouvrir le
    rapport, en conservant le même ordre et les mêmes colonnes que le rapport.

    Args:
        results: liste des résultats de mutation.
    """
    # Mapping explicite entre les clés internes et les titres affichés
    columns = [
        ("id", "id"),
        ("defaut_simule", "défaut simulé"),
        ("pourquoi_grave", "pourquoi c’est grave"),
        ("statut", "statut"),
        ("resume", "résumé pytest"),
        ("test_qui_detecte", "test qui détecte"),
    ]

    # Calcul des largeurs de colonnes
    col_widths = []
    for key, title in columns:
        max_len = max(len(str(row.get(key, ""))) for row in results + [{key: title}])
        col_widths.append(max_len)

    # Fonction d'affichage d'une ligne
    def fmt(row: Dict[str, str]) -> str:
        return " | ".join(str(row.get(key, "")).ljust(w) for (key, _), w in zip(columns, col_widths))

    # En-tête
    header_row = {key: title for key, title in columns}
    print(fmt(header_row))
    print("-|-".join("-" * w for w in col_widths))

    for r in results:
        print(fmt(r))


def main() -> int:
    """Point d'entrée du script.

    Pourquoi : orchestrer la mesure témoin, l'application des mutations et la
    génération du rapport dans un seul flux contrôlé.

    Returns:
        ``0`` si toutes les mutations sont tuées, ``1`` si au moins une
        survit ou est obsolète, ``2`` si le témoin échoue.
    """
    parser = argparse.ArgumentParser(
        description="Exécute les tests inverses (mutations) du projet ReviewPulse."
    )
    parser.add_argument(
        "--only",
        metavar="ID",
        help="Exécute uniquement la mutation dont l’identifiant correspond à ID.",
    )
    parser.add_argument(
        "--report",
        metavar="CHEMIN",
        default="docs/evidence/reverse_tests.md",
        help="Chemin du rapport Markdown généré (par défaut %(default)s).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        metavar="SECS",
        help="Durée maximale (en secondes) autorisée pour chaque exécution de pytest (par défaut %(default)s).",
    )
    args = parser.parse_args()

    root = _repo_root()
    mutations_path = root / "tests" / "reverse" / "mutations.json"
    mutations = _load_mutations(mutations_path)

    # Filtrage éventuel
    if args.only:
        mutations = [m for m in mutations if str(m.get("id")) == args.only]
        if not mutations:
            log.error("Aucune mutation avec l’identifiant %s", args.only)
            return 1

    # ------------------------------------------------------------
    # 1️⃣ Mesure témoin (aucune mutation)
    # ------------------------------------------------------------
    # Détermination de la portée de la mesure témoin :
    # - si au moins une mutation ne déclare pas de champ ``tests``, on exécute
    #   la batterie complète ;
    # - sinon, on exécute l'union dédoublonnée et triée des chemins déclarés.
    all_test_paths: set[str] = set()
    besoin_batterie_complete = False
    for m in mutations:
        tests = m.get("tests")
        if isinstance(tests, list):
            all_test_paths.update(tests)
        else:
            besoin_batterie_complete = True

    witness_paths: list[str] | None = None
    if not besoin_batterie_complete and all_test_paths:
        witness_paths = sorted(all_test_paths)

    with tempfile.TemporaryDirectory() as td_witness:
        witness_dir = Path(td_witness)
        _copy_project(witness_dir)
        # Journalisation de la portée retenue
        if witness_paths is None:
            log.info("Portée retenue : batterie complète")
        else:
            log.info("Portée retenue : %s", ", ".join(witness_paths))
        witness_retcode, witness_output, witness_last_line = _run_pytest(
            witness_dir, timeout_s=args.timeout, chemins=witness_paths
        )
        witness_ok = witness_retcode == 0
        witness_summary = witness_last_line

    if not witness_ok:
        # Rapport contenant uniquement le témoin en échec
        now_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
        commit_hash = _get_commit(root)
        report_md = _format_markdown_report(
            witness_ok=False,
            witness_summary=witness_summary,
            results=[],
            total=0,
            killed=0,
            survived=0,
            obsolete=0,
            commit=commit_hash,
            date_utc=now_utc,
        )
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_md, encoding="utf-8")
        # Affichage console minimal
        print("TÉMOIN EN ÉCHEC : résultats invalides –", witness_summary)
        return 2

    # ------------------------------------------------------------
    # 2️⃣ Exécution des mutations
    # ------------------------------------------------------------
    results: List[Dict[str, str]] = []
    killed = survived = obsolete = 0

    for mut in mutations:
        mut_id = str(mut.get("id", ""))
        defaut = str(mut.get("defaut_simule", ""))
        pourquoi = str(mut.get("pourquoi_grave", ""))

        # Détermination de la portée pour cette mutation
        mut_tests = mut.get("tests")
        if isinstance(mut_tests, list):
            portée = ", ".join(mut_tests)
            chemins_pytest = mut_tests
        else:
            portée = "batterie complète"
            chemins_pytest = None

        with tempfile.TemporaryDirectory() as td:
            temp_dir = Path(td)
            _copy_project(temp_dir)

            status, _ = _apply_mutation(temp_dir, mut)
            if status == "OBSOLETE":
                obsolete += 1
                results.append(
                    {
                        "id": mut_id,
                        "defaut_simule": defaut,
                        "pourquoi_grave": pourquoi,
                        "statut": "OBSOLETE",
                        "resume": "N/A",
                        "test_qui_detecte": "-",
                        "portee": portée,
                    }
                )
                continue

            # Journalisation de la portée retenue
            log.info("Portée retenue : %s", portée)

            retcode, output, summary = _run_pytest(
                temp_dir, timeout_s=args.timeout, chemins=chemins_pytest
            )
            test_name = _extract_failing_test(output)

            if retcode != 0:
                statut = "TUEE"
                killed += 1
            else:
                statut = "SURVIVANTE"
                survived += 1

            results.append(
                {
                    "id": mut_id,
                    "defaut_simule": defaut,
                    "pourquoi_grave": pourquoi,
                    "statut": statut,
                    "resume": summary,
                    "test_qui_detecte": test_name,
                    "portee": portée,
                }
            )

    # ------------------------------------------------------------
    # 3️⃣ Génération du rapport
    # ------------------------------------------------------------
    now_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    commit_hash = _get_commit(root)
    total = len(results)
    report_md = _format_markdown_report(
        witness_ok=True,
        witness_summary=witness_summary,
        results=results,
        total=total,
        killed=killed,
        survived=survived,
        obsolete=obsolete,
        commit=commit_hash,
        date_utc=now_utc,
    )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_md, encoding="utf-8")

    # Affichage console
    _print_console_table(results)

    # Code de sortie : 0 uniquement si aucune mutation n'est SURVIVANTE ou OBSOLETE
    if survived == 0 and obsolete == 0:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
