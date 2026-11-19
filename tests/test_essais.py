"""Cahiers d'essais FAT / SAT (lot 3, 19/11/2026) : édition, report des résultats, suivi. Ouvrage fictif (XTST)."""
import os
import tempfile
import unittest

from genvar import essais, tableur
from genvar.export_xlsx import ecrire_xlsx
from genvar.modele import Equipement
from tests.test_coherence import nouvelle


def ouvrage():
    s = nouvelle()
    for t, n in (("HV", "01"), ("PM", "01")):
        e = s.ajouter_equipement(Equipement("00", t, n, "Fictif"))
        s.decider_propositions(e.ident, "retenir")
    return s


class TestCahiers(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self.dossier.cleanup)
        self.f = os.path.join(self.dossier.name, "cahier.xlsx")

    def remplir(self, s, nature, fonction):
        essais.exporter(self.f, s, nature)
        feuilles = tableur.lire_classeur(self.f)
        sortie = []
        for nom, lignes in feuilles.items():
            lignes = [list(map(str, x)) for x in lignes]
            if nom != "Sommaire":
                for ligne in lignes[1:]:
                    fonction(ligne)
            sortie.append((nom, lignes[0], lignes[1:], [20] * len(lignes[0])))
        ecrire_xlsx(self.f, sortie)
        return tableur.lire_classeur(self.f)

    def test_points_fat_et_sat(self):
        s = ouvrage()
        fat, sat = essais.points(s, "FAT"), essais.points(s, "SAT")
        self.assertEqual({p["nature"] for p in fat} <= {"ET", "ST", "EA", "SA"}, True)
        self.assertEqual(len(sat), len(s.variables()))
        self.assertEqual(essais.etat(s, "SAT")["compte"]["à faire"], len(sat))
        with self.assertRaises(essais.EssaiRefuse):
            essais.points(s, "XYZ")

    def test_aller_retour_des_resultats(self):
        s = ouvrage()
        def saisir(ligne):
            ligne[8] = "OK" if ligne[1].endswith("_OUV") else ("nok" if ligne[1].endswith("_FER") else "")
            if ligne[1].endswith("_FER"):
                ligne[9], ligne[10], ligne[11] = "Inversion constatée", "46345", "JD"
        avant = dict(s.ouvrage.essais)
        lu = essais.lire(self.remplir(s, "SAT", saisir), s, "SAT")
        self.assertEqual(s.ouvrage.essais, avant)                    # lecture seule
        self.assertEqual(lu["erreurs"], [])
        self.assertEqual(sorted(r["resultat"] for r in lu["resultats"].values()), ["Conforme", "Non conforme"])
        nc = next(r for r in lu["resultats"].values() if r["resultat"] == "Non conforme")
        self.assertEqual((nc["remarque"], nc["date"], nc["visa"]), ("Inversion constatée", "19/11/2026", "JD"))
        self.assertEqual(essais.reporter(s, "SAT", lu["resultats"]), 2)
        e = essais.etat(s, "SAT")
        self.assertEqual((e["compte"]["Conforme"], e["compte"]["Non conforme"]), (1, 1))
        self.assertEqual(e["a_voir"][0]["remarque"], "Inversion constatée")
        # Réédition : résultats pré-remplis ; relu tel quel = inchangé ; cellule vidée = rien d'effacé
        relu = essais.lire(self.remplir(s, "SAT", lambda ligne: None), s, "SAT")
        self.assertEqual((relu["resultats"], relu["inchanges"]), ({}, 2))

    def test_adresse_changee_point_a_refaire(self):
        s = ouvrage()
        v = s.variables()[0]
        lu = essais.lire(self.remplir(s, "SAT", lambda ligne: ligne.__setitem__(8, "Conforme")), s, "SAT")
        essais.reporter(s, "SAT", lu["resultats"])
        eq = s.ouvrage.equipement(v.ident_eq)
        eq.adresses[v.cle] = "%MW1500.0"                           # adresse changée après l'essai
        e = essais.etat(s, "SAT")
        self.assertEqual(e["compte"]["à refaire"], 1)
        self.assertEqual(e["a_voir"][0]["etat"], "à refaire")

    def test_erreurs_de_saisie(self):
        s = ouvrage()
        def fautes(ligne):
            if ligne[1].endswith("_OUV"):
                ligne[8] = "Bof"
            if ligne[1].endswith("_FER"):
                ligne[8], ligne[12] = "Conforme", "cle|inconnue"
        lu = essais.lire(self.remplir(s, "SAT", fautes), s, "SAT")
        self.assertEqual(len(lu["erreurs"]), 2)
        self.assertTrue(any("inconnu" in x for x in lu["erreurs"]))
        with self.assertRaises(essais.EssaiRefuse):
            essais.lire({"Feuille": [["A", "B"], ["1", "2"]]}, s, "SAT")


if __name__ == "__main__":
    unittest.main()
