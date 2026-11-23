"""Sécurité et fiabilité des données (cahier V1-7-02, V1-7-05, V1-7-09, V1-7-11, V1-7-12). Ouvrages fictifs."""
import ast
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from genvar import copies, formats_appris, modeles_livrables
from genvar.modele import Ouvrage
from genvar.referentiel_depot import DepotRefuse, classeur_sain

RACINE = Path(__file__).resolve().parents[1]


def _ouvrage():
    o = Ouvrage()
    o.lieu, o.code_ouvrage, o.numero_ouvrage, o.libelle = "XTST", "RV", "01", "Essai de sécurité"
    return o


class TestAucunAppelReseauSortant(unittest.TestCase):
    """V1-7-09 : le programme livré n'importe aucune bibliothèque cliente réseau."""
    INTERDITS = {"urllib.request", "http.client", "requests", "httpx", "aiohttp", "smtplib", "ftplib", "telnetlib",
                 "poplib", "imaplib", "xmlrpc.client", "websocket", "websockets", "paramiko", "urllib3", "pycurl"}

    def test_aucun_import_client_reseau(self):
        for dossier in ("genvar", "sorep_web"):
            for f in (RACINE / dossier).rglob("*.py"):
                arbre = ast.parse(f.read_text(encoding="utf-8"))
                for n in ast.walk(arbre):
                    noms = [a.name for a in n.names] if isinstance(n, ast.Import) else \
                           [n.module or ""] if isinstance(n, ast.ImportFrom) else []
                    for nom in noms:
                        with self.subTest(fichier=str(f.relative_to(RACINE)), module=nom):
                            self.assertFalse(any(nom == i or nom.startswith(i + ".") for i in self.INTERDITS), nom)

    def test_aucune_connexion_sortante_dans_le_code(self):
        for dossier in ("genvar", "sorep_web"):
            for f in (RACINE / dossier).rglob("*.py"):
                texte = f.read_text(encoding="utf-8")
                with self.subTest(fichier=str(f.relative_to(RACINE))):
                    self.assertNotIn("create_connection", texte)
                    self.assertNotIn("socket.connect", texte)

    def test_aucune_ressource_distante_dans_l_interface(self):
        for f in (RACINE / "sorep_web" / "static").glob("*.html"):
            texte = f.read_text(encoding="utf-8")
            with self.subTest(fichier=f.name):
                self.assertNotIn("src=\"http", texte)
                self.assertNotIn("href=\"http://", texte)
                self.assertNotIn("href=\"https://", texte.replace('rel="noopener"', ''))


