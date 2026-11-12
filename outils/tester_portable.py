"""Essai du ZIP avec son Python isolé, sans utiliser le Python installé pour l'app."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def extract_verified(archive: Path, target: Path) -> Path:
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    expected = archive.with_name(archive.name + ".sha256").read_text(encoding="ascii").split()[0]
    if digest != expected:
        raise ValueError("Somme SHA-256 du portable incorrecte")
    with ZipFile(archive) as package:
        for member in package.infolist():
            path = PurePosixPath(member.filename)
            if (not path.parts or path.is_absolute() or ".." in path.parts or "\\" in member.filename
                    or ":" in member.filename or path.parts[0] != "OGIAS"
                    or stat.S_ISLNK(member.external_attr >> 16)):
                raise ValueError("Chemin d'archive portable invalide")
        package.extractall(target)
    return target / "OGIAS"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--web", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="ogias-portable-test-") as temporary:
        folder = Path(temporary)
        application = extract_verified(args.archive.resolve(), folder)
        runtime = application / "runtime/python.exe"
        entrypoint = application / "lancer_portable.py"
        environment = {key: value for key, value in os.environ.items()
                       if key not in ("PYTHONPATH", "PYTHONHOME")}
        environment.update(SOREP_DATA_DIR=str(folder / "donnees"),
                           PATH=str(runtime.parent) + os.pathsep + str(Path(os.environ["SystemRoot"]) / "System32"))
        log = folder / "application.log"
        with log.open("w", encoding="utf-8") as output:
            process = subprocess.Popen([str(runtime), "-I", "-B", "-u", "-X", "utf8", str(entrypoint),
                                        "--sans-navigateur"], cwd=application, env=environment,
                                       stdout=output, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    match = re.search(r"http://127\.0\.0\.1:\d+/", log.read_text(encoding="utf-8"))
                    if match:
                        with urllib.request.urlopen(match.group() + "api/accueil", timeout=10) as response:
                            assert json.load(response)["ouvrages"] == []
                        break
                    if process.poll() is not None:
                        raise RuntimeError(log.read_text(encoding="utf-8"))
                    time.sleep(0.05)
                else:
                    raise RuntimeError("Le portable ne démarre pas avec son runtime isolé")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        print("SHA-256, runtime isolé, serveur et accueil vierge : OK")
        if args.web:
            environment = dict(os.environ, OGIAS_TEST_PYTHON=str(runtime), OGIAS_TEST_ENTRYPOINT=str(entrypoint))
            return subprocess.run([sys.executable, "outils/ci.py", "web", "--managed-browser",
                                   "--output", "artifacts/ci-portable"], cwd=ROOT, env=environment).returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
