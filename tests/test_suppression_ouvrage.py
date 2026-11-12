"""Suppression d'un ouvrage depuis « Mes ouvrages » : déplacé dans la corbeille, jamais effacé."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genvar import projets
from genvar.modele import Ouvrage


class TestSuppressionOuvrage(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = tempfile.mkdtemp()
        self.dossier = projets.repertoire()
        self.dossier.mkdir(parents=True, exist_ok=True)
        o = Ouvrage()
        o.lieu, o.code_ouvrage, o.libelle = "F999", "RV", "Réservoir fictif"
        self.chemin = str(self.dossier / "F999RV.ouvrage.json")
        o.enregistrer(self.chemin)
        Path(self.chemin + ".bak").write_text("{}", encoding="utf-8")

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def test_supprimer_puis_restaurer(self):
        self.assertEqual(len(projets.lister()), 1)
        dans_corbeille = projets.supprimer(self.chemin)
        self.assertFalse(os.path.exists(self.chemin))
        self.assertFalse(os.path.exists(self.chemin + ".bak"))
        self.assertTrue(os.path.exists(dans_corbeille))
        self.assertTrue(os.path.exists(dans_corbeille + ".bak"))
        self.assertEqual(projets.lister(), [])                       # disparu de « Mes ouvrages »
        self.assertEqual(len(projets.lister_corbeille()), 1)
        remis = projets.restaurer(dans_corbeille)
        self.assertEqual(os.path.basename(remis), "F999RV.ouvrage.json")
        self.assertEqual(projets.lister()[0].libelle, "Réservoir fictif")
        self.assertEqual(projets.lister_corbeille(), [])

    def test_restaurer_n_ecrase_rien(self):
        dans_corbeille = projets.supprimer(self.chemin)
        Ouvrage().enregistrer(self.chemin)                          # un nouvel ouvrage a pris le nom
        remis = projets.restaurer(dans_corbeille)
        self.assertNotEqual(remis, self.chemin)
        self.assertEqual(len(projets.lister()), 2)

    def test_deux_suppressions_du_meme_nom(self):
        a = projets.supprimer(self.chemin)
        Ouvrage().enregistrer(self.chemin)
        b = projets.supprimer(self.chemin)
        self.assertNotEqual(a, b)
        self.assertEqual(len(projets.lister_corbeille()), 2)

    def test_fichier_absent(self):
        with self.assertRaises(ValueError):
            projets.supprimer(str(self.dossier / "absent.ouvrage.json"))


if __name__ == "__main__":
    unittest.main()
