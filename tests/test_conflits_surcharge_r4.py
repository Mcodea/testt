"""Décision R4 : conflits entre une propriété maître modifiée et une surcharge locale de l'équipement.

La surcharge est conservée et le conflit affiché dans l'aperçu d'adoption, jamais résolu en silence.
« Revenir au standard » retire une surcharge, propriété par propriété, seulement après confirmation.
"""
import copy
import unittest

from genvar import chemins, profils
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.referentiel_depot import empreinte
from genvar.session import RegleMetier, Session


class _Ouvrage(unittest.TestCase):
    def setUp(self):
        cat = Catalogue.charger(chemins.fichier_catalogue_origine())
        self.s = Session(cat)
        self.s.nouveau(False)
        self.s.definir("lieu", "XTST"); self.s.definir("code_ouvrage", "RV"); self.s.ouvrage.numero_ouvrage = "01"
        self.s.ajouter_sous_ensemble("00")
        self.eq = self.s.ajouter_equipement(Equipement("00", "MV", "01"))
        self.autre = self.s.ajouter_equipement(Equipement("00", "MV", "02"))
        self.eq.libelles["TS_DEF"] = "Défaut vanne amont"
        self.eq.commentaires["TS_DEF"] = "Commentaire local"
        self.eq.es_meta["ES_DEF"] = {"designation": "Contact défaut local", "type": "EBOOL"}
        self.eq.exclus.append("TS_DISC")
        # Révision publiée : information de TS_DEF, de ES_DEF et de TS_DISC modifiées ; TS_LOC inchangé.
        nouveau = copy.deepcopy(self.s._catalogue_commun)
        for s in nouveau.signaux:
            if s["type"] == "MV" and (s["famille"], s["code"]) in (("TS", "DEF"), ("ES", "DEF"), ("TS", "DISC")):
                s["information"] += " (révisé)"
        self.s._catalogue_commun = nouveau

    def _conflits(self):
        mv = next(x for x in self.s.apercu_adoption() if x["type"] == "MV")
        return {(c["equipement"], c["cle"], c["propriete"]): c for c in mv["conflits"]}


class TestConflits(_Ouvrage):
    def test_chaque_surcharge_touchee_est_signalee_et_conservee(self):
        avant = empreinte(self.s.ouvrage.vers_dict())
        c = self._conflits()
        code = self.eq.code_court()
        self.assertEqual(set(c), {(code, "TS_DEF", "libelle"), (code, "TS_DEF", "commentaire"),
                                  (code, "ES_DEF", "designation"), (code, "TS_DISC", "exclusion")})
        x = c[(code, "TS_DEF", "libelle")]
        self.assertEqual(x["local"], "Défaut vanne amont")
        self.assertTrue(x["nouveau"].endswith("(révisé)"))
        self.assertEqual(x["ident"], self.eq.ident)
        self.assertEqual(empreinte(self.s.ouvrage.vers_dict()), avant)          # rien n'est modifié

    def test_sans_surcharge_pas_de_conflit(self):
        self.assertFalse(any(k[0] == self.autre.code_court() for k in self._conflits()))

    def test_propriete_maitre_inchangee_pas_de_conflit(self):
        self.eq.libelles["TS_LOC"] = "Local amont"
        self.assertFalse(any(k[1] == "TS_LOC" for k in self._conflits()))

    def test_type_logique_change_et_type_surcharge(self):
        for s in self.s._catalogue_commun.signaux:
            if s["type"] == "MV" and s["famille"] == "ES" and s["code"] == "DEF":
                s["type_logique"] = "BOOL"
        self.assertIn((self.eq.code_court(), "ES_DEF", "type"), self._conflits())

    def test_conflit_rend_l_etat_de_synchronisation_a_examiner(self):
        c = self.s._catalogue_commun
        publie = {"catalogue": {"version": c.version, "types": c.types, "signaux": c.signaux, "regles": c.regles},
                  "modeles": self.s.modeles}
        e = profils.etat_synchronisation(self.s.ouvrage, self.s.catalogue, publie)
        self.assertEqual(e["types"]["MV"]["etat"], "Mise à jour à examiner")
        self.assertTrue(any("surcharge" in m for m in e["types"]["MV"]["motifs"]))
        self.assertEqual(e["equipements"][self.eq.ident]["etat"], "Mise à jour à examiner")
        self.assertEqual(e["equipements"][self.autre.ident]["etat"], "Mise à jour disponible")

    def test_adoption_conserve_les_surcharges(self):
        self.s.adopter_referentiel(["MV"])
        self.assertEqual(self.eq.libelles["TS_DEF"], "Défaut vanne amont")
        self.assertEqual(self.eq.commentaires["TS_DEF"], "Commentaire local")
        self.assertEqual(self.eq.es_meta["ES_DEF"]["designation"], "Contact défaut local")
        self.assertIn("TS_DISC", self.eq.exclus)


