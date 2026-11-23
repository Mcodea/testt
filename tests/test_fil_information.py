"""Fil de l'information d'un équipement (refonte de l'interface, lot 4) : état de chaque maillon, lecture seule.
Données fictives (lieu XTST)."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genvar.session import RegleMetier  # noqa: E402
from sorep_web.serveur import Application  # noqa: E402
from tests.test_audit_16_11 import _Base  # noqa: E402


class TestFilInformation(_Base):
    def setUp(self):
        super().setUp()
        self.app = Application()
        self.ouvrage(self.app)

    def test_equipement_non_valide_et_inconnu(self):
        ident = self.app.ajouter_equipement({"type": "PM", "numero": "01", "se": "00"})["ident"]
        fil = self.app.fil_web({"ident": ident})
        self.assertEqual(fil["repere"], "XTSTRV01PM01")
        self.assertEqual(fil["equipement"], {"etat": "al", "titre": "Équipement PM01", "detail": "paramétrage à valider"})
        self.assertEqual(fil["es"]["detail"], "après validation de l'équipement")
        self.assertEqual(fil["variables"]["etat"], "")
        with self.assertRaisesRegex(RegleMetier, "introuvable"):
            self.app.fil_web({"ident": "inconnu"})

    def test_chaine_complete_et_lecture_seule(self):
        ids = self.equipements_valides(self.app, types=("PM",))
        avant = json.dumps(self.app.s.ouvrage.vers_dict(), sort_keys=True, default=str)
        fil = self.app.fil_web({"ident": ids[0]})
        self.assertEqual(json.dumps(self.app.s.ouvrage.vers_dict(), sort_keys=True, default=str), avant, "Lecture seule")
        self.assertEqual(fil["equipement"]["etat"], "ok")
        self.assertEqual((fil["es"]["etat"], fil["es"]["detail"]), ("ok", "contenu validé"))
        self.assertTrue(fil["es"]["titre"].endswith("E/S physiques"))
        self.assertEqual(fil["carte"]["detail"].split()[1:], ["E/S", "sans", "voie"], "Matériel pas encore calculé")
        self.assertEqual(fil["variables"]["etat"], "al")
        self.assertIn("à valider", fil["variables"]["detail"])
        self.assertEqual(fil["nom_court"], "RV01PM01")
        # Matériel calculé et voies implantées : la carte et les voies apparaissent en plages
        self.app.materiel_action({"action": "appliquer"})
        self.app.modules_action({"action": "implanter"})
        fil = self.app.fil_web({"ident": ids[0]})
        self.assertRegex(fil["carte"]["titre"], r"^Carte \d+\.\d+ · voies \d+ à \d+$")
        self.assertEqual(fil["carte"]["detail"], f"{len([p for p in self.app.s.points() if p.ident_eq == ids[0]])} voie(s) à valider")

    def test_detail_une_ligne_par_information(self):
        ids = self.equipements_valides(self.app, types=("PM",))
        fil = self.app.fil_web({"ident": ids[0], "detail": "1"})
        variables = [v for v in self.app.s.variables() if v.ident_eq == ids[0]]
        self.assertGreaterEqual(len(fil["lignes"]), len(variables))
        self.assertEqual({x["variable"] for x in fil["lignes"] if x["variable"]}, {v.nom for v in variables})
        cablees = [x for x in fil["lignes"] if x["es"] and x["variable"]]
        self.assertTrue(cablees, "Au moins une variable lit une E/S câblée")
        self.assertTrue(all(x["etat"] in ("validée", "à valider", "sans adresse", "E/S seule") for x in fil["lignes"]))
        self.assertNotIn("lignes", self.app.fil_web({"ident": ids[0]}), "Détail seulement sur demande")

    def test_plages_de_voies(self):
        self.assertEqual(Application._plages_voies(["0", "1", "2", "5", "7", "8"]), "0 à 2, 5, 7 à 8")
        self.assertEqual(Application._plages_voies(["3"]), "3")
        self.assertEqual(Application._plages_voies([]), "")


if __name__ == "__main__":
    unittest.main()
