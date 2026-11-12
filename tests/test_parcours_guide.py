"""Retours d'essai 4, 5 et 7 (12/11/2026) : points bloquants exhaustifs de chaque étape, avec leur cible."""
import unittest

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.session import Session


def _session(automate="BMXP342020"):
    s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
    s.nouveau(False)
    s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
    s.ouvrage.libelle = "Essai"; s.ouvrage.automate = automate
    s.ouvrage.statut = "En cours"
    s.ajouter_sous_ensemble("00")
    return s


def _codes(etape):
    return [p["code"] for p in etape["bloquants"]]


class TestParcours(unittest.TestCase):
    def test_ouvrage_vide_dit_exactement_ce_qui_manque(self):
        s = _session(automate="")
        s.ouvrage.libelle = ""
        e1 = s.parcours()[0]
        self.assertFalse(e1["pret"])
        self.assertIn("identification:automate", _codes(e1))
        self.assertIn("identification:libelle", _codes(e1))
        self.assertIn("aucun_equipement", _codes(e1))
        self.assertTrue(all(p["vue"] == "ouvrage" and p["message"] for p in e1["bloquants"]))

    def test_equipement_non_valide_cite_et_cible(self):
        s = _session()
        eq = s.ajouter_equipement(Equipement("00", "MV", "01"))
        e1 = s.parcours()[0]
        self.assertEqual(_codes(e1), ["equipement_a_valider"])
        self.assertEqual(e1["bloquants"][0]["ident_eq"], eq.ident)
        self.assertIn("MV01", e1["bloquants"][0]["message"])

    def test_etapes_suivantes_jamais_pretes_avant_les_precedentes(self):
        s = _session()
        s.ajouter_equipement(Equipement("00", "MV", "01"))
        etapes = s.parcours()
        self.assertEqual([e["vue"] for e in etapes], ["ouvrage", "es", "materiel", "variables", "recette"])
        self.assertFalse(any(e["pret"] for e in etapes))

    def test_equipements_valides_alors_l_etape_1_est_prete(self):
        s = _session()
        eq = s.ajouter_equipement(Equipement("00", "MV", "01"))
        s.decider_propositions(eq.ident, "retenir")
        s.valider_equipements([eq.ident])
        etapes = s.parcours()
        self.assertTrue(etapes[0]["pret"], etapes[0]["bloquants"])
        self.assertIn("es_a_valider", _codes(etapes[1]))       # étape 2 : E/S à valider, par équipement
        self.assertEqual(etapes[1]["bloquants"][0]["vue"], "es")

    def test_gamme_non_decrite_bloque_le_materiel(self):
        s = _session(automate="TSX P57 4634")
        self.assertIn("gamme_non_decrite", _codes(s.parcours()[2]))
        s2 = _session()
        self.assertNotIn("gamme_non_decrite", _codes(s2.parcours()[2]))
        self.assertIn("materiel_non_calcule", _codes(s2.parcours()[2]))

    def test_recette_rappelle_la_qualification_sans_bloquer(self):
        r = _session().parcours()[4]
        self.assertEqual(r["bloquants"], [])
        self.assertEqual(r["a_verifier"][0]["code"], "exports_non_qualifies")

    def test_projet_existant_hors_parcours_neuf(self):
        s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s.nouveau(False)
        s.ouvrage.mode = "Existant"
        self.assertEqual(s.parcours(), [])

class TestProgrammeNonRenseigne(unittest.TestCase):
    def test_homonymes_non_controles_signales(self):
        s = _session()
        s.ouvrage.nom_projet = ""
        codes = [p["code"] for p in s.parcours()[3]["a_verifier"]]
        self.assertIn("programme_non_renseigne", codes)
        s.ouvrage.nom_projet = "PROG"
        self.assertNotIn("programme_non_renseigne", [p["code"] for p in s.parcours()[3]["a_verifier"]])

