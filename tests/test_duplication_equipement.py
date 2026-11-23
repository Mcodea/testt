"""Dupliquer un équipement (cahier V1-5-01) : aucune adresse recopiée, nouveau numéro proposé. Ouvrage fictif."""
import os
import tempfile
import unittest

from genvar import adressage
from sorep_web.serveur import Application, RegleMetier


class TestDuplication(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-duplication-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.appeler("nouveau", {"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.appeler("fiche_ouvrage", {"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "42", "libelle": "Essai duplication",
            "automate": "Sch - M580", "revision": "A"}})
        s = self.s = app.s
        i = app.appeler("ajouter_equipement", {"type": "PM", "numero": "01", "se": "00"})["ident"]
        app.appeler("decider_proposition", {"ident_eq": i, "decision": "retenir"})
        self.pm = s.ouvrage.equipement(i)
        self.pm.libelle = "Pompe d'exhaure"
        self.pm.attributs = {"PUISSANCE": "7,5 kW"}
        s.valider_contenu_es([(p.ident_eq, p.cle) for p in s.points()])
        s.appliquer_materiel()
        s.implanter_es()
        s.appliquer_adressage(adressage.calculer(s).empreinte, ("automate",))
        self.pm.valide = True

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def test_aucune_adresse_ni_voie_reprise(self):
        self.assertTrue(self.pm.adresses and any(m.get("module") for m in self.pm.es_meta.values()))
        r = self.app.appeler("dupliquer_equipement", {"ident": self.pm.ident})
        self.assertEqual(r["repere"], "XTSTRV42PM02")                       # numéro libre suivant
        copie = self.s.ouvrage.equipement(r["ident"])
        self.assertEqual((copie.adresses, copie.adresses_es, copie.validees, copie.traces, copie.valide),
                         ({}, {}, [], {}, False))
        self.assertFalse(any(k in m for m in copie.es_meta.values() for k in ("module", "voie", "validee", "adresse")))
        self.assertEqual((copie.type, copie.libelle, copie.attributs, copie.options),
                         ("PM", "Pompe d'exhaure", {"PUISSANCE": "7,5 kW"}, self.pm.options))
        points = [p for p in self.s.points() if p.ident_eq == copie.ident]
        self.assertTrue(points and all(not p.adresse and not p.module for p in points))
        variables = [v for v in self.s.variables() if v.ident_eq == copie.ident]
        self.assertTrue(variables and all(not v.adresse for v in variables))
        self.assertEqual(self.s.erreurs_materiel(), [])                    # aucune voie occupée deux fois
        self.assertTrue(all(v.adresse for v in self.s.variables() if v.ident_eq == self.pm.ident))   # original intact

    def test_numero_demande_et_controles(self):
        r = self.app.appeler("dupliquer_equipement", {"ident": self.pm.ident, "numero": "07"})
        self.assertEqual(r["repere"], "XTSTRV42PM07")
        with self.assertRaisesRegex(RegleMetier, "existe déjà"):
            self.app.appeler("dupliquer_equipement", {"ident": self.pm.ident, "numero": "07"})
        with self.assertRaisesRegex(RegleMetier, "introuvable"):
            self.app.appeler("dupliquer_equipement", {"ident": "inconnu"})

    def test_annulable_par_ctrl_z(self):
        n = len(self.s.ouvrage.equipements)
        self.app.appeler("dupliquer_equipement", {"ident": self.pm.ident})
        self.assertEqual(self.app.historique_web()["annuler"], "duplication d'équipement")
        self.app.appeler("annuler", {})
        self.assertEqual(len(self.s.ouvrage.equipements), n)


if __name__ == "__main__":
    unittest.main()
