"""Décision P5 : MV est le profil VANNE_MV ; options « Arrêt dédié câblé » et « Défauts de manœuvre détaillés ».

Aucune entrée obligatoire ajoutée, aucun signal sans sélection de l'option, aucune variable d'échange (%MW)
pour la sortie physique d'arrêt `ST_<repère>_ARR` (suffixe sur 3 lettres, décision de l'utilisateur du
11/11/2026) ; la télécommande `TC_AR` existante est inchangée.
"""
import unittest

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, generer, generer_points
from genvar.session import Session

ARRET = "Arrêt dédié câblé"
DEFAUTS = "Défauts de manœuvre détaillés"


class TestProfilVanneMV(unittest.TestCase):
    def setUp(self):
        self.cat = Catalogue.charger(chemins.fichier_catalogue_origine())

    def _mv(self, options):
        s = Session(self.cat)
        s.nouveau(False)
        s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
        s.ajouter_sous_ensemble("00")
        eq = s.ajouter_equipement(Equipement("00", "MV", "01"))
        eq.options = list(options)
        s.decider_propositions(eq.ident, "retenir")
        points = {p.nom: p for p in generer_points(s.ouvrage, s.catalogue)}
        variables = {v.nom: v for v in generer(s.ouvrage, s.catalogue)}
        return points, variables

    def _signal(self, cle):
        return next(s for s in self.cat.signaux_du_type("MV") if f"{s['famille']}_{s['code']}" == cle)

    def test_options_declarees_sur_le_type(self):
        options = self.cat.type("MV")["options"]
        self.assertIn(ARRET, options)
        self.assertIn(DEFAUTS, options)
        for cle, option in (("ES_ARR", ARRET), ("TS_DOV", DEFAUTS), ("TS_DFE", DEFAUTS)):
            s = self._signal(cle)
            self.assertEqual((s["presence"], s["option"]), ("Option", option))
            self.assertFalse(s.get("logique"))            # aucune logique automate imposée (D1, D5)

    def test_options_non_choisies_aucun_signal_ajoute(self):
        sans_points, sans_vars = self._mv(["Télécommandée"])
        self.assertNotIn("ST_RV01MV01_ARR", sans_points)
        self.assertNotIn("TS_RV01MV01_DOV", sans_vars)
        self.assertNotIn("TS_RV01MV01_DFE", sans_vars)
        # les options ne modifient que leurs propres signaux
        avec_points, avec_vars = self._mv(["Télécommandée", ARRET, DEFAUTS])
        self.assertEqual(set(avec_points) - set(sans_points), {"ST_RV01MV01_ARR"})
        self.assertEqual(set(avec_vars) - set(sans_vars), {"TS_RV01MV01_DOV", "TS_RV01MV01_DFE"})

    def test_sortie_arret_physique_sans_variable_d_echange(self):
        points, variables = self._mv([ARRET])
        p = points["ST_RV01MV01_ARR"]
        self.assertEqual((p.point, p.cle, p.type_logique, p.adresse), ("ST", "ES_ARR", "EBOOL", ""))
        self.assertNotIn("TC_RV01MV01_AR", variables)    # la télécommande reste portée par « Télécommandée »
        self.assertFalse(any(v.cle_es == "ES_ARR" or v.code == "ARR" for v in variables.values()))

    def test_sortie_d_arret_sur_trois_lettres_telecommande_inchangee(self):
        # décision de l'utilisateur du 11/11/2026 : suffixe sur 3 lettres (ARR) ; TC_AR existant non renommé
        points, variables = self._mv(["Télécommandée", ARRET])
        self.assertIn("ST_RV01MV01_ARR", points)
        self.assertNotIn("ST_RV01MV01_AR", points)
        self.assertIn("TC_RV01MV01_AR", variables)

    def test_defauts_de_manoeuvre_detailles(self):
        _, variables = self._mv(["Télécommandée", DEFAUTS])
        for nom in ("TS_RV01MV01_DOV", "TS_RV01MV01_DFE"):
            v = variables[nom]
            self.assertEqual((v.famille, v.es, v.alarme, v.adresse), ("TS", "Interne", True, ""))
        self.assertIn("TS_RV01MV01_DEFTPS", variables)  # conservé (P5)
        self.assertEqual(len(variables), len({v.nom for v in variables.values()}))

    def test_catalogue_sans_anomalie(self):
        self.assertEqual(self.cat.anomalies(), [])


if __name__ == "__main__":
    unittest.main()
