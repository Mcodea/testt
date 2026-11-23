"""Formats d'export appris (22/11/2026) : classeurs Excel, pour les outils qui importent leurs tables en .xlsx (TIA
Portal pour les automates Siemens).

Classeur FICTIF de la forme d'une table de variables exportée (feuille « PLC Tags » et feuille de constantes) :
aucune donnée réelle ; la conformité à l'outil cible reste à qualifier par un essai réel.
"""
import base64
import io
import os
import tempfile
import unittest

import openpyxl

from genvar import formats_appris as fa
from sorep_web.serveur import Application, RegleMetier

TITRES = ["Name", "Path", "Data Type", "Logical Address", "Comment", "Hmi Visible", "Hmi Accessible", "Hmi Writeable",
          "Typeobject ID", "Version ID"]


def classeur_exemple():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "PLC Tags"
    ws.append(TITRES)
    ws.append(["Marche_P1", "Table fictive", "Bool", "%I4.0", "Marche", True, True, True, None, None])
    ws.append(["Defaut_P1", "Table fictive", "Bool", "%I4.1", "Défaut", True, True, True, None, None])
    ws.append(["Niveau", "Table fictive", "Int", "%IW64", "Niveau", True, True, True, None, None])
    c = wb.create_sheet("User Constants")
    c.append(["Name", "Path", "Data Type", "Value", "Comment"])
    c.append(["CONSTANTE_D_UN_AUTRE_PROJET", "Table fictive", "Int", 12, ""])
    sortie = io.BytesIO()
    wb.save(sortie)
    return sortie.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-formats-xlsx-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.nouveau({"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.fiche_ouvrage({"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "37", "libelle": "Essai classeur",
            "automate": "Sie - S7-1500", "revision": "A"}})
        for t, n in (("PM", "01"), ("LT", "02")):
            i = app.ajouter_equipement({"type": t, "numero": n, "se": "00"})["ident"]
            app.decider_proposition({"ident_eq": i, "decision": "retenir"})
        s = self.s = app.s
        s.valider_contenu_es([(p.ident_eq, p.cle) for p in s.points()])
        s.appliquer_materiel()                       # gamme livrée Siemens S7-1500
        s.implanter_es()
        self.exemple = classeur_exemple()

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def apprendre(self, reglages=None, nom="E/S TIA fictif"):
        r = self.app.formats_appris_action({
            "action": "enregistrer", "fichier": "PLCTags.xlsx", "contenu": base64.b64encode(self.exemple).decode(),
            "nature": "es_physiques", "logiciel": "Sie - S7-1500", "nom": nom, "reglages": reglages or {}})
        return fa.trouver(r["ident"])


class TestAnalyseClasseur(Base):
    def test_feuille_colonnes_et_valeurs_typees(self):
        a = fa.analyser(self.exemple, "PLCTags.xlsx")
        self.assertEqual((a["type_fichier"], a["feuille"], a["entete_index"]), ("xlsx", "PLC Tags", 0))
        self.assertEqual(a["feuilles"], ["PLC Tags", "User Constants"])
        self.assertEqual({c["titre"]: c["champ"] for c in a["colonnes"]}, {
            "Name": "nom", "Path": "fixe", "Data Type": "type", "Logical Address": "adresse", "Comment": "libelle",
            "Hmi Visible": "fixe", "Hmi Accessible": "fixe", "Hmi Writeable": "fixe", "Typeobject ID": "vide",
            "Version ID": "vide"})
        self.assertIs(next(c for c in a["colonnes"] if c["titre"] == "Hmi Visible")["valeur"], True)
        self.assertEqual(a["adresse"]["reconnue"], "octet.bit")
        self.assertEqual((a["types"]["ET"], a["types"]["EA"]), ("Bool", "Int"))

    def test_feuille_choisie_et_refus(self):
        a = fa.analyser(self.exemple, "x.xlsx", feuille="User Constants")
        self.assertEqual(a["feuille"], "User Constants")
        with self.assertRaises(fa.FormatRefuse):
            fa.analyser(self.exemple, "x.xlsx", feuille="Absente")
        with self.assertRaises(fa.FormatRefuse):
            fa.analyser(b"PK\x03\x04pas un classeur", "x.xlsx")


