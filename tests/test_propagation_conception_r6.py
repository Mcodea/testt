"""Décision R6 : acceptation en un geste, limitée aux ouvrages neufs jamais validés ni exportés.

Seuls les types adoptables sans renommage ni conflit de surcharge sont proposés ; l'aperçu précède toujours
l'acceptation, qui est refusée si l'aperçu a changé. Tout autre ouvrage reste à l'adoption ligne à ligne (L2).
"""
import copy
import os
import tempfile
import unittest

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, Ouvrage
from genvar.session import RegleMetier, Session


class TestPropagation(unittest.TestCase):
    def setUp(self):
        self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        self.s.nouveau(False)
        self.s.definir("lieu", "XTST"); self.s.definir("code_ouvrage", "RV"); self.s.ouvrage.numero_ouvrage = "01"
        self.s.ajouter_sous_ensemble("00")
        self.mv = self.s.ajouter_equipement(Equipement("00", "MV", "01"))
        self.hv = self.s.ajouter_equipement(Equipement("00", "HV", "01"))
        nouveau = copy.deepcopy(self.s._catalogue_commun)
        for s in nouveau.signaux:
            if (s["type"], s["famille"], s["code"]) in (("MV", "TS", "DISC"), ("HV", "TS", "OUV")):
                s["information"] += " (révisé)"
        self.s._catalogue_commun = nouveau

    def test_ouvrage_en_conception_eligible_et_accepte_en_un_geste(self):
        a = self.s.apercu_propagation()
        self.assertTrue(a["eligible"], a)
        self.assertEqual([t["type"] for t in a["types"]], ["HV", "MV"])
        self.s.accepter_propagation(a["empreinte"])
        self.assertEqual(self.s.apercu_adoption(), [])
        actions = {(x["action"], x["profil"]) for x in self.s.ouvrage.journal_referentiel}
        self.assertEqual(actions, {("acceptation en un geste", "MV"), ("acceptation en un geste", "HV")})

    def test_type_en_conflit_exclu_du_geste(self):
        self.hv.libelles["TS_OUV"] = "Libellé local"
        a = self.s.apercu_propagation()
        self.assertEqual([t["type"] for t in a["types"]], ["MV"])
        self.assertEqual([x["type"] for x in a["exclus"]], ["HV"])
        self.s.accepter_propagation(a["empreinte"])
        self.assertEqual([x["type"] for x in self.s.apercu_adoption()], ["HV"])      # reste à examiner

    def test_apercu_perime_refuse(self):
        a = self.s.apercu_propagation()
        for s in self.s._catalogue_commun.signaux:
            if (s["type"], s["famille"], s["code"]) == ("MV", "TS", "INT"):
                s["information"] += " (encore)"
        with self.assertRaises(RegleMetier):
            self.s.accepter_propagation(a["empreinte"])
        self.assertEqual(len(self.s.apercu_adoption()), 2)                           # rien adopté

    def test_ouvrage_valide_exporte_existant_ou_historique_inconnu_non_eligible(self):
        cas = []
        s = copy.deepcopy(self.s); s.ouvrage.deja_valide = True; cas.append(s)
        s = copy.deepcopy(self.s); s.ouvrage.statut = "À contrôler"; cas.append(s)
        s = copy.deepcopy(self.s); s.ouvrage.mode = "Existant"; cas.append(s)
        s = copy.deepcopy(self.s); s.ouvrage.deja_exporte = None; cas.append(s)
        for s in cas:
            a = s.apercu_propagation()
            self.assertFalse(a["eligible"])
            self.assertTrue(a["raisons"])
            with self.assertRaises(RegleMetier):
                s.accepter_propagation(a["empreinte"])

    def test_validation_et_export_sont_memorises(self):
        self.assertIs(self.s.ouvrage.deja_exporte, False)
        with tempfile.TemporaryDirectory() as d:
            self.s.exporter_liste_es(os.path.join(d, "l.xlsx"))
        self.assertIs(self.s.ouvrage.deja_exporte, True)
        self.assertFalse(self.s.apercu_propagation()["eligible"])

    def test_ancien_fichier_historique_inconnu(self):
        d = Ouvrage().vers_dict()
        d.pop("deja_valide"); d.pop("deja_exporte")
        o = Ouvrage.depuis_dict(d)
        self.assertIsNone(o.deja_valide)
        self.assertIsNone(o.deja_exporte)
        o2 = Ouvrage.depuis_dict(Ouvrage().vers_dict())
        self.assertIs(o2.deja_valide, False)


    def test_routes_web_et_export_memorise_dans_le_fichier(self):
        import shutil
        from sorep_web.serveur import ROUTES_GET, ROUTES_POST, Application
        self.assertEqual(ROUTES_GET["/api/referentiel/propagation"], "apercu_propagation")
        self.assertEqual(ROUTES_POST["/api/referentiel/accepter-propagation"], "accepter_propagation")
        dossier, env = tempfile.mkdtemp(), os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = dossier
        self.addCleanup(shutil.rmtree, dossier, ignore_errors=True)
        self.addCleanup(lambda: os.environ.pop("SOREP_DATA_DIR", None) if env is None
                        else os.environ.__setitem__("SOREP_DATA_DIR", env))
        app = Application()
        app.s, app.ouvert = self.s, True
        with self.assertRaises(RegleMetier):                       # fichier non enregistré : pas de sauvegarde
            app.accepter_propagation({"empreinte": app.apercu_propagation({})["empreinte"]})
        chemin = os.path.join(dossier, "XTSTRV01.ouvrage.json")
        self.s.enregistrer(chemin)
        r = app.accepter_propagation({"empreinte": app.apercu_propagation({})["empreinte"]})
        self.assertEqual(r["types"], ["HV", "MV"])
        self.assertTrue(r["sauvegarde"])
        self.assertEqual(len(Ouvrage.ouvrir(chemin).journal_referentiel), 2)
        app.exporter({"quoi": "liste_es"})
        self.assertIs(Ouvrage.ouvrir(chemin).deja_exporte, True)


if __name__ == "__main__":
    unittest.main()
