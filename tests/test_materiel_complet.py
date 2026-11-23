"""Matériel M340 / M580 complet (12/11/2026) : alimentation, processeur, communication, cartes au choix,
extension de rack et nomenclature de commande, à partir du catalogue Schneider sourcé."""
import unittest

from genvar import chemins, materiel
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, PointES
from genvar.session import RegleMetier, Session


def _pts(nature, n):
    return [PointES("e1", "RV01PM01", nature, f"{nature}{i}", "EBOOL", "", "", "", f"C{nature}{i}") for i in range(n)]


class TestCatalogue(unittest.TestCase):
    def test_elements_sources(self):
        cat = materiel.catalogue()
        self.assertGreaterEqual(len(cat["cartes"]), 20)
        self.assertTrue(all(c.get("source") for c in cat["cartes"]))
        self.assertIn("BMX CPS 3500", [a["reference"] for a in cat["alimentations"]])
        self.assertIn("BMX P34 2020", [c["reference"] for c in cat["processeurs"]["M340"]])
        self.assertIn("BMX NOE 0100", [c["reference"] for c in cat["communication"]["M340"]])
        self.assertEqual(cat["_cartes"]["BMX DRA 1605"]["nature"], "ST")
        self.assertEqual(cat["_cartes"]["BMX ART 0414"]["nature"], "EA")


class TestProposition(unittest.TestCase):
    def test_processeur_deduit_du_champ_automate_et_choix_absents_signales(self):
        p = materiel.proposer(_pts("ET", 10), "BMXP342020")
        r0 = p.racks[0]
        self.assertEqual(r0["occupation"][0], {"position": 0, "reference": "BMX P34 2020", "role": "processeur"})
        self.assertEqual(r0["alimentation"], "Alimentation à choisir")
        self.assertTrue(any("Alimentation à choisir" in r for r in p.remarques))
        self.assertTrue(any("Bilan de consommation" in r for r in p.remarques))

    def test_communication_avant_les_cartes_et_carte_choisie(self):
        config = {"alimentation": "BMX CPS 3500", "communication": ["BMX NOE 0100"], "cartes": {"ST": "BMX DRA 1605"}}
        p = materiel.proposer(_pts("ET", 10) + _pts("ST", 10), "BMX P34 2000", config=config)
        r0 = p.racks[0]
        self.assertEqual([(o["position"], o["role"]) for o in r0["occupation"]], [(0, "processeur"), (1, "communication")])
        self.assertEqual(r0["cpu"], [0, 1])
        self.assertTrue(all(m["position"] >= 2 for m in p.modules))
        self.assertIn("BMX DRA 1605", [m["reference"] for m in p.modules])
        self.assertEqual(r0["alimentation"], "BMX CPS 3500")

    def test_m580_processeur_sur_deux_emplacements(self):
        p = materiel.proposer(_pts("ET", 10), "BMEP582040")
        self.assertEqual([o["position"] for o in p.racks[0]["occupation"]], [0, 1])

    def test_nomenclature_avec_extension(self):
        config = {"alimentation": "BMX CPS 2010", "processeur": "BMX P34 2000"}
        p = materiel.proposer(_pts("ET", 700), "M340", config=config)
        self.assertEqual(len(p.racks), 2)
        n = {x["reference"]: x["quantite"] for x in materiel.nomenclature(p.racks, p.modules)}
        self.assertEqual(n["BMX CPS 2010"], 2)                        # une alimentation par rack
        self.assertEqual(n["BMX P34 2000"], 1)
        self.assertEqual(n["BMX XBE 1000"], 2)
        self.assertEqual(n["TSX TLY EX"], 2)
        self.assertEqual(sum(q for r, q in n.items() if r.startswith("BMX DDI")), len(p.modules))


class TestSession(unittest.TestCase):
    def setUp(self):
        self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        self.s.nouveau(False)
        self.s.definir("lieu", "XTST"); self.s.definir("code_ouvrage", "RV"); self.s.ouvrage.numero_ouvrage = "01"
        self.s.ouvrage.automate = "BMXP342020"; self.s.ajouter_sous_ensemble("00")
        e = self.s.ajouter_equipement(Equipement("00", "PM", "01"))
        self.s.decider_propositions(e.ident, "retenir")
        self.s.valider_contenu_es([(p.ident_eq, p.cle) for p in self.s.points()])

    def test_choix_controles_puis_appliques(self):
        with self.assertRaises(RegleMetier):
            self.s.definir_config_materiel(alimentation="BMX CPS 9999")
        with self.assertRaises(RegleMetier):
            self.s.definir_config_materiel(cartes={"ET": "BMX DDO 1602"})      # mauvaise nature
        self.s.definir_config_materiel(alimentation="BMXCPS3500", communication=["BMX NOM 0200"])
        self.assertEqual(self.s.ouvrage.materiel_config["alimentation"], "BMX CPS 3500")
        self.s.appliquer_materiel()
        nom = {x["reference"]: x for x in self.s.nomenclature_materiel()}
        self.assertEqual(nom["BMX CPS 3500"]["role"], "alimentation")
        self.assertEqual(nom["BMX NOM 0200"]["role"], "communication")
        self.assertEqual(nom["BMX P34 2020"]["role"], "processeur")

    def test_export_nomenclature(self):
        import os
        import tempfile
        self.s.appliquer_materiel()
        chemin = os.path.join(tempfile.mkdtemp(), "n.xlsx")
        self.s.exporter_nomenclature(chemin)
        self.assertGreater(os.path.getsize(chemin), 0)


if __name__ == "__main__":
    unittest.main()
