"""Scénarios industriels fictifs : les signaux ATTENDUS sont écrits ici AVANT la génération,
d'après le fonctionnement de l'équipement, puis comparés au résultat d'OGIAS.

Lieu fictif XTST, ouvrage RV01, aucun nom d'ouvrage réel. Ces tests prouvent la cohérence de la
chaîne Équipement → E/S → informations fonctionnelles → matériel → exports ; ils ne remplacent pas
l'essai d'import dans Control Expert, S4W-Tools ou TOPKAPI.
"""
import os
import tempfile
import unittest

from genvar import chemins
from genvar import formats_control_expert as fce
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.session import Session, RegleMetier


def session(automate="M340"):
    s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
    s.nouveau(lieu_dans_le_nom=False)
    s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
    s.definir("automate", automate)
    s.ajouter_sous_ensemble("00")
    return s


def etat(s, eq):
    """{"es": {clé ES retenue}, "retenues": {...}, "a_decider": {...}, "ecartees": {...}}."""
    f = s.informations_fonctionnelles(eq)
    return {"es": {p.cle for p in s.points() if p.ident_eq == eq.ident},
            "retenues": {x["cle"] for x in f if x["etat"] == "retenue"},
            "a_decider": {x["cle"] for x in f if x["etat"] == "proposée"},
            "ecartees": {x["cle"] for x in f if x["etat"] == "écartée"}}


