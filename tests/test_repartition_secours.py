"""Retour d'essai 10 (12/11/2026), lot M5 : répartition des E/S selon les bonnes pratiques B3, B4, B7, B8."""
import unittest

from genvar import chemins, materiel
from genvar.cartes_es import Module, implanter, secours_partageant_une_carte
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, PointES
from genvar.session import RegleMetier, Session


def _pt(ident, n, nature="ET", module="", voie=""):
    return PointES(ident, f"R{ident}", nature, f"{ident}_{n}", "BOOL", "", "", "", f"C_{n}",
                   module=module, voie=voie)


def _pompe(ident, n=4, nature="ET"):
    return [_pt(ident, i, nature) for i in range(n)]


class TestImplanterSecours(unittest.TestCase):
    def test_sans_groupe_les_deux_pompes_partagent_la_premiere_carte(self):
        pts = _pompe("P1") + _pompe("P2")
        mods = [Module(0, 1, "ET", 16), Module(0, 2, "ET", 16)]
        aff, _, _ = implanter(pts, mods)
        self.assertEqual({k for _, k, _ in aff}, {"0.1"})

    def test_groupe_confirme_cartes_distinctes_et_motif(self):
        pts = _pompe("P1") + _pompe("P2")
        mods = [Module(0, 1, "ET", 16), Module(0, 2, "ET", 16)]
        rapport = {}
        aff, manq, _ = implanter(pts, mods, groupes=[["P1", "P2"]], rapport=rapport)
        cartes = {p.ident_eq: k for p, k, _ in aff}
        self.assertNotEqual(cartes["P1"], cartes["P2"])
        self.assertEqual(manq, {})
        self.assertEqual(rapport["secours_non_separes"], [])
        motif = rapport["motifs"][("P2", "C_0")]
        self.assertIn("carte distincte de son groupe de secours", motif)
        self.assertIn("RP1", motif)

    def test_separation_passe_avant_la_reserve(self):
        # 2e carte : la séparation l'emporte même si elle doit entamer la réserve (B4 > B2)
        pts = _pompe("P1", 4) + _pompe("P2", 8)
        mods = [Module(0, 1, "ET", 16), Module(0, 2, "ET", 8)]
        rapport = {}
        aff, _, _ = implanter(pts, mods, seuil=0.2, groupes=[["P1", "P2"]], rapport=rapport)
        cartes = {p.ident_eq: k for p, k, _ in aff}
        self.assertEqual(cartes, {"P1": "0.1", "P2": "0.2"})
        self.assertIn("réserve de voies entamée", rapport["motifs"][("P2", "C_0")])

    def test_separation_impossible_signalee_jamais_tue(self):
        pts = _pompe("P1") + _pompe("P2")
        mods = [Module(0, 1, "ET", 16)]
        rapport = {}
        aff, manq, _ = implanter(pts, mods, groupes=[["P1", "P2"]], rapport=rapport)
        self.assertEqual(len(aff), 8)
        self.assertEqual(manq, {})
        self.assertEqual(rapport["secours_non_separes"], [("P2", "0.1", ["P1"])])
        self.assertIn("ATTENTION", rapport["motifs"][("P2", "C_0")])

    def test_e_s_deja_placee_compte_et_ne_bouge_pas(self):
        # P1 déjà câblée sur 0.2 (existant validé, B7) : P2 va sur 0.1, P1 n'est pas déplacée
        pts = [_pt("P1", i, module="0.2", voie=str(i)) for i in range(4)] + _pompe("P2")
        mods = [Module(0, 1, "ET", 16), Module(0, 2, "ET", 16)]
        aff, _, _ = implanter(pts, mods, groupes=[["P1", "P2"]])
        self.assertEqual({p.ident_eq for p, _, _ in aff}, {"P2"})
        self.assertEqual({k for _, k, _ in aff}, {"0.1"})

    def test_controle_des_placements_existants(self):
        pts = [_pt("P1", 0, module="0.1", voie="0"), _pt("P2", 0, module="0.1", voie="1")]
        mods = [Module(0, 1, "ET", 16)]
        self.assertEqual(secours_partageant_une_carte(pts, mods, [["P1", "P2"]]), [("0.1", ["RP1", "RP2"])])
        self.assertEqual(secours_partageant_une_carte(pts, mods, []), [])


