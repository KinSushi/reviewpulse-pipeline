"""tools/reverse_tests.py
Où : module exécutable placé sous le répertoire ``tools`` du projet ReviewPulse.
Quoi : exécute la batterie de « mutations » décrites dans
``tests/reverse/mutations.json`` afin de vérifier que les tests
détectent les défauts volontairement injectés.
Comment :
- pour chaque mutation, copie les sources (``src/``, ``tests/``, ``dashboard/``,
  ``dags/``) et le fichier ``pyproject.toml`` dans un répertoire temporaire,
- s’assure que la chaîne ``avant`` apparaît exactement une fois dans le
  fichier ciblé, sinon la mutation est marquée ``OBSOLETE``,
- remplace cette occurrence par ``apres``,
- lance ``pytest`` dans la copie avec un environnement contrôlé
  (``PYTHONPATH`` pointant vers ``src`` et ``REVIEWPULSE_SALT`` fixé à
  ``reverse-salt``),
- interprète le code retour : ``non‑zero`` → ``TUEE`` (les tests ont
  détecté la mutation), ``zero`` → ``SURVIVANTE``,
- relève le premier test qui échoue (ou « ERREUR DE COLLECTE »),
- conserve la dernière ligne de sortie de ``pytest`` comme résumé.
Pourquoi : ce script constitue le test de robustesse du jeu de tests
en s’assurant qu’une mutation introduite volontairement entraîne l’échec
des tests. Le rapport Markdown généré sert de preuve d‑effet.

Le module expose ``main() -> int`` et se lance via
``if __name__ == "__main__": raise SystemExit(main())``.
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
    """Retourne le répertoire racine du dépôt (parent du répertoire ``tools``)."""
    return Path(__file__).resolve().parents[1]


def _load_mutations(path: Path) -> List[Mutation]:
    """Charge la liste des mutations depuis le fichier JSON indiqué."""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Le fichier {path} ne contient pas une liste JSON.")
    return data  # type: ignore[return-value]


def _copy_project(temp_dir: Path) -> None:
    """Copie ``src/``, ``tests/``, ``dashboard/``, ``dags/`` et ``pyproject.toml``."""
    root = _repo_root()
    for name in ("src", "tests", "dashboard", "dags"):
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
    ``"OBSOLETE"`` si la chaîne ``avant`` n’est pas trouvée exactement
    une fois, sinon ``"OK"``. ``chemin_fichier`` est le chemin absolu du
    fichier modifié (ou ``None`` en cas d’``OBSOLETE``).
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


def _run_pytest(temp_dir: Path, timeout_s: int = 3600) -> Tuple[int, str, str]:
    """
    Lance ``pytest`` dans ``temp_dir`` avec les options requises.

    Retourne ``(code_retour, sortie_complète, dernière_ligne_de_sortie)``.
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

    # Extraction de la dernière ligne non vide de la sortie (ou du message d’erreur)
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
    """Retourne le hash court du commit courant, ou ``'inconnu'`` en cas d’échec."""
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
    """Détermine le commit à reporter."""
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
    """Construit le texte complet du rapport Markdown."""
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
    header = "| id | défaut simulé | pourquoi c’est grave | statut | résumé pytest | test qui détecte |"
    separator = "|---|---------------|----------------------|--------|---------------|-----------------|"
    lines.append(header)
    lines.append(separator)
    for r in results:
        lines.append(
            f"| {r['id']} | {r['defaut_simule']} | {r['pourquoi_grave']} | {r['statut']} | {r['resume']} | {r['test_qui_detecte']} |"
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
    """Affiche un tableau simple en console (format Markdown)."""
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

    # En‑tête
    header_row = {key: title for key, title in columns}
    print(fmt(header_row))
    print("-|-".join("-" * w for w in col_widths))

    for r in results:
        print(fmt(r))


def main() -> int:
    """Point d’entrée du script."""
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
    with tempfile.TemporaryDirectory() as td_witness:
        witness_dir = Path(td_witness)
        _copy_project(witness_dir)
        witness_retcode, witness_output, witness_last_line = _run_pytest(witness_dir, timeout_s=args.timeout)
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
                    }
                )
                continue

            retcode, output, summary = _run_pytest(temp_dir, timeout_s=args.timeout)
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

    # Code de sortie : 0 uniquement si aucune mutation n’est SURVIVANTE ou OBSOLETE
    if survived == 0 and obsolete == 0:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
