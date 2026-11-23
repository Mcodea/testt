"""Annulation Ctrl+Z et rétablissement des modifications de l'ouvrage (cahier V1-4-47). Ouvrage fictif (XTST)."""
import os
import tempfile
import unittest

from genvar.modele import Ouvrage
from sorep_web.serveur import Application, RegleMetier


class TestAnnulation(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-annulation-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.appeler("nouveau", {"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.appeler("fiche_ouvrage", {"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "41", "libelle": "Essai annulation",
            "automate": "Sch - M580", "revision": "A"}})
        self.app.historique.clear()

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def reperes(self):
        return [self.app.s.ouvrage.repere(e) for e in self.app.s.ouvrage.equipements]

    def sur_disque(self):
        o = Ouvrage.ouvrir(self.app.s.chemin)
        return [o.repere(e) for e in o.equipements]

    def test_annuler_puis_retablir_et_fichier_enregistre(self):
        self.app.appeler("ajouter_equipement", {"type": "PM", "numero": "01", "se": "00"})
        self.app.appeler("ajouter_equipement", {"type": "HV", "numero": "02", "se": "00"})
        self.assertEqual(self.app.historique_web()["annuler"], "ajout d'équipement")
        r = self.app.appeler("annuler", {})
        self.assertEqual(r["annule"], "ajout d'équipement")
        self.assertEqual(self.reperes(), ["XTSTRV41PM01"])
        self.assertEqual(self.sur_disque(), ["XTSTRV41PM01"])             # l'annulation est enregistrée
        self.app.appeler("annuler", {})
        self.assertEqual(self.reperes(), [])
        with self.assertRaisesRegex(RegleMetier, "Rien à annuler"):
            self.app.appeler("annuler", {})
        self.app.appeler("retablir", {})
        self.app.appeler("retablir", {})
        self.assertEqual(self.reperes(), ["XTSTRV41PM01", "XTSTRV41HV02"])
        self.assertEqual(self.sur_disque(), ["XTSTRV41PM01", "XTSTRV41HV02"])
        with self.assertRaisesRegex(RegleMetier, "Rien à rétablir"):
            self.app.appeler("retablir", {})

    def test_nouvelle_modification_efface_le_retablissement(self):
        self.app.appeler("ajouter_equipement", {"type": "PM", "numero": "01", "se": "00"})
        self.app.appeler("annuler", {})
        self.app.appeler("ajouter_equipement", {"type": "HV", "numero": "02", "se": "00"})
        self.assertEqual(self.app.historique_web()["retablir"], "")

    def test_commande_sans_effet_ou_refusee_hors_historique(self):
        with self.assertRaises(RegleMetier):
            self.app.appeler("ajouter_equipement", {"type": "PM", "numero": "00", "se": "00"})   # numéro refusé
        self.app.appeler("journal_web", {})
        self.assertEqual(self.app.historique, [])

    def test_historique_borne_et_remis_a_zero_a_l_ouverture(self):
        for n in range(1, 36):
            self.app.appeler("ajouter_equipement", {"type": "PM", "numero": f"{n:02d}", "se": "00"})
        self.assertEqual(len(self.app.historique), self.app.HISTORIQUE_MAX)
        chemin = self.app.s.chemin
        self.app.appeler("fermer", {})
        self.app.appeler("ouvrir", {"chemin": chemin})
        self.assertEqual((self.app.historique, self.app.refaire), ([], []))

    def test_un_indice_livre_n_est_jamais_annule(self):
        self.app.appeler("ajouter_equipement", {"type": "PM", "numero": "01", "se": "00"})
        self.app.appeler("revisions_action", {"action": "livrer", "motif": "Première diffusion"})
        self.app.appeler("annuler", {})                                    # annule l'ajout, pas la livraison
        self.assertEqual([x["indice"] for x in self.app.s.ouvrage.indices], ["A"])
        self.assertEqual([x["indice"] for x in Ouvrage.ouvrir(self.app.s.chemin).indices], ["A"])

    def test_annulation_refusee_si_l_ouvrage_a_ete_repris_ailleurs(self):
        import json
        from pathlib import Path
        from genvar import verrou
        self.app.appeler("ajouter_equipement", {"type": "PM", "numero": "01", "se": "00"})
        Path(verrou.chemin_verrou(self.app.s.chemin)).write_text(json.dumps(
            {"jeton": "autre", "hote": "POSTE-FICTIF", "utilisateur": "dupont", "pid": 1, "depuis": "2026-11-23T00:00:00"}),
            encoding="utf-8")
        with self.assertRaisesRegex(RegleMetier, "Ouvrage repris"):
            self.app.appeler("annuler", {})
        self.assertEqual(self.sur_disque(), ["XTSTRV41PM01"])
        self.assertEqual(self.reperes(), ["XTSTRV41PM01"])                    # mémoire égale au fichier
        self.assertEqual(self.app.historique_web()["annuler"], "ajout d'équipement")   # rien n'est perdu


if __name__ == "__main__":
    unittest.main()
