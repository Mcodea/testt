"""Table de télétransmission (projet existant) : règles de décision et de statut."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, VariableExistante
from genvar.session import Session, RegleMetier


def ouvrage_essai():
    s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
    s.definir("mode", "Existant")
    for champ, val in (("lieu", "F999"), ("code_ouvrage", "RV"), ("libelle", "Essai"), ("automate", "M340")):
        s.definir(champ, val)
    s.ajouter_sous_ensemble("21", "Station")
    s.ouvrage.equipements.append(Equipement("21", "PM", "02", "Pompe 2"))
    s.ouvrage.existantes = [
        VariableExistante("TS_F999RV21PM02_MA", "BOOL", "%MW1000.0", "POMPE 2 EN MARCHE"),
        VariableExistante("P2_HEURES", "DINT", "%MW3500", "Compteur heures pompe 2"),
        VariableExistante("P2_HEURES_IMPAIR", "DINT", "%MW3501", "Heures pompe 2 (adresse impaire)"),
        VariableExistante("I_P2", "EBOOL", "%I0.1.4", "Entrée marche pompe 2"),
        VariableExistante("NIVEAU", "REAL", "%MW2500", "Niveau"),
    ]
    s.construire_table()
    return s


class TestTableTeletransmission(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = tempfile.mkdtemp()
        self.s = ouvrage_essai()
        self.eq = self.s.ouvrage.equipements[0].ident

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def statut(self, cle):
        return next(x for x in self.s.table() if x.ligne.cle == cle).statut

    def test_une_ligne_par_information_attendue_avec_nom_standard(self):
        lignes = self.s.table()
        cles = {x.ligne.cle for x in lignes}
        self.assertIn("TS_MA", cles)
        self.assertIn("CP_HF", cles)
        self.assertNotIn("TC_MA", cles)                    # option non choisie : pas attendue
        ma = next(x for x in lignes if x.ligne.cle == "TS_MA")
        self.assertEqual(ma.nom_standard, "TS_F999RV21PM02_MA")
        self.assertEqual(ma.sens, "Remontée")
        self.assertTrue(all(x.statut == "Sans source" for x in lignes))

    def test_proposition_ne_valide_rien(self):
        n = self.s.proposer_associations()
        self.assertGreaterEqual(n, 1)
        ma = next(x for x in self.s.table() if x.ligne.cle == "TS_MA")
        self.assertEqual(ma.variable_source, "TS_F999RV21PM02_MA")
        self.assertEqual(ma.statut, "À compléter")
        self.assertFalse(ma.ligne.fonction_validee or ma.ligne.acces_verifie)
        self.assertTrue(ma.ligne.preuves)                  # les raisons sont conservées

    def test_double_validation_pour_le_vert(self):
        self.s.associer(self.eq, "TS_MA", "TS_F999RV21PM02_MA")
        self.s.valider_fonction(self.eq, "TS_MA")
        self.assertEqual(self.statut("TS_MA"), "À compléter")      # accès non vérifié
        with self.assertRaises(RegleMetier):
            self.s.definir_acces(self.eq, "TS_MA", verifie=True)  # pas de protocole
        self.s.definir_acces(self.eq, "TS_MA", protocole="Modbus TCP", verifie=True)
        self.assertEqual(self.statut("TS_MA"), "Validée")
        # changer de source remet les deux validations à zéro
        self.s.dissocier(self.eq, "TS_MA")
        self.assertEqual(self.statut("TS_MA"), "Sans source")

    def test_incoherences_rouges(self):
        with self.assertRaises(RegleMetier):                       # REAL pour un BOOL : refusé
            self.s.associer(self.eq, "TS_MA", "NIVEAU")
        self.s.associer(self.eq, "CP_HF", "P2_HEURES_IMPAIR")
        self.assertEqual(self.statut("CP_HF"), "Incohérence")       # 32 bits impair sur M340
        self.s.associer(self.eq, "CP_NDEM", "P2_HEURES")
        with self.assertRaises(RegleMetier):                        # une source = une seule ligne
            self.s.associer(self.eq, "CP_HF", "P2_HEURES")

    def test_source_disparue_apres_reimport(self):
        self.s.associer(self.eq, "CP_HF", "P2_HEURES")
        self.s.ouvrage.existantes = [v for v in self.s.ouvrage.existantes if v.nom != "P2_HEURES"]
        self.assertEqual(self.statut("CP_HF"), "Incohérence")

    def test_entree_physique_reste_a_demontrer(self):
        self.s.associer(self.eq, "TS_MA", "I_P2")
        ligne = next(x for x in self.s.table() if x.ligne.cle == "TS_MA")
        self.assertEqual(ligne.statut, "À compléter")
        self.assertIn("E/S physique", ligne.motif)

    def test_non_accessible_exige_un_motif_et_reste_visible(self):
        with self.assertRaises(RegleMetier):
            self.s.declarer_non_accessible(self.eq, "TS_HS", "")
        self.s.declarer_non_accessible(self.eq, "TS_HS", "Absent du programme : à créer lors des travaux")
        self.assertEqual(self.statut("TS_HS"), "Non accessible")
        self.assertIn("TS_HS", {x.ligne.cle for x in self.s.table()})

    def test_non_applicable_retire_la_ligne(self):
        self.s.signal_non_applicable(self.eq, "TS_HS")
        self.assertNotIn("TS_HS", {x.ligne.cle for x in self.s.table()})

    def test_aucune_donnee_source_modifiee(self):
        avant = [(v.nom, v.type_logique, v.adresse, v.commentaire) for v in self.s.ouvrage.existantes]
        self.s.proposer_associations()
        self.s.associer(self.eq, "CP_HF", "P2_HEURES")
        self.s.declarer_non_accessible(self.eq, "TS_HS", "absent")
        apres = [(v.nom, v.type_logique, v.adresse, v.commentaire) for v in self.s.ouvrage.existantes]
        self.assertEqual(avant, apres)

    def test_validation_ouvrage_bloquee_tant_que_lignes_orange(self):
        self.s.ouvrage.statut = "Validé"
        with self.assertRaises(RegleMetier):
            self.s.enregistrer(os.path.join(os.environ["SOREP_DATA_DIR"], "x.ouvrage.json"))

    def test_sauvegarde_et_relecture_des_decisions(self):
        self.s.associer(self.eq, "TS_MA", "TS_F999RV21PM02_MA")
        self.s.valider_fonction(self.eq, "TS_MA")
        self.s.declarer_non_accessible(self.eq, "TS_HS", "absent")
        chemin = os.path.join(os.environ["SOREP_DATA_DIR"], "tt.ouvrage.json")
        self.s.enregistrer(chemin)
        s2 = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s2.ouvrir(chemin)
        lignes = {x.ligne.cle: x for x in s2.table()}
        self.assertTrue(lignes["TS_MA"].ligne.fonction_validee)
        self.assertEqual(lignes["TS_HS"].statut, "Non accessible")

    def test_equipements_detectes_proposes_sans_creation(self):
        self.s.ouvrage.existantes.append(VariableExistante("TS_F999RV21MV05_OUV", "BOOL", "%MW1000.5", ""))
        n_avant = len(self.s.ouvrage.equipements)
        detectes = self.s.equipements_detectes()
        self.assertEqual([d.code for d in detectes], ["21MV05"])
        self.assertEqual(len(self.s.ouvrage.equipements), n_avant)       # rien créé sans accord
        self.s.ajouter_detectes(detectes)
        self.assertEqual(len(self.s.ouvrage.equipements), n_avant + 1)

    def test_export_excel(self):
        self.s.proposer_associations()
        chemin = os.path.join(os.environ["SOREP_DATA_DIR"], "tt.xlsx")
        self.s.exporter_excel(chemin)
        import zipfile
        with zipfile.ZipFile(chemin) as z:
            contenu = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertIn("TS_F999RV21PM02_MA", contenu)
        self.assertIn("Sans source", contenu)


if __name__ == "__main__":
    unittest.main()
