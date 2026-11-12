"""Étape Matériel : cartes et racks PROPOSÉS depuis les E/S au contenu validé, puis validés (9 novembre 2026)."""
import json
import os
import tempfile
import unittest

from genvar import chemins, materiel
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.session import Session, RegleMetier


class _P:
    def __init__(self, point, raccordement="Câblé"):
        self.point, self.raccordement = point, raccordement


class TestCalcul(unittest.TestCase):
    def test_profil_64_8_reserve_20_et_m580(self):
        pts = [_P("ET")] * 120 + [_P("ST")] * 30 + [_P("EA")] * 13 + [_P("SA")] + [_P("ET", "Communication")] * 9
        p = materiel.proposer(pts, "M580")
        b = {x.nature: (x.es, x.reference, x.utilisables, x.cartes) for x in p.besoins}
        self.assertEqual(b["ET"], (120, "BMX DDI 6402K", 51, 3))      # communication exclue ; 64 × 0,8 = 51
        self.assertEqual(b["EA"], (13, "BMX AMI 0810", 6, 3))
        self.assertEqual(p.racks[0]["cpu"], [0, 1])
        self.assertEqual([m["position"] for m in p.modules], list(range(2, 10)))
        self.assertTrue(all(x.reserve >= 0.2 for x in p.besoins))

    def test_deterministe_et_extension(self):
        pts = [_P("ET")] * 700
        a, b = materiel.proposer(pts, ""), materiel.proposer(pts, "")
        self.assertEqual(a.dict(), b.dict())
        self.assertEqual([r["reference"] for r in a.racks], ["BMX XBP 1200", "BMX XBP 0400"])
        self.assertTrue(any("non renseigné" in r for r in a.remarques))
        self.assertTrue(any("extension" in r for r in a.remarques))

    def test_rack_le_plus_court_et_aucune_es(self):
        p = materiel.proposer([_P("ET")] * 10, "M340")
        self.assertEqual(p.racks[0]["reference"], "BMX XBP 0400")
        self.assertEqual(materiel.proposer([], "M340").modules, [])

    def test_catalogue_corrompu_refuse(self):
        d = tempfile.mkdtemp()
        f = os.path.join(d, "c.json")
        with open(f, "w", encoding="utf-8") as h:
            json.dump({"cartes": [], "profils": {"x": {"ET": "?"}}, "plateformes": {}}, h)
        with self.assertRaises(materiel.CatalogueMaterielErreur):
            materiel.proposer([_P("ET")], "M340", chemin=f)


class TestSession(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = tempfile.mkdtemp()
        s = self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s.nouveau(lieu_dans_le_nom=False)
        s.definir("lieu", "ATMS"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
        s.definir("automate", "M340")
        s.ajouter_sous_ensemble("00")
        s.ajouter_equipement(Equipement("00", "OD", "01"))
        s.ajouter_equipement(Equipement("00", "EX", "01", options=["Disponibilité câblée"]))

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def paires(self):
        return [(p.ident_eq, p.cle) for p in self.s.points()]

    def test_parcours_es_materiel(self):
        s = self.s
        with self.assertRaises(RegleMetier):
            s.proposer_materiel()                                 # contenu des E/S pas encore validé
        s.valider_contenu_es(self.paires())
        prop = s.appliquer_materiel()
        self.assertEqual({m.reference for m in s.ouvrage.modules}, {"BMX DDI 6402K"})
        self.assertEqual(s.ouvrage.racks[0]["reference"], "BMX XBP 0400")
        self.assertFalse(s.ouvrage.materiel_valide)
        s.valider_materiel()
        self.assertTrue(s.ouvrage.materiel_valide)
        n, manquantes, _ = s.implanter_es()
        self.assertGreater(n, 0)
        self.assertEqual(manquantes, {})
        self.assertTrue(all(p.contenu_valide and p.adresse.startswith("%I0.1.") for p in s.points()))
        with self.assertRaises(RegleMetier):
            s.appliquer_materiel()                                # E/S déjà placées : pas de remplacement silencieux
        s.definir_reserve(0.25)
        self.assertFalse(s.ouvrage.materiel_valide)             # toute modification remet le matériel à valider
        self.assertEqual(prop.plateforme, "M340")

    def test_contenu_modifie_a_revalider(self):
        s = self.s
        s.valider_contenu_es(self.paires())
        p = s.points()[0]
        s.definir_es(p.ident_eq, p.cle, sens="0 = Défaut (à manque)")
        q = next(x for x in s.points() if x.cle == p.cle and x.ident_eq == p.ident_eq)
        self.assertFalse(q.contenu_valide)
        self.assertEqual(s.bilan_es()["contenu_non_valide"], 1)

    def test_persistance(self):
        s = self.s
        s.valider_contenu_es(self.paires())
        s.appliquer_materiel("16_4")
        chemin = os.path.join(os.environ["SOREP_DATA_DIR"], "o.ouvrage.json")
        s.enregistrer(chemin)
        s2 = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s2.ouvrir(chemin)
        self.assertEqual(s2.ouvrage.profil_cartes, "16_4")
        self.assertEqual(s2.ouvrage.racks, s.ouvrage.racks)
        self.assertTrue(all(p.contenu_valide for p in s2.points()))


if __name__ == "__main__":
    unittest.main()


class TestS4W(unittest.TestCase):
    def test_boitier_le_plus_petit_et_indicatif(self):
        pts = [_P("ET")] * 10 + [_P("EA")] * 3 + [_P("ST")] * 2
        p = materiel.proposer(pts, "SOFREL S4W")
        self.assertEqual((p.plateforme, p.racks[0]["reference"], p.applicable), ("S4W", "S4W Medium", False))
        refs = [m["reference"] for m in p.modules]
        self.assertIn("Module 8DI", refs)
        self.assertNotIn("CPU", " ".join(refs))                 # règle 1 : CPU intégrée, pas de carte CPU
        et = next(b for b in p.besoins if b.nature == "ET")
        self.assertGreaterEqual(et.voies * 0.8, et.es)

    def test_capacite_depassee(self):
        p = materiel.proposer([_P("ET")] * 400, "S4W")
        self.assertEqual(p.modules, [])
        self.assertIn("capacité", p.remarques[0])
