"""Ouvrage d'exemple fictif livré à part (cahier V1-9-05) : il s'ouvre, reste fictif et suit le moteur."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

from genvar.modele import Ouvrage

RACINE = Path(__file__).resolve().parents[1]
EXEMPLE = RACINE / "exemples" / "OGIAS_exemple_XTSTRV01.ouvrage.json"


def _generateur():
    spec = importlib.util.spec_from_file_location("generer_exemple", RACINE / "outils" / "generer_exemple.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestOuvrageExemple(unittest.TestCase):
    def test_exemple_s_ouvre_et_reste_fictif(self):
        o = Ouvrage.ouvrir(str(EXEMPLE))
        self.assertEqual((o.lieu, o.code_ouvrage, o.numero_ouvrage), ("XTST", "RV", "01"))
        self.assertGreaterEqual(len(o.equipements), 5)
        self.assertTrue(any(e.valide for e in o.equipements) and not all(e.valide for e in o.equipements))
        self.assertIn("fictif", o.libelle.lower())

    def test_exemple_suit_le_moteur(self):
        self.assertEqual(_generateur().main(["--verifier"]), 0)

    def test_installation_vierge_ne_contient_aucune_donnee_de_demonstration(self):
        from sorep_web.serveur import Application
        ancien = os.environ.get("SOREP_DATA_DIR")
        with tempfile.TemporaryDirectory(prefix="ogias-vierge-") as tmp:
            os.environ["SOREP_DATA_DIR"] = tmp
            try:
                app = Application()
                self.assertEqual(app.accueil({})["ouvrages"], [])
            finally:
                if ancien is None:
                    os.environ.pop("SOREP_DATA_DIR", None)
                else:
                    os.environ["SOREP_DATA_DIR"] = ancien


if __name__ == "__main__":
    unittest.main()
