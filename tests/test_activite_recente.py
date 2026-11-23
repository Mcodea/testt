"""Activité récente du tableau de bord (cahier V1-4-33) : uniquement des faits enregistrés. Ouvrage fictif (XTST)."""
import os
import tempfile
import unittest

from genvar import adressage
from sorep_web.serveur import Application, RegleMetier


class TestActiviteRecente(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-activite-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.appeler("nouveau", {"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.appeler("fiche_ouvrage", {"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "46", "libelle": "Essai activité",
            "automate": "Sch - M580", "revision": "A"}})
        self.ident = app.appeler("ajouter_equipement", {"type": "PM", "numero": "01", "se": "00"})["ident"]
        app.appeler("decider_proposition", {"ident_eq": self.ident, "decision": "retenir"})

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def test_ouvrage_neuf_sans_fait_n_affiche_rien(self):
        self.assertEqual(self.app.activite_recente({})["faits"], [])

    def test_indices_copies_et_validations_sont_listes_du_plus_recent_au_plus_ancien(self):
        s = self.app.s
        s.creer_copie("adressage")
        s.appliquer_adressage(adressage.calculer(s).empreinte, ("automate",))
        paires = [(v.ident_eq, v.cle) for v in s.variables() if v.adresse][:3]
        s.valider_affectations("automate", paires)
        s.livrer_indice("Première diffusion", "Essai")
        faits = self.app.activite_recente({})["faits"]
        natures = [f["nature"] for f in faits]
        self.assertEqual(set(natures), {"copie", "indice", "validation"})      # l adressage appliqué écrit aussi sa copie
        indice = next(f for f in faits if f["nature"] == "indice")
        self.assertIn("Indice A livré : Première diffusion", indice["texte"])
        validation = next(f for f in faits if f["nature"] == "validation")
        self.assertTrue(validation["texte"].startswith("3 adresse(s) automate validée(s)"), validation)
        self.assertEqual([f["quand"] for f in faits], sorted((f["quand"] for f in faits), reverse=True))

    def test_borne_et_sans_ouvrage(self):
        for _ in range(12):
            self.app.s.creer_copie("adressage")
        r = self.app.activite_recente({})
        self.assertLessEqual(len(r["faits"]), 8)
        self.app.appeler("fermer", {})
        with self.assertRaises(RegleMetier):
            self.app.activite_recente({})


if __name__ == "__main__":
    unittest.main()
