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


class TestConventions(unittest.TestCase):
    """18/11 : plan mémoire %MW modifiable par ouvrage, et reprise des réglages d'un autre ouvrage."""

    def test_plages_controlees_avant_ecriture(self):
        from genvar.modele import PLAN_DEFAUT, zone
        from genvar.session import RegleMetier
        s = nouvelle()
        avant = (dict(s.ouvrage.zones), dict(s.ouvrage.zones_fin))
        for mauvais in ({**PLAN_DEFAUT, "TS": (1000, 2100)},           # recouvre TC (2000)
                        {**PLAN_DEFAUT, "TM": ("x", 3499)}, {**PLAN_DEFAUT, "CP": (3999, 3500)},
                        {**PLAN_DEFAUT, "RTR": (4000, 70000)}, {k: v for k, v in PLAN_DEFAUT.items() if k != "CP"}):
            with self.subTest(plages=mauvais), self.assertRaises(RegleMetier):
                s.definir_plages(mauvais)
            self.assertEqual((s.ouvrage.zones, s.ouvrage.zones_fin), avant)        # rien d'écrit
        nouvelles = {**PLAN_DEFAUT, "TS": (5000, 5999)}
        self.assertEqual(s.definir_plages(nouvelles), [])
        self.assertEqual(zone(s.ouvrage, "TS"), (5000, 5999))
        self.assertTrue(s.definir_plages({**PLAN_DEFAUT, "RTR": (4000, 4099)}))   # RTR plus courte : alerte

    def test_les_propositions_suivent_les_plages_et_les_validees_ne_bougent_pas(self):
        from genvar.modele import PLAN_DEFAUT, _mot
        s = nouvelle()
        e = s.ajouter_equipement(Equipement("00", "PM", "01"))
        s.decider_propositions(e.ident, "retenir")
        s.definir_plages({**PLAN_DEFAUT, "TS": (6000, 6999)})
        ts = [a for a in s.plan_adressage().affectations if a.niveau == "automate" and a.cle.startswith("TS")]
        self.assertTrue(ts)
        self.assertTrue(all(6000 <= _mot(a.proposee)[0] <= 6999 for a in ts if a.proposee))

    def test_reprendre_les_reglages_d_un_autre_ouvrage(self):
        from genvar.modele import PLAN_DEFAUT, zone
        source = nouvelle("Sch - M580").ouvrage
        source.supervision, source.ihm, source.decalage_modbus = "Autre supervision", "Vijeo Designer", 1
        source.zones = {f: d for f, (d, _) in PLAN_DEFAUT.items()} | {"TS": 7000}
        source.zones_fin = {f: x for f, (_, x) in PLAN_DEFAUT.items()} | {"TS": 7999}
        source.communication = "Modbus TCP/IP"
        cible = nouvelle("Sch - M340")
        r = cible.reprendre_reglages(source)
        o = cible.ouvrage
        self.assertEqual((o.supervision, o.ihm, o.decalage_modbus), ("Autre supervision", "Vijeo Designer", 1))
        self.assertEqual(zone(o, "TS"), (7000, 7999))
        self.assertEqual(o.automate, "Sch - M340")                    # déjà renseigné : conservé, alerte
        self.assertTrue(any("conservé" in a for a in r["alertes"]))
        self.assertEqual(o.communication, "Modbus TCP/IP")             # vide ici : repris
        self.assertEqual(o.lieu, "XTST")                               # l'identification n'est jamais copiée

    def test_reprise_tout_ou_rien(self):
        from genvar.session import RegleMetier
        source = nouvelle().ouvrage
        source.zones = dict(source.zones) | {"TS": 2100}               # plan source incohérent (recouvrement)
        cible = nouvelle()
        avant = (cible.ouvrage.supervision, dict(cible.ouvrage.zones))
        cible.ouvrage.supervision = "TOPKAPI"
        with self.assertRaises(RegleMetier):
            cible.reprendre_reglages(source)
        self.assertEqual((cible.ouvrage.supervision, dict(cible.ouvrage.zones)), avant)
