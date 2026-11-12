"""Décisions R2 / R3 : version calculée par profil et état de synchronisation des équipements.

Profil = type d'équipement du référentiel (type, signaux, règles, modèles). Sa version n'est pas stockée : elle
se déduit de l'historique des révisions publiées (empreinte SHA-256). L'état d'un équipement compare le profil
figé dans l'ouvrage au profil publié, sans rien modifier.
"""
import copy
import shutil
import tempfile
import unittest

from genvar import chemins, profils
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.referentiel_depot import Depot, empreinte
from genvar.session import Session


def _publie():
    return Depot(tempfile.mkdtemp()).publie()


class TestEmpreinteProfil(unittest.TestCase):
    def setUp(self):
        self.d = _publie()

    def test_stable_et_independante_du_libelle_de_version_et_des_autres_types(self):
        e = profils.empreinte_profil(self.d, "MV")
        self.assertEqual(len(e), 64)
        autre = copy.deepcopy(self.d)
        autre["catalogue"]["version"] = "R0099 autre libellé"
        next(s for s in autre["catalogue"]["signaux"] if s["type"] == "HV")["information"] += " (modifié)"
        self.assertEqual(profils.empreinte_profil(autre, "MV"), e)
        self.assertNotEqual(profils.empreinte_profil(autre, "HV"), profils.empreinte_profil(self.d, "HV"))

    def test_signal_regle_et_modele_du_type_changent_l_empreinte(self):
        e = profils.empreinte_profil(self.d, "MV")
        for modifier in (
            lambda d: next(s for s in d["catalogue"]["signaux"] if s["type"] == "MV").update(information="X"),
            lambda d: next(r for r in d["catalogue"]["regles"] if r["type"] == "MV").update(libelle="X"),
            lambda d: d["modeles"]["modeles"]["Vanne motorisée"].update(statut="X"),
        ):
            d = copy.deepcopy(self.d)
            modifier(d)
            self.assertNotEqual(profils.empreinte_profil(d, "MV"), e)

    def test_type_absent(self):
        self.assertIsNone(profils.empreinte_profil(self.d, "ZZ"))


