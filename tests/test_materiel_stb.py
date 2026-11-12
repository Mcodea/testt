"""Gamme Advantys STB (12/11/2026) : nomenclature d'îlot à partir des guides Schneider, sans adresse inventée."""
import unittest

from genvar import materiel
from genvar.modele import PointES


def _points(nature, n, ident="e1"):
    return [PointES(ident, "RV01PM01", nature, f"{nature}_{ident}_{i}", "EBOOL", "", "", "", f"C{nature}{i}")
            for i in range(n)]


class TestCatalogueStb(unittest.TestCase):
    def test_chaque_module_cite_sa_source_et_son_courant(self):
        cat = materiel.catalogue_stb()
        self.assertGreaterEqual(len(cat["cartes"]), 30)
        self.assertTrue(all(c["source"].startswith("https://") and c["courant_bus_ma"] > 0 for c in cat["cartes"]))
        self.assertEqual(cat["_cartes"]["STB DDO 3410"]["voies"], 4)      # incohérence « 2 S » levée : 4 sorties
        self.assertEqual(cat["nim"]["modules_max"], 32)
        self.assertEqual(cat["nim"]["courant_bus_ma"], 1200)

    def test_references_stb_reconnues(self):
        for a in ("STBNIP2212", "STB NIP 2212", "Advantys STB"):
            self.assertEqual(materiel.plateforme_materiel(a)[0], "STB", a)


class TestProposerStb(unittest.TestCase):
    def test_nomenclature_d_ilot(self):
        p = materiel.proposer(_points("ET", 20) + _points("EA", 3), "STBNIP2212")
        self.assertEqual(p.plateforme, "STB")
        self.assertFalse(p.applicable)                                  # aucune adresse n'est proposée
        self.assertEqual(len(p.racks), 1)
        self.assertEqual(p.racks[0]["nim"], "STB NIP 2212")
        self.assertEqual(p.racks[0]["pdm"], "STB PDT 3100")
        self.assertEqual(p.racks[0]["terminaison"], "STB XMP 1100")
        refs = [m["reference"] for m in p.modules]
        self.assertEqual(refs, ["STB DDI 3725", "STB DDI 3725", "STB ACI 1400"])   # 20 ET : 2 × 16 avec réserve
        self.assertTrue(all(m["embase"] for m in p.modules))
        # numérotation Advantys : 1/127 NIM, 2/- PDM, 3/1, 4/2, 5/3 modules, 6/- terminaison
        compo = [(c["emplacement"], c["noeud"], c["reference"]) for c in p.racks[0]["composition"]]
        self.assertEqual(compo, [(1, 127, "STB NIP 2212"), (2, None, "STB PDT 3100"), (3, 1, "STB DDI 3725"),
                                 (4, 2, "STB DDI 3725"), (5, 3, "STB ACI 1400"), (6, None, "STB XMP 1100")])
        self.assertEqual([(m["position"], m["noeud"]) for m in p.modules], [(3, 1), (4, 2), (5, 3)])
        self.assertTrue(any("fin de vie" in r for r in p.remarques))

    def test_budget_du_bus_logique_signale(self):
        p = materiel.proposer(_points("SA", 10), "STBNIP2212")          # 7 × STB ACO 0220 à 210 mA
        self.assertTrue(any("courant du bus logique" in r and "1200 mA" in r for r in p.remarques), p.remarques)

    def test_plus_de_32_modules_second_ilot(self):
        p = materiel.proposer(_points("SA", 60), "STBNIP2212", emplacements_libres=2)
        self.assertEqual(len(p.racks), 2)
        self.assertTrue(all(len([m for m in p.modules if m["rack"] == r["numero"]]) <= 30 for r in p.racks))

    def test_separation_des_secours(self):
        p = materiel.proposer(_points("ET", 2, "a") + _points("ET", 2, "b"), "STBNIP2212", min_cartes={"ET": 2})
        self.assertEqual(len(p.modules), 2)


class TestImageIlot(unittest.TestCase):
    def test_exemple_du_guide_nip2212(self):
        refs = ["STB DDI 3230", "STB DDO 3200", "STB DDI 3420", "STB DDO 3410", "STB DDI 3610", "STB DDO 3600",
                "STB AVI 1270", "STB AVO 1250"]
        img = materiel.image_ilot(refs)
        self.assertEqual(img[0]["entree"], [45392, 45393])          # 1er module : 45392 (capture Advantys)
        self.assertEqual(img[1]["sortie"], [40001])
        self.assertEqual(img[6]["entree"], [45404, 45405, 45406, 45407])
        self.assertEqual(img[7]["sortie"], [40004, 40005])
        self.assertEqual(img[7]["entree"], [45408, 45409])          # 18 registres d'entrée : 45392 à 45409

    def test_captures_advantys_de_l_utilisateur(self):
        # îlot de la capture : 1/3/1 DDO 3705, 1/4/2 ACI 1400, 1/5/3 ACO 0220
        ddo, aci, aco = materiel.image_ilot(["STB DDO 3705", "STB ACI 1400", "STB ACO 0220"])
        self.assertEqual((ddo["sortie"], ddo["entree"]), ([40001], []))
        self.assertEqual(aci["entree"], list(range(45392, 45408)))
        self.assertEqual((aci["voies"][0]["registre"], aci["voies"][0]["etat"]), (45392, 45393))
        self.assertEqual((aci["voies"][7]["registre"], aci["voies"][7]["etat"]), (45406, 45407))
        self.assertEqual((aco["sortie"], aco["entree"]), ([40002, 40003], [45408, 45409]))
        self.assertEqual((aco["voies"][1]["registre"], aco["voies"][1]["etat"]), (40003, 45409))
        ddi = materiel.image_ilot(["STB DDI 3725"])[0]                  # capture 1/3/1 : 16 voies en 45392
        self.assertEqual((ddi["entree"], len(ddi["voies"])), ([45392], 16))
        self.assertTrue(all(v["registre"] == 45392 and v["etat"] is None for v in ddi["voies"]))

    def test_profil_par_defaut_entierement_connu(self):
        p = materiel.proposer(_points("ET", 3) + _points("ST", 3) + _points("EA", 3) + _points("SA", 1),
                              "STBNIP2212")
        self.assertTrue(all(x["connu"] for x in p.racks[0]["image_es"]))

    def test_module_non_documente_arrete_le_calcul(self):
        img = materiel.image_ilot(["STB DDI 3230", "STB ACI 0320", "STB DDI 3230"])
        self.assertEqual([x["connu"] for x in img], [True, False, False])
        self.assertEqual(img[2]["entree"], [])


if __name__ == "__main__":
    unittest.main()
