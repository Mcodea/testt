"""Demandes de l'utilisateur du 16/11/2026 : emplacements réservés du rack, modules de communication posés sur
un emplacement choisi, sources d'acquisition classées et protocoles (liste fournie par l'utilisateur)."""
import json
import os
import tempfile
import unittest
from unittest import mock

from genvar import chemins, materiel
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, PointES
from genvar.session import RegleMetier, Session


def _session():
    s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
    s.nouveau(False)
    s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
    s.ouvrage.automate = "Sch - M340"; s.ajouter_sous_ensemble("00")
    e = s.ajouter_equipement(Equipement("00", "PM", "01"))
    s.decider_propositions(e.ident, "retenir")
    s.valider_contenu_es([(p.ident_eq, p.cle) for p in s.points()])
    s.definir_config_materiel(processeur="BMX P34 2020")
    s.appliquer_materiel()
    return s


class TestEmplacementsReserves(unittest.TestCase):
    def test_carte_refusee_sur_le_processeur_et_hors_du_rack(self):
        s = _session()
        with self.assertRaisesRegex(RegleMetier, "réservé"):
            s.ajouter_module(0, 0, "ET", 16, "BMX DDI 1602")
        positions = s.ouvrage.racks[0]["positions"]
        with self.assertRaisesRegex(RegleMetier, "emplacements"):
            s.ajouter_module(0, positions, "ET", 16, "BMX DDI 1602")

    def test_module_de_communication_sur_un_emplacement_choisi_puis_libere(self):
        s = _session()
        libre = next(p for p in range(s.ouvrage.racks[0]["positions"])
                     if p not in s.ouvrage.racks[0]["cpu"] and not any(m.position == p for m in s.ouvrage.modules))
        s.installer_communication(0, libre, "BMX NOE 0100")
        r = s.ouvrage.racks[0]
        self.assertIn({"position": libre, "reference": "BMX NOE 0100", "role": "communication"}, r["occupation"])
        self.assertIn(libre, r["cpu"])
        self.assertEqual(s.ouvrage.materiel_config["communication"], ["BMX NOE 0100"])
        self.assertFalse(s.ouvrage.materiel_valide)
        with self.assertRaisesRegex(RegleMetier, "réservé"):                 # plus de carte sur cet emplacement
            s.ajouter_module(0, libre, "ET", 16, "BMX DDI 1602")
        with self.assertRaisesRegex(RegleMetier, "inconnu"):
            s.installer_communication(0, libre + 1, "BMX XYZ 9999")
        s.retirer_communication(0, libre)
        self.assertNotIn(libre, s.ouvrage.racks[0]["cpu"])
        self.assertEqual(s.ouvrage.materiel_config["communication"], [])

    def test_choix_d_alimentation_et_processeur_reportes_sur_le_rack_retenu(self):
        s = _session()
        s.definir_config_materiel(alimentation="BMX CPS 2010", processeur="BMX P34 2000")
        r = s.ouvrage.racks[0]
        self.assertEqual(r["alimentation"], "BMX CPS 2010")
        self.assertEqual(next(o for o in r["occupation"] if o["role"] == "processeur")["reference"], "BMX P34 2000")


class TestSourcesDAcquisition(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        patcher = mock.patch.object(chemins, "dossier_donnees", return_value=self.dossier)
        patcher.start()
        self.addCleanup(patcher.stop)
        from sorep_web import referentiel_ouvrage
        self.ref = referentiel_ouvrage

    def test_liste_fournie_classee_par_categorie(self):
        l = self.ref.lire()
        self.assertEqual(l["protocoles"], ["Modbus TCP/IP", "LACBUS IP", "EtherNet/IP", "LACBUS IP / LX Connect"])
        for source, categorie in (("Sch - M340", "Automate"), ("Sof - S4W Dual", "Télégestion"),
                                  ("Sch - SCADAPack 474", "Télégestion"), ("Sch - STBNIP2311", "E/S déportées")):
            self.assertIn(source, l["automates"])
            self.assertEqual(self.ref.categorie_source(l, source), categorie)

    def test_migration_additive_des_anciennes_listes(self):
        with open(os.path.join(self.dossier, "referentiel_identification.json"), "w", encoding="utf-8") as f:
            json.dump({"version": self.ref.VERSION, "automates": ["M340", "SOFREL S4W", "Maison XYZ"],
                       "protocoles": ["Modbus TCP"]}, f)
        l = self.ref.lire()
        self.assertEqual(l["automates"][:3], ["M340", "SOFREL S4W", "Maison XYZ"])  # rien retiré ni renommé
        self.assertIn("Sch - M580", l["automates"])
        self.assertEqual(l["protocoles"][0], "Modbus TCP")
        self.assertIn("LACBUS IP", l["protocoles"])
        self.assertEqual(self.ref.categorie_source(l, "M340"), "Automate")
        self.assertEqual(self.ref.categorie_source(l, "Maison XYZ"), "Autres")        # aucune déduction
        self.assertEqual(self.ref.lire()["automates"].count("Sch - M580"), 1)       # migration une seule fois

    def test_categorie_saisie_avec_la_valeur(self):
        self.ref.modifier("ajouter", "automates", "Sch - M262", regie="Automate")
        self.assertEqual(self.ref.categorie_source(self.ref.lire(), "Sch - M262"), "Automate")
        with self.assertRaises(RegleMetier):
            self.ref.modifier("ajouter", "automates", "Sch - X", regie="Inventée")
        self.ref.modifier("supprimer", "automates", ancien="Sch - M262")
        self.assertNotIn("Sch - M262", self.ref.lire()["categories_sources"])


class TestSourcesEtPlateformes(unittest.TestCase):
    def test_reconnaissance_des_sources(self):
        pts = [PointES("e", "R", "ET", f"n{i}", "EBOOL", "", "", "", f"c{i}") for i in range(4)]
        self.assertEqual(materiel.proposer(pts, "Sch - M340").plateforme, "M340")
        self.assertEqual(materiel.proposer(pts, "Sof - S4W Small").plateforme, "S4W")
        p = materiel.proposer(pts, "Sch - STBNIP2311")
        self.assertEqual(p.racks[0]["nim"], "STB NIP 2311")                     # référence de la source reprise
        self.assertTrue(any("à titre indicatif" in r for r in p.remarques))
        for non_decrite in ("Sch - M221", "Sch - Micro TSX37", "Sch - SCADAPack 474", "Sof - S500"):
            with self.assertRaises(materiel.CatalogueMaterielErreur):
                materiel.proposer(pts, non_decrite)


if __name__ == "__main__":
    unittest.main()
