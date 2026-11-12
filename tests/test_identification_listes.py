"""Recette du panneau d'identification : données contrôlées, projets préservés."""
import os
import tempfile
import unittest
from unittest.mock import patch

from genvar.modele import Equipement
from genvar.session import RegleMetier
from sorep_web.serveur import Application
from sorep_web import referentiel_ouvrage as ref


class TestListesIdentification(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SOREP_DATA_DIR": self.temp.name})
        self.env.start()
        self.app = Application()
        self.app.nouveau({"mode": "Neuf"})

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_ouvrages_sans_lieu_precharge_ni_automate_impose(self):
        self.assertEqual(self.app.ouvrage({})["identification"]["lieu"], "")
        self.assertEqual(self.app.ouvrage({})["identification"]["automate"], "")
        self.assertEqual(len(ref.lire()["lieux"]), 15)
        self.assertTrue(ref.lire()["types_ouvrage"])
        self.assertFalse(os.path.isfile(ref.chemin()))

    def test_ajout_selection_et_persistance_du_lieu(self):
        self.app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "TEST", "libelle": "Lieu d'essai"})
        self.app.identifier_selection({"champ": "lieu", "valeur": "TEST"})
        self.assertEqual(self.app.ouvrage({})["identification"]["lieu"], "TEST")
        self.assertIn({"code": "TEST", "libelle": "Lieu d'essai", "regie": "AUTRE"}, ref.lire()["lieux"])
        self.assertTrue(os.path.isfile(ref.chemin()))

    def test_refus_valeurs_inconnues_et_codes_invalides(self):
        with self.assertRaises(RegleMetier):
            self.app.identifier_selection({"champ": "lieu", "valeur": "XXXX"})
        with self.assertRaises(RegleMetier):
            self.app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "TST", "libelle": "Invalide"})
        with self.assertRaises(RegleMetier):
            self.app.listes_ouvrage_action({"action": "ajouter", "groupe": "types_ouvrage", "code": "123", "libelle": "Invalide"})
        with self.assertRaises(RegleMetier):
            self.app.identifier_selection({"champ": "automate", "valeur": "M999"})
        self.assertEqual(self.app.ouvrage({})["identification"]["lieu"], "")

    def test_type_met_a_jour_code_et_libelle_ensemble(self):
        self.app.identifier_type({"code": "RV"})
        i = self.app.ouvrage({})["identification"]
        self.assertEqual((i["code_ouvrage"], i["type_ouvrage"]), ("RV", "Réservoir"))
        self.app.identifier_type({"code": "SP"})
        i = self.app.ouvrage({})["identification"]
        self.assertEqual((i["code_ouvrage"], i["type_ouvrage"]), ("SP", "Station de pompage"))
        with self.assertRaises(RegleMetier):
            self.app.identifier_type({"code": "ZZ"})
        self.assertEqual(self.app.ouvrage({})["identification"]["code_ouvrage"], "SP")

    def test_code_existant_avec_equipements_exige_confirmation(self):
        self.app.s.ouvrage.equipements.append(Equipement("11", "HV", "01", "Vanne fictive"))
        with self.assertRaisesRegex(RegleMetier, "confirmation"):
            self.app.identifier_type({"code": "RV"})
        self.assertEqual(self.app.s.ouvrage.code_ouvrage, "")
        self.app.identifier_type({"code": "RV", "confirmer_changement": True})
        self.assertEqual(self.app.s.ouvrage.code_ouvrage, "RV")

    def test_protocoles_multiple_et_sans_doublons(self):
        self.app.identifier_selection({"champ": "communication", "valeurs": ["Modbus TCP", "SOFREL S4W", "Modbus TCP"]})
        self.assertEqual(self.app.s.ouvrage.communication, "Modbus TCP, SOFREL S4W")
        with self.assertRaises(RegleMetier):
            self.app.identifier_selection({"champ": "communication", "valeurs": ["Nouveau protocole non déclaré"]})
        self.assertEqual(self.app.s.ouvrage.communication, "Modbus TCP, SOFREL S4W")

    def test_referentiel_modifiable_sans_modifier_projet(self):
        self.app.identifier_type({"code": "RV"})
        self.app.listes_ouvrage_action({"action": "modifier", "groupe": "types_ouvrage", "ancien": "RV", "code": "RV", "libelle": "Réservoir modifié"})
        self.assertEqual(self.app.s.ouvrage.type_ouvrage, "Réservoir")
        self.assertEqual(ref.type_par_code("RV")["libelle"], "Réservoir modifié")
        self.app.listes_ouvrage_action({"action": "supprimer", "groupe": "types_ouvrage", "ancien": "RV"})
        self.assertEqual(self.app.s.ouvrage.code_ouvrage, "RV")
        self.assertEqual(self.app.s.ouvrage.type_ouvrage, "Réservoir")
        with self.assertRaises(RegleMetier):
            self.app.identifier_type({"code": "RV"})

    def test_refus_liste_endommagee_sans_ecrasement(self):
        with open(ref.chemin(), "w", encoding="utf8") as f:
            f.write("{invalide")
        with self.assertRaisesRegex(RegleMetier, "illisible"):
            ref.lire()
        with open(ref.chemin(), encoding="utf8") as f:
            self.assertEqual(f.read(), "{invalide")

    def test_revision_reste_saisie_manuellement(self):
        self.assertEqual(self.app.s.ouvrage.revision, "A")
        self.app.identifier_type({"code": "RV"})
        self.assertEqual(self.app.s.ouvrage.revision, "A")


if __name__ == "__main__":
    unittest.main()
