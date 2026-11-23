"""Journal technique tournant (cahier V1-7-06) et écoute locale seulement (V1-7-08). Ouvrage fictif (lieu XTST)."""
import os
import tempfile
import unittest
from unittest import mock

from sorep_web import serveur
from sorep_web.serveur import Application


class TestJournal(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-journal-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def test_evenements_d_usage_sans_donnee_d_ouvrage(self):
        app = Application()
        app.nouveau({"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.fiche_ouvrage({"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "40", "libelle": "Libellé confidentiel fictif",
            "automate": "Sch - M580", "revision": "A"}})
        chemin = app.s.chemin
        app.fermer({})
        app.ouvrir({"chemin": chemin})
        try:
            app.exporter({"quoi": "nomenclature"})
        except Exception:                                    # refus métier attendu : aucun matériel
            pass
        lignes = serveur.lire_journal()
        texte = "\n".join(lignes)
        for attendu in ("[INFO] Ouvrage créé.", "[INFO] Ouvrage fermé.", "[INFO] Ouvrage ouvert (mode Neuf).",
                        "[INFO] Export demandé : nomenclature."):
            self.assertIn(attendu, texte)
        for interdit in ("XTST", "confidentiel", os.path.basename(chemin)):
            self.assertNotIn(interdit, texte)
        self.assertEqual(app.journal_web({})["lignes"], lignes)

    def test_rotation_et_lecture_dans_l_ordre(self):
        with mock.patch.object(serveur, "JOURNAL_TAILLE_MAX", 200):
            for i in range(40):
                serveur.evenement(f"ligne {i:02d} " + "x" * 30)
        fichiers = sorted(f for f in os.listdir(self.donnees.name) if f.startswith("journal"))
        self.assertEqual(fichiers, ["journal.1.log", "journal.2.log", "journal.log"])
        self.assertTrue(all(os.path.getsize(os.path.join(self.donnees.name, f)) < 400 for f in fichiers))
        lignes = serveur.lire_journal()
        self.assertTrue(lignes[-1].endswith("ligne 39 " + "x" * 30))
        numeros = [int(x.split("ligne ")[1][:2]) for x in lignes]
        self.assertEqual(numeros, sorted(numeros))                 # du plus ancien au plus récent
        self.assertNotIn(0, numeros)                               # les plus anciens sont sortis

    def test_erreur_inattendue_journalisee(self):
        serveur.journal("Traceback (most recent call last):\n  ValueError: essai")
        self.assertIn("[ERREUR] Traceback", "\n".join(serveur.lire_journal()))


class TestEcouteLocale(unittest.TestCase):
    def test_serveur_ecoute_sur_127_0_0_1_seulement(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"SOREP_DATA_DIR": d}):
            srv, url, _ = serveur.demarrer(ouvrir_navigateur=False, port=0)
            try:
                self.assertEqual(srv.server_address[0], "127.0.0.1")
                self.assertTrue(url.startswith("http://127.0.0.1:"))
                self.assertIn("[INFO] Démarrage d'OGIAS", "\n".join(serveur.lire_journal()))
            finally:
                srv.server_close()


if __name__ == "__main__":
    unittest.main()
