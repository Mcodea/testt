"""Décisions D3 / D4 du référentiel V2 : même suffixe pour la même information, `suffixe_es` limité aux collisions."""
import copy
import unittest

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, generer, generer_points, suffixe_physique
from genvar.session import Session

SUFFIXES = {"MV.ES_FDC_OUV": "OUV", "MV.ES_FDC_FER": "FER", "MV.ES_CONS_POS": "POS", "PM.ES_CMD_MA": "MA",
            "PM.ES_CONS_FREQ": "FREQ"}
FDC = {"CL.TS_OUV", "DJ.TS_FER", "EV.TS_OUV", "EV.TS_FER", "IS.TS_FER", "SV.TS_OUV", "SV.TS_FER", "XV.TS_OUV",
       "XV.TS_FER"}


def _cle(s):
    return f"{s['type']}.{s['famille']}_{s['code']}"


class TestReferentielLivre(unittest.TestCase):
    def setUp(self):
        self.cat = Catalogue.charger(chemins.fichier_catalogue_origine())

    def test_suffixe_es_seulement_sur_les_cinq_collisions(self):
        self.assertEqual({_cle(s): s["suffixe_es"] for s in self.cat.signaux if s.get("suffixe_es")}, SUFFIXES)

    def test_organe_fdc_retire_des_neuf_signaux_uniques(self):
        restants = {_cle(s) for s in self.cat.signaux if s.get("organe") == "FDC"}
        self.assertEqual(restants, set())
        for s in self.cat.signaux:
            if _cle(s) in FDC:
                self.assertEqual(suffixe_physique(s), s["code"])
                self.assertTrue(s["remarque"].startswith("Fin de course"))

    def test_aucune_collision_de_nom_physique(self):
        self.assertEqual(self.cat.anomalies(), [])

    def test_collision_et_suffixe_invalide_detectes(self):
        cat = copy.deepcopy(self.cat)
        for s in cat.signaux:
            if _cle(s) == "MV.ES_FDC_OUV":
                s["suffixe_es"] = "BP_OUV"                     # même nom physique que le bouton local
            if _cle(s) == "PM.ES_CMD_MA":
                s["suffixe_es"] = "ma-1"
        msg = cat.anomalies()
        self.assertTrue(any("serait le nom physique" in m for m in msg))
        self.assertTrue(any("suffixe ES « ma-1 »" in m for m in msg))


class TestNomsGeneres(unittest.TestCase):
    def _ouvrage(self, cat):
        s = Session(cat)
        s.nouveau(False)
        s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
        s.ajouter_sous_ensemble("00")
        for t in ("MV", "PM", "EV"):
            eq = s.ajouter_equipement(Equipement("00", t, "01"))
            eq.options = list(next(x for x in cat.types if x["code"] == t).get("options", []))
            s.decider_propositions(eq.ident, "retenir")
        return s

    def test_meme_suffixe_physique_et_fonctionnel(self):
        s = self._ouvrage(Catalogue.charger(chemins.fichier_catalogue_origine()))
        points = {p.nom: p for p in generer_points(s.ouvrage, s.catalogue)}
        noms = {v.nom for v in generer(s.ouvrage, s.catalogue)}
        for physique, fonctionnel in (("ET_RV01MV01_OUV", "TS_RV01MV01_OUV"),
                                      ("ET_RV01MV01_FER", "TS_RV01MV01_FER"),
                                      ("ST_RV01MV01_OUV", "TC_RV01MV01_OUV"),
                                      ("ET_RV01EV01_OUV", "TS_RV01EV01_OUV")):
            self.assertIn(physique, points, sorted(points))
            self.assertIn(fonctionnel, noms)
        self.assertNotIn("ET_RV01MV01_FDC_OUV", points)
        self.assertEqual(points["ET_RV01MV01_OUV"].cle, "ES_FDC_OUV")       # identifiant interne inchangé
        self.assertEqual(len(points), len({p.nom for p in points.values()}))

    def test_projet_existant_garde_ses_noms(self):
        ancien = Catalogue.charger(chemins.fichier_catalogue_origine())
        for x in ancien.signaux:
            x.pop("suffixe_es", None)
            if _cle(x) in FDC:
                x["organe"] = "FDC"
        s = self._ouvrage(ancien)
        points = {p.nom for p in generer_points(s.ouvrage, s.catalogue)}
        self.assertIn("ET_RV01MV01_FDC_OUV", points)
        self.assertIn("ET_RV01EV01_FDC_OUV", points)
