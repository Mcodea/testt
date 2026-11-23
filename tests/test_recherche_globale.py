"""Recherche globale par repère, variable, adresse et libellé (cahier V1-5-06). Ouvrage fictif (XTST)."""
import os
import tempfile
import unittest

from genvar import adressage
from sorep_web.serveur import Application


class TestRechercheGlobale(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-recherche-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.appeler("nouveau", {"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.appeler("fiche_ouvrage", {"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "45", "libelle": "Essai recherche",
            "automate": "Sch - M580", "revision": "A"}})
        i = app.appeler("ajouter_equipement", {"type": "PM", "numero": "01", "se": "00", "libelle": "Pompe Bellevue"})["ident"]
        app.appeler("decider_proposition", {"ident_eq": i, "decision": "retenir"})
        app.s.appliquer_adressage(adressage.calculer(app.s).empreinte, ("automate",))
        self.ident = i

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def chercher(self, q):
        return self.app.recherche_globale({"q": q})["resultats"]

    def test_par_repere(self):
        r = self.chercher("pm01")
        self.assertTrue(any(x["nature"] == "equipement" and x["ident_eq"] == self.ident and x["critere"] == "repère" for x in r), r)

    def test_par_libelle(self):
        r = self.chercher("bellevue")
        self.assertTrue(any(x["nature"] == "equipement" and x["critere"] == "libellé" for x in r), r)

    def test_par_nom_de_variable(self):
        r = self.chercher("TS_RV45PM01_MA")
        self.assertTrue(any(x["nature"] == "variable" and x["titre"] == "TS_RV45PM01_MA" and x["critere"] == "variable" for x in r), r)

    def test_par_adresse(self):
        v = next(v for v in self.app.s.variables() if v.adresse)
        r = self.chercher(v.adresse.lower())
        self.assertTrue(any(x["nature"] == "variable" and x["critere"] == "adresse" and x["titre"] == v.nom for x in r), (v.adresse, r))

    def test_garde_fous(self):
        self.assertEqual(self.chercher("p"), [])                       # deux caractères au moins
        self.assertEqual(self.chercher("zzzzzz"), [])
        r = self.app.recherche_globale({"q": "ts_"})
        self.assertLessEqual(len(r["resultats"]), 30)                   # résultats bornés
        self.assertEqual(r["complet"], r["total"] <= 30)
        self.app.appeler("fermer", {})
        self.assertEqual(self.chercher("pm01"), [])                    # aucun ouvrage ouvert : rien


if __name__ == "__main__":
    unittest.main()
