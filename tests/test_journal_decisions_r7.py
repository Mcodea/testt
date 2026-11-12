"""Décision R7 : journal des décisions de référentiel dans le fichier de l'ouvrage.

Chaque entrée : profil, version, équipement, action (adoption, refus, retour au standard), date, opérateur,
sauvegarde associée. L'annulation d'une adoption restaure le fichier à l'octet : elle n'ajoute pas d'entrée
au fichier (la copie de l'état annulé reste la trace), et l'entrée de l'adoption annulée disparaît avec elle.
"""
import copy
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, Ouvrage
from genvar.session import RegleMetier, Session


class TestJournal(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dossier, ignore_errors=True)
        env = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = self.dossier
        self.addCleanup(lambda: os.environ.pop("SOREP_DATA_DIR", None) if env is None
                        else os.environ.__setitem__("SOREP_DATA_DIR", env))
        self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        self.s.nouveau(False)
        self.s.definir("lieu", "XTST"); self.s.definir("code_ouvrage", "RV"); self.s.ouvrage.numero_ouvrage = "01"
        self.s.ajouter_sous_ensemble("00")
        self.mv = self.s.ajouter_equipement(Equipement("00", "MV", "01"))
        self.hv = self.s.ajouter_equipement(Equipement("00", "HV", "01"))
        self.mv.libelles["TS_DEF"] = "Libellé local"
        self.chemin = str(Path(self.dossier) / "XTSTRV01.ouvrage.json")
        self.s.enregistrer(self.chemin)
        nouveau = copy.deepcopy(self.s._catalogue_commun)
        for s in nouveau.signaux:
            if s["type"] == "MV" and s["famille"] == "TS" and s["code"] == "DISC":
                s["remarque"] = "Révisée."
        self.s._catalogue_commun = nouveau

    def test_ancien_fichier_sans_journal_ouvert_avec_journal_vide(self):
        d = Ouvrage().vers_dict()
        d.pop("journal_referentiel")
        self.assertEqual(Ouvrage.depuis_dict(d).journal_referentiel, [])

    def test_adoption_journalisee_par_equipement_et_enregistree(self):
        self.s.adopter_referentiel(["MV"])
        j = self.s.ouvrage.journal_referentiel
        self.assertEqual(len(j), 1)
        e = j[0]
        self.assertEqual((e["action"], e["profil"], e["equipement"], e["ident_eq"]),
                         ("adoption", "MV", "XTSTRV01MV01", self.mv.ident))
        self.assertTrue(e["le"] and "par" in e and "version" in e)
        self.assertEqual(e["sauvegarde"], os.path.basename(self.s.sauvegarde_adoption))
        self.assertTrue(e["sauvegarde"])
        self.s.enregistrer(self.chemin)
        self.assertEqual(Ouvrage.ouvrir(self.chemin).journal_referentiel, j)

    def test_annulation_retire_l_entree_et_restaure_le_fichier(self):
        octets = Path(self.chemin).read_bytes()
        self.s.adopter_referentiel(["MV"])
        self.s.enregistrer(self.chemin)
        self.s.annuler_adoption(enregistrer=True)
        self.assertEqual(Path(self.chemin).read_bytes(), octets)
        self.assertEqual(self.s.ouvrage.journal_referentiel, [])

    def test_refus_motive_journalise_sans_rien_adopter(self):
        catalogue_avant = copy.deepcopy(self.s.catalogue.signaux)
        with self.assertRaises(RegleMetier):
            self.s.refuser_mise_a_jour(["MV"], "  ")
        self.assertEqual(self.s.ouvrage.journal_referentiel, [])
        self.s.refuser_mise_a_jour(["MV"], "Révision à étudier avec l'exploitant")
        j = self.s.ouvrage.journal_referentiel
        self.assertEqual([(x["action"], x["profil"], x["equipement"]) for x in j], [("refus", "MV", "XTSTRV01MV01")])
        self.assertEqual(j[0]["detail"], "Révision à étudier avec l'exploitant")
        self.assertEqual(self.s.catalogue.signaux, catalogue_avant)
        with self.assertRaises(RegleMetier):
            self.s.refuser_mise_a_jour(["HV"], "Aucun écart")      # rien à refuser pour HV

    def test_retour_au_standard_journalise(self):
        self.s.revenir_au_standard(self.mv.ident, "TS_DEF", "libelle", confirme=True)
        e = self.s.ouvrage.journal_referentiel[-1]
        self.assertEqual((e["action"], e["profil"], e["equipement"]), ("retour au standard", "MV", "XTSTRV01MV01"))
        self.assertIn("TS_DEF", e["detail"])
        self.assertIn("Libellé local", e["detail"])


    def test_route_web_de_refus(self):
        from sorep_web.serveur import ROUTES_POST, Application
        self.assertEqual(ROUTES_POST["/api/referentiel/refuser-mise-a-jour"], "refuser_mise_a_jour")
        app = Application()
        app.s, app.ouvert = self.s, True
        with self.assertRaises(RegleMetier):
            app.refuser_mise_a_jour({"types": "MV", "motif": "x"})
        r = app.refuser_mise_a_jour({"types": ["MV"], "motif": "À étudier"})
        self.assertEqual(r["journal"][-1]["action"], "refus")
        self.assertEqual(Ouvrage.ouvrir(self.chemin).journal_referentiel[-1]["detail"], "À étudier")


if __name__ == "__main__":
    unittest.main()
