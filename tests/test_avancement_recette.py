"""Avancement de la recette (cahier V1-4-30) : le moteur fournit le total des règles et celles qui sont respectées."""
import os
import tempfile
import unittest

from genvar.coherence import REGLES
from sorep_web.serveur import Application


class TestAvancementRecette(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-avancement-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.appeler("nouveau", {"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.appeler("fiche_ouvrage", {"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "53", "libelle": "Essai avancement",
            "automate": "Sch - M580", "revision": "A"}})

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def test_total_et_conformes_coherents_avec_les_constats(self):
        r = self.app.recette_web({})
        self.assertEqual(r["controles_total"], len(REGLES))
        violees = {c["regle"] for c in r["controles"] if c["regle"] in REGLES}
        self.assertEqual(r["controles_conformes"], len(REGLES) - len(violees))
        self.assertTrue(0 <= r["controles_conformes"] <= r["controles_total"])

    def test_un_equipement_non_valide_fait_baisser_les_regles_respectees(self):
        avant = self.app.recette_web({})["controles_conformes"]
        i = self.app.appeler("ajouter_equipement", {"type": "PM", "numero": "01", "se": "00"})["ident"]
        r = self.app.recette_web({})
        self.assertIn("R-EQ-01", {c["regle"] for c in r["controles"]})
        self.assertLessEqual(r["controles_conformes"], avant)
        self.app.appeler("decider_proposition", {"ident_eq": i, "decision": "retenir"})
        self.app.appeler("valider_equipements", {"idents": [i], "valide": True})
        self.assertNotIn("R-EQ-01", {c["regle"] for c in self.app.recette_web({})["controles"]})


if __name__ == "__main__":
    unittest.main()
