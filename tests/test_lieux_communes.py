"""Régression liste de communes, codification 4 caractères, migration sans perte."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from sorep_web import referentiel_ouvrage as ref
from sorep_web.serveur import Application
from genvar.session import RegleMetier


class TestCommunes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = patch.dict(os.environ, {"SOREP_DATA_DIR": self.tmp.name})
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def test_quinze_communes_regies_et_codes_uniques(self):
        lieux = ref.lire()["lieux"]
        self.assertEqual(len(lieux), 15)
        self.assertEqual(sum(x["regie"] == "ESB" for x in lieux), 11)
        self.assertEqual(sum(x["regie"] == "RESO" for x in lieux), 4)
        self.assertEqual(len({x["code"] for x in lieux}), 15)
        self.assertTrue(all(len(x["code"]) == 4 and x["code"].isalpha() for x in lieux))
        self.assertEqual(next(x for x in lieux if x["libelle"] == "Morangis")["code"], "MRGS")

    def test_lieu_exemple_morg_repere(self):
        app = Application()
        app.nouveau({"mode": "Neuf"})
        app.identifier_selection({"champ": "lieu", "valeur": "MRGS"})
        app.identifier_type({"code": "RV"})
        self.assertEqual(app.ouvrage({})["prefixe"], "MRGSRV")
        self.assertEqual(app.ouvrage({})["equipements"], [])

    def test_lieu_personnalise_rattache_a_regie(self):
        result = ref.modifier("ajouter", "lieux", "ZZZZ", "Lieu complémentaire", regie="RESO")
        self.assertIn({"code": "ZZZZ", "libelle": "Lieu complémentaire", "regie": "RESO"}, result["lieux"])
        with self.assertRaises(RegleMetier):
            ref.modifier("ajouter", "lieux", "TROP-LONG", "Lieu invalide")
        with self.assertRaises(RegleMetier):
            ref.modifier("ajouter", "lieux", "ABCD", "Lieu 2", regie="INCONNUE")
        with self.assertRaises(RegleMetier):
            ref.modifier("ajouter", "lieux", "ABCD", "Arcueil")

    def test_migration_v1_ajoute_sans_remplacer(self):
        os.makedirs(os.path.dirname(ref.chemin()), exist_ok=True)
        with open(ref.chemin(), "w", encoding="utf8") as f:
            json.dump({"version":1, "lieux":[{"code":"MRGS", "libelle":"Morangis personnalisé"},
                                              {"code":"PRIV", "libelle":"Lieu propre"}]}, f)
        result=ref.lire()
        self.assertEqual(result["version"], ref.VERSION)
        self.assertEqual(len(result["lieux"]), 16)  # 14 lieux ajoutés et 2 conservés
        self.assertEqual(next(x for x in result["lieux"] if x["code"] == "MRGS")["libelle"], "Morangis personnalisé")
        self.assertIn("PRIV", {x["code"] for x in result["lieux"]})
        self.assertEqual(len(ref.lire()["lieux"]), 16)

    def test_une_suppression_ne_reapparait_pas(self):
        ref.modifier("supprimer", "lieux", ancien="VLJF")
        self.assertNotIn("VLJF", {x["code"] for x in ref.lire()["lieux"]})
        self.assertEqual(ref.lire()["version"], ref.VERSION)

    def test_ancienne_valeur_lieu_reste_dans_projet(self):
        app=Application()
        app.nouveau({"mode":"Neuf"})
        app.identifier_selection({"champ":"lieu", "valeur":"ORLY"})
        app.identifier_type({"code":"RV"})
        ref.modifier("modifier", "lieux", "ORLI", "Orly", ancien="ORLY", regie="ESB")
        self.assertEqual(app.ouvrage({})["identification"]["lieu"], "ORLY")
        self.assertEqual(app.ouvrage({})["prefixe"], "ORLYRV")
        with self.assertRaises(RegleMetier):
            app.identifier_selection({"champ":"lieu", "valeur":"ORLY"})

if __name__ == "__main__":
    unittest.main()
