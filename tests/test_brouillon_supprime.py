"""Retour d'essai n° 2 (12/11/2026) : supprimer un brouillon de référentiel, sans perte irrémédiable."""
import os
import tempfile
import unittest

from genvar.referentiel_depot import Depot, DepotRefuse


class TestSuppressionBrouillon(unittest.TestCase):
    def setUp(self):
        self.env = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = tempfile.mkdtemp()
        self.depot = Depot()

    def tearDown(self):
        if self.env is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.env

    def test_supprimer_puis_recuperer(self):
        publie = self.depot.publie()
        self.depot.creer_brouillon("essai")
        nom = self.depot.abandonner()
        self.assertTrue(nom)
        self.assertIsNone(self.depot.brouillon())
        self.assertEqual(self.depot.publie(), publie)                      # révision publiée intacte
        self.assertEqual(self.depot.brouillons_supprimes(), [nom])
        self.depot.recuperer_brouillon(nom)
        self.assertIsNotNone(self.depot.brouillon())
        self.assertEqual(self.depot.brouillons_supprimes(), [])

    def test_recuperation_refusee_si_brouillon_en_cours_ou_nom_inconnu(self):
        self.depot.creer_brouillon("a")
        nom = self.depot.abandonner()
        self.depot.creer_brouillon("b")
        with self.assertRaises(DepotRefuse):
            self.depot.recuperer_brouillon(nom)
        self.depot.abandonner()
        with self.assertRaises(DepotRefuse):
            self.depot.recuperer_brouillon("../brouillon.json")

    def test_sans_brouillon_rien_a_supprimer_et_cinq_copies_au_plus(self):
        self.assertEqual(self.depot.abandonner(), "")
        for _ in range(7):
            self.depot.creer_brouillon("x")
            self.depot.abandonner()
        self.assertEqual(len(self.depot.brouillons_supprimes()), 5)