class TestProductionClasseur(Base):
    def test_export_relu_types_conserves_et_autres_feuilles_videes(self):
        f = self.apprendre()
        nom, octets, statut = fa.exporter(f, self.s)
        self.assertTrue(nom.endswith(".xlsx"))
        wb = openpyxl.load_workbook(io.BytesIO(octets))
        ws = wb["PLC Tags"]
        lignes = list(ws.iter_rows(values_only=True))
        self.assertEqual(list(lignes[0]), TITRES)
        points = fa.points_exportes(self.s)
        self.assertEqual(len(lignes) - 1, len(points))
        par_nom = {r[0]: r for r in lignes[1:]}
        for p in points:
            r = par_nom[p.nom]
            self.assertEqual(r[3], fa.adresse_de(p, f["definition"]))
            self.assertTrue(r[3].startswith("%I"))
            self.assertIs(r[5], True)                                    # booléen conservé, pas « True » texte
            self.assertEqual(r[1], "Table fictive")
            self.assertIsNone(r[8])
        self.assertEqual([list(x) for x in wb["User Constants"].iter_rows(values_only=True)],
                         [["Name", "Path", "Data Type", "Value", "Comment"]])     # rien de l'exemple
        self.assertIn("NON QUALIFIÉ", statut)

    def test_autres_feuilles_conservees_sur_demande(self):
        f = self.apprendre({"autres_feuilles": "conserver"}, "E/S TIA conserver")
        wb = openpyxl.load_workbook(io.BytesIO(fa.exporter(f, self.s)[1]))
        self.assertEqual(wb["User Constants"].max_row, 2)

    def test_gabarit_controle_par_empreinte(self):
        f = self.apprendre()
        with open(fa._gabarit_chemin(f["ident"]), "ab") as fh:
            fh.write(b"modifie")
        with self.assertRaises(fa.FormatRefuse) as ctx:
            fa.exporter(f, self.s)
        self.assertIn("modifié hors d'OGIAS", str(ctx.exception))
        fa.supprimer(f["ident"])
        self.assertFalse(os.path.exists(fa._gabarit_chemin(f["ident"])))

    def test_relecture_detecte_un_classeur_altere(self):
        f = self.apprendre()
        octets, ecarts = fa.produire(f["definition"], self.s, fa.gabarit(f))
        self.assertEqual(ecarts, [])
        wb = openpyxl.load_workbook(io.BytesIO(octets))
        wb["PLC Tags"].cell(row=2, column=4, value="%I99.9")
        sortie = io.BytesIO()
        wb.save(sortie)
        self.assertTrue(fa.relire_xlsx(f["definition"], sortie.getvalue(), self.s))

    def test_api_apercu_et_export(self):
        contenu = base64.b64encode(self.exemple).decode()
        r = self.app.formats_appris_action({"action": "apercu", "fichier": "PLCTags.xlsx", "contenu": contenu,
                                            "nature": "es_physiques", "reglages": {}})
        self.assertEqual(r["apercu"][0], " | ".join(TITRES))
        self.assertEqual((r["refus"], r["ecarts"]), ([], []))
        f = self.apprendre()
        nom, octets = self.app.exporter({"quoi": "format_appris", "ident": f["ident"]})
        self.assertTrue(octets.startswith(b"PK\x03\x04"))
        etat = next(x for x in self.app.formats_appris_web({})["formats"] if x["ident"] == f["ident"])
        self.assertEqual((etat["type_fichier"], etat["feuille"]), ("xlsx", "PLC Tags"))
        self.assertTrue(etat["controle"]["pret"], etat["controle"])
        with self.assertRaises(RegleMetier):
            self.app.formats_appris_action({"action": "analyser", "fichier": "x.xlsx", "contenu": contenu,
                                            "feuille": "Absente"})


if __name__ == "__main__":
    unittest.main()
