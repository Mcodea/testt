"""Guidage : prochaines actions, regroupement des contrôles, explications (module sans Qt)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, SousEnsemble
from genvar.session import Session
from genvar_qt import guide


class TestGuide(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = tempfile.mkdtemp()
        self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def commandes(self):
        return [a.commande for a in guide.a_faire(self.s)]

    def test_parcours_guide_de_bout_en_bout(self):
        s = self.s
        self.assertEqual(self.commandes()[:3], ["fiche", "ajouter_uf", "ajouter_eq"])
        s.definir("lieu", "ATHR"); s.definir("code_ouvrage", "P"); s.definir("libelle", "Détendeur")
        a = guide.a_faire(s)[0]
        self.assertEqual(a.commande, "fiche")
        self.assertIn("2 lettres", a.detail)                       # le défaut réel de l'utilisateur
        s.definir("code_ouvrage", "DT")
        s.ajouter_sous_ensemble("11", "Détendeur")
        s.ajouter_equipement(Equipement("11", "MV", "01"))
        c = self.commandes()
        self.assertEqual(c[0], "es")                               # la liste des E/S d'abord
        s.valider_es([(p.ident_eq, p.cle) for p in s.points()])
        c = self.commandes()
        self.assertEqual(c[0], "propositions")                     # discordance / intermédiaire à examiner
        self.assertIn("attribuer", c)
        for cle, p in s.propositions(s.ouvrage.equipements[0]).items():
            if p.etat == "proposé":
                Session.refuser_proposition(s.ouvrage.equipements[0], cle)
        self.assertEqual(self.commandes()[0], "attribuer")
        props, _ = s.plan(); s.appliquer(props)
        self.assertEqual(self.commandes()[0], "valider")
        s.valider_adresses([(v.ident_eq, v.cle) for v in s.variables()])
        self.assertEqual(self.commandes()[0], "es")                # adresses physiques : dernière étape
        adresses = iter(f"%I0.1.{i}" for i in range(16))
        for p in s.points():
            s.definir_adresses(p.ident_eq, p.cle, adresse_es=next(adresses))
        self.assertEqual(self.commandes(), ["exports"])

    def test_controles_regroupes(self):
        s = self.s
        s.definir("lieu", "ATHR"); s.definir("code_ouvrage", "P")
        s.ouvrage.sous_ensembles.append(SousEnsemble("DT"))
        s.ouvrage.equipements.append(Equipement("DT", "CH", "01"))
        groupes = guide.grouper(s.anomalies())
        cles = [g.cle for g in groupes]
        self.assertEqual(cles[0], "identification")
        self.assertIn("sans_adresse", cles)
        g = next(g for g in groupes if g.cle == "sans_adresse")
        self.assertEqual(g.commande, "attribuer")
        self.assertEqual(len(g.anomalies), len(s.variables()))

    def test_explications(self):
        s = self.s
        s.definir("lieu", "XT25"); s.definir("code_ouvrage", "RV")
        s.ajouter_sous_ensemble("11")
        s.ajouter_equipement(Equipement("11", "MV", "03"))
        v = next(x for x in s.variables() if x.code == "FER")
        self.assertIn("XT25 (lieu) + RV (ouvrage) + 11 (sous-ensemble) + MV (type) + 03 (numéro)",
                      guide.expliquer_nom(s.ouvrage, v))
        self.assertIn("Attribuer", guide.expliquer_adresse(s.ouvrage, v))
        props, _ = s.plan(); s.appliquer(props)
        v = next(x for x in s.variables() if x.code == "FER")
        texte = guide.expliquer_adresse(s.ouvrage, v)
        self.assertIn("bit", texte)
        self.assertIn("proposée", texte)
        rep = guide.expliquer_repere(s.ouvrage, s.ouvrage.equipements[0])
        self.assertTrue(all(ok for *_, ok in rep))


if __name__ == "__main__":
    unittest.main()