class TestRevenirAuStandard(_Ouvrage):
    def test_confirmation_obligatoire(self):
        avant = empreinte(self.s.ouvrage.vers_dict())
        with self.assertRaises(RegleMetier):
            self.s.revenir_au_standard(self.eq.ident, "TS_DEF", "libelle")
        self.assertEqual(empreinte(self.s.ouvrage.vers_dict()), avant)

    def test_une_propriete_a_la_fois(self):
        self.eq.valide = True
        self.s.revenir_au_standard(self.eq.ident, "TS_DEF", "libelle", confirme=True)
        self.assertNotIn("TS_DEF", self.eq.libelles)
        self.assertEqual(self.eq.commentaires["TS_DEF"], "Commentaire local")    # les autres restent
        self.s.revenir_au_standard(self.eq.ident, "ES_DEF", "designation", confirme=True)
        self.assertNotIn("designation", self.eq.es_meta["ES_DEF"])
        self.assertEqual(self.eq.es_meta["ES_DEF"]["type"], "EBOOL")
        self.s.revenir_au_standard(self.eq.ident, "TS_DISC", "exclusion", confirme=True)
        self.assertNotIn("TS_DISC", self.eq.exclus)
        self.assertFalse(self.eq.valide)                                        # contenu à revalider
        self.assertTrue(self.s.modifie)

    def test_propriete_ou_surcharge_inconnue_refusee(self):
        for cle, prop in (("TS_DEF", "adresse"), ("TS_LOC", "libelle"), ("TS_DEF", "inconnue")):
            with self.assertRaises(RegleMetier):
                self.s.revenir_au_standard(self.eq.ident, cle, prop, confirme=True)
        with self.assertRaises(RegleMetier):
            self.s.revenir_au_standard("absent", "TS_DEF", "libelle", confirme=True)


    def test_route_web(self):
        import os
        import shutil
        import tempfile
        from sorep_web.serveur import ROUTES_POST, Application
        dossier, env = tempfile.mkdtemp(), os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = dossier                     # l'enregistrement automatique reste isolé
        self.addCleanup(shutil.rmtree, dossier, ignore_errors=True)
        self.addCleanup(lambda: os.environ.pop("SOREP_DATA_DIR", None) if env is None
                        else os.environ.__setitem__("SOREP_DATA_DIR", env))
        self.assertEqual(ROUTES_POST["/api/referentiel/revenir-au-standard"], "revenir_au_standard")
        app = Application()
        app.s, app.ouvert = self.s, True
        with self.assertRaises(RegleMetier):
            app.revenir_au_standard({"ident_eq": self.eq.ident, "cle": "TS_DEF", "propriete": "libelle"})
        self.assertIn("TS_DEF", self.eq.libelles)
        app.revenir_au_standard({"ident_eq": self.eq.ident, "cle": "TS_DEF", "propriete": "libelle", "confirme": True})
        self.assertNotIn("TS_DEF", self.eq.libelles)


if __name__ == "__main__":
    unittest.main()