class TestClasseursPieges(unittest.TestCase):
    """V1-7-12 : macros, liens externes et formules sont refusés ; un classeur de valeurs passe."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def classeur(self, **parties):
        chemin = os.path.join(self.tmp.name, "c.xlsx")
        with zipfile.ZipFile(chemin, "w") as z:
            z.writestr("xl/worksheets/sheet1.xml", '<worksheet><sheetData><row><c r="A1"><v>1</v></c></row></sheetData></worksheet>')
            for nom, contenu in parties.items():
                z.writestr(nom, contenu)
        return chemin

    def test_classeur_de_valeurs_accepte(self):
        classeur_sain(self.classeur())

    def test_macros_refusees(self):
        for nom in ("xl/vbaProject.bin", "xl/VBAPROJECT.BIN"):
            chemin = os.path.join(self.tmp.name, "m.xlsm")
            with zipfile.ZipFile(chemin, "w") as z:
                z.writestr(nom, b"x")
            with self.subTest(nom=nom), self.assertRaisesRegex(DepotRefuse, "macros"):
                classeur_sain(chemin)

    def test_liens_externes_refuses(self):
        with self.assertRaisesRegex(DepotRefuse, "liens"):
            classeur_sain(self.classeur(**{"xl/externalLinks/externalLink1.xml": "<externalLink/>"}))

    def test_formules_refusees(self):
        chemin = os.path.join(self.tmp.name, "f.xlsx")
        with zipfile.ZipFile(chemin, "w") as z:
            z.writestr("xl/worksheets/sheet1.xml", '<worksheet><sheetData><row><c r="A1"><f>1+1</f></c></row></sheetData></worksheet>')
        with self.assertRaisesRegex(DepotRefuse, "formule"):
            classeur_sain(chemin)

    def test_fichier_qui_n_est_pas_un_classeur_refuse(self):
        chemin = os.path.join(self.tmp.name, "x.xlsx")
        Path(chemin).write_bytes(b"pas un zip")
        with self.assertRaises(DepotRefuse):
            classeur_sain(chemin)


class TestCheminsHorsDossier(unittest.TestCase):
    """V1-7-11 : aucun identifiant ou nom reçu ne peut désigner un chemin hors des dossiers autorisés."""
    HORS = ["../secret", "..\\secret", "/etc/passwd", "C:\\Windows\\win.ini", "a/b", "..", ".", "", None, 5]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = self.tmp.name
        self.addCleanup(lambda: os.environ.pop("SOREP_DATA_DIR", None) if self.ancien is None
                        else os.environ.__setitem__("SOREP_DATA_DIR", self.ancien))
        self.chemin = os.path.join(self.tmp.name, "XTSTRV01.ouvrage.json")
        _ouvrage().enregistrer(self.chemin)
        copies.ecrire(self.chemin, "adressage", Path(self.chemin).read_text(encoding="utf-8"))

    def test_copies_restaurables_par_nom_seul(self):
        Path(self.tmp.name, "hors.json").write_text("{}", encoding="utf-8")
        for nom in self.HORS + ["hors.json"]:
            with self.subTest(nom=nom):
                with self.assertRaises(ValueError):
                    copies.resoudre(self.chemin, nom)

    def test_formats_appris_identifiant_strict(self):
        for ident in self.HORS:
            with self.subTest(ident=ident):
                with self.assertRaises(formats_appris.FormatRefuse):
                    formats_appris._gabarit_chemin(ident)
                self.assertIsNone(formats_appris.trouver(ident))

    def test_modeles_livrables_identifiant_strict(self):
        for ident in self.HORS:
            with self.subTest(ident=ident):
                with self.assertRaises(modeles_livrables.ModeleRefuse):
                    modeles_livrables._fichier(ident)


class TestArretBrutal(unittest.TestCase):
    """V1-7-02, V1-7-05 : un arrêt pendant l'écriture ne laisse jamais un fichier à moitié écrit ; reprise sans perte."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.chemin = os.path.join(self.tmp.name, "XTSTRV01.ouvrage.json")
        self.o = _ouvrage()
        self.o.enregistrer(self.chemin)

    def test_arret_pendant_l_ecriture_laisse_l_ouvrage_intact(self):
        self.o.libelle = "Nouvelle version jamais terminée"

        def ecriture_interrompue(donnees, f, **_):
            f.write('{"format": "ouvrage-genvar", "version": 1, "ouvr')      # coupure en plein milieu
            raise KeyboardInterrupt("arrêt brutal simulé")
        with mock.patch("genvar.modele.json.dump", ecriture_interrompue):
            with self.assertRaises(KeyboardInterrupt):
                self.o.enregistrer(self.chemin)
        repris = Ouvrage.ouvrir(self.chemin)
        self.assertEqual(repris.libelle, "Essai de sécurité")             # ancienne version complète, rien perdu
        json.loads(Path(self.chemin).read_text(encoding="utf-8"))

    def test_arret_avant_le_remplacement_laisse_l_ouvrage_intact(self):
        self.o.libelle = "Écrit mais jamais substitué"
        with mock.patch("genvar.modele.os.replace", side_effect=OSError("coupure")):
            with self.assertRaises(OSError):
                self.o.enregistrer(self.chemin)
        self.assertEqual(Ouvrage.ouvrir(self.chemin).libelle, "Essai de sécurité")

    def test_fichier_provisoire_abandonne_ne_gene_pas_la_reprise(self):
        Path(self.chemin + ".tmp").write_text('{"format": "ouv', encoding="utf-8")   # reste d'un arrêt brutal
        self.o.libelle = "Reprise"
        self.o.enregistrer(self.chemin)
        self.assertEqual(Ouvrage.ouvrir(self.chemin).libelle, "Reprise")
        self.assertFalse(os.path.exists(self.chemin + ".tmp"))


if __name__ == "__main__":
    unittest.main()
