"""Tests de la couche Session (moteur sans interface)."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, SignalPropre
from genvar.session import Session, RegleMetier


class TestSession(unittest.TestCase):
    def setUp(self):
        self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        self.s.definir("lieu", "xt25"); self.s.definir("code_ouvrage", "rv")
        self.s.ajouter_sous_ensemble("11", "Réservoir 1")

    def test_identification_en_majuscules(self):
        self.assertEqual((self.s.ouvrage.lieu, self.s.ouvrage.code_ouvrage), ("XT25", "RV"))
        self.assertTrue(self.s.modifie)

    def test_sous_ensembles(self):
        with self.assertRaises(RegleMetier):
            self.s.ajouter_sous_ensemble("11")
        with self.assertRaises(RegleMetier):
            self.s.ajouter_sous_ensemble("1")
        self.s.ajouter_equipement(Equipement("11", "PM", "01"))
        with self.assertRaises(RegleMetier):
            self.s.supprimer_sous_ensemble("11")
        self.s.modifier_sous_ensemble("11", "12", "Réservoir 2")
        self.assertEqual(self.s.ouvrage.equipements[0].sous_ensemble, "12")

    def test_equipements(self):
        eq = self.s.ajouter_equipement(Equipement("11", "PM", "01", options=["Variateur"]))
        with self.assertRaises(RegleMetier):
            self.s.ajouter_equipement(Equipement("11", "PM", "01"))       # repère en double
        with self.assertRaises(RegleMetier):
            self.s.ajouter_equipement(Equipement("11", "ZZ", "01"))       # type inconnu
        copie = self.s.copie_pour_duplication(eq.ident)
        self.assertEqual(copie.numero, "02")
        self.s.ajouter_equipement(copie)
        self.assertEqual(len(self.s.ouvrage.equipements), 2)

    def test_basculer_et_option(self):
        eq = Equipement("11", "PM", "01")
        lignes = self.s.signaux_proposes(eq)
        tc = next(s for s, *_ in lignes if s["famille"] == "TC" and s["code"] == "AUTO")
        with self.assertRaises(RegleMetier):
            Session.basculer_signal(eq, tc)                          # option non cochée
        hs = next(s for s, *_ in lignes if s["code"] == "HS")
        Session.basculer_signal(eq, hs)
        self.assertIn("TS_HS", eq.exclus)

    def test_signal_propre_et_sens(self):
        with self.assertRaises(RegleMetier):
            Session.verifier_signal_propre(SignalPropre("Essai", "TM", "ESSAI", "REAL", es="SA"))
        Session.verifier_signal_propre(SignalPropre("Essai", "TR", "ESSAI", "REAL", es="SA"))

    def test_plan_et_export(self):
        self.s.ajouter_equipement(Equipement("11", "PM", "01", options=["Variateur"]))
        props, err = self.s.plan()
        self.assertTrue(props and not err)
        self.assertTrue(self.s.manque_adresses())
        self.s.appliquer(props)
        self.assertFalse(self.s.manque_adresses())
        r = self.s.recap_export()
        self.assertEqual(r.avec_adresse, 0)
        self.assertEqual(len(r.sans_adresse), r.points)
        v = self.s.variables()[0]
        with self.assertRaises(RegleMetier):
            self.s.definir_adresses(v.ident_eq, v.cle, adresse="MW12")
        self.s.definir_adresses(v.ident_eq, v.cle, adresse_es="%i0.3.5")
        self.assertEqual(self.s.ouvrage.equipements[0].adresses_es[v.cle_es], "%I0.3.5")   # clé de l'E/S source
        with tempfile.TemporaryDirectory() as d:
            n = self.s.exporter_xsy(os.path.join(d, "t.xsy"))
            self.s.exporter_excel(os.path.join(d, "t.xlsx"))
            self.s.enregistrer(os.path.join(d, "o.ouvrage.json"))
            self.assertFalse(self.s.modifie)
            s2 = Session(self.s.catalogue); s2.ouvrir(os.path.join(d, "o.ouvrage.json"))
        self.assertEqual([x.nom for x in s2.variables()], [x.nom for x in self.s.variables()])
        self.assertEqual(n, len(self.s.variables()) + 1)

    def test_anomalies_par_variable(self):
        self.s.ajouter_equipement(Equipement("11", "PM", "01"))
        v = self.s.variables()
        a = Session.anomalies_par_variable(v, self.s.anomalies(v))
        self.assertEqual(a.get("TS_XT25RV11PM01_MA"), "Erreur")         # pas encore d'adresse
        self.assertEqual(a.get("ET_XT25RV11PM01_MA"), "Alerte")         # adresse physique à renseigner


if __name__ == "__main__":
    unittest.main()
