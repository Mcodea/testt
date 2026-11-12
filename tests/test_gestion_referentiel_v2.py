"""L6 : dupliquer, archiver, suppression bloquée si utilisée, correspondances éditables et exportées."""
import os
import tempfile
import unittest

from openpyxl import load_workbook

from genvar import chemins
from genvar import referentiel_excel as rx
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.referentiel_depot import Depot, DepotRefuse, editer
from genvar.session import RegleMetier, Session


class Base(unittest.TestCase):
    def setUp(self):
        self.env = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier
        self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        self.nom = next(n for n, m in self.s.modeles["modeles"].items() if m["lignes"])
        self.type = self.s.modeles["modeles"][self.nom]["type"]

    def tearDown(self):
        if self.env is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.env

    def projet_avec(self, modele):
        s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s.nouveau(False)
        s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
        s.ajouter_sous_ensemble("00")
        s.ajouter_equipement(Equipement("00", self.type, "01", modele=modele))
        f = os.path.join(chemins.dossier_projets(), "essai.ouvrage.json")
        s.enregistrer(f)
        return s


class TestModeles(Base):
    def test_dupliquer_cree_des_lignes_neuves_sans_toucher_l_original(self):
        original = [dict(l) for l in self.s.modeles["modeles"][self.nom]["lignes"]]
        n = self.s.dupliquer_modele(self.nom, "Copie d'essai")
        copie = self.s.modeles["modeles"][n]
        self.assertEqual((copie["statut"], copie["duplique_de"], copie["type"]), ("à valider", self.nom, self.type))
        self.assertEqual([l["libelle"] for l in copie["lignes"]], [l["libelle"] for l in original])
        self.assertFalse({l["id"] for l in copie["lignes"]} & {l["id"] for l in original})
        self.assertEqual(self.s.modeles["modeles"][self.nom]["lignes"], original)
        self.assertIn(n, self.s.modeles["types"][self.type]["modeles"])
        for nom in ("", self.nom):
            with self.assertRaises(RegleMetier):
                self.s.dupliquer_modele(self.nom, nom)

    def test_modele_archive_non_propose_mais_conserve(self):
        self.s.archiver_modele(self.nom)
        offerts = next(t for t in self.s.types_disponibles() if t["code"] == self.type)["modeles"]
        self.assertNotIn(self.nom, offerts)
        self.assertIn(self.nom, self.s.modeles["modeles"])
        self.s.nouveau(False)
        self.s.definir("lieu", "XTST"); self.s.definir("code_ouvrage", "RV"); self.s.ouvrage.numero_ouvrage = "01"
        self.s.ajouter_sous_ensemble("00")
        with self.assertRaisesRegex(RegleMetier, "archivé"):
            self.s.ajouter_equipement(Equipement("00", self.type, "01", modele=self.nom))
        self.s.archiver_modele(self.nom, False)
        self.assertEqual(self.s.modeles["modeles"][self.nom]["statut"], "à valider")

    def test_type_archive_non_propose(self):
        self.s.archiver_type(self.type)
        self.assertNotIn(self.type, {t["code"] for t in self.s.types_disponibles()})
        self.s.archiver_type(self.type, False)
        self.assertIn(self.type, {t["code"] for t in self.s.types_disponibles()})
        with self.assertRaises(RegleMetier):
            self.s.archiver_type("ZZ")

    def test_suppression_bloquee_si_employe_par_un_projet(self):
        self.projet_avec(self.nom)
        with self.assertRaisesRegex(RegleMetier, "archivez-le"):
            self.s.supprimer_modele(self.nom)
        self.assertIn(self.nom, self.s.modeles["modeles"])
        n = self.s.dupliquer_modele(self.nom, "Inutilisé")
        self.s.supprimer_modele(n)                                      # non employé : suppression permise
        self.assertNotIn(n, self.s.modeles["modeles"])

    def test_suppression_de_type_employe_bloquee(self):
        self.projet_avec("")
        self.s.modeles["types"].setdefault(self.type, {"modeles": []})
        self.s.modeles["types"][self.type]["modeles"] = []
        with self.assertRaisesRegex(RegleMetier, "archivez-le"):
            self.s.supprimer_type(self.type)


