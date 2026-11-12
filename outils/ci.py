"""Contrôles CI bloquants ; aucun rapport ancien ne vaut résultat du lancement."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ("genvar/export_xsy.py", "genvar/formats_control_expert.py", "genvar/formats_topkapi.py")


def check_junit(path: Path, minimum: int) -> dict:
    root = ET.parse(path).getroot()
    cases = list(root.iter("testcase"))
    counts = {name: sum(case.find(name) is not None for case in cases)
              for name in ("failure", "error", "skipped")}
    if len(cases) < minimum or any(counts.values()):
        raise ValueError(f"JUnit non conforme : {len(cases)} tests, minimum {minimum}, {counts}")
    return {"tests": len(cases), **counts}


def check_coverage(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    total = data["totals"]["percent_covered"]
    problems = []
    if total < 85:
        problems.append(f"genvar : {total:.2f} %, minimum 85 %")
    files = {name.replace("\\", "/"): value for name, value in data["files"].items()}
    for name in EXPORTS:
        file = files.get(name)
        if not file or file["missing_lines"] or file.get("summary", {}).get("excluded_lines", 0):
            problems.append(f"{name} : couverture incomplète ou rapport absent")
    if problems:
        raise ValueError(" ; ".join(problems))
    return {"genvar_percent": total, "industrial_exports_percent": 100}


def execute(command: list[str], log: Path, env: dict[str, str] | None = None) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        assert process.stdout is not None
        for line in process.stdout:
            output.write(line)
            print(line, end="", flush=True)
        process.stdout.close()
        return process.wait()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=("python", "web", "coverage", "static", "audit", "performance", "data"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/ci"))
    parser.add_argument("--managed-browser", action="store_true")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONUTF8="1")
    with tempfile.TemporaryDirectory(prefix="ogias-ci-") as temporary:
        env.update(SOREP_DATA_DIR=temporary, QT_QPA_PLATFORM="offscreen",
                   XDG_CONFIG_HOME=str(Path(temporary) / "config"),
                   XDG_CACHE_HOME=str(Path(temporary) / "cache"),
                   COVERAGE_FILE=str(output / ".coverage"))
        if args.suite in ("python", "web"):
            report = output / f"{args.suite}.xml"
            report.unlink(missing_ok=True)
            command = [sys.executable, "-m", "pytest", "-q", "-r", "fEs", "-p", "no:cacheprovider",
                       f"--junitxml={report}"]
            if args.suite == "python":
                coverage = output / "coverage.json"
                coverage.unlink(missing_ok=True)
                command += ["tests", "tests_qt", "--cov=genvar", f"--cov-report=json:{coverage}",
                            f"--cov-report=xml:{output / 'coverage.xml'}", "--cov-report=term:skip-covered"]
            else:
                command += ["tests_web"]
                if args.managed_browser:
                    from playwright.sync_api import sync_playwright
                    with sync_playwright() as playwright:
                        env["OGIAS_TEST_CHROMIUM"] = playwright.chromium.executable_path
            code = execute(command, output / f"{args.suite}.log", env)
            if code:
                return code
            check_junit(report, 402 if args.suite == "python" else 6)
        elif args.suite == "coverage":
            print(json.dumps(check_coverage(output / "coverage.json")))
        elif args.suite == "static":
            for index, command in enumerate(([sys.executable, "-m", "ruff", "check", "--config", "ruff.toml", "."],
                            [sys.executable, "-m", "mypy", "--config-file", "mypy.ini", "genvar"],
                            *(["node", "--check", str(file)] for file in sorted((ROOT / "sorep_web/static").glob("*.js"))))):
                code = execute(command, output / f"static-{index}.log", env)
                if code:
                    return code
        elif args.suite == "audit":
            report = output / "dependencies.json"
            report.unlink(missing_ok=True)
            return execute([sys.executable, "-m", "pip_audit", "--strict", "--no-deps", "--disable-pip",
                            "--cache-dir", str(Path(temporary) / "audit-cache"),
                            "-r", "requirements-ci.lock", "--format", "json", "--output", str(report)],
                           output / "audit.log", env)
        elif args.suite == "performance":
            return execute([sys.executable, "-m", "bench.performance", "--output", str(output / "performance.json")],
                           output / "performance.log", env)
        elif args.suite == "data":
            return execute([sys.executable, "outils/verifier_donnees.py", "--output", str(output / "data.json")],
                           output / "data.log", env)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        print(f"Contrôle CI non validé : {error}", file=sys.stderr)
        raise SystemExit(1)
