"""Brouillon A1 : renommages approuvés le 23/11/2026, ajouts non appliqués, rien de publié."""
import copy
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, suffixe_physique
from genvar.referentiel_depot import Depot
from genvar.session import Session

RACINE = Path(__file__).resolve().parents[1]
LIVRE = RACINE / "genvar" / "data"


def _outil():
    spec = importlib.util.spec_from_file_location("brouillon_a1", RACINE / "outils" / "brouillon_a1.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestBrouillonA1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outil = _outil()
        cls.candidat, cls.rapport = cls.outil.construire()
        cls.livre = json.loads((LIVRE / "catalogue_defaut.json").read_text(encoding="utf-8"))

    def test_candidat_a_jour(self):
        self.assertEqual(self.outil.main(["--verifier"]), 0, "py outils/brouillon_a1.py")

    def test_referentiel_livre_jamais_modifie(self):
        for nom in ("catalogue_defaut.json", "referentiel_modeles.json"):
            f = LIVRE / nom
            self.assertNotIn("A1", f.read_text(encoding="utf-8")[:2000] if nom == "catalogue_defaut.json" else "")
        self.assertNotIn("A1 (", self.livre["version"])
        self.assertNotEqual(self.candidat["catalogue"]["signaux"], self.livre["signaux"])

    def test_aucun_ajout_et_aucun_type_cree(self):
        self.assertEqual(len(self.candidat["catalogue"]["signaux"]), len(self.livre["signaux"]))
        self.assertEqual([t["code"] for t in self.candidat["catalogue"]["types"]], [t["code"] for t in self.livre["types"]])
        self.assertEqual(self.rapport["ajouts_non_appliques"], 49)

    def test_les_refus_gardent_leur_code_et_les_approbations_changent(self):
        actuels = {(s["type"], s["es"], s["code"]) for s in self.candidat["catalogue"]["signaux"]}
        refuses = self.rapport["decision"]["renommages_refuses"]
        self.assertEqual(len(refuses), 19)
        for ident in refuses:
            type_, nature, code = ident.split(".")
            self.assertIn((type_, nature, code), actuels, ident)
        for a in self.rapport["appliques"]:
            self.assertNotIn(a["ident"], refuses)
            self.assertIn((a["type"], a["nature"], a["nouvelle"].split("_", 1)[1]), actuels, a)
            self.assertNotIn((a["type"], a["nature"], a["ancienne"].split("_", 1)[1]), actuels, a)

    def test_aucun_ecart_et_exceptions_d4_decidees(self):
        self.assertEqual(self.rapport["ecarts"], [])
        self.assertEqual({x["ident"]: x["suffixe_es"] for x in self.rapport["exceptions_d4"]},
                         {"PD.SA.TAUX": "CONS_TAU", "PM.SA.CONS_FREQ": "CONS_FRQ"})

    def test_controles_du_depot_sans_erreur_ni_doublon_et_regles_a_jour(self):
        c = self.outil.controler(self.candidat)
        self.assertEqual(c["erreurs"], [])
        self.assertEqual(c["doublons"], [])
        cles = {(s["type"], f"{s['famille']}_{s['code']}") for s in self.candidat["catalogue"]["signaux"]}
        for r in self.candidat["catalogue"]["regles"]:
            for k in r["propose"]:
                if "*" not in k:                                   # « RTR_* » : motif générique, pas une clé
                    self.assertIn((r["type"], k), cles, (r["id"], k))

    def test_noms_physiques_conformes_a_la_bibliotheque(self):
        self.assertEqual(self.rapport["physiques_divergents"], [])
        for a in self.rapport["appliques"]:
            if a["physique_propose"] == "—" or a["nouvelle"].split("_", 1)[0] == "RTR":
                continue
            signal = next(s for s in self.candidat["catalogue"]["signaux"] if s["type"] == a["type"] and s["es"] == a["nature"]
                          and f"{s['famille']}_{s['code']}" == a["nouvelle"])
            self.assertEqual(suffixe_physique(signal), a["physique_propose"].split("_", 2)[2], a)

    def test_correspondances_declarees_pour_chaque_cle_renommee(self):
        declarees = {(c["type"], c["ancienne"], c["nouvelle"]) for c in self.candidat["modeles"]["correspondances"] if c.get("motif", "").startswith("A1")}
        voulues = {(a["type"], a["ancienne"], a["nouvelle"]) for a in self.rapport["appliques"]}
        self.assertEqual(declarees, voulues)


class TestAdoptionDuCandidat(unittest.TestCase):
    """Un ouvrage existant adopte le candidat sans perdre ni adresse %MW, ni voie, ni commentaire."""

    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def test_adresses_voies_et_commentaires_reportes(self):
        candidat, _ = _outil().construire()
        s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s.nouveau(False)
        s.definir("lieu", "XTST")
        s.definir("code_ouvrage", "RV")
        s.ouvrage.numero_ouvrage = "01"
        s.ajouter_sous_ensemble("00")
        ar = s.ajouter_equipement(Equipement("00", "AR", "01", options=["Ventilation"]))
        s.decider_propositions(ar.ident, "retenir")
        props, _ = s.plan()
        s.appliquer(props)
        s.catalogue = copy.deepcopy(s._catalogue_commun)
        ar.adresses_es["TS_ISOL"] = "%I0.1.3"
        ar.commentaires["TS_ISOL"] = "commentaire saisi"
        avant = {v.nom: v.adresse for v in s.variables()}
        nom = next(n for n in avant if n.endswith("_ISOL"))
        # Le candidat devient le référentiel courant.
        catalogue, modeles = Depot.objets(candidat)
        s._catalogue_commun = catalogue
        s.modeles["correspondances"] = modeles["correspondances"]
        s.adopter_referentiel(["AR"], renommages_confirmes=True)
        apres = {v.nom: v for v in s.variables()}
        nouveau = nom[:-len("ISOL")] + "DEF_ISOL"
        self.assertIn(nouveau, apres)
        self.assertEqual(apres[nouveau].adresse, avant[nom])                 # %MW conservé
        self.assertEqual(apres[nouveau].adresse_es, "%I0.1.3")               # voie conservée
        self.assertEqual(ar.commentaires.get("TS_DEF_ISOL"), "commentaire saisi")
        self.assertEqual(sorted(v.adresse for v in apres.values() if v.adresse), sorted(a for a in avant.values() if a))


if __name__ == "__main__":
    unittest.main()
