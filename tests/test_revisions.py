"""Indices de livraison et liste des modifications (22/11/2026). Ouvrage fictif (lieu XTST)."""
import csv
import io
import os
import tempfile
import unittest
import zipfile

import openpyxl

from genvar import adressage
from genvar import revisions
from genvar.modele import Ouvrage
from sorep_web.serveur import Application, RegleMetier


class Base(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-revisions-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.nouveau({"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.fiche_ouvrage({"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "38", "libelle": "Essai indices",
            "automate": "Sch - M580", "revision": "A"}})
        self.ids = {}
        for t, n in (("PM", "01"), ("HV", "02")):
            i = app.ajouter_equipement({"type": t, "numero": n, "se": "00"})["ident"]
            app.decider_proposition({"ident_eq": i, "decision": "retenir"})
            self.ids[t] = i
        s = self.s = app.s
        s.valider_contenu_es([(p.ident_eq, p.cle) for p in s.points()])
        s.appliquer_materiel()
        s.implanter_es()
        s.appliquer_adressage(adressage.calculer(s).empreinte, ("automate",))

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien


class TestIndices(Base):
    def test_livrer_puis_passer_au_suivant(self):
        x = self.s.livrer_indice("Première diffusion", "Essai")
        self.assertEqual((x["indice"], x["motif"], x["auteur"]), ("A", "Première diffusion", "Essai"))
        self.assertEqual(len(x["empreinte"]), 64)
        with self.assertRaises(RegleMetier) as ctx:                  # un indice livré ne change plus
            self.s.livrer_indice("Autre")
        self.assertIn("déjà livré", str(ctx.exception))
        self.assertEqual(self.s.passer_indice_suivant(), "B")
        with self.assertRaises(RegleMetier):                          # B pas encore livré
            self.s.passer_indice_suivant()
        with self.assertRaises(RegleMetier):
            self.s.livrer_indice("  ")

    def test_indice_suivant(self):
        self.assertEqual([revisions.indice_suivant(x) for x in ("A", "Y", "1", "A9", "B12")], ["B", "Z", "2", "A10", "B13"])
        for x in ("Z", "9999"):
            with self.subTest(x=x), self.assertRaises(revisions.IndiceRefuse):
                revisions.indice_suivant(x)

    def test_indices_enregistres_et_relus(self):
        self.s.livrer_indice("Première diffusion")
        chemin = os.path.join(self.donnees.name, "essai.ouvrage.json")
        self.s.enregistrer(chemin)
        relu = Ouvrage.ouvrir(chemin)
        self.assertEqual([x["indice"] for x in relu.indices], ["A"])
        self.assertEqual(relu.indices[0]["photo"], self.s.ouvrage.indices[0]["photo"])

    def test_ancien_fichier_sans_indices(self):
        d = self.s.ouvrage.vers_dict()
        d.pop("indices")
        self.assertEqual(Ouvrage.depuis_dict(d).indices, [])


