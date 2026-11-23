"""Installation vierge : le référentiel livré est publié comme révision 1 (cahier V1-3-21)."""
import os
import tempfile
import unittest

from genvar.referentiel_depot import Depot, editer
from sorep_web.serveur import Application


class TestInstallationVierge(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-vierge-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def test_premier_demarrage_publie_le_referentiel_livre_comme_revision_1(self):
        self.assertIsNone(Depot().head())
        Application()
        d = Depot()
        self.assertEqual(d.head()["revision"], 1)
        self.assertEqual([r["numero"] for r in d.revisions()], [1])
        self.assertEqual(d.etat()["revision"], 1)
        self.assertEqual(d.etat()["incoherence"], "")

    def test_demarrages_suivants_ne_changent_rien(self):
        Application()
        avant = Depot().head()
        Application()
        Application()
        self.assertEqual(Depot().head(), avant)
        self.assertEqual(len(Depot().revisions()), 1)

    def test_un_historique_existant_n_est_jamais_touche(self):
        d = Depot()
        d.initialiser()
        d.creer_brouillon("auteur")
        donnees, _ = editer(d.brouillon()["donnees"], "ajouter_correspondance",
                            champs={"type": "ga", "ancienne": "ts_ancien", "nouvelle": "ts_intr", "motif": "essai"})
        d.remplacer_donnees(donnees, "Correspondance d'essai")
        d.valider("auteur")
        d.publier("Révision de test", d.etat()["brouillon"]["empreinte"], "auteur")
        assert d.head()["revision"] == 2
        Application()
        self.assertEqual(d.head()["revision"], 2)
        self.assertEqual([r["numero"] for r in d.revisions()], [2, 1])

    def test_dossier_non_inscriptible_ne_bloque_pas_le_demarrage(self):
        from unittest import mock
        depot = Depot()
        with mock.patch("genvar.referentiel_depot.os.makedirs", side_effect=PermissionError("lecture seule")):
            self.assertFalse(depot.initialiser())
        self.assertIsNone(Depot().head())                          # rien n'a été écrit, aucune erreur au démarrage


if __name__ == "__main__":
    unittest.main()
