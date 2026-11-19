"""Attributs d'équipement définis par l'atelier (lot 4, 19/11/2026) : définitions, saisie, règles, modèles,
aller-retour Excel. Ouvrage fictif (lieu XTST)."""
import os
import tempfile
import unittest
from unittest import mock

from genvar import aller_retour, attributs, modeles_livrables as ml, tableur
from genvar.export_xlsx import ecrire_xlsx
from genvar.inbound import InputKind, RowAction, preview_import, stage_import
from genvar.modele import Equipement
from genvar.session import RegleMetier
from tests.test_coherence import nouvelle


class AvecAtelier(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self.dossier.cleanup)
        p = mock.patch.dict(os.environ, {"SOREP_DATA_DIR": self.dossier.name})
        p.start()
        self.addCleanup(p.stop)
        attributs.creer({"code": "PUISSANCE", "nom": "Puissance", "type": "nombre", "unite": "kW", "types": ["PM"],
                         "obligatoire": True})
        attributs.creer({"code": "ALIM", "nom": "Alimentation", "type": "liste", "valeurs": ["230 V", "400 V"]})
        attributs.creer({"code": "SECOURS", "nom": "Secouru", "type": "oui_non"})
        self.s = nouvelle()
        self.pm = self.s.ajouter_equipement(Equipement("00", "PM", "01", "Pompe fictive"))
        self.hv = self.s.ajouter_equipement(Equipement("00", "HV", "01", "Vanne fictive"))


class TestDefinitions(AvecAtelier):
    def test_validation_par_type(self):
        a = {x["code"]: x for x in attributs.lister()}
        self.assertEqual(attributs.valider(a["PUISSANCE"], " 7.50 "), "7,5")
        self.assertEqual(attributs.valider(a["ALIM"], "400 v"), "400 V")
        self.assertEqual(attributs.valider(a["SECOURS"], "oui"), "Oui")
        for code, v in (("PUISSANCE", "beaucoup"), ("ALIM", "24 V"), ("SECOURS", "peut-être")):
            with self.subTest(code=code), self.assertRaises(attributs.AttributRefuse):
                attributs.valider(a[code], v)

    def test_code_et_type_figes_archivage(self):
        with self.assertRaisesRegex(attributs.AttributRefuse, "existe déjà"):
            attributs.creer({"code": "ALIM", "nom": "Doublon", "type": "texte"})
        with self.assertRaisesRegex(attributs.AttributRefuse, "Code"):
            attributs.creer({"code": "9X", "nom": "Mauvais code", "type": "texte"})
        m = attributs.modifier("ALIM", {"nom": "Tension", "type": "texte", "valeurs": ["230 V"]})
        self.assertEqual((m["type"], m["valeurs"]), ("liste", ["230 V"]))     # type inchangé
        attributs.archiver("SECOURS")
        self.assertNotIn("SECOURS", {a["code"] for a in attributs.lister(actifs_seulement=True)})


class TestSaisieEtRegles(AvecAtelier):
    def test_saisie_regles_et_hors_liste(self):
        codes = lambda: {a.code for a in self.s.anomalies() if a.ident_eq == self.pm.ident}
        self.assertIn("R-ATT-01", codes())
        self.assertEqual(self.s.definir_attribut(self.pm.ident, "PUISSANCE", "15"), "15")
        self.assertNotIn("R-ATT-01", codes())
        with self.assertRaisesRegex(RegleMetier, "ne concerne pas"):
            self.s.definir_attribut(self.hv.ident, "PUISSANCE", "3")
        with self.assertRaisesRegex(RegleMetier, "hors liste"):
            self.s.definir_attribut(self.pm.ident, "ALIM", "24 V")
        self.s.definir_attribut(self.pm.ident, "ALIM", "400 V")
        attributs.modifier("ALIM", {"nom": "Alimentation", "valeurs": ["230 V"]})
        self.assertIn("R-ATT-02", codes())                                     # valeur conservée, signalée
        self.assertEqual(self.pm.attributs["ALIM"], "400 V")
        self.s.definir_attribut(self.pm.ident, "ALIM", "")
        self.assertNotIn("ALIM", self.pm.attributs)

    def test_variables_de_modele(self):
        self.s.definir_attribut(self.pm.ident, "PUISSANCE", "15")
        texte = "<#DEBUT_EQUIPEMENTS#><#REPERE#>=<#ATTR_PUISSANCE#>;<#FIN_EQUIPEMENTS#>"
        self.assertEqual(ml.analyser(texte)[1], [])
        self.assertEqual(ml.remplir(texte, self.s), "XTSTRV01HV01=;XTSTRV01PM01=15;")
        self.assertTrue(any("attribut" in e for e in ml.analyser("<#DEBUT_EQUIPEMENTS#><#ATTR_INCONNU#><#FIN_EQUIPEMENTS#>")[1]))


class TestAllerRetour(AvecAtelier):
    def test_colonnes_d_attributs(self):
        f = os.path.join(self.dossier.name, "liste.xlsx")
        aller_retour.exporter(f, self.s.ouvrage)
        feuille = tableur.lire_classeur(f)["Équipements"]
        entetes = [str(x) for x in feuille[0]]
        self.assertIn("Puissance (kW) [PUISSANCE]", entetes)
        i_p, i_a = entetes.index("Puissance (kW) [PUISSANCE]"), entetes.index("Alimentation [ALIM]")
        lignes = [list(map(str, x)) for x in feuille[1:]]
        hv = next(x for x in lignes if x[0].endswith("HV01"))
        pm = next(x for x in lignes if x[0].endswith("PM01"))
        self.assertEqual(hv[i_p], "—")
        pm[i_p], pm[i_a] = "18,5", "230 v"
        ecrire_xlsx(f, [("Équipements", feuille[0], lignes, [20] * len(entetes))])
        apercu = preview_import(f, InputKind.EQUIPMENT_SYNC, self.s)
        ligne = next(r for r in apercu.rows if r.values["repere"].endswith("PM01"))
        self.assertEqual(ligne.action, RowAction.UPDATE)
        self.assertIn("Puissance : «  » → « 18,5 »", ligne.values["changements"])
        copie = stage_import(apercu, self.s, confirmed=True).session
        pm_copie = copie.ouvrage.equipement(self.pm.ident)
        self.assertEqual(pm_copie.attributs, {"PUISSANCE": "18,5", "ALIM": "230 V"})
        pm[i_a] = "24 V"
        ecrire_xlsx(f, [("Équipements", feuille[0], lignes, [20] * len(entetes))])
        self.assertIn("ATTRIBUT_INVALIDE", {d.code for d in preview_import(f, InputKind.EQUIPMENT_SYNC, self.s).errors})


if __name__ == "__main__":
    unittest.main()
