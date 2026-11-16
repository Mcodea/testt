"""Liste des E/S par carte d'après la trame de l'utilisateur (16/11/2026) : architecture, une feuille par carte,
réserves en formules, E/S hors cartes conservées. Données fictives."""
import io
import os
import sys
import tempfile
import unittest

from openpyxl import load_workbook

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genvar.session import RegleMetier  # noqa: E402
from sorep_web.serveur import Application  # noqa: E402


class TestExportESParCarte(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-es-cartes-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.nouveau({"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.fiche_ouvrage({"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "11", "libelle": "Essai trame",
            "automate": "Sch - M580", "communication": "Modbus TCP/IP", "revision": "A"}})
        ids = [app.ajouter_equipement({"type": t, "numero": n, "se": "00", "libelle": lib})["ident"]
               for t, n, lib in (("MV", "03", "Vanne de remplissage"), ("PM", "01", "Pompe 1"), ("LT", "01", "Niveau cuve"))]
        for i in ids:
            for pt in app.equipement({"ident": i}).get("signaux_es", []):
                if pt["point"] in ("EA", "SA") and pt["retenu"]:
                    app.configurer_equipement({"action": "analogique", "ident_eq": i, "cle": pt["cle"], "params": {
                        "signal_min": 4, "signal_max": 20, "phys_min": 0, "phys_max": 6, "unite": "m"}})
            app.decider_proposition({"ident_eq": i, "decision": "retenir"})
        app.valider_equipements({"idents": ids, "valide": True})
        pts = app.es({})["points"]
        app.es_valider({"niveau": "contenu", "paires": [{"ident_eq": p["ident_eq"], "cle": p["cle"]} for p in pts]})
        app.materiel_action({"action": "config", "alimentation": "BMX CPS 3500", "processeur": "BME P58 2020"})

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def test_refus_sans_carte(self):
        with self.assertRaisesRegex(RegleMetier, "Aucune carte"):
            self.app.exporter({"quoi": "es_cartes"})

    def test_architecture_et_feuilles_de_cartes(self):
        self.app.materiel_action({"action": "appliquer"})
        self.app.modules_action({"action": "implanter"})
        nom, octets = self.app.exporter({"quoi": "es_cartes"})
        self.assertTrue(nom.endswith("_ES_par_carte.xlsx"))
        wb = load_workbook(io.BytesIO(octets))
        modules = self.app.s.ouvrage.modules
        attendues = {f"{dict(ET='ETOR', ST='STOR', EA='EANA', SA='SANA')[m.nature]}-{m.rack}-{m.position:02d}" for m in modules}
        self.assertEqual(set(wb.sheetnames), {"Architecture", "Hors cartes"} | attendues)
        arch = wb["Architecture"]
        textes = [c.value for row in arch.iter_rows() for c in row if isinstance(c.value, str)]
        self.assertIn("Gamme automate : Modicon M580", textes)
        self.assertIn("BME P58 2020", textes)                      # processeur double largeur : une seule case
        self.assertEqual(textes.count("BME P58 2020"), 1)
        self.assertIn("0–1", textes)
        self.assertEqual(textes.count("à renseigner"), 4)          # nom et adresses réseau : jamais inventés
        # Une feuille par carte : chaque voie listée, chaque E/S placée à son adresse, réserve en formule
        points = {p.nom: p for p in self.app.s.points()}
        for m in modules:
            ws = wb[f"{dict(ET='ETOR', ST='STOR', EA='EANA', SA='SANA')[m.nature]}-{m.rack}-{m.position:02d}"]
            self.assertEqual(ws["E5"].value, m.voies)
            self.assertTrue(str(ws["G5"].value).startswith("=SUM(I7:I"))
            adresses = [ws.cell(7 + v, 1).value for v in range(m.voies)]
            self.assertEqual(len(set(adresses)), m.voies)
            for v in range(m.voies):
                nom_api = ws.cell(7 + v, 7).value
                if nom_api:
                    self.assertEqual(points[nom_api].adresse.upper(), adresses[v].upper())
                    self.assertEqual(ws.cell(7 + v, 9).value, 0)
                else:
                    self.assertEqual(ws.cell(7 + v, 9).value, 1)
            if m.nature == "EA":
                self.assertIn("0 – 6 m", "".join(str(ws.cell(7 + v, 2).value or "") for v in range(m.voies)))
        # Toutes les E/S câblées sont dans une feuille de carte
        noms = {c.value for s in wb.worksheets if s.title not in ("Architecture", "Hors cartes")
                for c in s["G"] if isinstance(c.value, str) and "_" in c.value}
        self.assertEqual(noms, {p.nom for p in self.app.s.points() if p.raccordement != "Communication"})

    def test_e_s_sans_voie_conservees(self):
        self.app.materiel_action({"action": "appliquer"})          # cartes posées, E/S pas encore implantées
        nom, octets = self.app.exporter({"quoi": "es_cartes"})
        hors = load_workbook(io.BytesIO(octets))["Hors cartes"]
        self.assertEqual(sum(1 for r in hors.iter_rows(min_row=5) if r[0].value), len(self.app.s.points()))


if __name__ == "__main__":
    unittest.main()
