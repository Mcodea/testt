"""Fichier d'import de variables TOPKAPI « .$$t » (Version 1) : échantillon SYNTHÉTIQUE reproduisant la mise
en forme relevée sur un projet réel (Windows-1252, CRLF, 38 colonnes, mot$bit en hexadécimal). Aucune donnée
de ce projet n'est reprise ici. Format NON qualifié dans TOPKAPI 6.3."""
import os
import tempfile
import unittest
import zipfile

from genvar import chemins, formats_topkapi as ft
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.session import Session, RegleMetier

VIDE = "\t" * 33
ECHANTILLON = ("Version\t1\r\n" + "\t".join(ft.ENTETE) + "\r\n"
               "E_Essai_df\t100$A\t0\t Essai - Défaut \t" + VIDE + "\r\n"
               "Essai_mesure\t2100\t2\t Essai - Mesure \t" + VIDE + "\r\n").encode("cp1252")


class TestFormat(unittest.TestCase):
    def test_relecture_identique(self):
        pts = ft.lire_octets(ECHANTILLON)
        self.assertEqual([(p.mnemo, p.mot_bit, p.format) for p in pts],
                         [("E_Essai_df", (100, 10), "0"), ("Essai_mesure", (2100, None), "2")])
        self.assertEqual(ft.ecrire_octets(pts), ECHANTILLON)

    def test_refus(self):
        with self.assertRaises(ft.FormatTopkapiInvalide):
            ft.lire_octets(ECHANTILLON.replace(b"\r\n", b"\n"))
        with self.assertRaises(ft.FormatTopkapiInvalide):
            ft.lire_octets(ECHANTILLON.replace(b"100$A", b"100$G"))
        pts = ft.lire_octets(ECHANTILLON)
        pts[1].adresse = "100"
        self.assertTrue(ft.controler(pts))                      # mot entier sur un mot découpé en bits
        pts = ft.lire_octets(ECHANTILLON)
        pts.append(ft.PointTopkapi("Double", "2099", "102", " x "))          # 2099-2100
        self.assertTrue(any("mot 2100" in e for e in ft.controler(pts)))   # deux mots : chevauchement


class TestExportOuvrage(unittest.TestCase):
    def setUp(self):
        os.environ["SOREP_DATA_DIR"] = self.d = tempfile.mkdtemp()
        s = self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s.nouveau(False)
        s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
        s.definir("automate", "M340"); s.ajouter_sous_ensemble("00")
        e = s.ajouter_equipement(Equipement("00", "PM", "01"))
        s.decider_propositions(e.ident, "retenir")
        p = s.plan_adressage(); s.appliquer_adressage(p.empreinte)

    def test_convention_obligatoire_puis_export(self):
        z = os.path.join(self.d, "t.zip")
        with self.assertRaises(RegleMetier):
            self.s.exporter_topkapi(z)                          # convention protocolaire non déclarée
        self.s.declarer_protocole(True, 0)
        n, exclus = self.s.exporter_topkapi(z)
        with zipfile.ZipFile(z) as f:
            nom = next(x for x in f.namelist() if x.endswith(".$$t"))
            pts = ft.lire_octets(f.read(nom))
            self.assertIn("NON QUALIFIÉ", f.read("LISEZ-MOI_export_TOPKAPI.txt").decode("utf-8"))
        self.assertEqual(len(pts), n)
        self.assertEqual(ft.controler(pts), [])
        variables = {v.nom: v for v in self.s.variables()}
        for p in pts:
            v = variables[p.mnemo]
            mot, bit = p.mot_bit
            self.assertEqual(f"%MW{mot}" + (f".{bit}" if bit is not None else ""), v.adresse)
        self.assertTrue(all("deux mots" in x for x in exclus))  # 32 bits exclus tant que 102/105 non confirmés


if __name__ == "__main__":
    unittest.main()
