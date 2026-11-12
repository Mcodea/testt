"""V1-3-11 à V1-3-14 : dictionnaire des codes des E/S, objet du référentiel, et ses contrôles."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from openpyxl import load_workbook

from genvar import chemins, dictionnaire_es as de, modeles
from genvar import referentiel_excel as rx
from genvar.catalogue import Catalogue
from genvar.referentiel_depot import Depot, DepotRefuse, controler_modeles, editer
from genvar.session import Session

ROOT = Path(__file__).resolve().parents[1]


class TestControles(unittest.TestCase):
    def test_format_du_code(self):
        for code in ("N", "ABCDEFGHIJ", "NIV-B", "NIV B", ""):
            self.assertTrue(de.controler([de.entree(code, "ET", "Libellé")])[0], code)
        for code in ("NV", "ABCDEFGHI", "NIV_B", "MQ_24V"):
            self.assertEqual(de.controler([de.entree(code, "ET", "Libellé")]), ([], []), code)

    def test_nature_et_libelle_obligatoires(self):
        erreurs, _ = de.controler([de.entree("NIV", "XX", "Niveau"), de.entree("PRE", "EA", "")])
        self.assertEqual(len(erreurs), 2)
        self.assertEqual(de.controler("x")[0], ["Dictionnaire des E/S : liste d'entrées attendue."])
        self.assertEqual(len(de.controler(["x"])[0]), 1)

    def test_meme_code_deux_sens_est_une_erreur(self):
        erreurs, _ = de.controler([de.entree("DEF", "ET", "Défaut"), de.entree("DEF", "ET", "Défaut thermique")])
        self.assertIn("un même code avec deux sens", erreurs[0])

    def test_meme_code_dans_deux_natures_admis(self):
        self.assertEqual(de.controler([de.entree("NIV", "ET", "Niveau atteint"), de.entree("NIV", "EA", "Niveau")]),
                         ([], []))

    def test_repetition_identique_et_deux_codes_un_libelle_alertent(self):
        _, alertes = de.controler([de.entree("DEF", "ET", "Défaut"), de.entree("DEF", "ET", "défaut")])
        self.assertIn("répété à l'identique", alertes[0])
        erreurs, alertes = de.controler([de.entree("DEF", "ET", "Défaut"), de.entree("DFT", "ET", "Défaut")])
        self.assertEqual(erreurs, [])
        self.assertIn("deux codes pour un même libellé : DEF, DFT", alertes[0])

    def test_code_non_standard(self):
        dico = [de.entree("FDC_OUV", "ET", "Fin de course ouvert")]
        signaux = [{"type": "MV", "es": "ET", "code": "OUV", "organe": "FDC"},
                   {"type": "PM", "es": "ET", "code": "DEFTH", "organe": "DEF"},
                   {"type": "PM", "es": "Interne", "code": "X", "organe": ""}]
        self.assertEqual(de.codes_non_standard(signaux, dico),
                         ["Code non standard ET.DEFTH (types PM) : absent du dictionnaire des E/S."])
        self.assertEqual(de.codes_non_standard(signaux, []), [])

    def test_types_lus_depuis_un_texte(self):
        self.assertEqual(de.entree("niv", "ea", types="cu, da ;LT")["types"], ["CU", "DA", "LT"])


class TestDictionnaireLivre(unittest.TestCase):
    def test_conforme_au_classeur(self):
        livre = json.loads((ROOT / "genvar/data/referentiel_modeles.json").read_text(encoding="utf-8"))["dictionnaire_es"]
        wb = load_workbook(ROOT / "docs/referentiel/OGIAS_V031_bibliotheque_ES_physiques.xlsx", read_only=True)
        try:
            source = [r for r in list(wb["Dictionnaire"].values)[1:] if r[1] in de.NATURES]
        finally:
            wb.close()
        self.assertEqual(len(livre), 81)
        self.assertEqual(len({e["code"] for e in livre}), 80)
        attendu = [(r[0], r[1], r[3], r[4] or "") for r in source]
        # Corrections V2 documentées : ET.IMP alimente CP_VOL (TS_IMP n'existe pas, D7) ; CT supprimé (D2).
        attendu = [(c, n, lib, "CP_VOL" if (c, n) == ("IMP", "ET") else t) for c, n, lib, t in attendu]
        self.assertEqual([(e["code"], e["nature"], e["libelle"], e["teletransmission"]) for e in livre], attendu)
        self.assertFalse([e for e in livre if "CT" in e["types"]])
        self.assertEqual(de.controler(livre), ([], []))


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

    def test_edition_dans_le_brouillon(self):
        d, _ = editer(self.donnees, "ajouter_code_es", champs={"code": "niv_x", "nature": "et", "libelle": "Niveau X"})
        self.assertEqual(d["modeles"]["dictionnaire_es"][-1]["code"], "NIV_X")
        d, _ = editer(d, "modifier_code_es", "ET.NIV_X", {"libelle": "Niveau extrême"})
        self.assertEqual(d["modeles"]["dictionnaire_es"][-1]["libelle"], "Niveau extrême")
        for action, cible, champs in (("ajouter_code_es", "", {"code": "NIV_X", "nature": "ET", "libelle": "Autre"}),
                                      ("ajouter_code_es", "", {"code": "N", "nature": "ET", "libelle": "Court"}),
                                      ("ajouter_code_es", "", {"code": "AB", "nature": "ET", "libelle": "x", "z": 1}),
                                      ("modifier_code_es", "ET.NIV_X", {"code": "AUTRE"}),
                                      ("supprimer_code_es", "ET.ABSENT", {})):
            with self.assertRaises(DepotRefuse):
                editer(d, action, cible, champs)
        d, _ = editer(d, "supprimer_code_es", "et.niv_x")
        self.assertEqual(d["modeles"]["dictionnaire_es"], self.donnees["modeles"]["dictionnaire_es"])

    def test_controle_du_brouillon(self):
        cat, ref = Depot.objets(self.donnees)
        erreurs, alertes = controler_modeles(ref, cat)
        self.assertEqual(erreurs, [])
        self.assertTrue(any(a.startswith("Code non standard") for a in alertes))   # harmonisation en attente
        ref["dictionnaire_es"].append(de.entree("CIRC", "ET", "Autre sens"))
        self.assertTrue(any("deux sens" in e for e in controler_modeles(ref, cat)[0]))

    def _classeur(self):
        s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        f = os.path.join(self.dossier, "ref.xlsx")
        s.exporter_referentiel(f)
        self.depot.creer_brouillon("essai")
        return s, f

    def test_export_import(self):
        s, f = self._classeur()
        nouveau, _, _ = rx.lire(f)
        _, ref = rx.construire(nouveau, s._catalogue_commun, modeles.charger())
        self.assertEqual(ref["dictionnaire_es"], modeles.charger()["dictionnaire_es"])
        wb = load_workbook(f)
        ws = wb["Dictionnaire E-S"]
        ws.cell(2, 4, "Autre libellé")
        wb.save(f)
        r = s.analyser_classeur_referentiel(f)
        self.assertEqual(r["erreurs"], [])
        self.assertIn(("code du dictionnaire des E/S", "modification"),
                      [(x["objet"], x["action"]) for x in r["differences"]])

    def test_code_disparu_ou_invalide_bloque(self):
        s, f = self._classeur()
        wb = load_workbook(f)
        wb["Dictionnaire E-S"].delete_rows(2)
        wb["Dictionnaire E-S"].cell(2, 1, "X")
        wb.save(f)
        r = s.analyser_classeur_referentiel(f)
        self.assertTrue(any("code(s) du dictionnaire" in e for e in r["erreurs"]))
        self.assertTrue(any("2 à 9 caractères" in e for e in r["erreurs"]))

    def test_export_anterieur_sans_onglet(self):
        s, f = self._classeur()
        wb = load_workbook(f)
        del wb["Dictionnaire E-S"]
        wb.save(f)
        nouveau, lect, _ = rx.lire(f)
        self.assertIsNone(nouveau["dictionnaire_es"])
        _, ref = rx.construire(nouveau, s._catalogue_commun, modeles.charger())
        self.assertEqual(ref["dictionnaire_es"], modeles.charger()["dictionnaire_es"])
