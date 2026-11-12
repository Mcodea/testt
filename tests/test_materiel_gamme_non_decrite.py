"""Retour d'essai n° 8 (12/11/2026) : un automate d'une gamme non décrite ne reçoit jamais le matériel d'une autre."""
import unittest

from genvar import materiel
from genvar.modele import PointES


def _points():
    return [PointES("e1", "RV01MV01", "ET", f"ET_RV01MV01_X{i}", "EBOOL", "", "", "", f"ES_X{i}") for i in range(3)]


class TestGammeNonDecrite(unittest.TestCase):
    def test_gamme_inconnue_refusee_sans_repli_m340(self):
        with self.assertRaisesRegex(materiel.CatalogueMaterielErreur, "cette gamme.*Aucune configuration"):
            materiel.proposer(_points(), "TSX P57 4634")
        with self.assertRaisesRegex(materiel.CatalogueMaterielErreur, "cette gamme"):
            materiel.plateforme_materiel("TSX Premium P57")

    def test_gammes_decrites_inchangees(self):
        self.assertEqual(materiel.plateforme_materiel("BMXP342020")[0], "M340")
        self.assertEqual(materiel.plateforme("BMX P34 2020"), ("M340", ""))   # référence reconnue, sans remarque
        self.assertEqual(materiel.plateforme_materiel("BMEP584040")[0], "M580")
        self.assertEqual(materiel.plateforme_materiel("M580 BMEP58")[0], "M580")
        self.assertEqual(materiel.plateforme_materiel("SOFREL S4W")[0], "S4W")
        self.assertEqual(materiel.plateforme_materiel("STBNIP2212")[0], "STB")     # gamme décrite le 12/11
        self.assertEqual(materiel.plateforme_materiel("")[0], "M340")       # non renseigné : comportement documenté
        self.assertEqual(materiel.proposer(_points(), "BMX P34 2020").plateforme, "M340")
