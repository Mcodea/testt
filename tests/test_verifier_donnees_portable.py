"""Portée de l'audit anti-données dans l'archive portable."""
import hashlib
import importlib.util
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verifier_donnees", ROOT / "outils/verifier_donnees.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)

IP_EXEMPLE = ".".join(("192", "168", "0", "1"))  # assemblée : le dépôt reste sans adresse
INTERDIT = "valeur de site retiree"
POLICY = {
    "forbidden_value_sha256": [hashlib.sha256(verifier.normalized(INTERDIT).encode()).hexdigest()],
    "forbidden_patterns": [{"id": "private-network-ip", "regex": r"192\.168\.\d{1,3}\.\d{1,3}"}],
}


def _archive(tmp_path, membres):
    chemin = tmp_path / "OGIAS-essai.zip"
    with ZipFile(chemin, "w") as archive:
        for nom, texte in membres.items():
            archive.writestr(nom, texte)
    return chemin


def test_adresse_exemple_du_runtime_tiers_toleree(tmp_path):
    archive = _archive(tmp_path, {"OGIAS/runtime/Lib/ipaddress.py": "exemple " + IP_EXEMPLE + "\n"})
    assert verifier.inspect_file(archive, POLICY) == []


def test_adresse_dans_le_code_ogias_refusee(tmp_path):
    archive = _archive(tmp_path, {"OGIAS/genvar/module.py": "hote = '" + IP_EXEMPLE + "'\n"})
    assert [v["rule"] for v in verifier.inspect_file(archive, POLICY)] == ["private-network-ip"]


def test_contenu_retire_refuse_meme_dans_le_runtime(tmp_path):
    archive = _archive(tmp_path, {"OGIAS/runtime/Lib/x.txt": INTERDIT + "\n"})
    assert [v["rule"] for v in verifier.inspect_file(archive, POLICY)] == ["retired-site-content"]
