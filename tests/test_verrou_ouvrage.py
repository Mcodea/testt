"""Verrou d'ouvrage (cahier V1-7-04) : un même ouvrage n'est jamais modifié par deux OGIAS à la fois.

Deux instances de l'application dans le même processus simulent deux OGIAS ; un verrou « d'un autre poste » ou
« d'un processus disparu » est écrit à la main. Ouvrage fictif (lieu XTST).
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from genvar import verrou
from sorep_web.serveur import Application, RegleMetier


class Base(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-verrou-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        self.app = self.creer("38")

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def creer(self, numero):
        app = Application()
        app.nouveau({"mode": "Neuf"})
        try:
            app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        except RegleMetier:
            pass
        app.fiche_ouvrage({"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": numero, "libelle": "Essai verrou",
            "automate": "Sch - M580", "revision": "A"}})
        return app

    @property
    def chemin(self):
        return self.app.s.chemin

    def ecrire_verrou(self, **champs):
        Path(verrou.chemin_verrou(self.chemin)).write_text(json.dumps(champs), encoding="utf-8")


class TestVerrou(Base):
    def test_cree_a_la_creation_et_libere_a_la_fermeture(self):
        chemin = self.chemin
        d = verrou.lire(chemin)
        self.assertEqual((d["jeton"], d["pid"], d["logiciel"]), (self.app.jeton, os.getpid(), "OGIAS"))
        self.assertNotIn("xtst", json.dumps(d).lower())                     # aucune donnée de l'ouvrage
        self.app.fermer({})
        self.assertIsNone(verrou.lire(chemin))
        self.assertFalse(os.path.exists(verrou.chemin_verrou(chemin)))

    def test_second_ogias_refuse_puis_accepte_apres_fermeture(self):
        chemin = self.chemin
        autre = Application()
        with self.assertRaises(verrou.VerrouPris) as ctx:
            autre.ouvrir({"chemin": chemin})
        self.assertIn("déjà ouvert", str(ctx.exception))
        self.assertTrue(ctx.exception.detail["meme_poste"])
        self.assertFalse(autre.ouvert)
        self.app.fermer({})
        autre.ouvrir({"chemin": chemin})
        self.assertEqual(verrou.lire(chemin)["jeton"], autre.jeton)

    def test_verrou_abandonne_sur_ce_poste_repris_automatiquement(self):
        chemin = self.chemin
        self.app.fermer({})
        self.app = Application()
        import socket
        Path(verrou.chemin_verrou(chemin)).write_text(json.dumps(
            {"jeton": "ancien", "hote": socket.gethostname(), "utilisateur": "x", "pid": 2 ** 22 + 12345,
             "depuis": "2026-11-22T10:00:00+00:00"}), encoding="utf-8")
        self.app.ouvrir({"chemin": chemin})                                  # processus disparu : reprise
        self.assertEqual(verrou.lire(chemin)["jeton"], self.app.jeton)

    def test_autre_poste_refuse_puis_reprise_explicite(self):
        chemin = self.chemin
        self.app.fermer({})
        self.app = Application()
        Path(verrou.chemin_verrou(chemin)).write_text(json.dumps(
            {"jeton": "autre", "hote": "POSTE-FICTIF", "utilisateur": "dupont", "pid": 1,
             "depuis": "2026-11-22T10:00:00+00:00"}), encoding="utf-8")
        with self.assertRaises(verrou.VerrouPris) as ctx:
            self.app.ouvrir({"chemin": chemin})
        self.assertIn("dupont sur POSTE-FICTIF", str(ctx.exception))
        self.assertFalse(ctx.exception.detail["meme_poste"])
        self.app.ouvrir({"chemin": chemin, "forcer": True})
        d = verrou.lire(chemin)
        self.assertEqual(d["jeton"], self.app.jeton)
        self.assertIn("dupont sur POSTE-FICTIF", d["repris_de"])

    def test_poste_qui_a_perdu_le_verrou_ne_peut_plus_enregistrer(self):
        chemin = self.chemin
        avant = Path(chemin).read_bytes()
        Path(verrou.chemin_verrou(chemin)).write_text(json.dumps(
            {"jeton": "repreneur", "hote": "POSTE-FICTIF", "utilisateur": "dupont", "pid": 1,
             "depuis": "2026-11-22T10:00:00+00:00"}), encoding="utf-8")
        with self.assertRaises(RegleMetier) as ctx:
            self.app.ajouter_equipement({"type": "PM", "numero": "01", "se": "00"})
        self.assertIn("Ouvrage repris par dupont sur POSTE-FICTIF", str(ctx.exception))
        self.assertEqual(Path(chemin).read_bytes(), avant)                  # rien n'est écrit
        self.assertEqual(verrou.lire(chemin)["jeton"], "repreneur")          # son verrou n'est pas retiré
        self.app.fermer({})
        self.assertEqual(verrou.lire(chemin)["jeton"], "repreneur")

    def test_ouvrir_un_autre_ouvrage_libere_le_premier(self):
        premier = self.chemin
        second = self.creer("39")
        deuxieme = second.s.chemin
        second.fermer({})
        self.app.ouvrir({"chemin": deuxieme})
        self.assertIsNone(verrou.lire(premier))
        self.assertEqual(verrou.lire(deuxieme)["jeton"], self.app.jeton)

    def test_corbeille_refusee_pour_un_ouvrage_ouvert_ailleurs(self):
        chemin = self.chemin
        autre = Application()
        with self.assertRaises(RegleMetier) as ctx:
            autre.supprimer_ouvrage({"chemin": chemin})
        self.assertIn("ne peut pas aller à la corbeille", str(ctx.exception))
        self.assertTrue(os.path.exists(chemin))

    def test_processus_actif(self):
        self.assertTrue(verrou.processus_actif(os.getpid()))
        self.assertFalse(verrou.processus_actif(0))
        self.assertFalse(verrou.processus_actif(2 ** 22 + 12345))


if __name__ == "__main__":
    unittest.main()
