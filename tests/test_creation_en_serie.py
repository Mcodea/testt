"""Création en série d'équipements d'un même type (cahier V1-5-05). Ouvrage fictif (XTST)."""
import os
import tempfile
import unittest

from sorep_web.serveur import Application, RegleMetier


class TestCreationEnSerie(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-serie-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.appeler("nouveau", {"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.appeler("fiche_ouvrage", {"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "44", "libelle": "Essai série",
            "automate": "Sch - M580", "revision": "A"}})

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def numeros(self, type_):
        return sorted(e.numero for e in self.app.s.ouvrage.equipements if e.type == type_)

    def test_cinq_pompes_aux_numeros_libres(self):
        r = self.app.appeler("ajouter_equipements_serie", {"type": "PM", "se": "00", "quantite": 5, "libelle": "Pompe de relevage"})
        self.assertEqual(len(r["idents"]), 5)
        self.assertEqual(self.numeros("PM"), ["01", "02", "03", "04", "05"])
        self.assertEqual(len(set(r["reperes"])), 5)
        self.assertTrue(all(e.libelle == "Pompe de relevage" for e in self.app.s.ouvrage.equipements))

    def test_numeros_deja_pris_sont_sautes_et_depart_respecte(self):
        self.app.appeler("ajouter_equipement", {"type": "PM", "numero": "02", "se": "00"})
        self.app.appeler("ajouter_equipements_serie", {"type": "PM", "se": "00", "quantite": 3})
        self.assertEqual(self.numeros("PM"), ["01", "02", "03", "04"])
        self.app.appeler("ajouter_equipements_serie", {"type": "HV", "se": "00", "quantite": 2, "depart": 10})
        self.assertEqual(self.numeros("HV"), ["10", "11"])

    def test_tout_ou_rien(self):
        avant = len(self.app.s.ouvrage.equipements)
        with self.assertRaisesRegex(RegleMetier, "Pas assez de numéros libres"):
            self.app.appeler("ajouter_equipements_serie", {"type": "PM", "se": "00", "quantite": 5, "depart": 97})
        self.assertEqual(len(self.app.s.ouvrage.equipements), avant)
        for quantite in (0, 51, -1, "x", None):
            with self.subTest(quantite=quantite), self.assertRaises(RegleMetier):
                self.app.appeler("ajouter_equipements_serie", {"type": "PM", "se": "00", "quantite": quantite})
        with self.assertRaises(RegleMetier):
            self.app.appeler("ajouter_equipements_serie", {"type": "ZZ", "se": "00", "quantite": 2})
        self.assertEqual(len(self.app.s.ouvrage.equipements), avant)

    def test_annulation_en_un_pas(self):
        self.app.appeler("ajouter_equipements_serie", {"type": "PM", "se": "00", "quantite": 4})
        self.assertEqual(self.app.historique_web()["annuler"], "création en série d'équipements")
        self.app.appeler("annuler", {})
        self.assertEqual(self.numeros("PM"), [])


if __name__ == "__main__":
    unittest.main()
