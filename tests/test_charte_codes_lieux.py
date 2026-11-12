"""Charte de codification ESB / RESO : code lieu par règle, exceptions, doublons, migration des
codes proposés le 6 novembre (remplacés seulement s'ils ne sont utilisés par aucun ouvrage)."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from genvar import codification as c
from genvar.modele import Ouvrage
from sorep_web import referentiel_ouvrage as ref
from sorep_web.serveur import Application

VALIDES = {"Arcueil": "ARCL", "Athis-Mons": "ATMS", "Cachan": "CACH", "Chevilly-Larue": "CVLR",
           "Fresnes": "FRSN", "Gentilly": "GTLY", "Ivry-sur-Seine": "IVSN", "Le Kremlin-Bicêtre": "KRBC",
           "Orly": "ORLY", "Villejuif": "VLJF", "Vitry-sur-Seine": "VTSN", "Morangis": "MRGS",
           "Paray-Vieille-Poste": "PVPS", "Savigny-sur-Orge": "SVOR", "Villeneuve-Saint-Georges": "VSGR"}


class TestRegleCodeLieu(unittest.TestCase):
    def test_seize_codes_valides(self):
        self.assertEqual({n: c.code_propose(n) for n in VALIDES}, VALIDES)

    def test_registre_initial_conforme_a_la_regle(self):
        for x in ref.COMMUNES_DEFAUT:
            self.assertEqual(c.code_propose(x["libelle"]), x["code"], x["libelle"])

    def test_exception_cachan_et_regle_insuffisante(self):
        self.assertEqual(c.code_par_regle("Cachan"), "")         # 3 lettres seulement : exception écrite
        self.assertEqual(c.proposition("Cachan")["origine"], "exception")
        self.assertIn("à la main", c.proposition("Eu")["message"])

    def test_mots_ignores_et_saint_conserve(self):
        self.assertEqual(c.code_propose("Réservoir de Fresnes"), "FRSN")
        self.assertEqual(c.mots_significatifs("Villeneuve-Saint-Georges"), ["VILLENEUVE", "SAINT", "GEORGES"])

    def test_doublon_refuse_et_variantes_libres(self):
        r = c.proposition("Athis-Mons", ["ATMS", "ATMT"])
        self.assertTrue(r["conflit"])
        self.assertTrue(r["variantes"])
        self.assertTrue(all(len(v) == 4 and v not in ("ATMS", "ATMT") for v in r["variantes"]))


class TestRegistreEtMigration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = patch.dict(os.environ, {"SOREP_DATA_DIR": self.tmp.name})
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def _v2(self, lieux):
        os.makedirs(os.path.dirname(ref.chemin()), exist_ok=True)
        with open(ref.chemin(), "w", encoding="utf8") as f:
            json.dump({"version": 2, "lieux": lieux}, f)

    def test_anciens_codes_non_utilises_remplaces(self):
        self._v2([{"code": "ATHM", "libelle": "Athis-Mons", "regie": "ESB"},
                  {"code": "MORG", "libelle": "Morangis", "regie": "RESO"},
                  {"code": "PRIV", "libelle": "Lieu propre", "regie": "AUTRE"}])
        lieux = {x["libelle"]: x["code"] for x in ref.lire()["lieux"]}
        self.assertEqual((lieux["Athis-Mons"], lieux["Morangis"], lieux["Lieu propre"]), ("ATMS", "MRGS", "PRIV"))
        with open(ref.chemin(), encoding="utf8") as f:
            self.assertEqual(json.load(f)["version"], ref.VERSION)

    def test_ancien_code_utilise_par_un_ouvrage_conserve(self):
        from genvar import projets
        o = Ouvrage(lieu="MORG", code_ouvrage="RV")
        o.numero_ouvrage = "01"
        o.enregistrer(str(projets.nom_libre("MORGRV01")))
        self._v2([{"code": "MORG", "libelle": "Morangis", "regie": "RESO"},
                  {"code": "ATHM", "libelle": "Athis-Mons", "regie": "ESB"}])
        lieux = {x["libelle"]: x["code"] for x in ref.lire()["lieux"]}
        self.assertEqual(lieux["Morangis"], "MORG")                # un code utilisé ne change jamais
        self.assertEqual(lieux["Athis-Mons"], "ATMS")

    def test_libelle_personnalise_non_remplace(self):
        self._v2([{"code": "ATHM", "libelle": "Athis-Mons (centre)", "regie": "ESB"}])
        self.assertIn("ATHM", {x["code"] for x in ref.lire()["lieux"]})

    def test_proposition_http_signale_le_doublon(self):
        app = Application()
        self.assertEqual(app.lieu_proposition({"nom": "Le Kremlin-Bicêtre"})["code"], "KRBC")
        r = app.lieu_proposition({"nom": "Orly"})
        self.assertTrue(r["conflit"])                              # ORLY déjà au registre
        self.assertFalse(app.lieu_proposition({"nom": "Orly", "ancien": "ORLY"})["conflit"])


if __name__ == "__main__":
    unittest.main()
