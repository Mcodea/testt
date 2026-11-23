"""Ordre d'export des variables (cahier V1-5-02, option B décidée par l'utilisateur le 23/11/2026) : un ordre choisi
par équipement s'applique aux tables exportées et JAMAIS aux adresses. Ouvrage fictif (XTST)."""
import base64
import os
import re
import tempfile
import unittest

import openpyxl

from genvar import adressage, export_tele_etudes
from genvar import formats_appris as fa
from sorep_web.serveur import Application, RegleMetier


class TestOrdreExport(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-ordre-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.appeler("nouveau", {"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.appeler("fiche_ouvrage", {"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "43", "libelle": "Essai ordre d'export",
            "automate": "Sch - M580", "revision": "A"}})
        self.ids = []
        for t, n in (("PM", "01"), ("HV", "02")):
            i = app.appeler("ajouter_equipement", {"type": t, "numero": n, "se": "00"})["ident"]
            app.appeler("decider_proposition", {"ident_eq": i, "decision": "retenir"})
            self.ids.append(i)
        self.s = app.s
        self.pm = self.ids[0]

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def noms(self, ident):
        return [x["nom"] for x in self.s.ordre_export_equipement(ident)]

    def inverser(self):
        cles = [x["cle"] for x in self.s.ordre_export_equipement(self.pm)][::-1]
        self.app.appeler("definir_ordre_export", {"ident": self.pm, "cles": cles})
        return cles

    def test_ordre_applique_aux_variables_de_l_equipement_seulement(self):
        avant_pm, avant_hv = self.noms(self.pm), self.noms(self.ids[1])
        self.inverser()
        self.assertEqual(self.noms(self.pm), avant_pm[::-1])
        self.assertEqual(self.noms(self.ids[1]), avant_hv)
        # les variables gardent leur place relative entre équipements
        export = [v.ident_eq for v in self.s.variables_export()]
        self.assertEqual(export, [v.ident_eq for v in self.s.variables()])

    def test_adresses_jamais_modifiees(self):
        plan_avant = [(a.niveau, a.ident_eq, a.cle, a.proposee) for a in adressage.calculer(self.s).affectations]
        self.inverser()
        plan_apres = [(a.niveau, a.ident_eq, a.cle, a.proposee) for a in adressage.calculer(self.s).affectations]
        self.assertEqual(plan_apres, plan_avant)
        self.s.appliquer_adressage(adressage.calculer(self.s).empreinte, ("automate",))
        adresses = {v.nom: v.adresse for v in self.s.variables()}
        self.app.appeler("definir_ordre_export", {"ident": self.pm, "cles": []})
        self.assertEqual({v.nom: v.adresse for v in self.s.variables()}, adresses)

    def test_exports_suivent_l_ordre(self):
        self.s.appliquer_adressage(adressage.calculer(self.s).empreinte, ("automate",))
        attendu = self.noms(self.pm)[::-1]
        self.inverser()
        noms_etudes = [l["nom"] for l in export_tele_etudes.lignes(self.s) if l["nom"] in attendu]
        self.assertEqual(noms_etudes, attendu)
        exemple = b"Tag;Address\r\nA;%MW100.0\r\nB;%MW300\r\n"
        r = self.app.formats_appris_action({"action": "enregistrer", "fichier": "s.csv", "contenu": base64.b64encode(exemple).decode(),
                                            "nature": "teletransmission", "logiciel": "TOPKAPI", "nom": "Supervision fictive"})
        texte = fa.exporter(fa.trouver(r["ident"]), self.s)[1].decode("cp1252")
        ordre_fichier = [l.split(";")[0] for l in texte.split("\r\n")[1:] if l.split(";")[0] in attendu]
        self.assertEqual(ordre_fichier, attendu)
        chemin = os.path.join(self.donnees.name, "table.xlsx")
        self.s.exporter_excel(chemin)
        wb = openpyxl.load_workbook(chemin)
        cellules = [c for ws in wb.worksheets for row in ws.iter_rows(values_only=True) for c in row if c in attendu]
        self.assertEqual(cellules[:len(attendu)], attendu)
        xsy = os.path.join(self.donnees.name, "table.xsy")
        self.s.exporter_xsy(xsy)
        noms_xsy = [n for n in re.findall(r'name="([^"]+)"', open(xsy, encoding="utf-8", errors="replace").read())
                    if n in attendu]
        self.assertEqual(noms_xsy, attendu)

    def test_controles_retour_et_annulation(self):
        with self.assertRaisesRegex(RegleMetier, "une fois et une seule"):
            self.app.appeler("definir_ordre_export", {"ident": self.pm, "cles": ["TS_INCONNU"]})
        origine = self.noms(self.pm)
        self.inverser()
        self.assertTrue(self.app.ordre_export_web({"ident": self.pm})["personnalise"])
        self.assertEqual(self.app.historique_web()["annuler"], "ordre d'export")
        self.app.appeler("annuler", {})
        self.assertEqual(self.noms(self.pm), origine)
        self.inverser()
        self.app.appeler("definir_ordre_export", {"ident": self.pm, "cles": []})
        self.assertEqual(self.noms(self.pm), origine)
        self.assertFalse(self.app.ordre_export_web({"ident": self.pm})["personnalise"])
        self.assertTrue(all(e.valide is not None for e in self.s.ouvrage.equipements))


if __name__ == "__main__":
    unittest.main()
