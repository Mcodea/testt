"""Table de télétransmission au format d'études, d'après la trame fournie le 16/11/2026. Données fictives."""
import io
import os
import sys
import tempfile
import unittest

from openpyxl import load_workbook

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genvar.session import RegleMetier  # noqa: E402
from sorep_web.serveur import Application  # noqa: E402

COLONNES = ["Repère", "UF", "Sous-ensemble", "Équipement", "Information", "Famille", "Nom de variable", "Type",
            "Adresse", "Adresse validée", "Registre Modbus", "Unité", "Alarme", "Priorité", "Commentaire automate",
            "Libellé Topkapi"]


class TestExportTeleEtudes(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-tele-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.nouveau({"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.fiche_ouvrage({"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "12", "libelle": "Essai télétransmission",
            "automate": "Sch - M340", "revision": "A"}})

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def test_refus_sans_variable(self):
        with self.assertRaisesRegex(RegleMetier, "Aucune variable"):
            self.app.exporter({"quoi": "tele_etudes"})

    def test_colonnes_de_la_trame_et_rien_d_invente(self):
        for t, n in (("PM", "01"), ("HV", "02")):
            i = self.app.ajouter_equipement({"type": t, "numero": n, "se": "00"})["ident"]
            self.app.decider_proposition({"ident_eq": i, "decision": "retenir"})
        nom, octets = self.app.exporter({"quoi": "tele_etudes"})
        self.assertTrue(nom.endswith("_teletransmission_etudes.xlsx"))
        wb = load_workbook(io.BytesIO(octets))
        self.assertEqual(wb.sheetnames, ["Télétransmission", "Synthèse"])
        ws = wb["Télétransmission"]
        self.assertEqual([c.value for c in ws[5]], COLONNES)
        variables = {v.nom: v for v in self.app.s.variables()}
        lignes = [[c.value for c in r] for r in ws.iter_rows(min_row=6) if r[6].value]
        self.assertEqual({r[6] for r in lignes}, set(variables))
        for r in lignes:
            v = variables[r[6]]
            self.assertEqual((r[0], r[5], r[7]), (v.repere, v.famille, v.type_logique))
            self.assertEqual(r[12] or "", "Oui" if v.alarme else "")
            self.assertIn(r[9], ("Oui", "Appliquée", "Proposée", "Non"))
            self.assertIsNone(r[13])                                   # priorité : à renseigner, jamais inventée
            if r[8]:                                                   # convention non déclarée : pas de registre
                self.assertEqual(r[10], "convention à déclarer")


if __name__ == "__main__":
    unittest.main()
