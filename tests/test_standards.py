"""Standards d'ingénierie (19/11/2026) : un standard est un assemblage de briques, copié dans l'ouvrage à sa création ;
un ouvrage existant n'est jamais modifié quand le standard évolue, OGIAS signale l'écart. Ouvrages fictifs (XTST)."""
from dataclasses import asdict
import json
import os
import tempfile
import unittest
from unittest import mock

from genvar import standards
from genvar.modele import ORDRE_ZONES, PLAN_DEFAUT, Ouvrage, zone
from tests.test_coherence import nouvelle


class AvecDossier(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self.dossier.cleanup)
        patch = mock.patch.dict(os.environ, {"SOREP_DATA_DIR": self.dossier.name})
        patch.start()
        self.addCleanup(patch.stop)


class TestBibliotheque(AvecDossier):
    def test_standard_initial_cree_au_premier_acces(self):
        self.assertFalse(os.path.exists(standards.chemin()))
        liste = standards.lire()
        self.assertEqual([s["ident"] for s in liste], [standards.IDENT_INITIAL])
        s = liste[0]
        self.assertEqual(set(s["briques"]), set(standards.FAMILLES))
        self.assertEqual(s["briques"]["adressage"]["plages"], {f: list(PLAN_DEFAUT[f]) for f in ORDRE_ZONES})
        self.assertEqual((s["briques"]["outils"]["supervision"], s["briques"]["outils"]["ihm"]), ("TOPKAPI", ""))
        self.assertTrue(os.path.exists(standards.chemin()))
        self.assertEqual(standards.lire(), liste)                       # relu tel quel, pas recréé

    def test_fichier_illisible_n_est_pas_ecrase(self):
        os.makedirs(os.path.dirname(standards.chemin()), exist_ok=True)
        with open(standards.chemin(), "w", encoding="utf-8") as fh:
            fh.write('{"standards": []}')
        with self.assertRaises(ValueError):
            standards.lire()
        with open(standards.chemin(), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), {"standards": []})

    def test_trouver(self):
        self.assertEqual(standards.trouver(standards.IDENT_INITIAL)["nom"], "Standard initial")
        self.assertIsNone(standards.trouver("client-inexistant"))


class TestApplication(AvecDossier):
    def test_standard_initial_reproduit_le_comportement_d_avant(self):
        s = nouvelle()
        avant = (dict((f, zone(s.ouvrage, f)) for f in ORDRE_ZONES), s.ouvrage.decalage_modbus, s.ouvrage.supervision, s.ouvrage.ihm)
        ref = standards.appliquer(s, standards.trouver(standards.IDENT_INITIAL))
        apres = (dict((f, zone(s.ouvrage, f)) for f in ORDRE_ZONES), s.ouvrage.decalage_modbus, s.ouvrage.supervision, s.ouvrage.ihm)
        self.assertEqual(avant, apres)
        self.assertEqual((ref["ident"], ref["version"]), (standards.IDENT_INITIAL, 1))
        self.assertEqual(standards.ecarts(s.ouvrage), [])
        self.assertEqual(Ouvrage.depuis_dict(asdict(s.ouvrage)).standard["ident"], standards.IDENT_INITIAL)

    def test_copie_independante_du_standard(self):
        """L'ouvrage garde sa copie : une évolution du standard ne le modifie pas, l'écart local est signalé."""
        s = nouvelle()
        choisi = standards.trouver(standards.IDENT_INITIAL)
        standards.appliquer(s, choisi)
        choisi["briques"]["outils"]["supervision"] = "Autre supervision fictive"
        choisi["version"] = 2
        standards.ecrire([choisi])
        self.assertEqual(s.ouvrage.supervision, "TOPKAPI")
        self.assertEqual(s.ouvrage.standard["version"], 1)
        self.assertEqual(s.ouvrage.standard["briques"]["outils"]["supervision"], "TOPKAPI")
        s.ouvrage.ihm = "Vijeo Designer"
        self.assertEqual(standards.ecarts(s.ouvrage), ["IHM : Vijeo Designer (standard : aucune)"])

    def test_tout_ou_rien(self):
        s = nouvelle()
        mauvais = standards.standard_initial()
        mauvais["briques"]["adressage"]["plages"]["TS"] = [3000, 3999]          # recouvre TR : refusé
        sup_avant = s.ouvrage.supervision
        with self.assertRaises(Exception):
            standards.appliquer(s, mauvais)
        self.assertEqual(zone(s.ouvrage, "TS"), tuple(PLAN_DEFAUT["TS"]))
        self.assertEqual((s.ouvrage.standard, s.ouvrage.supervision), ({}, sup_avant))

    def test_ouvrage_anterieur_sans_standard(self):
        self.assertEqual(Ouvrage.depuis_dict({"lieu": "XTST"}).standard, {})
        self.assertEqual(standards.ecarts(Ouvrage()), [])


if __name__ == "__main__":
    unittest.main()
