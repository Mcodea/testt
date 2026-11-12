"""Cartes d'E/S par module (règles R1 à R11).

Ouvrage fictif : lieu retiré des noms, local W3, extracteur avec disponibilité câblée.
Un test réussi ne vaut pas validation sur l'automate : les adresses restent « proposées » jusqu'à la recette.
"""
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genvar import chemins
from genvar.cartes_es import sens_par_defaut, implanter, Module
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.session import Session, RegleMetier


class TestCartesES(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier
        s = self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s.nouveau(lieu_dans_le_nom=False)                  # comme un projet neuf créé dans l'interface
        s.definir("lieu", "XTST"); s.definir("code_ouvrage", "S2"); s.definir("libelle", "Ouvrage d'essai")
        s.ajouter_uf("UF01", "Électricité", "E0")
        s.ajouter_uf("UF02", "Ventilation", "W3")
        s.modifier_sous_ensemble("W3", "W3", "Local stockage fuel 20m3")
        s.ajouter_equipement(Equipement("E0", "OD", "01", uf="UF01"))
        s.ajouter_equipement(Equipement("W3", "EX", "02", options=["Disponibilité câblée"], uf="UF02"))

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def es(self):
        return {p.nom: p for p in self.s.liste_es()}

    # ------------------------------------------------------------------ R1 à R8
    def test_nommage_textes_sens(self):
        es = self.es()
        p = es["ET_S2W3EX02_DISPO"]                                  # R2 sans lieu, R8 DISPO câblée
        self.assertEqual(p.repere, "XTSTS2W3EX02")                   # R1 : le PCF garde le lieu
        self.assertEqual(p.extension, "dispo")                       # R3
        self.assertEqual(p.sens, "1 = Disponible")                   # R7
        self.assertEqual((p.organe1, p.organe2), ("Extracteur d’air", "Bâtiment et sécurité"))   # R6 type / domaine
        self.assertEqual(es["ET_S2W3EX02_MA"].sens, "1 = En marche")
        self.assertEqual(es["ET_S2W3EX02_DEF"].sens, "1 = Défaut")
        # sans l'option, DISPO redevient une information calculée (pas de voie)
        eq = next(e for e in self.s.ouvrage.equipements if e.type == "EX")
        eq.options.remove("Disponibilité câblée")
        self.assertNotIn("ET_S2W3EX02_DISPO", self.es())
        self.assertTrue(any(v.nom == "TS_S2W3EX02_DISPO" for v in self.s.variables()))

    def test_sens_par_defaut_et_surcharge(self):
        self.assertEqual(sens_par_defaut("ET", "AL_GRL", "Alarme générale"), "1 = Alarme")
        self.assertEqual(sens_par_defaut("ET", "ASI_BYP", "ASI sur by-pass"), "1 = Sur by-pass")
        self.assertEqual(sens_par_defaut("EA", "NIV", "Niveau"), "")
        p = self.es()["ET_S2W3EX02_DEF"]
        self.s.definir_es(p.ident_eq, p.cle, sens="0 = Défaut (à manque)")
        self.assertEqual(self.es()["ET_S2W3EX02_DEF"].sens, "0 = Défaut (à manque)")

    # ------------------------------------------------------------------ R5, R9, R10
    def test_modules_et_implantation(self):
        s = self.s
        with self.assertRaises(RegleMetier):
            s.implanter_es()                                         # aucun module : rien n'est inventé
        s.ajouter_module(0, 2, "ET", 16, "BMX DDI 1602")
        s.ajouter_module(0, 3, "ET", 16, "BMX DDI 1602")
        with self.assertRaises(RegleMetier):
            s.ajouter_module(0, 2, "ST", 16)                          # même position
        n, manquantes, depassements = s.implanter_es()
        es = self.es()
        et = [p for p in es.values() if p.point == "ET"]
        self.assertEqual(n, len(et))
        self.assertEqual(manquantes, {})
        # E/S d'un même équipement groupées sur un module, voies dans l'ordre
        od = sorted((p for p in et if "OD01" in p.nom), key=lambda p: int(p.voie))
        self.assertEqual({p.module for p in od}, {"0.2"})
        self.assertEqual(od[0].adresse, "%I0.2.0")
        ex = [p for p in et if "EX02" in p.nom]
        self.assertEqual(len({p.module for p in ex}), 1)
        self.assertTrue(all(not p.validee for p in et))              # proposées, pas validées
        # réserve de 20 % respectée : 16 voies → 12 au plus par module tant qu'un autre module a de la place
        for b in s.bilan_modules():
            self.assertLessEqual(b["occupees"], 12)
        # valider une E/S, ajouter un équipement, réimplanter : rien ne bouge
        avant = {p.nom: p.adresse for p in self.es().values()}
        p = es["ET_S2W3EX02_DISPO"]
        s.definir_es(p.ident_eq, p.cle, validee=True)
        s.ajouter_equipement(Equipement("E0", "AR", "01", uf="UF01"))
        s.implanter_es()
        apres = {p.nom: p.adresse for p in self.es().values()}
        self.assertTrue(all(apres[k] == v for k, v in avant.items()))
        self.assertTrue(apres["ET_S2E0AR01_MQU"])
        # libérer les voies proposées : la validée reste
        s.liberer_voies_proposees()
        es = self.es()
        self.assertEqual(es["ET_S2W3EX02_DISPO"].adresse, avant["ET_S2W3EX02_DISPO"])
        self.assertEqual(es["ET_S2E0OD01_DEF"].adresse, "")

    def test_voies_manquantes_et_adresse_saisie(self):
        s = self.s
        s.ajouter_module(0, 2, "ET", 4)
        p = self.es()["ET_S2E0OD01_DEF"]
        s.definir_es(p.ident_eq, p.cle, adresse="%I0.2.0")           # adresse saisie à la main : voie occupée
        n, manquantes, _ = s.implanter_es()
        adresses = [x.adresse for x in self.es().values() if x.adresse]
        self.assertEqual(len(adresses), len(set(adresses)))
        self.assertGreater(manquantes.get("ET", 0), 0)               # pas assez de voies : signalé, pas inventé
        self.assertLessEqual(len(adresses), 4)

    # ------------------------------------------------------------------ R11
    def test_controles(self):
        s = self.s
        s.ajouter_module(0, 2, "ET", 16)
        s.ajouter_module(0, 4, "ST", 8)
        p = self.es()["ET_S2E0OD01_DEF"]
        s.definir_es(p.ident_eq, p.cle, module="0.4", voie=1)        # ET sur un module de sorties
        q = self.es()["ET_S2W3EX02_MA"]
        s.definir_es(q.ident_eq, q.cle, module="0.2", voie=20)       # voie hors module
        r = self.es()["ET_S2W3EX02_DEF"]
        s.definir_es(r.ident_eq, r.cle, module="0.7", voie=0)        # module non déclaré
        messages = [a.message for a in s.anomalies() if a.niveau == "Erreur"]
        self.assertTrue(any("nature ST" in m for m in messages))
        self.assertTrue(any("hors du module 0.2" in m for m in messages))
        self.assertTrue(any("module 0.7 non déclaré" in m for m in messages))

    def test_reserve_sous_seuil(self):
        s = self.s
        s.ajouter_module(0, 2, "ET", 6)                              # 5 ET sur 6 voies : réserve 17 %
        s.implanter_es()
        self.assertTrue(any("sous le seuil" in a.message for a in s.anomalies()))

    # ------------------------------------------------------------------ export et persistance
    def test_export_et_relecture(self):
        s = self.s
        s.ajouter_module(0, 2, "ET", 16, "BMX DDI 1602")
        s.implanter_es()
        xlsx = os.path.join(self.dossier, "cartes.xlsx")
        s.exporter_cartes_es(xlsx)
        with zipfile.ZipFile(xlsx) as z:
            noms = z.namelist()
            texte = "".join(z.read(n).decode("utf-8") for n in noms if n.startswith("xl/worksheets/"))
        self.assertIn("ET_S2W3EX02_DISPO", texte)
        self.assertIn("RESERVE", texte)
        self.assertIn("1 = Disponible", texte)
        self.assertIn("EXTRACTEUR D'AIR", texte)                     # organe en majuscules sans accents
        self.assertIn("DEFAUT GENERAL", texte)                       # désignation sans accents
        self.assertIn("%I0.2.0", texte)
        chemin = os.path.join(self.dossier, "o.ouvrage.json")
        s.enregistrer(chemin)
        s2 = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s2.ouvrir(chemin)
        self.assertEqual([(m.cle, m.nature, m.voies) for m in s2.ouvrage.modules], [("0.2", "ET", 16)])
        self.assertEqual({p.nom: p.adresse for p in s2.liste_es()}, {p.nom: p.adresse for p in s.liste_es()})

    def test_modifier_une_carte(self):
        s = self.s
        s.ajouter_module(0, 2, "ET", 16, "BMX DDI 1602")
        s.ajouter_module(0, 5, "ST", 16)
        s.implanter_es()
        avant = {p.nom: p.adresse for p in s.liste_es() if p.adresse}
        self.assertTrue(all(a.startswith("%I0.2.") for a in avant.values()))
        s.modifier_module("0.2", 0, 3, "ET", 32, "BMX DDI 3202K")         # déplacement : les E/S proposées suivent
        apres = {p.nom: p.adresse for p in s.liste_es() if p.adresse}
        self.assertEqual({n: a.replace("%I0.3.", "%I0.2.") for n, a in apres.items()}, avant)
        self.assertEqual([(m.cle, m.voies, m.reference) for m in s.ouvrage.modules][0], ("0.3", 32, "BMX DDI 3202K"))
        with self.assertRaises(RegleMetier):
            s.modifier_module("0.3", 0, 3, "ST", 32)                        # nature : E/S placées
        with self.assertRaises(RegleMetier):
            s.modifier_module("0.3", 0, 3, "ET", 2)                         # voies occupées au-delà
        with self.assertRaises(RegleMetier):
            s.modifier_module("0.3", 0, 5, "ET", 32)                        # position déjà prise
        p = next(x for x in s.liste_es() if x.adresse)
        s.definir_es(p.ident_eq, p.cle, validee=True)
        with self.assertRaises(RegleMetier):
            s.modifier_module("0.3", 0, 4, "ET", 32)                        # E/S validée : pas de déplacement silencieux
        s.modifier_module("0.3", 0, 3, "ET", 32, "BMX DDI 3202K (rev. B)")   # référence seule : permis

    def test_implantation_deterministe(self):
        pts = self.s.points()
        mods = [Module(0, 2, "ET", 16), Module(0, 3, "ST", 8)]
        a = [(p.nom, k, v) for p, k, v in implanter(pts, mods)[0]]
        b = [(p.nom, k, v) for p, k, v in implanter(self.s.points(), mods)[0]]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
