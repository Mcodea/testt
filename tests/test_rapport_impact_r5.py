"""Décision R5 : rapport d'impact multi-ouvrages d'une révision du référentiel, sans rien modifier."""
import copy
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from genvar import chemins, profils
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.referentiel_depot import Depot
from genvar.session import RegleMetier, Session


def _ouvrage(cat, numero, types):
    s = Session(cat)
    s.nouveau(False)
    s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = numero
    s.ajouter_sous_ensemble("00")
    for t in types:
        s.ajouter_equipement(Equipement("00", t, "01"))
    return s


class TestRapportImpact(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dossier, ignore_errors=True)
        env = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = self.dossier
        self.addCleanup(lambda: os.environ.pop("SOREP_DATA_DIR", None) if env is None
                        else os.environ.__setitem__("SOREP_DATA_DIR", env))
        self.cat = Catalogue.charger(chemins.fichier_catalogue_origine())
        projets = Path(chemins.dossier_projets())
        projets.mkdir(parents=True, exist_ok=True)
        self.f1, self.f2 = projets / "XTSTRV01.ouvrage.json", projets / "XTSTRV02.ouvrage.json"
        _ouvrage(self.cat, "01", ["MV", "HV"]).enregistrer(str(self.f1))
        _ouvrage(self.cat, "02", ["HV"]).enregistrer(str(self.f2))
        self.octets = (self.f1.read_bytes(), self.f2.read_bytes())
        self.depot = Depot()
        b = self.depot.creer_brouillon("essai")
        d = copy.deepcopy(b["donnees"])
        next(s for s in d["catalogue"]["signaux"] if s["type"] == "MV" and s["code"] == "DISC")["remarque"] = "R."
        self.depot.remplacer_donnees(d, "Essai")

    def test_seuls_les_profils_modifies_et_les_ouvrages_concernes(self):
        r = Session(self.cat).rapport_impact()
        self.assertEqual([p["profil"] for p in r["profils"]], ["MV"])
        mv = r["profils"][0]
        self.assertEqual(mv["version_actuelle"], 1)
        self.assertEqual(mv["version_suivante"], 2)
        self.assertEqual([o["repere"] for o in mv["ouvrages"]], ["XTSTRV01"])
        eqs = mv["ouvrages"][0]["equipements"]
        self.assertEqual([(e["repere"], e["etat"]) for e in eqs], [("XTSTRV01MV01", "Mise à jour disponible")])
        self.assertEqual((self.f1.read_bytes(), self.f2.read_bytes()), self.octets)    # aucune écriture

    def test_ouvrage_illisible_signale_sans_bloquer(self):
        (Path(chemins.dossier_projets()) / "casse.ouvrage.json").write_text("{", encoding="utf-8")
        r = Session(self.cat).rapport_impact()
        self.assertEqual([p["profil"] for p in r["profils"]], ["MV"])
        self.assertTrue(r["illisibles"])

    def test_sans_brouillon_refuse(self):
        self.depot.abandonner()
        with self.assertRaises(RegleMetier):
            Session(self.cat).rapport_impact()

    def test_fonction_pure(self):
        avant = self.depot.publie()
        apres = self.depot.brouillon()["donnees"]
        self.assertEqual(profils.profils_modifies(avant, apres), ["MV"])
        self.assertEqual(profils.profils_modifies(avant, avant), [])

    def test_route_web(self):
        from sorep_web.serveur import ROUTES_GET, Application
        self.assertEqual(ROUTES_GET["/api/referentiel/impact"], "rapport_impact")
        self.assertEqual(Application().rapport_impact({})["profils"][0]["profil"], "MV")


if __name__ == "__main__":
    unittest.main()