class TestModifications(Base):
    def test_aucune_modification_juste_apres_livraison(self):
        self.s.livrer_indice("Première diffusion")
        c = self.s.comparer_indices()
        self.assertEqual((c["depuis"], c["vers"], c["modifications"]), ("A", "A (en cours)", []))

    def test_ajout_modification_suppression_et_renommage(self):
        self.s.livrer_indice("Première diffusion")
        self.s.passer_indice_suivant()
        o = self.s.ouvrage
        hv = o.equipement(self.ids["HV"])
        hv.libelle = "Vanne d'isolement"
        hv.numero = "05"                                              # renommage : repère et noms changent
        pm = o.equipement(self.ids["PM"])
        o.equipements.remove(pm)
        i = self.app.ajouter_equipement({"type": "PM", "numero": "03", "se": "00"})["ident"]
        self.app.decider_proposition({"ident_eq": i, "decision": "retenir"})
        o.decalage_modbus = 1
        c = self.s.comparer_indices()
        self.assertEqual((c["depuis"], c["vers"]), ("A", "B (en cours)"))
        par = {(x["categorie"], x["element"], x["etat"]): x for x in c["modifications"]}
        self.assertIn(("equipements", "XTSTRV38PM01", "supprimé"), par)
        self.assertIn(("equipements", "XTSTRV38PM03", "ajouté"), par)
        modif = par[("equipements", "XTSTRV38HV05", "modifié")]          # rapproché par identité, pas par nom
        champs = {ch["champ"]: (ch["avant"], ch["apres"]) for ch in modif["champs"]}
        self.assertEqual(champs["repere"], ("XTSTRV38HV02", "XTSTRV38HV05"))
        self.assertEqual(champs["libelle"], ("", "Vanne d'isolement"))
        es_hv = [x for x in c["modifications"] if x["categorie"] == "es" and "HV05" in x["element"]]
        self.assertTrue(es_hv and all(x["etat"] == "modifié" for x in es_hv))
        self.assertTrue(any(ch["champ"] == "nom" for ch in es_hv[0]["champs"]))
        ouv = par[("ouvrage", "Identification de l'ouvrage", "modifié")]
        self.assertEqual([(ch["avant"], ch["apres"]) for ch in ouv["champs"]], [("0", "1")])
        variables = [x for x in c["modifications"] if x["categorie"] == "variables" and x["etat"] == "modifié"]
        self.assertTrue(any(ch["champ"] == "registre" for x in variables for ch in x["champs"]))   # décalage Modbus
        self.assertEqual(c["bilan"]["equipements"], {"ajouté": 1, "supprimé": 1, "modifié": 1})

    def test_comparaison_entre_deux_indices_livres(self):
        self.s.livrer_indice("Première diffusion")
        self.s.passer_indice_suivant()
        self.s.ouvrage.equipement(self.ids["HV"]).libelle = "Vanne B"
        self.s.livrer_indice("Indice B")
        self.s.passer_indice_suivant()
        self.s.ouvrage.equipement(self.ids["HV"]).libelle = "Vanne C"
        c = self.s.comparer_indices("A", "B")
        self.assertEqual([(x["element"], x["etat"]) for x in c["modifications"]], [("XTSTRV38HV02", "modifié")])
        self.assertEqual(c["modifications"][0]["champs"][0]["apres"], "Vanne B")
        self.assertEqual(self.s.comparer_indices("B")["modifications"][0]["champs"][0]["apres"], "Vanne C")
        with self.assertRaises(RegleMetier):
            self.s.comparer_indices("Z")

    def test_sans_indice_livre_refus_explicite(self):
        with self.assertRaises(RegleMetier) as ctx:
            self.s.comparer_indices()
        self.assertIn("Aucun indice livré", str(ctx.exception))


class TestLivrables(Base):
    def test_export_excel_et_generation_groupee(self):
        _, octets = self.app.exporter({"quoi": "generation_groupee", "familles": "documents"})
        journal = {r["Pièce"]: r for r in csv.DictReader(io.StringIO(zipfile.ZipFile(io.BytesIO(octets))
                   .read("00_journal.csv").decode("utf-8-sig")), delimiter=";")}
        piece = journal["Liste des modifications depuis le dernier indice livré"]
        self.assertEqual(piece["État"], "non produit")
        self.assertIn("Aucun indice livré", piece["Motif ou remarque"])
        self.app.revisions_action({"action": "livrer", "motif": "Première diffusion"})
        self.app.revisions_action({"action": "suivant"})
        self.s.ouvrage.equipement(self.ids["HV"]).libelle = "Vanne modifiée"
        nom, octets = self.app.exporter({"quoi": "modifications"})
        self.assertTrue(nom.endswith("_modifications_A_B.xlsx"))
        wb = openpyxl.load_workbook(io.BytesIO(octets))
        self.assertEqual(wb.sheetnames, ["Modifications", "Synthèse", "Indices"])
        lignes = list(wb["Modifications"].iter_rows(values_only=True))
        self.assertEqual(lignes[0], ("Catégorie", "Élément", "État", "Champ", "Indice A", "Indice B (en cours)"))
        self.assertIn(("Équipements", "XTSTRV38HV02", "modifié", "Libellé", None, "Vanne modifiée"), lignes)
        _, octets = self.app.exporter({"quoi": "generation_groupee", "familles": "documents"})
        z = zipfile.ZipFile(io.BytesIO(octets))
        self.assertTrue(any(n.startswith("04_Documents/") and "modifications_A_B" in n for n in z.namelist()))

    def test_api(self):
        r = self.app.revisions_web({})
        self.assertEqual((r["revision"], r["indices"], r["livre"], r["comparaison"]), ("A", [], False, None))
        r = self.app.revisions_action({"action": "livrer", "motif": "Première diffusion", "auteur": "Essai"})
        self.assertEqual((r["livre_indice"], r["livre"], r["suivant"]), ("A", True, "B"))
        self.assertNotIn("photo", r["indices"][0])                    # la photo reste dans le fichier
        r = self.app.revisions_action({"action": "suivant"})
        self.assertEqual((r["revision"], r["livre"]), ("B", False))
        with self.assertRaises(RegleMetier):
            self.app.revisions_action({"action": "inconnue"})


if __name__ == "__main__":
    unittest.main()
