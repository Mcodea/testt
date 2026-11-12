"""Contrôle de conception du référentiel : constats attendus et non-régression des corrections V0.26."""
import copy
import unittest

from genvar import audit_referentiel as a, chemins
from genvar.catalogue import Catalogue


class TestAudit(unittest.TestCase):
    def setUp(self):
        self.cat = Catalogue.charger(chemins.fichier_catalogue_origine())

    def constats(self, cat=None):
        return {(c.type, c.code) for c in a.auditer(cat or self.cat)}

    def test_catalogue_livre(self):
        c = self.constats()
        self.assertFalse({x for x in c if x[1] in ("DOUBLON", "REGLE_SANS_SOURCE", "CALCULEE_SANS_ORDRE",
                                                       "CALCULEE_SANS_SOURCE")}, c)
        # points de conception laissés à l'arbitrage de l'exploitant, signalés et non corrigés en silence
        self.assertIn(("LT", "SEUILS_PAR_DEFAUT"), c)
        self.assertIn(("FT", "OPTION_SANS_EFFET"), c)

    def test_detecte_defaut_de_manoeuvre_sans_ordre(self):
        cat = copy.deepcopy(self.cat)
        for s in cat.signaux:
            if s["type"] == "EV" and s["code"] == "DEFTPS":
                s["presence"] = "Par défaut"                         # état du référentiel V1.1
        self.assertIn(("EV", "CALCULEE_SANS_ORDRE"), self.constats(cat))

    def test_detecte_doublon_et_regle_sans_source(self):
        cat = copy.deepcopy(self.cat)
        cat.signaux.append(copy.deepcopy(next(s for s in cat.signaux if s["type"] == "HV" and s["code"] == "OUV")))
        cat.regles.append({"id": "HV-99", "type": "HV", "si": ["ES_INEXISTANTE"], "propose": ["TS_DISC"],
                           "mode": "proposition", "logique": "x"})
        c = self.constats(cat)
        self.assertIn(("HV", "DOUBLON"), c)
        self.assertIn(("HV", "REGLE_SANS_SOURCE"), c)


if __name__ == "__main__":
    unittest.main()


class TestReferentielFige(unittest.TestCase):
    def test_ancien_ouvrage_non_modifie_puis_adoption_explicite(self):
        import os, tempfile
        from genvar.modele import Equipement
        from genvar.session import Session
        os.environ["SOREP_DATA_DIR"] = tempfile.mkdtemp()
        ancien = Catalogue.charger(chemins.fichier_catalogue_origine())
        ancien.version = "référentiel V1.1"
        ancien.signaux = [s for s in ancien.signaux if not (s["type"] == "HV" and s["code"] == "INT")]
        for r in ancien.regles:
            if r["id"] == "HV-03":
                r["propose"] = ["TS_DISC"]
        s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s.nouveau(False)
        s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
        s.ajouter_sous_ensemble("00")
        s.catalogue = ancien                                       # ouvrage enregistré avec l'ancien référentiel
        hv = s.ajouter_equipement(Equipement("00", "HV", "01"))
        s.decider_propositions(hv.ident, "retenir")
        s.valider_equipements([hv.ident])
        s.plan(); props, _ = s.plan(); s.appliquer(props)
        adresses = {v.nom: v.adresse for v in s.variables()}
        ecarts = s.ecarts_referentiel()
        self.assertEqual([(x["type"], x["ajoutees"]) for x in ecarts], [("HV", ["TS_INT"])])
        self.assertNotIn("TS_INT", {p.cle for p in s.propositions(hv).values()})   # rien d'appliqué en silence
        s.adopter_referentiel()
        self.assertFalse(hv.valide)
        self.assertEqual([p.cle for p in s.propositions_en_attente(hv)], ["TS_INT"])
        self.assertEqual({v.nom: v.adresse for v in s.variables() if v.nom in adresses}, adresses)
        self.assertEqual(s.ecarts_referentiel(), [])
