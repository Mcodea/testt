"""Type de signal analogique : courant (4-20 mA, défaut) ou tension (0-10 V), sans changer les échelles existantes (23/11/2026)."""
import os
import tempfile
import unittest

from genvar import export_liste_es
from genvar.modele import unite_signal
from sorep_web.serveur import Application, RegleMetier


class TestSignalTension(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-tension-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.appeler("nouveau", {"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.appeler("fiche_ouvrage", {"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "44", "libelle": "Essai tension",
            "automate": "Sch - M580", "revision": "A"}})
        self.s = app.s
        self.eq = self.app.appeler("ajouter_equipement", {"type": "TT", "numero": "01", "se": "00"})["ident"]
        self.app.appeler("decider_proposition", {"ident_eq": self.eq, "decision": "retenir"})

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def cle(self):
        return next(p.cle for p in self.s.points() if p.ident_eq == self.eq and p.point == "EA")

    def echelle(self, **plus):
        base = {"signal_min": 0, "signal_max": 10, "phys_min": 0, "phys_max": 50, "unite": "°C"}
        self.s.definir_analogique(self.eq, self.cle(), {**base, **plus})
        return next(p for p in self.s.points() if p.ident_eq == self.eq and p.cle == self.cle())

    def test_courant_par_defaut_et_echelle_existante_inchangee(self):
        p = self.echelle(signal_min=4, signal_max=20)
        self.assertNotIn("signal_type", p.analogique)               # aucune clé nouvelle pour une échelle en courant
        self.assertEqual(unite_signal(p.analogique), "mA")

    def test_tension_0_10_v(self):
        p = self.echelle(signal_type="tension")
        self.assertEqual(p.analogique["signal_type"], "tension")
        self.assertEqual(unite_signal(p.analogique), "V")
        self.assertIn("0–10 V → 0–50 °C", export_liste_es.description_analogique(p))

    def test_controles(self):
        with self.assertRaisesRegex(RegleMetier, "tension invalides"):
            self.echelle(signal_type="tension", signal_min=4, signal_max=20)
        with self.assertRaisesRegex(RegleMetier, "Type de signal inconnu"):
            self.echelle(signal_type="resistance")
        with self.assertRaisesRegex(RegleMetier, "courant invalides"):
            self.echelle(signal_type="courant", signal_min=4, signal_max=40)

    def test_export_cartes_affiche_l_unite(self):
        from genvar import export_es_cartes
        p = self.echelle(signal_type="tension")
        self.assertTrue(export_es_cartes._echelle(p).endswith("0–10 V"))


if __name__ == "__main__":
    unittest.main()