class TestVersionsParRevision(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        self.depot = Depot(self.base)

    def _publier(self, modifier, motif):
        b = self.depot.creer_brouillon("essai")
        d = copy.deepcopy(b["donnees"])
        modifier(d)
        self.depot.remplacer_donnees(d, motif)
        v = self.depot.valider("essai")
        return self.depot.publier(motif, v["empreinte_validee"], "essai")

    def test_sans_historique_version_1_du_referentiel_en_service(self):
        v = profils.versions(self.depot)
        self.assertEqual(v["MV"][-1]["version"], 1)
        self.assertEqual(v["MV"][-1]["revision"], 0)

    def test_version_incrementee_seulement_si_le_profil_change(self):
        def mv(d):
            next(s for s in d["catalogue"]["signaux"] if s["type"] == "MV" and s["code"] == "DISC")[
                "remarque"] = "Remarque d'essai."
        self._publier(mv, "Essai MV")
        def hv(d):
            next(s for s in d["catalogue"]["signaux"] if s["type"] == "HV")["remarque"] = "Remarque d'essai."
        self._publier(hv, "Essai HV")
        v = profils.versions(self.depot)
        self.assertEqual([(x["revision"], x["version"]) for x in v["MV"]], [(1, 1), (2, 2)])
        self.assertEqual([(x["revision"], x["version"]) for x in v["HV"]], [(1, 1), (3, 2)])
        self.assertEqual(profils.version_publiee(self.depot, "MV")["version"], 2)
        # l'historique n'est pas modifié par le calcul
        self.assertEqual([r["numero"] for r in self.depot.revisions()], [3, 2, 1])


class TestEtatSynchronisation(unittest.TestCase):
    def setUp(self):
        self.cat = Catalogue.charger(chemins.fichier_catalogue_origine())
        self.s = Session(self.cat)
        self.s.nouveau(False)
        self.s.definir("lieu", "XTST"); self.s.definir("code_ouvrage", "RV"); self.s.ouvrage.numero_ouvrage = "01"
        self.s.ajouter_sous_ensemble("00")
        self.mv = self.s.ajouter_equipement(Equipement("00", "MV", "01"))
        self.hv = self.s.ajouter_equipement(Equipement("00", "HV", "01"))
        self.publie = {"catalogue": {"version": self.cat.version, "types": copy.deepcopy(self.cat.types),
                                     "signaux": copy.deepcopy(self.cat.signaux), "regles": copy.deepcopy(self.cat.regles)},
                       "modeles": copy.deepcopy(self.s.modeles)}

    def _etat(self, publie=None):
        avant = empreinte(self.s.ouvrage.vers_dict())
        e = profils.etat_synchronisation(self.s.ouvrage, self.s.catalogue, publie or self.publie)
        self.assertEqual(empreinte(self.s.ouvrage.vers_dict()), avant)          # lecture seule
        return e

    def test_ouvrage_neuf_a_jour(self):
        e = self._etat()
        self.assertEqual({t: x["etat"] for t, x in e["types"].items()}, {"MV": "À jour", "HV": "À jour"})
        self.assertEqual({x["etat"] for x in e["equipements"].values()}, {"À jour"})

    def test_modification_publiee_mise_a_jour_disponible_pour_le_seul_type_concerne(self):
        p = copy.deepcopy(self.publie)
        next(s for s in p["catalogue"]["signaux"] if s["type"] == "MV" and s["code"] == "DISC")["remarque"] = "R."
        e = self._etat(p)
        self.assertEqual(e["types"]["MV"]["etat"], "Mise à jour disponible")
        self.assertEqual(e["types"]["HV"]["etat"], "À jour")
        self.assertEqual(e["equipements"][self.mv.ident]["etat"], "Mise à jour disponible")
        self.assertEqual(e["equipements"][self.hv.ident]["etat"], "À jour")

    def test_retrait_d_un_signal_porteur_de_donnees_a_examiner(self):
        self.mv.adresses["TS_DEF"] = "%MW100.0"
        p = copy.deepcopy(self.publie)
        p["catalogue"]["signaux"] = [s for s in p["catalogue"]["signaux"]
                                     if not (s["type"] == "MV" and s["famille"] == "TS" and s["code"] == "DEF")]
        e = self._etat(p)
        self.assertEqual(e["types"]["MV"]["etat"], "Mise à jour à examiner")
        self.assertTrue(any("TS_DEF" in m for m in e["types"]["MV"]["motifs"]))
        self.assertEqual(e["equipements"][self.mv.ident]["etat"], "Mise à jour à examiner")

    def test_type_retire_du_referentiel_a_examiner(self):
        p = copy.deepcopy(self.publie)
        p["catalogue"]["types"] = [t for t in p["catalogue"]["types"] if t["code"] != "HV"]
        p["catalogue"]["signaux"] = [s for s in p["catalogue"]["signaux"] if s["type"] != "HV"]
        self.assertEqual(self._etat(p)["types"]["HV"]["etat"], "Mise à jour à examiner")

    def test_modele_fige_modifie_reprise_disponible_ou_a_examiner(self):
        eq = Equipement("00", "MV", "02")
        eq.modele = "Vanne motorisée"
        self.s.ajouter_equipement(eq)
        self.assertEqual(self._etat()["equipements"][eq.ident]["etat"], "À jour")
        p = copy.deepcopy(self.publie)
        p["modeles"]["modeles"]["Vanne motorisée"]["statut"] = "validé autrement"
        x = self._etat(p)["equipements"][eq.ident]
        self.assertEqual(x["etat"], "Mise à jour disponible")                  # reprise contrôlée possible
        self.assertTrue(any("Vanne motorisée" in m for m in x["motifs"]))
        eq.adresses["TS_DEF"] = "%MW100.0"
        p["modeles"]["modeles"]["Vanne motorisée"]["signaux"] = [
            s for s in p["modeles"]["modeles"]["Vanne motorisée"]["signaux"]
            if not (s["famille"] == "TS" and s["code"] == "DEF")]
        x = self._etat(p)["equipements"][eq.ident]
        self.assertEqual(x["etat"], "Mise à jour à examiner")                  # donnée portée par une clé retirée
        self.assertTrue(any("TS_DEF" in m for m in x["motifs"]))
        p["modeles"]["modeles"].pop("Vanne motorisée")
        self.assertEqual(self._etat(p)["equipements"][eq.ident]["etat"], "Mise à jour à examiner")

    def test_session_utilise_le_referentiel_en_service(self):
        e = self.s.synchronisation()
        self.assertIn("MV", e["types"])
        self.assertIn("version_publiee", e["types"]["MV"])


    def test_route_web_en_lecture_seule(self):
        from sorep_web.serveur import ROUTES_GET, Application
        self.assertEqual(ROUTES_GET["/api/referentiel/synchronisation"], "synchronisation_referentiel")
        app = Application()
        app.s, app.ouvert = self.s, True
        avant = empreinte(self.s.ouvrage.vers_dict())
        e = app.synchronisation_referentiel({})
        self.assertEqual(e["equipements"][self.mv.ident]["etat"], "À jour")
        self.assertEqual(empreinte(self.s.ouvrage.vers_dict()), avant)


if __name__ == "__main__":
    unittest.main()
