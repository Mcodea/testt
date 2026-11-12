"""Construction native Windows : runtime embarqué, données séparées, ZIP + SHA-256."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from zipfile import ZIP_DEFLATED, ZipFile
from zipfile import ZipInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from genvar import VERSION


def archive_reproductible(staging: Path, archive: Path, epoch: int) -> None:
    date = time.gmtime(max(epoch, 315532800))[:6]
    with ZipFile(archive, "w", ZIP_DEFLATED, compresslevel=9) as target:
        for file in sorted(staging.rglob("*")):
            if not file.is_file() or "__pycache__" in file.parts or file.suffix == ".pyc":
                continue
            info = ZipInfo((Path("OGIAS") / file.relative_to(staging)).as_posix(), date)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            target.writestr(info, file.read_bytes())


def build(output: Path) -> Path:
    if sys.platform != "win32" or sys.maxsize <= 2**32:
        raise RuntimeError("La version Windows x64 se construit avec un Python Windows x64 natif.")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ogias-portable-") as temporary:
        staging = Path(temporary) / "OGIAS"
        runtime = staging / "runtime"
        runtime.mkdir(parents=True)
        base = Path(sys.base_prefix)
        for pattern in ("python*.exe", "python*.dll", "vcruntime*.dll", "LICENSE*.txt"):
            for file in base.glob(pattern):
                shutil.copy2(file, runtime / file.name)
        for name in ("DLLs", "Lib"):
            shutil.copytree(base / name, runtime / name,
                            ignore=shutil.ignore_patterns("site-packages", "__pycache__", "*.pyc", "test", "tests"))
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", "--no-compile", "--target",
                        str(runtime / "Lib/site-packages"), "-r", str(ROOT / "requirements-runtime.lock")], check=True)
        for name in ("genvar", "genvar_qt", "sorep_web"):
            shutil.copytree(ROOT / name, staging / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy2(ROOT / "lancer_qt.py", staging / "lancer_qt.py")
        (staging / "lancer_portable.py").write_text(
            'from pathlib import Path\nimport runpy, sys\n'
            'sys.path.insert(0, str(Path(__file__).resolve().parent))\n'
            'runpy.run_module("sorep_web", run_name="__main__")\n', encoding="utf-8")
        (staging / "OGIAS.bat").write_bytes(
            b'@echo off\r\n"%~dp0runtime\\python.exe" -I -B -X utf8 "%~dp0lancer_portable.py" %*\r\n')
        (staging / "BUILD.json").write_text(json.dumps({
            "version": VERSION, "python": sys.version.split()[0], "architecture": "windows-x64",
            "commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                                     capture_output=True, text=True).stdout.strip(),
            "industrial_formats_qualified": False,
        }, indent=2) + "\n", encoding="utf-8")
        subprocess.run([str(runtime / "python.exe"), "-I", "-c",
                        'import openpyxl, fitz; from PySide6 import QtCore; print("Runtime portable disponible")'],
                       check=True, cwd=staging)
        name = f"OGIAS-{VERSION}-windows-x64.zip"
        archive = output / name
        epoch = int(subprocess.run(["git", "show", "-s", "--format=%ct", "HEAD"], cwd=ROOT,
                                   check=True, capture_output=True, text=True).stdout.strip())
        archive_reproductible(staging, archive, epoch)
        subprocess.run([sys.executable, str(ROOT / "outils/verifier_donnees.py"), "--artifact", str(archive),
                        "--output", str(output / "audit-donnees.json")], check=True, cwd=ROOT)
        with archive.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        (output / (name + ".sha256")).write_text(f"{digest}  {name}\n", encoding="ascii")
        return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/portable"))
    print(build(parser.parse_args().output.resolve()))
