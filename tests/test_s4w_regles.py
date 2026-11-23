"""Règles du matériel SOFREL S4W (cahier V1-3-17, V1-3-18) : proposition indicative, jamais d'adresse S4W inventée."""
import unittest
from types import SimpleNamespace

from genvar import materiel


def points(**nb):
    return [SimpleNamespace(point=n, raccordement="Câblée") for n, k in nb.items() for _ in range(k)]


class TestReglesS4W(unittest.TestCase):
    def test_une_sortie_analogique_impose_un_module_ao(self):
        cat = materiel.catalogue_s4w()
        self.assertTrue(all(b.get("AO", 0) == 0 for b in cat["_boitiers"].values()), "aucun boîtier n'a de voie AO intégrée")
        p = materiel.proposer_s4w(points(ET=4, SA=1))
        modules_ao = [m for m in p.modules if m["nature"] == "SA"]
        self.assertTrue(modules_ao, "une sortie analogique doit créer un module AO")
        self.assertTrue(all("AO" in m["reference"] for m in modules_ao), modules_ao)
        self.assertTrue(any("module AO" in r for r in p.remarques))
        sans = materiel.proposer_s4w(points(ET=4))
        self.assertFalse([m for m in sans.modules if m["nature"] == "SA"])
        self.assertFalse(any("module AO" in r for r in sans.remarques))

    def test_sortie_tor_signale_la_limite_de_150_ma(self):
        p = materiel.proposer_s4w(points(ET=4, ST=2))
        self.assertTrue(any("150 mA" in r and "relais d'interface" in r for r in p.remarques), p.remarques)
        sans = materiel.proposer_s4w(points(ET=4))
        self.assertFalse(any("150 mA" in r for r in sans.remarques))

    def test_proposition_toujours_indicative_sans_adresse_inventee(self):
        p = materiel.proposer_s4w(points(ET=8, ST=2, EA=2, SA=1))
        self.assertFalse(p.applicable)
        self.assertTrue(any("S4W-Tools" in r for r in p.remarques))
        self.assertTrue(all(m["reference"] and "BMX" not in m["reference"] for m in p.modules))

    def test_references_a_confirmer_avec_lacroix(self):
        p = materiel.proposer_s4w(points(ET=2))
        self.assertTrue(any("LACROIX" in r for r in p.remarques))


if __name__ == "__main__":
    unittest.main()
