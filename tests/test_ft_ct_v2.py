"""Décision D2 du référentiel V2 : CT supprimé, FT unique pour débitmètre / compteur d'eau."""
import copy
import json
import os
import tempfile
import unittest

from genvar import adoption, chemins, modeles
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, generer, generer_points
from genvar.session import Session

OPT_IMP, OPT_DEF, OPT_SENS = "Sortie impulsions câblée", "Contact défaut TOR", "Sens d’écoulement TOR"
# Définition de CT dans le référentiel V1.2 (commit c3e506e), pour simuler un projet existant.
CT_TYPE = {"code": "CT", "designation": "Compteur d'eau à impulsions", "categorie": "Équipement",
           "famille_biblio": "Compteur d’achat", "options": ["Seuils d’alarme"], "domaine": "Hydraulique",
           "remarque": "Compteur de volume (hors achat d'eau en gros : FQ)."}
CT_SIGNAUX = [
    {"type": "CT", "information": "Volume compté", "famille": "CP", "code": "VOL", "type_logique": "DINT",
     "unite": "m3", "es": "ET", "alarme": False, "presence": "Par défaut", "option": "", "statut": "Validé",
     "remarque": "", "organe": "", "source": "", "logique": ""},
    {"type": "CT", "information": "Absence d'impulsions", "famille": "TS", "code": "ABSIMP", "type_logique": "BOOL",
     "unite": "", "es": "Interne", "alarme": True, "presence": "Option", "option": "Seuils d’alarme",
     "statut": "Validé", "remarque": "", "organe": "", "source": "", "logique": ""}]


class Base(unittest.TestCase):
    def setUp(self):
        self.env = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier
        self.cat = Catalogue.charger(chemins.fichier_catalogue_origine())

    def tearDown(self):
        if self.env is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.env

    def session(self, cat=None):
        s = Session(cat or self.cat)
        s.nouveau(False)
        s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
        s.ajouter_sous_ensemble("00")
        return s

    def ft(self, options=(), exclus=()):
        s = self.session()
        eq = s.ajouter_equipement(Equipement("00", "FT", "01"))
        eq.options, eq.exclus = list(options), list(exclus)
        s.decider_propositions(eq.ident, "retenir")
        points = [p.nom for p in generer_points(s.ouvrage, s.catalogue)]
        noms = [v.nom for v in generer(s.ouvrage, s.catalogue)]
        return s, eq, points, noms


class TestCatalogue(Base):
    def test_aucune_reference_ct(self):
        self.assertNotIn("CT", {t["code"] for t in self.cat.types})
        self.assertFalse([s for s in self.cat.signaux if s["type"] == "CT"])
        self.assertFalse([r for r in self.cat.regles if r["type"] == "CT"])
        d = json.load(open(os.path.join(chemins.dossier_ressources(), "referentiel_modeles.json"), encoding="utf-8"))
        self.assertFalse([e for e in d["dictionnaire_es"] if "CT" in e["types"]])
        self.assertFalse([m for m in d["modeles"].values() if m["type"] == "CT"])

    def test_correspondances_ct_vers_ft_valides(self):
        corr = modeles.charger()["correspondances"]
        self.assertEqual({(c["ancienne"], c["type_nouveau"], c["nouvelle"]) for c in corr if c["type"] == "CT"},
                         {("CP_VOL", "FT", "CP_VOL"), ("TS_ABSIMP", "FT", "TS_ABSIMP")})
        self.assertEqual(adoption.controler_correspondances(corr, self.cat), [])


class TestFT(Base):
    def test_mesure_4_20_seule(self):
        _, _, points, noms = self.ft()
        self.assertEqual(points, ["EA_RV01FT01_DEB"])
        self.assertIn("TM_RV01FT01_DEB", noms)

    def test_impulsions_seules(self):
        _, _, points, noms = self.ft([OPT_IMP], ["ES_DEB"])
        self.assertEqual(points, ["ET_RV01FT01_IMP"])
        self.assertEqual(noms.count("CP_RV01FT01_VOL"), 1)
        self.assertNotIn("TM_RV01FT01_DEB", noms)
        self.assertNotIn("TS_RV01FT01_ABSIMP", noms)              # FT-05 exige mesure et impulsions

    def test_combine_defaut_et_sens(self):
        _, _, points, noms = self.ft([OPT_IMP, OPT_DEF, OPT_SENS])
        self.assertEqual(sorted(points), ["EA_RV01FT01_DEB", "ET_RV01FT01_DEF_EXT", "ET_RV01FT01_IMP",
                                          "ET_RV01FT01_SENS"])
        self.assertEqual(noms.count("CP_RV01FT01_VOL"), 1)        # FT-03 et FT-04 : un seul volume
        self.assertIn("TS_RV01FT01_DEF", noms)
        self.assertIn("TS_RV01FT01_DEF_EXT", noms)                # défauts distincts, jamais fusionnés
        self.assertEqual(len(noms), len(set(noms)))
        self.assertEqual(len(points), len(set(points)))

    def test_options_desactivees_aucune_es_fictive(self):
        _, _, points, _ = self.ft([OPT_DEF])
        self.assertNotIn("ET_RV01FT01_SENS", points)
        self.assertNotIn("ET_RV01FT01_IMP", points)

    def test_sens_configurable_conserve_apres_reouverture(self):
        s, eq, _, _ = self.ft([OPT_SENS])
        s.definir_es(eq.ident, "ES_SENS", sens="1 = sortant")
        f = os.path.join(self.dossier, "ft.json")
        s.enregistrer(f)
        s2 = Session(self.cat)
        s2.ouvrir(f)
        p = next(p for p in generer_points(s2.ouvrage, s2.catalogue) if p.nom == "ET_RV01FT01_SENS")
        self.assertEqual(p.sens, "1 = sortant")

    def test_aucun_mw_pour_une_simple_es_physique(self):
        s, eq, _, _ = self.ft([OPT_IMP, OPT_DEF, OPT_SENS])
        props, _ = s.plan(); s.appliquer(props)
        self.assertTrue(eq.adresses)
        self.assertFalse([k for k in eq.adresses if k.startswith("ES_")])


class TestProjetCTExistant(Base):
    def test_projet_ct_conserve_et_conversion_soumise_a_decision(self):
        ancien = copy.deepcopy(self.cat)
        ancien.types.append(copy.deepcopy(CT_TYPE))
        ancien.signaux += copy.deepcopy(CT_SIGNAUX)
        s = self.session(ancien)
        eq = s.ajouter_equipement(Equipement("00", "CT", "01"))
        s.decider_propositions(eq.ident, "retenir")
        props, _ = s.plan(); s.appliquer(props)
        avant = {v.nom: v.adresse for v in s.variables()}
        self.assertIn("CP_RV01CT01_VOL", avant)
        s._catalogue_commun = copy.deepcopy(self.cat)              # référentiel V2 : plus de CT
        ct = next(x for x in s.apercu_adoption() if x["type"] == "CT")
        self.assertFalse(ct["adoptable"])
        self.assertTrue(any("R1" in b for b in ct["bloquants"]))
        self.assertEqual(s.adopter_referentiel(), [])
        self.assertEqual({v.nom: v.adresse for v in s.variables()}, avant)   # rien de supprimé ni réaffecté
