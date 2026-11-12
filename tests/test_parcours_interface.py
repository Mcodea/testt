"""Avancement du parcours affiché par l'interface (module sans Qt : exécuté partout)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, VariableExistante
from genvar.session import Session
from genvar_qt import parcours


class TestParcours(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = tempfile.mkdtemp()
        self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def test_ouvrage_vide_recommande_la_fiche(self):
        av = parcours.calculer(self.s)
        self.assertEqual([e.nom for e in av.etapes], list(parcours.PARCOURS_NEUF))
        self.assertEqual(av.prochaine().nom, "Ouvrage")
        self.assertEqual(av.faites, 0)
        self.assertEqual(sum(e.recommande for e in av.etapes), 1)

    def test_neuf_progression_et_adresses(self):
        s = self.s
        s.definir("lieu", "XT25"); s.definir("code_ouvrage", "RV"); s.definir("libelle", "Réservoir")
        s.ajouter_sous_ensemble("11", "Réservoir 1")
        s.ajouter_equipement(Equipement("11", "PM", "01"))
        av = parcours.calculer(s)
        self.assertEqual(av.etape("Ouvrage").etat, "fait")
        self.assertEqual(av.prochaine().nom, "E/S automate")       # la liste des E/S d'abord
        s.valider_es([(p.ident_eq, p.cle) for p in s.points()])
        av = parcours.calculer(s)
        self.assertEqual(av.etape("E/S automate").etat, "fait")
        self.assertEqual(av.prochaine().nom, "Variables")
        sans = sum(1 for v in s.variables() if not v.adresse)
        self.assertEqual(av.etape("Variables").badge, str(sans))
        props, erreurs = s.plan()
        s.appliquer(props)
        av = parcours.calculer(s)
        self.assertEqual(av.etape("Variables").etat, "fait")
        self.assertEqual(av.variables, len(s.variables()))
        b = s.bilan()
        self.assertEqual((av.erreurs, av.alertes), (b["erreurs"], b["alertes"]))

    def test_existant_suit_la_qualification(self):
        s = self.s
        s.definir("mode", "Existant")
        s.definir("lieu", "F999"); s.definir("code_ouvrage", "RV"); s.definir("libelle", "Essai")
        av = parcours.calculer(s)
        self.assertEqual([e.nom for e in av.etapes], list(parcours.PARCOURS_EXISTANT))
        self.assertEqual(av.prochaine().nom, "Projet existant")
        s.ouvrage.existantes = [VariableExistante("TS_F999RV21PM02_MA", "BOOL", "%MW10.0")]
        self.assertIn("équipements", parcours.calculer(s).etape("Projet existant").detail)
        s.ajouter_detectes(s.equipements_detectes())
        self.assertIn("Construire", parcours.calculer(s).etape("Projet existant").detail)
        s.construire_table()
        etape = parcours.calculer(s).etape("Projet existant")
        self.assertEqual(etape.etat, "a_faire")
        self.assertEqual(etape.badge, str(len(s.ouvrage.table_tt)))   # toutes les lignes sont à traiter
        self.assertEqual(parcours.calculer(s).variables, 1)


if __name__ == "__main__":
    unittest.main()
