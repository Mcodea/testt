"""Structure Ouvrage → UF → équipements : l'UF porte le sous-ensemble proposé aux équipements."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.session import Session, RegleMetier


class TestStructureOuvrage(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = tempfile.mkdtemp()
        s = self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s.definir("lieu", "VLJF"); s.definir("code_ouvrage", "RV"); s.definir("libelle", "Réservoir")

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def test_uf_cree_son_sous_ensemble(self):
        s = self.s
        s.ajouter_uf("UF01", "Stockage", "11")
        self.assertEqual([(x.code, x.libelle) for x in s.ouvrage.sous_ensembles], [("11", "Stockage")])
        eq = s.equipement_vierge(uf="UF01")
        self.assertEqual((eq.uf, eq.sous_ensemble), ("UF01", "11"))
        eq.type = "MV"
        s.ajouter_equipement(eq)
        self.assertEqual(s.ouvrage.repere(eq), "VLJFRV11MV01")

    def test_deux_uf_meme_sous_ensemble(self):
        s = self.s
        s.ajouter_uf("UF01", "Stockage", "11")
        s.ajouter_uf("UF02", "Distribution", "11")              # autorisé : le repère ne contient pas l'UF
        self.assertEqual(len(s.ouvrage.sous_ensembles), 1)

    def test_changer_le_sous_ensemble_ne_renomme_rien(self):
        s = self.s
        s.ajouter_uf("UF01", "Stockage", "11")
        eq = s.equipement_vierge(uf="UF01"); eq.type = "MV"
        s.ajouter_equipement(eq)
        s.modifier_uf("UF01", "UF01", "Stockage", "21")
        self.assertEqual(s.ouvrage.repere(eq), "VLJFRV11MV01")   # l'existant ne bouge pas
        self.assertEqual(s.equipement_vierge(uf="UF01").sous_ensemble, "21")

    def test_uf_sans_sous_ensemble_et_code_invalide(self):
        s = self.s
        s.ajouter_uf("UF01", "Stockage")
        self.assertEqual(s.ouvrage.sous_ensembles, [])
        with self.assertRaises(RegleMetier):
            s.ajouter_uf("UF02", "Distribution", "1")
        self.assertEqual([u.code for u in s.ouvrage.unites], ["UF01"])

    def test_equipements_communs(self):
        s = self.s
        s.ajouter_uf("UF01", "Stockage", "11")
        eq = s.equipement_vierge(); eq.type = "AR"
        s.ajouter_equipement(eq)
        self.assertEqual(s.equipements_communs(), [eq])
        self.assertEqual(s.libelle_communs(), "Équipements communs (hors UF)")
        s.renommer_communs("Armoire de commande")
        self.assertEqual(s.libelle_communs(), "Armoire de commande")
        s.affecter_uf({eq.ident}, "UF01")                         # « ranger dans une UF »
        self.assertEqual(s.equipements_communs(), [])
        s.supprimer_uf("UF01")                                    # l'équipement redevient commun
        self.assertEqual(s.equipements_communs(), [eq])
        chemin = os.path.join(os.environ["SOREP_DATA_DIR"], "c.ouvrage.json")
        s.enregistrer(chemin)
        s2 = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s2.ouvrir(chemin)
        self.assertEqual(s2.libelle_communs(), "Armoire de commande")

    def test_relecture_ancien_fichier(self):
        s = self.s
        s.ajouter_uf("UF01", "Stockage", "11")
        chemin = os.path.join(os.environ["SOREP_DATA_DIR"], "o.ouvrage.json")
        s.enregistrer(chemin)
        s2 = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s2.ouvrir(chemin)
        self.assertEqual(s2.ouvrage.unites[0].sous_ensemble, "11")


if __name__ == "__main__":
    unittest.main()
