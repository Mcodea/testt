"""Aperçu A1 des renommages et ajouts à approuver : généré, à jour, et sans aucun effet sur le référentiel livré."""
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def _outil():
    spec = importlib.util.spec_from_file_location("apercu_a1", RACINE / "outils" / "apercu_a1.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestApercuA1(unittest.TestCase):
    def test_apercu_a_jour(self):
        self.assertEqual(_outil().main(["--verifier"]), 0, "py outils/apercu_a1.py")

    def test_chiffres_et_contenu(self):
        d = _outil().calculer()
        self.assertEqual(len(d["ajouts"]), 49)                        # les 49 ajouts du rapport V1
        self.assertEqual(len(d["renommages"]), 57)
        self.assertTrue(any("CT.ET.IMP" in x for x in d["particuliers"]))
        texte = (RACINE / "docs" / "APERCU_A1_A_APPROUVER.md").read_text(encoding="utf-8")
        self.assertIn("Rien n'est appliqué", texte)
        self.assertEqual(texte.count("| ☐ |"), 57 + 49)               # une case de décision par ligne

    def test_aucun_ajout_n_est_deja_dans_le_catalogue_et_chaque_renommage_part_d_un_signal_existant(self):
        d = _outil().calculer()
        catalogue = json.loads((RACINE / "genvar/data/catalogue_defaut.json").read_text(encoding="utf-8"))
        existants = {(s["type"], s["es"], s["code"]) for s in catalogue["signaux"]}
        for a in d["ajouts"]:
            self.assertNotIn((a["type"], a["nature"], a["code"]), existants, a["id"])
        for r in d["renommages"]:
            self.assertIn((r["type"], r["nature"], r["code_actuel"]), existants, r)
            self.assertNotEqual(r["code_actuel"], r["code_propose"])

    def test_la_generation_ne_modifie_pas_le_catalogue_livre(self):
        chemin = RACINE / "genvar/data/catalogue_defaut.json"
        avant = hashlib.sha256(chemin.read_bytes()).hexdigest()
        _outil().calculer()
        self.assertEqual(hashlib.sha256(chemin.read_bytes()).hexdigest(), avant)


if __name__ == "__main__":
    unittest.main()
