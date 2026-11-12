"""Intégrité des références reçues ; ne prouve pas leur intégration applicative."""
import hashlib
from pathlib import Path
import struct

from openpyxl import load_workbook
import pytest

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_SHA256 = {'docs/referentiel/OGIAS_V031_informations_modeles.xlsx': 'c2742f872a2dceba16d2eb86c4e0ce1c42b65628a5b4e3f6b46dec7d857db8de', 'docs/referentiel/OGIAS_V031_bibliotheque_ES_physiques.xlsx': '7010c79de0019f0364729c92e8f767148821613b5edf3dac303bd2cbf356a749', 'docs/CAHIER_DES_CHARGES_V1.md': '3a04aed54b47d6c222b09a8151f67d24e26b4185a0e55eb71a0b1d3d318a538c', 'docs/maquettes/OGIAS_maquette_1_tableau_de_bord.png': '952cb09d94c8161bbb1787f1c6df5a1c0342f6fcaf2e7a3f29dd126e22e32bae', 'docs/maquettes/OGIAS_maquette_3_variables_detail.png': 'cd64ca0c25ec0088b265e18e5cc0b93682ec5ecdbe8cd2c887f58cc92db7913a', 'docs/maquettes/OGIAS_maquette_2_variables.png': '3824200ef6e2a8381a7c478dd27178b5f6f24eb3e60bf3617d04474b2869d344'}


@pytest.mark.parametrize("name,digest", REFERENCE_SHA256.items())
def test_reference_fournie_preservee(name, digest):
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest


def test_classeurs_sources_complets():
    with_modeles = load_workbook(ROOT / "docs/referentiel/OGIAS_V031_informations_modeles.xlsx", read_only=True, data_only=True)
    try:
        rows = [r for r in list(with_modeles["Informations"].values)[1:] if r[0]]
        assert len(rows) == len({r[0] for r in rows}) == 740
        assert sum(r[11] == "Retiré" for r in rows) == 8
        assert sum(r[11] != "Retiré" for r in rows) == 732
        assert len({r[2] for r in rows}) == 25
        assert all(len(r[5]) <= 12 for r in rows if r[11] != "Retiré")
    finally:
        with_modeles.close()
    workbook = load_workbook(ROOT / "docs/referentiel/OGIAS_V031_bibliotheque_ES_physiques.xlsx", read_only=True, data_only=True)
    try:
        rows = [r for r in list(workbook["Bibliothèque E-S"].values)[1:] if r[0]]
        assert len(rows) == len({r[0] for r in rows}) == 193
        assert sum(r[20] == "Ajouté" for r in rows) == 49
        dictionary = [r for r in list(workbook["Dictionnaire"].values)[1:] if r[1] in ("ET", "ST", "EA", "SA")]
        assert len(dictionary) == 81
        assert {r[7] for r in rows} == {r[0] for r in dictionary}
    finally:
        workbook.close()


@pytest.mark.parametrize("name", [name for name in REFERENCE_SHA256 if name.endswith(".png")])
def test_maquettes_format_et_dimensions(name):
    data = (ROOT / name).read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", data[16:24]) == (1920, 1080)
