"""Outils d'ingénierie de l'ouvrage (18/11/2026) : les règles propres à un outil ne s'appliquent que s'il est choisi ;
aucune contrainte n'est devinée pour un outil non décrit. Ouvrages fictifs (lieu XTST)."""
import unittest

from genvar import outils
from genvar.existant import controler_existant
from genvar.modele import Ouvrage, VariableExistante
from tests.test_coherence import nouvelle
from genvar.modele import Equipement


class TestOutils(unittest.TestCase):
    def test_gamme_reconnue_quel_que_soit_le_libelle(self):
        for nom, gamme in (("M340", "M340"), ("Sch - M340", "M340"), ("Sch - M580", "M580"), ("Sof - S4W Dual", "S4W"),
                           ("Sch - M221", None), ("", None)):
            with self.subTest(nom=nom):
                self.assertEqual(outils.gamme_automate(Ouvrage(automate=nom)), gamme)
                self.assertEqual(outils.adresse_paire_32_bits(Ouvrage(automate=nom)), gamme in ("M340", "M580"))

    def test_supervision_par_defaut_et_libelle(self):
        self.assertEqual(Ouvrage().supervision, "TOPKAPI")             # comportement d'avant le 18/11 conservé
        self.assertEqual(outils.libelle_max(Ouvrage()), 40)
        self.assertIsNone(outils.libelle_max(Ouvrage(supervision="Autre supervision")))
        self.assertEqual(Ouvrage.depuis_dict({"lieu": "XTST"}).supervision, "TOPKAPI")   # ancien fichier
        r = outils.resume(Ouvrage(automate="Sch - M340"))
        self.assertEqual(r["gamme"], "M340")
        self.assertEqual(len(r["contraintes"]), 2)

    def test_existant_sch_m340_adresse_impaire_detectee(self):
        """Défaut corrigé le 18/11 : avec « Sch - M340 », le contrôle d'adresse paire ne se déclenchait plus."""
        for automate, attendu in (("Sch - M340", True), ("M580", True), ("Sch - M221", False)):
            with self.subTest(automate=automate):
                o = Ouvrage(mode="Existant", automate=automate,
                            existantes=[VariableExistante("CP_XTST_FICTIF", "DINT", "%MW101")])
                codes = {a.code for a in controler_existant(o, None)}
                self.assertEqual("R-EXI-03" in codes, attendu)


class TestReglesSelonLesOutils(unittest.TestCase):
    def ouvrage(self, automate="Sch - M580", supervision="TOPKAPI"):
        s = nouvelle(automate)
        s.ouvrage.supervision = supervision
        e = s.ajouter_equipement(Equipement("00", "PM", "01"))
        s.decider_propositions(e.ident, "retenir")
        return s

    def codes(self, s, adresse=None, libelle=None):
        vs = s.variables()
        v = next(x for x in vs if x.type_logique in ("DINT", "UDINT", "REAL"))
        if adresse:
            v.adresse = adresse
        if libelle:
            v.libelle_topkapi = libelle
        return {a.code for a in s.anomalies(vs)}

    def test_adresse_paire_seulement_sur_m340_m580(self):
        self.assertIn("R-VAR-07", self.codes(self.ouvrage("Sch - M580"), adresse="%MW3501"))
        self.assertNotIn("R-VAR-07", self.codes(self.ouvrage("Sch - M221"), adresse="%MW3501"))

    def test_libelle_40_seulement_avec_topkapi(self):
        long = "Libellé fictif volontairement beaucoup trop long pour TOPKAPI"
        self.assertIn("R-VAR-10", self.codes(self.ouvrage(supervision="TOPKAPI"), libelle=long))
        self.assertNotIn("R-VAR-10", self.codes(self.ouvrage(supervision="Autre supervision"), libelle=long))


if __name__ == "__main__":
    unittest.main()