class Base(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien


class TestVanneDeuxFinsDeCourse(Base):
    """HV manuelle, deux fins de course, aucune commande."""
    ATTENDU_ES = {"ES_FDC_OUV", "ES_FDC_FER"}
    ATTENDU_RETENUES = {"TS_OUV", "TS_FER"}
    ATTENDU_A_DECIDER = {"TS_DISC", "TS_INT"}               # calculées, exigent une logique automate
    INTERDITES = {"TS_DEFTPS", "TS_MNV", "TS_DEFMNV", "TM_TPS"}   # pas d'ordre : pas de défaut de manœuvre

    def test_attendus_puis_decision(self):
        s = session()
        hv = s.ajouter_equipement(Equipement("00", "HV", "01", "Vanne d'isolement"))
        e = etat(s, hv)
        self.assertEqual(e["es"], self.ATTENDU_ES)
        self.assertEqual(e["retenues"], self.ATTENDU_RETENUES)
        self.assertEqual(e["a_decider"], self.ATTENDU_A_DECIDER)
        self.assertFalse(e["retenues"] & self.INTERDITES)
        self.assertNotIn("TS_DISC", {v.cle for v in s.variables()})       # proposé ≠ généré
        with self.assertRaisesRegex(RegleMetier, "à décider"):            # aucune omission silencieuse
            s.valider_equipements([hv.ident])
        self.assertTrue(any("non décidée" in a.message and "TS_DISC" in a.message for a in s.anomalies()))
        disc = next(x for x in s.informations_fonctionnelles(hv) if x["cle"] == "TS_DISC")
        self.assertEqual(disc["sources"], ["ES_FDC_FER", "ES_FDC_OUV"])
        self.assertIn("analyse fonctionnelle", disc["logique"])               # D5 : aucun algorithme imposé
        self.assertNotIn("T_DISC", disc["logique"])
        s.decider_proposition(hv.ident, "TS_DISC", "retenir")
        with self.assertRaises(RegleMetier):
            s.decider_proposition(hv.ident, "TS_INT", "ecarter", "")        # motif obligatoire
        s.decider_proposition(hv.ident, "TS_INT", "ecarter", "vanne quart de tour")
        noms = {v.cle: v.nom for v in s.variables() if v.ident_eq == hv.ident}
        self.assertEqual(set(noms), self.ATTENDU_RETENUES | {"TS_DISC"})
        self.assertEqual(noms["TS_DISC"], "TS_RV01HV01_DISC")
        self.assertEqual(s.valider_equipements([hv.ident]), 1)
        self.assertFalse([a for a in s.anomalies() if "non décidée" in a.message])

    def test_une_seule_fin_de_course_pas_de_discordance(self):
        s = session()
        hv = s.ajouter_equipement(Equipement("00", "HV", "01"))
        Session.basculer_signal(hv, next(x for x in s.catalogue.signaux_du_type("HV") if x["code"] == "FDC_FER"))
        e = etat(s, hv)
        self.assertEqual(e["es"], {"ES_FDC_OUV"})
        self.assertEqual(e["retenues"], {"TS_OUV"})
        self.assertEqual(e["a_decider"], set())                 # discordance impossible avec un seul retour


class TestElectrovanne(Base):
    """Type « porté » (contacts câblés portés par les TS) : la commande n'est qu'une option."""

    def test_non_commandee_pas_de_defaut_de_manoeuvre(self):
        s = session()
        ev = s.ajouter_equipement(Equipement("00", "EV", "01"))
        e = etat(s, ev)
        self.assertTrue({"TS_OUV", "TS_FER"} <= e["retenues"])
        self.assertEqual(e["a_decider"], {"TS_DISC"})                # deux retours : discordance à décider
        self.assertFalse({"TS_DEFTPS", "TC_OUV", "TC_FER"} & (e["retenues"] | e["a_decider"]))

    def test_commandee(self):
        s = session()
        ev = s.ajouter_equipement(Equipement("00", "EV", "01", options=["Télécommandée"]))
        e = etat(s, ev)
        self.assertTrue({"TC_OUV", "TC_FER"} <= e["retenues"])
        self.assertEqual(e["a_decider"], {"TS_DISC", "TS_DEFTPS"})
        self.assertEqual({p.point for p in s.points() if p.ident_eq == ev.ident and p.cle.startswith("TC_")}, {"ST"})


class TestPompe(Base):
    ES_BASE = {"ES_MA", "ES_DEFTH", "ES_LOC"}

    def test_pompe_non_commandee(self):
        s = session()
        pm = s.ajouter_equipement(Equipement("00", "PM", "01", "Pompe 1"))
        e = etat(s, pm)
        self.assertEqual(e["es"], self.ES_BASE)
        self.assertTrue({"TS_MA", "TS_DEFTH", "TS_LOC", "TS_DEF", "CP_HF", "CP_NDEM"} <= e["retenues"])
        self.assertFalse({"TS_DISC", "TS_DEFDEM", "TC_MA", "TC_AR"} & (e["retenues"] | e["a_decider"]))

    def test_pompe_telecommandee(self):
        s = session()
        pm = s.ajouter_equipement(Equipement("00", "PM", "01", "Pompe 1", options=["Télécommandée"]))
        e = etat(s, pm)
        self.assertEqual(e["es"], self.ES_BASE | {"ES_CMD_MA", "ES_CMD_AR"})
        self.assertTrue({"TC_MA", "TC_AR"} <= e["retenues"])
        self.assertEqual(e["a_decider"], {"TS_DISC", "TS_DEFDEM"})   # commande + retour de marche
        d = {x["cle"]: x for x in s.informations_fonctionnelles(pm)}
        self.assertEqual(d["TS_DEFDEM"]["sources"], ["ES_CMD_MA", "ES_MA"])
        self.assertTrue(d["TS_DEF"]["logique"])                  # défaut général : regroupement documenté


class TestDebitmetre(Base):
    def test_analogique_et_impulsions_un_seul_compteur(self):
        s = session()
        ft = s.ajouter_equipement(Equipement("00", "FT", "01", "Débit de sortie", options=["Sortie impulsions câblée"]))
        e = etat(s, ft)
        self.assertEqual(e["es"], {"ES_DEB", "ES_IMP"})
        self.assertTrue({"TM_DEB", "TS_DEF", "CP_VOL"} <= e["retenues"])
        self.assertEqual(e["a_decider"], {"TS_ABSIMP"})
        cp = [v for v in s.variables() if v.ident_eq == ft.ident and v.cle.startswith("CP_")]
        self.assertEqual([v.cle for v in cp], ["CP_VOL"])          # un seul compteur de volume
        d = next(x for x in s.informations_fonctionnelles(ft) if x["cle"] == "CP_VOL")
        self.assertEqual((d["regles"], d["sources"]), (["FT-03"], ["ES_IMP"]))   # pas l'intégration du débit
        # paramètres propres à l'installation : dans la fiche de l'équipement, exigés avant validation
        s.decider_propositions(ft.ident, "retenir")
        with self.assertRaisesRegex(RegleMetier, "échelle analogique"):
            s.valider_equipements([ft.ident])
        s.definir_analogique(ft.ident, "ES_DEB", {"signal_min": 4, "signal_max": 20, "phys_min": 0,
                                                  "phys_max": 250, "unite": "m³/h"})
        with self.assertRaisesRegex(RegleMetier, "impulsion"):
            s.valider_equipements([ft.ident])
        s.definir_impulsion(ft.ident, "ES_IMP", {"poids": "0.1", "front": "Montant", "unite": "m³"})
        self.assertEqual(s.valider_equipements([ft.ident]), 1)

    def test_sans_impulsions_volume_par_integration_propose(self):
        s = session()
        ft = s.ajouter_equipement(Equipement("00", "FT", "01"))
        e = etat(s, ft)
        self.assertEqual(e["es"], {"ES_DEB"})
        self.assertEqual(e["a_decider"], {"CP_VOL"})               # intégration : précision limitée, à décider
        self.assertNotIn("TS_ABSIMP", e["retenues"] | e["a_decider"])


class TestMesureAnalogique(Base):
    def test_niveau(self):
        s = session()
        lt = s.ajouter_equipement(Equipement("00", "LT", "01", "Niveau réservoir"))
        e = etat(s, lt)
        self.assertEqual(e["es"], {"ES_NIV"})
        self.assertTrue({"TM_NIV", "TS_DEF"} <= e["retenues"])      # mesure + rupture / hors plage
        d = next(x for x in s.informations_fonctionnelles(lt) if x["cle"] == "TS_DEF")
        self.assertIn("analyse fonctionnelle", d["logique"])                  # D5 : seuils en mA non imposés
        self.assertNotIn("mA", d["logique"])
        with self.assertRaisesRegex(RegleMetier, "échelle analogique"):
            s.valider_equipements([lt.ident])


class TestCuveStockage(Base):
    def test_mesure_portee_avec_defaut(self):
        s = session()
        da = s.ajouter_equipement(Equipement("00", "DA", "01"))
        e = etat(s, da)
        self.assertEqual({p.point for p in s.points() if p.ident_eq == da.ident}, {"EA"})
        self.assertIn("TS_DEF", e["retenues"])                     # rupture / hors plage de la voie analogique


class TestArchitectures(Base):
    def ouvrage_type(self, automate):
        s = session(automate)
        s.ajouter_equipement(Equipement("00", "HV", "01"))
        s.ajouter_equipement(Equipement("00", "PM", "01", options=["Télécommandée"]))
        s.ajouter_equipement(Equipement("00", "FT", "01", options=["Sortie impulsions câblée"]))
        s.ajouter_equipement(Equipement("00", "LT", "01"))
        s.valider_contenu_es([(p.ident_eq, p.cle) for p in s.points()])
        return s

    def test_m340_et_m580(self):
        attendu = {"ET": 2 + 3 + 1, "ST": 2, "EA": 2, "SA": 0}      # HV 2 FDC, PM 3 + FT IMP ; PM 2 cmd ; FT + LT
        for automate, cpu in (("M340", [0]), ("M580", [0, 1])):
            s = self.ouvrage_type(automate)
            p = s.proposer_materiel()
            self.assertEqual({b.nature: b.es for b in p.besoins}, attendu)
            self.assertEqual(p.racks[0]["cpu"], cpu)
            self.assertTrue(all(b.reserve >= 0.2 for b in p.besoins if b.es))
            s.appliquer_materiel(); s.valider_materiel()
            n, manquantes, _ = s.implanter_es()
            self.assertEqual((n, manquantes), (sum(attendu.values()), {}))
            adresses = [p.adresse for p in s.points()]
            self.assertEqual(len(adresses), len(set(adresses)))     # aucune adresse en double
            chemin = os.path.join(self.dossier, f"{automate}.xsy")
            s.exporter_xsy_es(chemin)
            relu = {v.nom for v in fce.lire(chemin) if v.nom}
            self.assertEqual(relu, {p.nom for p in s.points()})

    def test_s4w_indicatif(self):
        s = self.ouvrage_type("SOFREL S4W")
        p = s.proposer_materiel()
        self.assertEqual(p.plateforme, "S4W")
        self.assertFalse(p.applicable)                              # pas de transposition du modèle M340
        self.assertNotIn("BMX", " ".join(m["reference"] for m in p.modules))
        with self.assertRaises(RegleMetier):
            s.appliquer_materiel()


class TestProjetExistantAdresses(Base):
    def test_adresses_conservees_apres_ajout(self):
        s = session("M580")
        hv = s.ajouter_equipement(Equipement("00", "HV", "01"))
        s.decider_propositions(hv.ident, "retenir")
        props, erreurs = s.plan()
        self.assertFalse(erreurs)
        s.appliquer(props)
        avant = {v.nom: v.adresse for v in s.variables()}
        self.assertTrue(all(avant.values()))
        chemin = os.path.join(self.dossier, "o.ouvrage.json")
        s.enregistrer(chemin)
        s2 = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s2.ouvrir(chemin)
        s2.ajouter_equipement(Equipement("00", "PM", "01"))
        props, _ = s2.plan()
        s2.appliquer(props)
        apres = {v.nom: v.adresse for v in s2.variables()}
        for nom, adr in avant.items():
            self.assertEqual(apres[nom], adr)                      # anciennes adresses inchangées
        self.assertEqual(len(set(apres.values())), len(apres))


if __name__ == "__main__":
    unittest.main()
