"""Les portes CI doivent refuser un faux vert, un rapport vide ou des ignorés."""
import json
import os
import hashlib
import stat
import sys
from zipfile import ZipFile, ZipInfo

import pytest

from outils.ci import EXPORTS, check_coverage, check_junit, execute
from outils.construire_portable import archive_reproductible
from outils.tester_portable import extract_verified
from outils.verifier_donnees import inspect_bytes, normalized


@pytest.mark.parametrize("contents", [
    "<testsuites/>",
    '<testsuite><testcase><failure/></testcase></testsuite>',
    '<testsuite><testcase><error/></testcase></testsuite>',
    '<testsuite><testcase><skipped/></testcase></testsuite>',
])
def test_junit_rejects_incomplete_runs(tmp_path, contents):
    report = tmp_path / "tests.xml"
    report.write_text(contents)
    with pytest.raises(ValueError):
        check_junit(report, 1)


def test_junit_counts_actual_cases_instead_of_announced_totals(tmp_path):
    report = tmp_path / "tests.xml"
    report.write_text('<testsuite tests="999"><testcase name="one"/></testsuite>')
    with pytest.raises(ValueError):
        check_junit(report, 2)
    assert check_junit(report, 1)["tests"] == 1


def test_command_failure_preserves_exit_status_and_output(tmp_path):
    log = tmp_path / "command.log"
    assert execute([sys.executable, "-c", 'print("échec contrôlé"); raise SystemExit(7)'], log,
                   {**os.environ, "PYTHONUTF8": "1"}) == 7
    assert "échec contrôlé" in log.read_text(encoding="utf-8")


@pytest.mark.parametrize("percent,missing", [(84.99, []), (90, [1])])
def test_coverage_gate_rejects_engine_or_export_gap(tmp_path, percent, missing):
    report = tmp_path / "coverage.json"
    report.write_text(json.dumps({"totals": {"percent_covered": percent},
                                  "files": {name: {"missing_lines": missing} for name in EXPORTS}}))
    with pytest.raises(ValueError):
        check_coverage(report)


def test_coverage_gate_accepts_required_metrics(tmp_path):
    report = tmp_path / "coverage.json"
    report.write_text(json.dumps({"totals": {"percent_covered": 85},
                                  "files": {name: {"missing_lines": []} for name in EXPORTS}}))
    assert check_coverage(report)["industrial_exports_percent"] == 100


def test_windows_coverage_paths_are_accepted(tmp_path):
    report = tmp_path / "coverage.json"
    report.write_text(json.dumps({"totals": {"percent_covered": 85}, "files": {
        name.replace("/", "\\"): {"missing_lines": []} for name in EXPORTS}}))
    assert check_coverage(report)["genvar_percent"] == 85


def test_data_control_finds_normalized_content_without_disclosing_it():
    value = "Contenu confidentiel FICTIF"
    digest = hashlib.sha256(normalized(value).encode()).hexdigest()
    policy = {"forbidden_value_sha256": [digest], "forbidden_patterns": []}
    report = inspect_bytes("fictif.json", json.dumps({"nested": [value.upper()]}).encode(), policy)
    assert report == [{"file": "fictif.json", "rule": "retired-site-content", "value_sha256": digest}]
    assert value not in json.dumps(report)
    assert inspect_bytes("fictif.json", b'{"value":"contenu autorise"}', policy) == []


def test_portable_archive_is_reproducible(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "fictif.txt").write_text("Données fictives", encoding="utf-8")
    (source / "__pycache__").mkdir()
    (source / "__pycache__" / "fictif.pyc").write_bytes(b"cache")
    first, second = tmp_path / "first.zip", tmp_path / "second.zip"
    archive_reproductible(source, first, 1700000000)
    os.utime(source / "fictif.txt", (1700000500, 1700000500))
    archive_reproductible(source, second, 1700000000)
    assert first.read_bytes() == second.read_bytes()
    with ZipFile(first) as archive:
        assert archive.namelist() == ["OGIAS/fictif.txt"]
        assert archive.read("OGIAS/fictif.txt").decode() == "Données fictives"


@pytest.mark.parametrize("name,symlink", [("../outside", False), ("OGIAS/../../outside", False),
                                        ("OGIAS/C:/outside", False), ("OGIAS/link", True)])
def test_portable_rejects_unsafe_paths(tmp_path, name, symlink):
    package = tmp_path / "fictif.zip"
    with ZipFile(package, "w") as archive:
        info = ZipInfo(name)
        if symlink:
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "Fictif")
    package.with_name(package.name + ".sha256").write_text(hashlib.sha256(package.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match="Chemin"):
        extract_verified(package, tmp_path / "destination")
    assert not (tmp_path / "outside").exists()


def test_portable_rejects_incorrect_checksum(tmp_path):
    package = tmp_path / "fictif.zip"
    package.write_bytes(b"faux paquet")
    package.with_name(package.name + ".sha256").write_text("0" * 64)
    with pytest.raises(ValueError, match="SHA-256"):
        extract_verified(package, tmp_path / "destination")
