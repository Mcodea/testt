"""V1-3-02 / V1-3-03 : suffixe proposé sans troncature et lexique, objet du référentiel."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from openpyxl import load_workbook

from genvar import chemins, lexique as lx, modeles
from genvar import referentiel_excel as rx
from genvar.catalogue import Catalogue
from genvar.referentiel_depot import Depot, DepotRefuse, controler_modeles, editer
from genvar.session import Session

ROOT = Path(__file__).resolve().parents[1]
LEX = [lx.entree("défaut", "DEF"), lx.entree("alimentation", "ALIM"), lx.entree("défaut d'alimentation", "DEF_ALIM"),
       lx.entree("230 v", "230V")]


class TestProposition(unittest.TestCase):
    def test_normalisation(self):
        self.assertEqual(lx.normaliser("Défaut d'alimentation, 24 V"), "DEFAUT D ALIMENTATION 24 V")

    def test_expression_la_plus_longue_d_abord(self):
        self.assertEqual(lx.abreger("Défaut d'alimentation 230 V", LEX), "DEF_ALIM_230V")
        self.assertEqual(lx.abreger("Défaut pompe", LEX), "DEF_POMPE")

    def test_jamais_tronque_et_alerte_au_dela_de_12(self):
        suffixe = lx.proposer_suffixe("Température enroulement moteur", (), LEX)
        self.assertEqual(suffixe, "TEMPERATURE_ENROULEMENT_MOTEUR")
        self.assertEqual(lx.alerte(suffixe), "suffixe à raccourcir")
        self.assertEqual(lx.alerte("DEF_ALIM"), "")
        self.assertEqual(lx.alerte("X" * 12), "")

    def test_code_du_catalogue_prioritaire(self):
        self.assertEqual(lx.proposer_suffixe("Défaut alimentation", (), LEX, {"DEFAUT ALIMENTATION": "DALIM"}), "DALIM")

    def test_unicite_et_mots_vides(self):
        self.assertEqual(lx.proposer_suffixe("Défaut", {"DEF"}, LEX), "DEF_2")
        self.assertEqual(lx.abreger("Mise en service de la pompe", LEX), "MISE_SERVICE_POMPE")
        self.assertEqual(lx.abreger("Redémarrage API A", LEX), "REDEMARRAGE_API_A")
        self.assertEqual(lx.abreger("de la", LEX), "INFO")

    def test_codes_du_catalogue_par_type(self):
        cat = Catalogue.charger(chemins.fichier_catalogue_origine())
        codes = lx.codes_du_catalogue(cat, "GA")
        self.assertEqual(codes[lx.normaliser("Intrusion")], "INTR")
        self.assertEqual(lx.codes_du_catalogue(None, "GA"), {})

    def test_import_de_base_annote_la_longueur(self):
        feuilles = {"F": [["COD_TYP_MAT", "NOM_MODELE", "COD_ROLE", "LIB_SIGNIF"],
                          ["PM", "Modèle essai", "TS", "TS Température enroulement moteur"]]}
        ref = modeles.extraire(feuilles, "essai", lexique=LEX)
        ligne = ref["modeles"]["Modèle essai"]["lignes"][0]
        self.assertEqual(ligne["suffixe"], "TEMPERATURE_ENROULEMENT_MOTEUR")
        self.assertIn("suffixe à raccourcir", ligne["commentaire"])


class TestControles(unittest.TestCase):
    def test_doublon_conflictuel_bloque_doublon_identique_alerte(self):
        erreurs, alertes = lx.controler([lx.entree("verrouillé", "VERR"), lx.entree("verrouille", "VERR")])
        self.assertEqual((erreurs, len(alertes)), ([], 1))
        erreurs, _ = lx.controler([lx.entree("verrouillé", "VERR"), lx.entree("verrouille", "VER")])
        self.assertEqual(len(erreurs), 1)

    def test_entrees_invalides(self):
        erreurs, _ = lx.controler([{"mot": "", "abreviation": "X", "nature": "Mot"},
                                   {"mot": "pompe", "abreviation": "po mpe", "nature": "Mot"},
                                   {"mot": "pompe2", "abreviation": "P2", "nature": "Autre"}, "texte"])
        self.assertEqual(len(erreurs), 4)
        self.assertEqual(lx.controler("x")[0], ["Lexique : liste d'entrées attendue."])

    def test_abreviation_trop_longue_alerte(self):
        self.assertEqual(len(lx.controler([lx.entree("mot", "ABCDEFGHIJKLM")])[1]), 1)


class TestLexiqueLivre(unittest.TestCase):
    def test_lexique_livre_conforme_au_classeur(self):
        livre = json.loads((ROOT / "genvar/data/referentiel_modeles.json").read_text(encoding="utf-8"))["lexique"]
        wb = load_workbook(ROOT / "docs/referentiel/OGIAS_V031_informations_modeles.xlsx", read_only=True)
        try:
            source = [r for r in list(wb["Lexique"].values)[1:] if r[0]]
        finally:
            wb.close()
        attendu = {lx.normaliser(r[0]): (r[1], r[2], r[3] == "Oui") for r in source}
        self.assertEqual({lx.normaliser(e["mot"]): (e["abreviation"], e["nature"], e["dictionnaire_es"]) for e in livre},
                         attendu)
        self.assertEqual(len(livre), 354)                    # « verrouille » / « verrouillé » : une seule entrée
        self.assertEqual(lx.controler(livre), ([], []))
        self.assertEqual(modeles.lexique_livre(), livre)


class TestDepotEtExcel(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier
        self.depot = Depot()
        self.donnees = self.depot.publie()

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def test_edition_du_lexique_dans_le_brouillon(self):
        d, msg = editer(self.donnees, "ajouter_lexique", champs={"mot": "Surpresseur", "abreviation": "surp"})
        self.assertIn("ajouté", msg)
        self.assertIn({"mot": "Surpresseur", "abreviation": "SURP", "nature": "Mot", "dictionnaire_es": False},
                      d["modeles"]["lexique"])
        d, _ = editer(d, "modifier_lexique", "surpresseur", {"abreviation": "SURPR"})
        self.assertEqual(d["modeles"]["lexique"][-1]["abreviation"], "SURPR")
        with self.assertRaises(DepotRefuse):
            editer(d, "ajouter_lexique", champs={"mot": "SURPRESSEUR", "abreviation": "S"})
        with self.assertRaises(DepotRefuse):
            editer(d, "modifier_lexique", "surpresseur", {"mot": "autre"})
        with self.assertRaises(DepotRefuse):
            editer(d, "ajouter_lexique", champs={"mot": "x", "abreviation": "X", "inconnu": 1})
        with self.assertRaises(DepotRefuse):
            editer(d, "supprimer_lexique", "absent")
        with self.assertRaises(DepotRefuse):
            editer(d, "ajouter_lexique", champs={"abreviation": "X"})
        d, _ = editer(d, "supprimer_lexique", "Surpresseur")
        self.assertEqual(d["modeles"]["lexique"], self.donnees["modeles"]["lexique"])
        self.assertFalse(any(e["mot"] == "Surpresseur" for e in self.donnees["modeles"]["lexique"]))   # copie

    def test_controle_du_brouillon(self):
        cat, ref = Depot.objets(self.donnees)
        self.assertEqual(controler_modeles(ref, cat)[0], [])
        ref["lexique"].append(lx.entree("verrouille", "VER"))
        ref["modeles"]["UF usine"]["lignes"][0]["suffixe"] = "SUFFIXE_TROP_LONG"
        erreurs, alertes = controler_modeles(ref, cat)
        self.assertTrue(any("deux abréviations" in e for e in erreurs))
        self.assertTrue(any("suffixe à raccourcir" in a for a in alertes))

    def test_publication_versionne_le_lexique(self):
        self.depot.creer_brouillon("essai")
        b = self.depot.brouillon()
        d, motif = editer(b["donnees"], "ajouter_lexique", champs={"mot": "Surpresseur", "abreviation": "SURP"})
        self.depot.remplacer_donnees(d, motif)
        v = self.depot.valider("essai")
        r = self.depot.publier("lexique", v["empreinte_validee"], "essai")
        archive = self.depot.revision(r["revision"])["donnees"]["modeles"]["lexique"]
        self.assertEqual(archive[-1]["mot"], "Surpresseur")
        self.assertEqual(self.depot.publie()["modeles"]["lexique"][-1]["abreviation"], "SURP")

    def _session_et_classeur(self):
        s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        f = os.path.join(self.dossier, "ref.xlsx")
        s.exporter_referentiel(f)
        self.depot.creer_brouillon("essai")
        return s, f

    def test_export_import_du_lexique(self):
        s, f = self._session_et_classeur()
        nouveau, lect, _ = rx.lire(f)
        self.assertEqual(len(nouveau["lexique"]), 354)
        cat, ref = rx.construire(nouveau, s._catalogue_commun, modeles.charger())
        self.assertEqual(ref["lexique"], modeles.charger()["lexique"])
        wb = load_workbook(f)
        ws = wb["Lexique"]
        ws.cell(ws.max_row + 1, 1, "Surpresseur")
        ws.cell(ws.max_row, 2, "SURP")
        ws.cell(ws.max_row, 3, "Mot")
        wb.save(f)
        r = s.analyser_classeur_referentiel(f)
        self.assertEqual(r["erreurs"], [])
        self.assertIn(("entrée de lexique", "SURPRESSEUR", "ajout"),
                      [(x["objet"], x["id"], x["action"]) for x in r["differences"]])

    def test_entree_disparue_bloque_l_import(self):
        s, f = self._session_et_classeur()
        wb = load_workbook(f)
        wb["Lexique"].delete_rows(2)
        wb.save(f)
        r = s.analyser_classeur_referentiel(f)
        self.assertTrue(any("entrée(s) de lexique" in e for e in r["erreurs"]))

    def test_export_anterieur_sans_onglet_lexique(self):
        s, f = self._session_et_classeur()
        wb = load_workbook(f)
        del wb["Lexique"]
        wb.save(f)
        nouveau, lect, _ = rx.lire(f)
        self.assertIsNone(nouveau["lexique"])
        self.assertTrue(any("lexique en service est conservé" in a for a in lect.alertes))
        cat, ref = rx.construire(nouveau, s._catalogue_commun, modeles.charger())
        self.assertEqual(ref["lexique"], modeles.charger()["lexique"])
