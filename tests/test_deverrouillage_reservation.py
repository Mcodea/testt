"""Déverrouiller (avec motif) et réserver depuis le détail d'une variable (cahier V1-4-42). Ouvrage fictif (XTST)."""
import os
import tempfile
import unittest

from genvar import adressage
from sorep_web.serveur import Application, RegleMetier


class TestDeverrouillageEtReservation(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-deverr-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.appeler("nouveau", {"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.appeler("fiche_ouvrage", {"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "52", "libelle": "Essai déverrouillage",
            "automate": "Sch - M580", "revision": "A"}})
        i = app.appeler("ajouter_equipement", {"type": "PM", "numero": "01", "se": "00"})["ident"]
        app.appeler("decider_proposition", {"ident_eq": i, "decision": "retenir"})
        s = app.s
        s.appliquer_adressage(adressage.calculer(s).empreinte, ("automate",))
        self.v = next(v for v in s.variables() if v.adresse)
        s.valider_affectations("automate", [(self.v.ident_eq, self.v.cle)])
        self.cle = {"ident_eq": self.v.ident_eq, "cle": self.v.cle}

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def courante(self):
        return next(v for v in self.app.s.variables() if v.ident_eq == self.v.ident_eq and v.cle == self.v.cle)

    def test_deverrouiller_exige_un_motif_et_n_altere_pas_l_adresse(self):
        adresse = self.v.adresse
        self.assertTrue(self.courante().adresse_validee)
        for motif in ("", "  ", "ab"):
            with self.subTest(motif=motif), self.assertRaisesRegex(RegleMetier, "motif"):
                self.app.appeler("variables_action", {"action": "deverrouiller", **self.cle, "motif": motif})
        self.app.appeler("variables_action", {"action": "deverrouiller", **self.cle, "motif": "Reprise après modification du programme"})
        c = self.courante()
        self.assertFalse(c.adresse_validee)
        self.assertEqual(c.adresse, adresse)                       # jamais modifiée : elle repasse « à valider »
        journal = self.app.s.ouvrage.journal_adressage[-1]
        self.assertEqual((journal["action"], journal["variable"], journal["motif"]),
                         ("déverrouillage", self.v.nom, "Reprise après modification du programme"))
        with self.assertRaisesRegex(RegleMetier, "rien à déverrouiller"):
            self.app.appeler("variables_action", {"action": "deverrouiller", **self.cle, "motif": "Encore"})

    def test_deverrouillage_annulable(self):
        self.app.appeler("variables_action", {"action": "deverrouiller", **self.cle, "motif": "Essai annulation"})
        self.assertFalse(self.courante().adresse_validee)
        self.app.appeler("annuler", {})
        self.assertTrue(self.courante().adresse_validee)

    def test_reserver_le_mot_de_la_variable(self):
        self.app.appeler("variables_action", {"action": "reserver", **self.cle, "motif": "Mot gardé pour l'exploitant"})
        reservations = self.app.s.ouvrage.reservations
        self.assertEqual(len(reservations), 1)
        self.assertEqual((reservations[0]["niveau"], reservations[0]["motif"]), ("memoire", "Mot gardé pour l'exploitant"))
        with self.assertRaisesRegex(RegleMetier, "déjà réservé"):
            self.app.appeler("variables_action", {"action": "reserver", **self.cle, "motif": "Doublon"})
        with self.assertRaisesRegex(RegleMetier, "motif"):
            sans = next(v for v in self.app.s.variables() if v.adresse and v.cle != self.v.cle)
            self.app.appeler("variables_action", {"action": "reserver", "ident_eq": sans.ident_eq, "cle": sans.cle, "motif": ""})

    def test_projet_existant_refuse(self):
        self.app.appeler("fermer", {})
        autre = Application()
        autre.appeler("nouveau", {"mode": "Existant"})
        with self.assertRaises(RegleMetier):
            autre.s.deverrouiller_adresse("x", "TS_MA", "motif valable")


if __name__ == "__main__":
    unittest.main()
