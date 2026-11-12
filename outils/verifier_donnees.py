"""Audit des motifs interdits sans exposer les valeurs détectées dans le rapport."""
from __future__ import annotations

import argparse
import csv
import hashlib
from io import BytesIO, StringIO
import json
from pathlib import Path
import re
import subprocess
import unicodedata
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
# Runtime Python tiers embarqué dans le portable : la documentation de la bibliothèque
# standard contient des adresses d'exemple. Les contenus retirés y restent recherchés.
RUNTIME_TIERS = "OGIAS/runtime/"
TEXT = {".py", ".md", ".txt", ".json", ".csv", ".js", ".css", ".html", ".xml", ".xsy", ".scy", ".yml", ".yaml", ".bat", ".ps1"}


def normalized(value: str) -> str:
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", value.casefold())
                            if not unicodedata.combining(c)).split())


def values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from values(child)
    elif isinstance(value, list):
        for child in value:
            yield from values(child)


def inspect_bytes(name: str, data: bytes, policy: dict, patterns: bool = True) -> list[dict]:
    suffix = Path(name).suffix.lower()
    found = []
    if suffix == ".xlsx":
        from openpyxl import load_workbook
        workbook = load_workbook(BytesIO(data), read_only=True, data_only=False)
        try:
            strings = [str(value) for sheet in workbook for row in sheet.iter_rows(values_only=True)
                       for value in row if value is not None]
        finally:
            workbook.close()
        text = "\n".join(strings)
    elif suffix in TEXT:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("cp1252")
        if suffix == ".json":
            strings = list(values(json.loads(text)))
        elif suffix == ".csv":
            strings = [cell for row in csv.reader(StringIO(text), delimiter=";") for cell in row]
        else:
            strings = text.splitlines()
    else:
        return found
    blocked = set(policy["forbidden_value_sha256"])
    for value in strings:
        digest = hashlib.sha256(normalized(value).encode()).hexdigest()
        if digest in blocked:
            found.append({"file": name, "rule": "retired-site-content", "value_sha256": digest})
    for pattern in policy["forbidden_patterns"] if patterns else ():
        if re.search(pattern["regex"], text):
            found.append({"file": name, "rule": pattern["id"]})
    return found


def inspect_file(path: Path, policy: dict) -> list[dict]:
    if path.suffix.lower() == ".zip":
        found = []
        with ZipFile(path) as archive:
            for entry in archive.infolist():
                if Path(entry.filename).suffix.lower() not in TEXT | {".xlsx"} or entry.is_dir():
                    continue
                if entry.file_size > 100 * 1024 * 1024:
                    raise ValueError("Membre d'archive trop volumineux pour être audité")
                found.extend(inspect_bytes(f"{path.name}!{entry.filename}", archive.read(entry), policy,
                                           patterns=not entry.filename.startswith(RUNTIME_TIERS)))
        return found
    if path.suffix.lower() not in TEXT | {".xlsx"}:
        return []
    return inspect_bytes(path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name,
                         path.read_bytes(), policy)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/ci/data.json"))
    parser.add_argument("--artifact", type=Path, action="append", default=[])
    args = parser.parse_args()
    policy = json.loads((ROOT / "validation/CONTROLE_DONNEES.json").read_text(encoding="utf-8"))
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, stdout=subprocess.PIPE).stdout
    paths = ([path.resolve() for path in args.artifact] if args.artifact else
             [ROOT / name.decode("utf-8") for name in tracked.split(b"\0") if name])
    violations = []
    failures = []
    for path in paths:
        try:
            violations.extend(inspect_file(path, policy))
        except (OSError, ValueError, UnicodeError) as error:
            failures.append({"file": path.name, "error_type": type(error).__name__})
    report = {"checked_files": len(paths), "violations": violations, "scan_failures": failures}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Audit données : {len(violations)} détection(s), {len(failures)} échec(s) de lecture.")
    return int(bool(violations or failures))


if __name__ == "__main__":
    raise SystemExit(main())
