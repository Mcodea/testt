"""Lot 6 (19/11/2026) : génération groupée des livrables, rangés par destination, avec journal."""
import csv
import io
import os
import tempfile
import unittest
import zipfile

from genvar import generation_groupee as gg
from genvar import modeles_livrables as ml
from genvar.session import RegleMetier
from sorep_web.serveur import Application


class TestGenerationGroupee(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-groupe-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.nouveau({"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.fiche_ouvrage({"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "31", "libelle": "Essai génération groupée",
            "automate": "Sch - M340", "revision": "A"}})
        for t, n in (("PM", "01"), ("HV", "02")):
            i = app.ajouter_equipement({"type": t, "numero": n, "se": "00"})["ident"]
            app.decider_proposition({"ident_eq": i, "decision": "retenir"})

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def _zip(self, familles=None):
        q = {"quoi": "generation_groupee"}
        if familles:
            q["familles"] = familles
        nom, octets = self.app.exporter(q)
        return nom, zipfile.ZipFile(io.BytesIO(octets))

    def _journal(self, z):
        return list(csv.DictReader(io.StringIO(z.read("00_journal.csv").decode("utf-8-sig")), delimiter=";"))

    def test_rangement_journal_et_empreintes(self):
        nom, z = self._zip()
        self.assertTrue(nom.endswith("_livrables.zip"))
        noms = set(z.namelist())
        self.assertTrue({"00_journal.html", "00_journal.csv"} <= noms)
        journal = self._journal(z)
        produits = [j for j in journal if j["État"] == "produit"]
        self.assertTrue(produits)
        for j in produits:
            self.assertIn(j["Fichier"], noms)
            import hashlib
            self.assertEqual(hashlib.sha256(z.read(j["Fichier"])).hexdigest(), j["SHA-256"])
        # chaque fichier est rangé dans le dossier de sa destination
        for n in noms - {"00_journal.html", "00_journal.csv"}:
            self.assertIn(n.split("/")[0], {d for d, _ in gg.FAMILLES.values()})
        self.assertTrue(any(n.startswith("04_Documents/") and n.endswith("_variables_controle.xlsx") for n in noms))
        self.assertTrue(any(n.endswith("_equipements_aller_retour.xlsx") for n in noms))
        self.assertEqual(self.app.dernier_bilan_groupe["produits"], len(produits))

    def test_refus_motives_identiques_aux_exports_unitaires(self):
        _, z = self._zip()
        journal = {j["Pièce"]: j for j in self._journal(z)}
        # pas de cartes déclarées : même motif que l'export unitaire, aucune pièce inventée
        with self.assertRaises(RegleMetier) as unitaire:
            self.app.exporter({"quoi": "cartes"})
        self.assertEqual(journal["Cartes d'E/S"]["État"], "non produit")
        self.assertEqual(journal["Cartes d'E/S"]["Motif ou remarque"], str(unitaire.exception))
        self.assertEqual(journal["Liste des E/S SOFREL"]["État"], "non disponible")
        self.assertEqual(journal["Table de télétransmission IHM Vijeo"]["État"], "non disponible")
        self.assertIn("Aucun modèle", journal["Modèles de l'atelier"]["Motif ou remarque"])
        html = z.read("00_journal.html").decode("utf-8")
        self.assertIn("non qualifiés", html)
        self.assertIn("RV31", html)

    def test_familles_choisies_et_refus(self):
        _, z = self._zip("documents")
        self.assertEqual({j["Destination"] for j in self._journal(z)}, {"Documents d'études"})
        with self.assertRaisesRegex(RegleMetier, "inconnue"):
            self.app.exporter({"quoi": "generation_groupee", "familles": "documents,tout"})

    def test_modeles_client_rempli_ou_refuse(self):
        ml.ajouter_exemple()
        ml.importer("Modèle cassé", "casse.txt", b"<#DEBUT_VARIABLES#>\n<#NOM#>\n")
        _, z = self._zip("modeles")
        journal = {j["Pièce"]: j for j in self._journal(z)}
        ok = journal[f"Modèle « {ml.EXEMPLE_NOM} »"]
        self.assertEqual(ok["État"], "produit")
        self.assertTrue(ok["Fichier"].startswith("06_Modeles_client/"))
        self.assertIn("Repère;Variable", z.read(ok["Fichier"]).decode("utf-8"))
        casse = journal["Modèle « Modèle cassé »"]
        self.assertEqual(casse["État"], "non produit")
        self.assertIn("Modèle à corriger", casse["Motif ou remarque"])

    def test_noms_en_double_departages(self):
        pris: set[str] = set()
        self.assertEqual(gg._nom_libre("a/x.csv", pris), "a/x.csv")
        self.assertEqual(gg._nom_libre("a/x.csv", pris), "a/x_2.csv")


if __name__ == "__main__":
    unittest.main()