class TestProposerMateriel(unittest.TestCase):
    def test_cartes_minimales_pour_separer(self):
        pts = _pompe("P1", 2) + _pompe("P2", 2)
        sans = materiel.proposer(pts, "BMXP342020")
        avec = materiel.proposer(pts, "BMXP342020", min_cartes={"ET": 2})
        n = lambda p: len([m for m in p.modules if m["nature"] == "ET"])  # noqa: E731
        self.assertEqual(n(sans), 1)
        self.assertEqual(n(avec), 2)
        self.assertTrue(any("groupe de secours" in r for r in avec.remarques))

    def test_emplacements_libres_par_rack(self):
        pts = _pompe("P1", 2)
        prop = materiel.proposer(pts, "BMXP342020", emplacements_libres=2)
        libres = materiel.emplacements_libres(prop.racks, [Module(**{k: m[k] for k in ("rack", "position", "nature",
                                                                                         "voies")})
                                                           for m in prop.modules])
        self.assertTrue(all(v >= 2 for v in libres.values()), libres)
        self.assertTrue(any("emplacement(s) laissé(s) libre(s)" in r for r in prop.remarques))


def _session():
    s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
    s.nouveau(False)
    s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
    s.ouvrage.libelle = "Essai"; s.ouvrage.automate = "BMXP342020"; s.ouvrage.statut = "En cours"
    s.ajouter_sous_ensemble("00")
    return s


class TestSessionGroupes(unittest.TestCase):
    def setUp(self):
        self.s = _session()
        self.a = self.s.ajouter_equipement(Equipement("00", "MV", "01"))
        self.b = self.s.ajouter_equipement(Equipement("00", "MV", "02"))

    def test_proposition_puis_confirmation(self):
        prop = self.s.groupes_secours_proposes()
        self.assertEqual(len(prop), 1)
        self.assertEqual({m["ident"] for m in prop[0]["membres"]}, {self.a.ident, self.b.ident})
        self.assertEqual(self.s.groupes_secours_actifs(), [])        # rien appliqué sans confirmation
        self.s.confirmer_groupe_secours([self.a.ident, self.b.ident])
        self.assertEqual(self.s.groupes_secours_proposes(), [])
        self.assertEqual(self.s.groupes_secours_actifs(), [[self.a.ident, self.b.ident]])

    def test_refus_et_desactivation(self):
        self.s.refuser_groupe_secours([self.b.ident, self.a.ident])
        self.assertEqual(self.s.groupes_secours_proposes(), [])
        self.s.confirmer_groupe_secours([self.a.ident, self.b.ident])
        self.s.regles_repartition(separation_secours=False)
        self.assertEqual(self.s.groupes_secours_actifs(), [])
        etat = self.s.regles_repartition(separation_secours=True, emplacements_libres_rack=3)
        self.assertEqual(etat["emplacements_libres_rack"], 3)
        self.assertEqual(len(etat["groupes_secours"]), 1)
        self.s.retirer_groupe_secours([self.b.ident, self.a.ident])
        self.assertEqual(self.s.ouvrage.groupes_secours, [])

    def test_groupe_invalide_refuse(self):
        with self.assertRaises(RegleMetier):
            self.s.confirmer_groupe_secours([self.a.ident])
        with self.assertRaises(RegleMetier):
            self.s.confirmer_groupe_secours([self.a.ident, "inconnu"])
        with self.assertRaises(RegleMetier):
            self.s.regles_repartition(emplacements_libres_rack=9)

    def test_un_equipement_n_appartient_qu_a_un_groupe(self):
        c = self.s.ajouter_equipement(Equipement("00", "MV", "03"))
        self.s.confirmer_groupe_secours([self.a.ident, self.b.ident])
        self.s.confirmer_groupe_secours([self.b.ident, c.ident])
        self.assertEqual(self.s.ouvrage.groupes_secours, [[self.b.ident, c.ident]])

    def test_groupes_survivent_a_la_sauvegarde(self):
        from genvar.modele import Ouvrage
        self.s.confirmer_groupe_secours([self.a.ident, self.b.ident])
        o = Ouvrage.depuis_dict(self.s.ouvrage.vers_dict())
        self.assertEqual(o.groupes_secours, [[self.a.ident, self.b.ident]])
        self.assertTrue(o.separation_secours)
        self.assertEqual(o.emplacements_libres_rack, 2)


if __name__ == "__main__":
    unittest.main()