class TestCorrespondances(Base):
    def test_edition_dans_le_brouillon(self):
        d = Depot().publie()
        n = len(d["modeles"]["correspondances"])
        d2, _ = editer(d, "ajouter_correspondance", champs={"type": "ga", "ancienne": "ts_ancien", "nouvelle": "ts_intr",
                                                            "motif": "essai"})
        self.assertEqual(d2["modeles"]["correspondances"][-1],
                         {"type": "GA", "ancienne": "TS_ANCIEN", "type_nouveau": "GA", "nouvelle": "TS_INTR",
                          "motif": "essai"})
        for champs in ({"type": "GA", "ancienne": "TS_ANCIEN", "nouvelle": "TS_DEF", "motif": "x"},   # ambiguë
                       {"type": "GA", "ancienne": "TS_B", "nouvelle": "TS_INTR"},                     # sans motif
                       {"type": "GA", "ancienne": "", "nouvelle": "TS_INTR", "motif": "x"},
                       {"type": "GA", "ancienne": "X", "nouvelle": "Y", "motif": "x", "z": 1}):
            with self.assertRaises(DepotRefuse):
                editer(d2, "ajouter_correspondance", champs=champs)
        d3, _ = editer(d2, "supprimer_correspondance", "ga.ts_ancien")
        self.assertEqual(len(d3["modeles"]["correspondances"]), n)
        with self.assertRaises(DepotRefuse):
            editer(d3, "supprimer_correspondance", "GA.ABSENT")
        cat, ref = Depot.objets(d2)
        from genvar.referentiel_depot import controler_modeles
        self.assertEqual(controler_modeles(ref, cat)[0], [])

    def test_export_import_des_correspondances(self):
        f = os.path.join(self.dossier, "ref.xlsx")
        self.s.exporter_referentiel(f)
        nouveau, _, _ = rx.lire(f)
        self.assertEqual({(c["type"], c["ancienne"]) for c in nouveau["correspondances"]},
                         {("CT", "CP_VOL"), ("CT", "TS_ABSIMP")})
        _, ref = rx.construire(nouveau, self.s._catalogue_commun, self.s.modeles)
        self.assertEqual(ref["correspondances"], self.s.modeles["correspondances"])
        wb = load_workbook(f)
        del wb["Correspondances"]
        wb.save(f)
        nouveau, _, _ = rx.lire(f)
        self.assertIsNone(nouveau["correspondances"])
        _, ref = rx.construire(nouveau, self.s._catalogue_commun, self.s.modeles)
        self.assertEqual(ref["correspondances"], self.s.modeles["correspondances"])


class TestArchivageExcel(Base):
    def preparer(self):
        self.s.archiver_type(self.type)
        fichier = os.path.join(self.dossier, "reference.xlsx")
        rx.exporter(self.s._catalogue_commun, self.s.modeles, fichier)
        return fichier

    def test_export_import_conserve_archivage_du_type(self):
        fichier = self.preparer()
        nouveau, lecture, _ = rx.lire(fichier)
        self.assertEqual(lecture.erreurs, [])
        _, ref = rx.construire(nouveau, self.s._catalogue_commun, self.s.modeles)
        self.assertTrue(ref["types"][self.type]["archive"])
        self.assertEqual(rx.etat(self.s._catalogue_commun, ref), rx.etat(self.s._catalogue_commun, self.s.modeles))

    def test_ancien_classeur_sans_colonne_ne_reactive_pas_un_type(self):
        fichier = self.preparer()
        wb = load_workbook(fichier)
        ws = wb["Types de modèles"]
        colonne = [c.value for c in ws[1]].index("Archivé") + 1
        ws.delete_cols(colonne)
        wb.save(fichier)
        nouveau, lecture, _ = rx.lire(fichier)
        self.assertEqual(lecture.erreurs, [])
        _, ref = rx.construire(nouveau, self.s._catalogue_commun, self.s.modeles)
        self.assertTrue(ref["types"][self.type]["archive"])

    def test_desarchivage_explicite_via_excel(self):
        fichier = self.preparer()
        wb = load_workbook(fichier)
        ws = wb["Types de modèles"]
        colonne = [c.value for c in ws[1]].index("Archivé") + 1
        for row in ws.iter_rows(min_row=2):
            if row[0].value == self.type:
                row[colonne-1].value = "Non"
        wb.save(fichier)
        nouveau, lecture, _ = rx.lire(fichier)
        self.assertEqual(lecture.erreurs, [])
        _, ref = rx.construire(nouveau, self.s._catalogue_commun, self.s.modeles)
        self.assertFalse(ref["types"][self.type]["archive"])

    def test_valeur_archive_inconnue_refusee(self):
        fichier = self.preparer()
        wb = load_workbook(fichier)
        ws = wb["Types de modèles"]
        colonne = [c.value for c in ws[1]].index("Archivé") + 1
        ws.cell(2, colonne).value = "inconnu"
        wb.save(fichier)
        _, lecture, _ = rx.lire(fichier)
        self.assertTrue(any("Archivé : choisissez Oui ou Non" in e for e in lecture.erreurs))

    def test_feuille_types_vide_signalee_sans_exception(self):
        fichier = self.preparer()
        wb = load_workbook(fichier)
        wb["Types de modèles"].delete_rows(1, wb["Types de modèles"].max_row)
        wb.save(fichier)
        _, lecture, _ = rx.lire(fichier)
        self.assertTrue(any("Types de modèles : onglet vide" in e for e in lecture.erreurs))

    def test_modele_explicitement_sans_signaux_ne_recoit_pas_ceux_du_type(self):
        from genvar import modeles
        nom = next(n for n, m in self.s.modeles["modeles"].items() if m["type"] == "HV")
        self.s.modeles["modeles"][nom]["signaux"] = []
        fichier = os.path.join(self.dossier, "sans-es.xlsx")
        rx.exporter(self.s._catalogue_commun, self.s.modeles, fichier)
        nouveau, lecture, _ = rx.lire(fichier)
        self.assertEqual(lecture.erreurs, [])
        cat, ref = rx.construire(nouveau, self.s._catalogue_commun, self.s.modeles)
        modeles.completer_signaux(ref, cat)
        self.assertEqual(ref["modeles"][nom]["signaux"], [])
