"""Écran de rapprochement d'un projet existant (cahier V1-6-02, V1-6-05) : confiance et raison affichées,
confirmation une par une ou en lot, tracée et annulable. Ouvrages fictifs (XTST)."""
import os
import tempfile
import unittest

from genvar import existant
from sorep_web.serveur import Application, RegleMetier


def _neuf(dossier):
    os.environ["SOREP_DATA_DIR"] = dossier
    app = Application()
    app.appeler("nouveau", {"mode": "Neuf"})
    app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
    app.appeler("fiche_ouvrage", {"action": "creer", "identification": {
        "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "49", "libelle": "Source historique",
        "automate": "Sch - M580", "revision": "A"}})
    for t, n in (("PM", "01"), ("HV", "02")):
        i = app.appeler("ajouter_equipement", {"type": t, "numero": n, "se": "00"})["ident"]
        app.appeler("decider_proposition", {"ident_eq": i, "decision": "retenir"})
    return app


class TestRapprochementWeb(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.a = tempfile.TemporaryDirectory(prefix="ogias-rap-a-")
        self.b = tempfile.TemporaryDirectory(prefix="ogias-rap-b-")
        neuf = _neuf(self.a.name)
        xsy = os.path.join(self.a.name, "historique.xsy")
        neuf.s.exporter_xsy(xsy)
        neuf.appeler("fermer", {})
        os.environ["SOREP_DATA_DIR"] = self.b.name
        app = self.app = Application()
        app.appeler("nouveau", {"mode": "Existant"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.appeler("fiche_ouvrage", {"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "49", "libelle": "Projet existant",
            "automate": "Sch - M580", "revision": "A", "mode": "Existant"}})
        existant.importer_xsy_detaille(app.s.ouvrage, existant.lire_xsy_detaille(xsy))
        app._sauver()

    def tearDown(self):
        self.app.appeler("fermer", {})
        for d in (self.a, self.b):
            d.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def preparer(self):
        d = self.app.rapprochement_web({})
        self.assertGreater(len(d["detectes"]), 0)
        self.app.appeler("rapprochement_action", {"action": "detectes", "cles": [x["cle"] for x in d["detectes"]]})
        return self.app.appeler("rapprochement_action", {"action": "proposer"})

    def test_reserve_aux_projets_existants(self):
        neuf = Application()
        neuf.appeler("nouveau", {"mode": "Neuf"})
        with self.assertRaises(RegleMetier):
            neuf.rapprochement_web({})
        with self.assertRaisesRegex(RegleMetier, "inconnue"):
            self.app.rapprochement_action({"action": "pirate"})

    def test_equipements_detectes_acceptes_puis_proposition_avec_confiance_et_raison(self):
        d = self.preparer()
        self.assertEqual(d["equipements"], 2)
        associees = [l for l in d["lignes"] if l["variable_source"]]
        self.assertTrue(associees)
        for l in associees:
            self.assertIn(l["confiance"], ("élevée", "à rapprocher manuellement"))
            self.assertTrue(l["raison"], l["cle"])
            self.assertFalse(l["fonction_validee"])                 # une proposition n'est jamais confirmée d'office
        self.assertEqual(d["bilan"]["Validée"], 0)

    def test_confirmation_une_par_une_tracee_et_retirable(self):
        d = self.preparer()
        l = next(x for x in d["lignes"] if x["variable_source"])
        r = self.app.appeler("rapprochement_action", {"action": "confirmer", "ident_eq": l["ident_eq"], "cle": l["cle"]})
        self.assertTrue(next(x for x in r["lignes"] if x["cle"] == l["cle"] and x["ident_eq"] == l["ident_eq"])["fonction_validee"])
        journal = self.app.s.ouvrage.journal_rapprochement
        self.assertEqual(journal[-1]["action"], "confirmation")
        r = self.app.appeler("rapprochement_action", {"action": "retirer_confirmation", "ident_eq": l["ident_eq"], "cle": l["cle"]})
        self.assertFalse(next(x for x in r["lignes"] if x["cle"] == l["cle"] and x["ident_eq"] == l["ident_eq"])["fonction_validee"])
        self.app.appeler("rapprochement_action", {"action": "dissocier", "ident_eq": l["ident_eq"], "cle": l["cle"]})
        with self.assertRaisesRegex(RegleMetier, "Associer d'abord"):
            self.app.appeler("rapprochement_action", {"action": "confirmer", "ident_eq": l["ident_eq"], "cle": l["cle"]})

    def test_lot_limite_aux_confiances_elevees_puis_annule(self):
        d = self.preparer()
        n = d["confirmables"]
        if n == 0:
            with self.assertRaisesRegex(RegleMetier, "Aucune ligne"):
                self.app.appeler("rapprochement_action", {"action": "lot"})
            return
        r = self.app.appeler("rapprochement_action", {"action": "lot"})
        confirmees = [x for x in r["lignes"] if x["fonction_validee"]]
        self.assertEqual(len(confirmees), n)
        self.assertTrue(all(x["confiance"] == "élevée" for x in confirmees))
        self.assertEqual(len(r["lots"]), 1)
        r = self.app.appeler("rapprochement_action", {"action": "annuler_lot", "id": r["lots"][0]["id"]})
        self.assertEqual(r["lots"], [])
        self.assertFalse(any(x["fonction_validee"] for x in r["lignes"]))

    def test_associer_et_dissocier_manuellement(self):
        d = self.preparer()
        l = next(x for x in d["lignes"] if x["variable_source"])
        r = self.app.appeler("rapprochement_action", {"action": "dissocier", "ident_eq": l["ident_eq"], "cle": l["cle"]})
        self.assertEqual(next(x for x in r["lignes"] if x["cle"] == l["cle"] and x["ident_eq"] == l["ident_eq"])["variable_source"], "")
        r = self.app.appeler("rapprochement_action", {"action": "associer", "ident_eq": l["ident_eq"], "cle": l["cle"], "variable": l["variable_source"]})
        courant = next(x for x in r["lignes"] if x["cle"] == l["cle"] and x["ident_eq"] == l["ident_eq"])
        self.assertEqual(courant["variable_source"], l["variable_source"])
        self.assertEqual(courant["origine"], "Choix manuel")
        with self.assertRaises(RegleMetier):
            self.app.appeler("rapprochement_action", {"action": "associer", "ident_eq": l["ident_eq"], "cle": l["cle"], "variable": "VARIABLE_INEXISTANTE"})


if __name__ == "__main__":
    unittest.main()
