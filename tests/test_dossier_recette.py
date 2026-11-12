"""Retour d'essai n° 11 (12/11/2026) : dossier de recette assemblé à partir des exports existants."""
import os
import tempfile
import unittest
import zipfile

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.session import Session


def _ouvrage(automate="BMXP342020"):
    s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
    s.nouveau(False)
    s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
    s.ouvrage.libelle = "Essai recette"; s.ouvrage.automate = automate
    s.ajouter_sous_ensemble("00")
    eq = s.ajouter_equipement(Equipement("00", "MV", "01"))
    s.decider_propositions(eq.ident, "retenir")
    s.valider_equipements([eq.ident])
    props, _ = s.plan(); s.appliquer(props)
    return s


class TestDossierRecette(unittest.TestCase):
    def setUp(self):
        self.env = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = tempfile.mkdtemp()
        self.zip = os.path.join(tempfile.mkdtemp(), "recette.zip")

    def tearDown(self):
        if self.env is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.env

    def test_pieces_et_sommaire(self):
        s = _ouvrage()
        m = s.dossier_recette(self.zip)
        noms = zipfile.ZipFile(self.zip).namelist()
        self.assertIn("00_sommaire.html", noms)
        for p in m["pieces"]:
            self.assertIn(p["fichier"], noms)
            self.assertEqual(len(p["sha256"]), 64)
        self.assertTrue({"01_equipements.xlsx", "02_liste_es.xlsx", "04_variables.xlsx"} <= set(noms))
        sommaire = zipfile.ZipFile(self.zip).read("00_sommaire.html").decode("utf-8")
        self.assertIn("non qualifiés", sommaire)
        self.assertIn("Aucun échange inter-automates déclaré", sommaire)
        self.assertIn("RV01", sommaire)

    def test_piece_impossible_signalee_avec_son_motif_jamais_inventee(self):
        s = _ouvrage()
        m = s.dossier_recette(self.zip)
        noms = set(zipfile.ZipFile(self.zip).namelist())
        for p in m["non_produites"]:
            self.assertNotIn(p["fichier"], noms)
            self.assertTrue(p["motif"])
        self.assertNotIn("03_cartes_es.xlsx", noms)          # matériel non retenu : pièce absente, pas inventée
