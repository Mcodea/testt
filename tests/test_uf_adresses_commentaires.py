"""Unités fonctionnelles, commentaires modifiables, validation des adresses (projet neuf)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.session import Session, RegleMetier


class TestNeufV09(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = tempfile.mkdtemp()
        s = self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s.definir("lieu", "XT25"); s.definir("code_ouvrage", "RV"); s.definir("libelle", "Réservoir")
        s.ajouter_sous_ensemble("11", "Réservoir 1")
        s.ajouter_equipement(Equipement("11", "MV", "03"))
        s.ajouter_equipement(Equipement("11", "PM", "01"))
        self.mv, self.pm = (e.ident for e in s.ouvrage.equipements)

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def var(self, ident, cle):
        return next(v for v in self.s.variables() if v.ident_eq == ident and v.cle == cle)

    def test_uf_regroupe_sans_changer_les_noms(self):
        noms_avant = [v.nom for v in self.s.variables()]
        self.s.ajouter_uf("UF01", "Alimentation")
        self.s.affecter_uf({self.mv}, "UF01")
        self.assertEqual([v.nom for v in self.s.variables()], noms_avant)
        self.assertEqual(self.var(self.mv, "TS_FER").uf, "UF01")
        with self.assertRaises(RegleMetier):
            self.s.ajouter_uf("UF01")
        self.s.supprimer_uf("UF01")                         # l'équipement reste, sans UF
        self.assertEqual(len(self.s.ouvrage.equipements), 2)
        self.assertEqual(self.s.ouvrage.equipement(self.mv).uf, "")

    def test_commentaire_modifiable_et_retour_au_texte_propose(self):
        propose = self.var(self.mv, "TS_FER").commentaire
        self.s.definir_textes(self.mv, "TS_FER", commentaire="Vanne sortie fermée (FDC)")
        v = self.var(self.mv, "TS_FER")
        self.assertEqual(v.commentaire, "Vanne sortie fermée (FDC)")
        self.assertTrue(v.commentaire_saisi)
        self.assertEqual(v.commentaire_propose, propose)
        self.s.definir_textes(self.mv, "TS_FER", commentaire="")
        self.assertEqual(self.var(self.mv, "TS_FER").commentaire, propose)
        with self.assertRaises(RegleMetier):
            self.s.definir_textes(self.mv, "TS_FER", libelle="x" * 41)

    def test_adresse_validee_jamais_modifiee_en_silence(self):
        props, err = self.s.plan()
        self.s.appliquer(props)
        self.var(self.mv, "TS_FER")
        ok, refus = self.s.valider_adresses([(self.mv, "TS_FER")])
        self.assertEqual(ok, 1)
        self.assertTrue(self.var(self.mv, "TS_FER").adresse_validee)
        with self.assertRaises(RegleMetier):
            self.s.definir_adresses(self.mv, "TS_FER", adresse="%MW1010.0")
        self.s.definir_adresses(self.mv, "TS_FER", adresse="%MW1010.0", deverrouiller=True)
        v2 = self.var(self.mv, "TS_FER")
        self.assertEqual(v2.adresse, "%MW1010.0")
        self.assertFalse(v2.adresse_validee)               # repasse « proposée »

    def test_reattribution_complete_conserve_les_adresses_validees(self):
        props, _ = self.s.plan()
        self.s.appliquer(props)
        adresse = self.var(self.pm, "CP_HF").adresse
        self.s.valider_adresses([(self.pm, "CP_HF")])
        props, err = self.s.plan(tout_refaire=True)
        self.assertFalse(err)
        self.s.appliquer(props, tout_refaire=True)
        self.assertEqual(self.var(self.pm, "CP_HF").adresse, adresse)

    def test_validation_refusee_sans_adresse(self):
        ok, refus = self.s.valider_adresses([(self.mv, "TS_FER")])
        self.assertEqual(ok, 0)
        self.assertTrue(refus)

    def test_alerte_adresses_non_validees(self):
        props, _ = self.s.plan()
        self.s.appliquer(props)
        self.assertTrue(any(a.repere == "Adresses" for a in self.s.anomalies()))
        self.s.valider_adresses([(v.ident_eq, v.cle) for v in self.s.variables()])
        self.assertFalse(any(a.repere == "Adresses" for a in self.s.anomalies()))


if __name__ == "__main__":
    unittest.main()


class TestSignalAdapte(unittest.TestCase):
    """Un signal du catalogue modifié pour un seul équipement."""

    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = tempfile.mkdtemp()
        s = self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s.definir("lieu", "XT25"); s.definir("code_ouvrage", "RV")
        s.ajouter_sous_ensemble("C1", "Cuve")
        s.ajouter_equipement(Equipement("C1", "CH", "01"))
        s.ajouter_equipement(Equipement("C1", "CH", "02"))
        self.eq1, self.eq2 = s.ouvrage.equipements

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def test_adaptation_limitee_a_l_equipement(self):
        from genvar.modele import SignalPropre
        signal = next(x for x in self.s.catalogue.signaux_du_type("CH") if x["code"] == "MA")
        props, _ = self.s.plan(); self.s.appliquer(props)
        avant = next(v for v in self.s.variables() if v.ident_eq == self.eq1.ident and v.code == "MA")
        nouveau = SignalPropre("En chauffe", signal["famille"], signal["code"], "BOOL", "", "Interne")
        Session.personnaliser_signal(self.eq1, signal, nouveau)
        v1 = next(v for v in self.s.variables() if v.ident_eq == self.eq1.ident and v.code == "MA")
        v2 = next(v for v in self.s.variables() if v.ident_eq == self.eq2.ident and v.code == "MA")
        self.assertEqual((v1.nom, v1.adresse), (avant.nom, avant.adresse))   # nom et adresse conservés
        self.assertEqual(v1.information, "En chauffe")
        self.assertEqual(v1.es, "Interne")
        self.assertEqual(v1.origine, "Catalogue adapté")
        self.assertEqual(v2.information, signal["information"])            # l'autre équipement ne change pas
        self.assertEqual(sum(v.code == "MA" for v in self.s.variables() if v.ident_eq == self.eq1.ident), 1)
        self.assertFalse(any("obligatoire retiré" in a.message for a in self.s.anomalies()))
        with self.assertRaises(RegleMetier):                               # le code ne change pas
            Session.personnaliser_signal(self.eq1, signal, SignalPropre("x", "TS", "AUTRE"))
        Session.retablir_signal(self.eq1, "TS_MA")
        v1 = next(v for v in self.s.variables() if v.ident_eq == self.eq1.ident and v.code == "MA")
        self.assertEqual(v1.information, signal["information"])
        self.assertEqual(v1.adresse, avant.adresse)
