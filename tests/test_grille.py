"""Grille d'ingénierie (lot 5, 19/11/2026) : modification en masse des champs descriptifs et des attributs, tout ou
rien, sans toucher aux repères, signaux, adresses ni à la validation des équipements. Ouvrage fictif (XTST)."""
import os
import tempfile
import unittest
from unittest import mock

from genvar import attributs
from genvar.modele import Equipement, UniteFonctionnelle
from genvar.session import RegleMetier
from tests.test_coherence import nouvelle


class TestGrille(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self.dossier.cleanup)
        p = mock.patch.dict(os.environ, {"SOREP_DATA_DIR": self.dossier.name})
        p.start()
        self.addCleanup(p.stop)
        attributs.creer({"code": "DN", "nom": "Diamètre", "type": "nombre", "types": ["HV"]})
        self.s = nouvelle()
        self.s.ouvrage.unites.append(UniteFonctionnelle("UF01", "Fictive"))
        self.hv = [self.s.ajouter_equipement(Equipement("00", "HV", f"0{i}")) for i in (1, 2)]
        self.pm = self.s.ajouter_equipement(Equipement("00", "PM", "01"))
        for e in (*self.hv, self.pm):
            self.s.decider_propositions(e.ident, "retenir")
            e.valide = True
        self.tous = [e.ident for e in (*self.hv, self.pm)]

    def test_masse_sans_devalider(self):
        noms = sorted(v.nom for v in self.s.variables())
        r = self.s.appliquer_en_masse(self.tous, "uf", "UF01")
        self.assertEqual((r["modifies"], r["sans_objet"]), (3, 0))
        self.assertEqual(self.s.appliquer_en_masse(self.tous, "uf", "UF01")["inchanges"], 3)
        r = self.s.appliquer_en_masse(self.tous, "attr:DN", "150")
        self.assertEqual((r["modifies"], r["sans_objet"]), (2, 1))           # la pompe n'est pas concernée
        self.assertEqual(self.pm.attributs, {})
        self.assertTrue(all(e.valide for e in (*self.hv, self.pm)))
        self.assertEqual(sorted(v.nom for v in self.s.variables()), noms)     # repères et noms inchangés

    def test_tout_ou_rien(self):
        avant = [(e.libelle, e.uf) for e in self.s.ouvrage.equipements]
        for champ, valeur in (("uf", "UF99"), ("libelle", "x" * 33), ("attr:DN", "large"), ("modele", "Autre"),
                              ("type", "PM"), ("attr:INCONNU", "1")):
            with self.subTest(champ=champ), self.assertRaises(RegleMetier):
                self.s.appliquer_en_masse(self.tous, champ, valeur)
        with self.assertRaises(RegleMetier):
            self.s.appliquer_en_masse([self.hv[0].ident, "inconnu"], "local", "Local fictif")
        self.assertEqual([(e.libelle, e.uf) for e in self.s.ouvrage.equipements], avant)
        self.assertEqual(self.hv[0].local, "")

    def test_ouvrage_valide_repasse_en_controle_sauf_attribut(self):
        self.s.ouvrage.statut = "Validé"
        self.s.appliquer_en_masse([self.hv[0].ident], "attr:DN", "80")
        self.assertEqual(self.s.ouvrage.statut, "Validé")
        self.s.appliquer_en_masse([self.hv[0].ident], "local", "Local fictif")
        self.assertEqual(self.s.ouvrage.statut, "À contrôler")


if __name__ == "__main__":
    unittest.main()
