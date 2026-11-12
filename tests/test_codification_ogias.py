"""Recette de la règle OGIAS lieu(4) + type(2) + numéro(2)."""
import os
import tempfile
import unittest
from unittest.mock import patch

from genvar import projets
from genvar.modele import Ouvrage, Equipement
from genvar.session import RegleMetier
from sorep_web.serveur import Application


class TestCodificationOGIAS(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SOREP_DATA_DIR": self.t.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.t.cleanup()

    def creer(self, numero, lieu="MRGS", typ="RP"):
        app = Application()
        app.nouveau({"mode": "Neuf"})
        ident = {"lieu": lieu, "code_ouvrage": typ, "numero_ouvrage": numero,
                 "libelle": "Ouvrage fictif", "automate": "", "revision": "A",
                 "localisation": "", "communication": ""}
        return app, app.fiche_ouvrage({"action": "creer", "identification": ident})

    def test_numeros_non_consecutifs_meme_lieu(self):
        self.creer("01")
        self.creer("02")
        self.creer("05")
        self.assertEqual({x.repere for x in projets.lister()}, {"MRGSRP01", "MRGSRP02", "MRGSRP05"})
        self.assertEqual(Application().numero_ouvrage_suggere({"lieu": "MRGS", "type": "RP"})["numero"], "06")
        self.assertEqual(Application().numero_ouvrage_suggere({"lieu": "MRGS", "type": "RV"})["numero"], "01")

    def test_doublon_verrouille_meme_archive(self):
        _, r = self.creer("05")
        projets.archiver(r["chemin"])
        app = Application()
        app.nouveau({"mode": "Neuf"})
        with self.assertRaisesRegex(RegleMetier, "utilise déjà"):
            app.fiche_ouvrage({"action": "creer", "identification": {
                "lieu": "MRGS", "code_ouvrage": "RP", "numero_ouvrage": "05",
                "libelle": "Second", "automate": "", "revision": "A",
                "localisation": "", "communication": ""}})
        self.assertEqual(Application().numero_ouvrage_suggere({"lieu": "MRGS", "type": "RP"})["numero"], "06")

    def test_reperes_anciens_preserves_et_nouveaux(self):
        o = Ouvrage(lieu="MRGS", code_ouvrage="RP")
        e = Equipement("11", "HV", "01")
        self.assertEqual(o.repere(e), "MRGSRP11HV01")
        path = projets.nom_libre("legacy")
        o.enregistrer(str(path))
        self.assertEqual(Ouvrage.ouvrir(str(path)).repere(e), "MRGSRP11HV01")
        o.numero_ouvrage = "05"
        self.assertEqual(o.repere(e), "MRGSRP0511HV01")

    def test_numero_invalide(self):
        for numero in ("00", "1", "100", "AA"):
            app=Application();app.nouveau({"mode":"Neuf"})
            with self.assertRaises(RegleMetier):
                app.fiche_ouvrage({"action":"creer","identification":{
                    "lieu":"MRGS", "code_ouvrage":"RP", "numero_ouvrage": numero,
                    "libelle":"Fictif", "automate":"", "revision":"A", "localisation":"", "communication":""}})

if __name__ == "__main__":
    unittest.main()
