"""Tests du cœur de l'outil (lancer : python -m unittest discover tests)."""
import os, sys, tempfile, unittest, zipfile
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from genvar.catalogue import Catalogue
from genvar import chemins
from genvar.modele import Ouvrage, Equipement, SousEnsemble, SignalPropre, generer, generer_points, attribuer_adresses, controler, plan_adresses
from genvar import existant, catalogue_excel
from genvar.export_xsy import contenu_xsy
from genvar.export_xlsx import exporter_table


def ouvrage_essai():
    o = Ouvrage(lieu="XT25", code_ouvrage="RV", libelle="Réservoir fictif", nom_projet="XT25RV")
    o.sous_ensembles = [SousEnsemble("00", "Commun"), SousEnsemble("11", "Réservoir 1 cuve 1"), SousEnsemble("Y1", "Automatisme")]
    o.equipements = [
        Equipement("11", "MV", "03", "Vanne de remplissage", options=["Télécommandée"]),
        Equipement("11", "PM", "01", "Pompe de reprise", options=["Variateur"]),
        Equipement("11", "LT", "01", "Niveau cuve 1"),
        Equipement("00", "UF", "12", "UF réservoir", options=["Réarmement par UF"]),
        Equipement("Y1", "AP", "12", "Automate du réservoir"),
    ]
    return o


class TestCoeur(unittest.TestCase):
    def setUp(self):
        self.cat = Catalogue.charger(chemins.fichier_catalogue_origine())
        self.o = ouvrage_essai()

    def test_catalogue_sans_anomalie(self):
        self.assertEqual(self.cat.anomalies(), [])

    def test_noms(self):
        v = generer(self.o, self.cat)
        noms = [x.nom for x in v]
        self.assertIn("TS_XT25RV11MV03_FER", noms)
        self.assertIn("TC_XT25RV11MV03_OUV", noms)
        self.assertIn("TR_XT25RV11PM01_FREQ", noms)
        self.assertNotIn("TC_XT25RV11PM01_MA", noms)          # pompe non télécommandée
        self.assertEqual(len(noms), len(set(noms)))
        x = next(x for x in v if x.nom == "TS_XT25RV11MV03_FER")
        self.assertEqual(x.commentaire, "Vanne motorisée MV03 – TS Fermée")
        self.assertEqual(x.libelle_topkapi, "11MV03 — Fermée")
        self.assertEqual(x.nom_es, "ET_XT25RV11MV03_FER")
        self.assertEqual(x.type_es, "EBOOL")
        pts = {p.nom: p for p in generer_points(self.o, self.cat)}
        self.assertIn("ET_XT25RV11PM01_MA", pts)              # organe MA : pas de répétition
        self.assertIn("ET_XT25RV11PM01_DEFTH", pts)
        self.assertIn("ST_XT25RV11MV03_OUV", pts)             # sortie : pas de code d'organe
        self.assertIn("EA_XT25RV11LT01_NIV", pts)
        self.assertEqual(pts["ET_XT25RV11MV03_FER"].commentaire, "Vanne motorisée MV03 – ET Fin de course fermée")
        # sens fonctionnel : la mesure remonte par une EA, la consigne descend par une SA
        self.assertEqual(pts["EA_XT25RV11PM01_FREQ"].variable, "TM_XT25RV11PM01_FREQ")
        self.assertEqual(pts["SA_XT25RV11PM01_FREQ"].variable, "TR_XT25RV11PM01_FREQ")   # E/S distincte de la TR (référentiel V1)

    def test_sens_fonctionnel(self):
        from genvar.catalogue import sens_incoherent
        self.assertTrue(sens_incoherent("TM", "SA"))
        self.assertTrue(sens_incoherent("TC", "ET"))
        self.assertFalse(sens_incoherent("TR", "SA"))
        self.o.equipements[0].ajouts.append(SignalPropre("Essai", "TM", "ESSAI", "REAL", es="SA"))
        attribuer_adresses(self.o, self.cat)
        self.assertTrue(any("ne peut pas être porté" in a.message for a in controler(self.o, self.cat)))

    def test_boutons_locaux(self):
        self.o.equipements[0].options.append("Boutons locaux")
        pts = {p.nom: p for p in generer_points(self.o, self.cat)}
        self.assertIn("ET_XT25RV11MV03_BP_FER", pts)
        self.assertEqual(pts["ET_XT25RV11MV03_BP_FER"].variable, "")
        noms = [v.nom for v in generer(self.o, self.cat)]
        self.assertFalse(any("BP" in n for n in noms))          # pas de variable d'échange

    def test_exclusion_et_ajout(self):
        eq = self.o.equipements[0]
        eq.exclus.append("TS_MNV")
        eq.ajouts.append(SignalPropre("Fin de course intermédiaire", "TS", "FDCI", es="ET"))
        noms = [x.nom for x in generer(self.o, self.cat)]
        self.assertNotIn("TS_XT25RV11MV03_MNV", noms)
        self.assertIn("TS_XT25RV11MV03_FDCI", noms)

    def test_adresses_stables(self):
        n = attribuer_adresses(self.o, self.cat)
        v1 = {x.nom: x.adresse for x in generer(self.o, self.cat)}
        self.assertEqual(n, len(v1))
        self.assertEqual(v1["TS_XT25RV11MV03_OUV"], "%MW1000.0")
        reals = [a for nom, a in v1.items() if nom.startswith(("TM_", "TR_", "RTR_")) and "FREQ" in nom]
        for a in reals:
            self.assertEqual(int(a[3:]) % 2, 0)
        # ajout d'un équipement : les adresses existantes ne bougent pas
        self.o.equipements.append(Equipement("11", "PT", "02", "Pression refoulement"))
        attribuer_adresses(self.o, self.cat)
        v2 = {x.nom: x.adresse for x in generer(self.o, self.cat)}
        for nom, a in v1.items():
            self.assertEqual(v2[nom], a)
        self.assertEqual(len(set(v2.values())), len(v2))

    def test_controles(self):
        attribuer_adresses(self.o, self.cat)
        erreurs = [a for a in controler(self.o, self.cat) if a.niveau == "Erreur"]
        self.assertTrue(erreurs and all("non décidée" in a.message for a in erreurs))   # rien d'oublié en silence
        from genvar.modele import propositions_regles
        for eq in self.o.equipements:
            for cle, p in propositions_regles(self.cat, eq).items():
                if p.etat == "proposé":
                    eq.exclus.append(cle); eq.motifs[cle] = "non prévu au cahier des charges"
        erreurs = [a for a in controler(self.o, self.cat) if a.niveau == "Erreur"]
        self.assertEqual(erreurs, [])
        self.o.equipements.append(Equipement("11", "MV", "03", "Doublon"))
        attribuer_adresses(self.o, self.cat)
        msgs = [a.message for a in controler(self.o, self.cat) if a.niveau == "Erreur"]
        self.assertTrue(any("Repère utilisé" in m for m in msgs))
        self.assertTrue(any("nom en double" in m for m in msgs))

    def test_nom_trop_long(self):
        self.o.equipements.append(Equipement("11", "TR", "01", options=[]))
        self.o.equipements[-1].ajouts.append(SignalPropre("Essai", "TS", "CODEBEAUCOUPTROPLONG"))
        attribuer_adresses(self.o, self.cat)
        msgs = [a.message for a in controler(self.o, self.cat)]
        self.assertTrue(any("32 au plus" in m for m in msgs))

    def test_xsy(self):
        attribuer_adresses(self.o, self.cat)
        eq = self.o.equipements[0]; eq.adresses_es["TS_FER"] = "%I0.3.5"
        v = generer(self.o, self.cat)
        texte, nb = contenu_xsy(self.o, v, generer_points(self.o, self.cat))
        racine = ET.fromstring(texte.encode("utf-8"))
        self.assertEqual(racine.tag, "VariablesExchangeFile")
        self.assertEqual(racine.find("fileHeader").get("DTDVersion"), "41")
        vars_ = racine.find("dataBlock").findall("variables")
        self.assertEqual(len(vars_), nb)
        es = [x for x in vars_ if x.get("name") == "ET_XT25RV11MV03_FER"][0]
        self.assertEqual(es.get("typeName"), "EBOOL")
        self.assertEqual(es.get("topologicalAddress"), "%I0.3.5")
        self.assertEqual(es.find("comment").text, "Vanne motorisée MV03 – ET Fin de course fermée")

    def test_fichier_ouvrage(self):
        attribuer_adresses(self.o, self.cat)
        self.o.equipements[0].ajouts.append(SignalPropre("Essai", "TS", "ESSAI"))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "o.ouvrage.json")
            self.o.enregistrer(p)
            o2 = Ouvrage.ouvrir(p)
        self.assertEqual([x.nom for x in generer(o2, self.cat)], [x.nom for x in generer(self.o, self.cat)])
        self.assertEqual([x.adresse for x in generer(o2, self.cat)], [x.adresse for x in generer(self.o, self.cat)])

    def test_xlsx(self):
        attribuer_adresses(self.o, self.cat)
        v = generer(self.o, self.cat)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.xlsx")
            exporter_table(p, self.o, self.cat, v, controler(self.o, self.cat, v))
            with zipfile.ZipFile(p) as z:
                for n in z.namelist():
                    if n.endswith(".xml") or n.endswith(".rels"):
                        ET.fromstring(z.read(n))
            self.assertTrue(os.path.getsize(p) > 1000)


class TestPlanMemoire(unittest.TestCase):
    def setUp(self):
        self.cat = Catalogue.charger(chemins.fichier_catalogue_origine())
        self.o = Ouvrage(lieu="XT25", code_ouvrage="RV")
        self.o.sous_ensembles = [SousEnsemble("11", "Réservoir 1")]
        self.o.equipements = [Equipement("11", "PM", "01", options=["Variateur"]),
                              Equipement("11", "LT", "01", options=["Seuils réglables"])]

    def adresses(self):
        return {v.nom: v.adresse for v in generer(self.o, self.cat)}

    def test_tr_rtr_en_miroir(self):
        attribuer_adresses(self.o, self.cat)
        a = self.adresses()
        self.assertEqual(a["TR_XT25RV11PM01_FREQ"], "%MW100")           # REAL : 2 mots
        self.assertEqual(a["RTR_XT25RV11PM01_FREQ"], "%MW4000")
        self.assertEqual(a["TR_XT25RV11LT01_SH"], "%MW102")
        self.assertEqual(a["RTR_XT25RV11LT01_SH"], "%MW4002")
        self.assertEqual(a["TS_XT25RV11PM01_MA"], "%MW1000.0")
        self.assertFalse([x for x in controler(self.o, self.cat) if x.niveau == "Erreur"])

    def test_ajout_sans_decalage_et_trou_reutilise(self):
        attribuer_adresses(self.o, self.cat)
        avant = self.adresses()
        self.o.equipements.insert(0, Equipement("11", "PM", "02", options=["Variateur"]))   # inséré en tête de liste
        attribuer_adresses(self.o, self.cat)
        apres = self.adresses()
        for nom, adr in avant.items():
            self.assertEqual(apres[nom], adr)
        self.assertEqual(apres["TR_XT25RV11PM02_FREQ"], "%MW106")
        self.assertEqual(apres["RTR_XT25RV11PM02_FREQ"], "%MW4006")
        # suppression de la première pompe : sa place est reprise par le prochain équipement
        self.o.equipements = [e for e in self.o.equipements if not (e.type == "PM" and e.numero == "01")]
        self.o.equipements.append(Equipement("11", "PM", "03", options=["Variateur"]))
        attribuer_adresses(self.o, self.cat)
        a = self.adresses()
        self.assertEqual(a["TR_XT25RV11PM03_FREQ"], "%MW100")
        self.assertEqual(a["RTR_XT25RV11PM03_FREQ"], "%MW4000")

    def test_plage_pleine_sans_hors_zone(self):
        self.o.zones_fin["TR"] = 101                       # place pour un seul REAL
        props, erreurs = plan_adresses(self.o, self.cat)
        self.assertTrue(any("Plage TR pleine" in e for e in erreurs))
        self.assertTrue(all(int(p.adresse[3:].split(".")[0]) <= 101 for p in props if p.variable.famille == "TR"))

    def test_simulation_sans_modification(self):
        props, _ = plan_adresses(self.o, self.cat)
        self.assertTrue(props)
        self.assertTrue(all(not v.adresse for v in generer(self.o, self.cat)))

    def test_chevauchement_bit_et_mot(self):
        attribuer_adresses(self.o, self.cat)
        eq = self.o.equipements[0]
        eq.adresses["TM_FREQ"] = "%MW1000"                 # mots déjà utilisés par des bits de TS
        msgs = [x.message for x in controler(self.o, self.cat) if x.niveau == "Erreur"]
        self.assertTrue(any("chevauche" in m for m in msgs))

    def test_modbus_et_ancien_fichier(self):
        from genvar.modele import registre_modbus
        self.assertEqual(registre_modbus("%MW1000.3", 0), "1000.3")
        self.assertEqual(registre_modbus("%MW100", 1), "101")
        o = Ouvrage.depuis_dict({"lieu": "XT25", "code_ouvrage": "RV",
                                 "zones": {"TS": 1000, "TC": 1200, "TM": 1400, "TR": 1700, "RTR": 1900, "CP": 2100}})
        self.assertEqual(o.zones_fin["TS"], 1199)
        self.assertEqual(o.zones_fin["CP"], 3099)


XSY_ANCIEN = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<VariablesExchangeFile>
 <fileHeader company="Schneider Automation" product="Unity Pro XL V13.1" dateTime="date_and_time#2026-1-1-0:0:0" content="Variable source file" DTDVersion="41"></fileHeader>
 <contentHeader name="XT25RV" version="0.0.000"></contentHeader>
 <dataBlock>
  <variables name="TS_RV11MV03_OUV" typeName="BOOL" topologicalAddress="%MW25.1"><comment>TS OUVERTE</comment></variables>
  <variables name="TS_RV11MV03_FERME" typeName="BOOL" topologicalAddress="%MW25.2"><comment>TS FERMEE</comment></variables>
  <variables name="TS_RV11MV03_INDISPO" typeName="BOOL" topologicalAddress="%MW25.0"><comment>TS INDISPONIBLE</comment></variables>
  <variables name="DEF_RV11MV03_TTLE_FERM" typeName="BOOL" topologicalAddress="%MW25.6"><comment>DEF TEMPS DE MANOEUVRE DEPASSE</comment></variables>
  <variables name="TC_RV11MV03_OUVERTURE" typeName="BOOL" topologicalAddress="%MW59.0"><comment>TC OUVERTURE</comment></variables>
  <variables name="TM_RV11LT01_NIV" typeName="REAL" topologicalAddress="%MW146"><comment>NIVEAU CUVE 1</comment></variables>
  <variables name="DEF_RV11XX99_" typeName="BOOL" topologicalAddress="%MW30.0"><comment>?</comment></variables>
  <variables name="ET_RV11MV03_FER" typeName="EBOOL" topologicalAddress="%I0.3.5"><comment>FDC</comment></variables>
  <variables name="Tempo_remplissage" typeName="TIME"><comment>interne</comment></variables>
 </dataBlock>
</VariablesExchangeFile>
"""


class TestExistant(unittest.TestCase):
    def setUp(self):
        self.cat = Catalogue.charger(chemins.fichier_catalogue_origine())
        self.o = Ouvrage(mode="Existant", lieu="XT25", code_ouvrage="RV")
        self.d = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.d.name, "ancien.xsy")
        with open(self.p, "w", encoding="utf-8") as f:
            f.write(XSY_ANCIEN)

    def tearDown(self):
        self.d.cleanup()

    def test_import_et_identification(self):
        lues, nouv = existant.importer(self.o, self.p)
        self.assertEqual((lues, nouv), (9, 9))
        existant.identifier(self.o, self.cat)
        v = {x.nom: x for x in self.o.existantes}
        self.assertEqual((v["TS_RV11MV03_OUV"].cle, v["TS_RV11MV03_OUV"].identification), ("TS_OUV", "Exacte"))
        self.assertEqual((v["TS_RV11MV03_FERME"].cle, v["TS_RV11MV03_FERME"].identification), ("TS_FER", "Probable"))
        self.assertEqual(v["TS_RV11MV03_INDISPO"].cle, "TS_DISPO")
        self.assertIn("Polarité", v["TS_RV11MV03_INDISPO"].remarque)
        self.assertEqual((v["DEF_RV11MV03_TTLE_FERM"].cle, v["DEF_RV11MV03_TTLE_FERM"].identification), ("TS_DEFTPS", "Probable"))
        self.assertEqual(v["TC_RV11MV03_OUVERTURE"].cle, "TC_OUV")
        self.assertEqual((v["TM_RV11LT01_NIV"].cle, v["TM_RV11LT01_NIV"].identification), ("TM_NIV", "Exacte"))
        self.assertEqual(v["DEF_RV11XX99_"].identification, "À identifier")
        self.assertFalse(v["ET_RV11MV03_FER"].retenue)
        self.assertFalse(v["Tempo_remplissage"].retenue)
        self.assertEqual(sorted(self.o.repere(e) for e in self.o.equipements), ["XT25RV11LT01", "XT25RV11MV03"])
        # les noms ne changent pas
        self.assertEqual([x.nom for x in self.o.existantes][0], "TS_RV11MV03_OUV")
        manque = [m[2] for m in existant.oublis(self.o, self.cat) if m[0] == "XT25RV11MV03"]
        self.assertIn("TS_HS", manque)        # TS_MNV n'est plus attendue d'office : proposée par règle (V1)
        self.assertNotIn("TS_OUV", manque)

    def test_manuel_conserve(self):
        existant.importer(self.o, self.p)
        existant.identifier(self.o, self.cat)
        v = next(x for x in self.o.existantes if x.nom == "DEF_RV11XX99_")
        v.identification, v.retenue = "Confirmée", False
        existant.importer(self.o, self.p)          # réimport : rien n'est perdu
        existant.identifier(self.o, self.cat)
        v = next(x for x in self.o.existantes if x.nom == "DEF_RV11XX99_")
        self.assertEqual(v.identification, "Confirmée")
        self.assertEqual(len(self.o.existantes), 9)

    def test_noms_et_adresses_intacts(self):
        lues = existant.lire_xsy(self.p)
        existant.importer(self.o, self.p)
        existant.identifier(self.o, self.cat)
        existant.confirmer(self.o.existantes)
        existant.identifier(self.o, self.cat, tout_refaire=True)
        self.assertEqual([(x.nom, x.type_logique, x.adresse, x.commentaire) for x in self.o.existantes], lues)

    def test_controle_adresses(self):
        texte = XSY_ANCIEN.replace('<variables name="Tempo_remplissage" typeName="TIME">',
            '<variables name="TM_RV11LT01_VOL" typeName="REAL" topologicalAddress="%MW147"><comment>volume</comment></variables>'
            '<variables name="TC_RV11MV03_FER" typeName="BOOL" topologicalAddress="%MW59"><comment>TC</comment></variables>'
            '<variables name="Tempo_remplissage" typeName="TIME">')
        with open(self.p, "w", encoding="utf-8") as f:
            f.write(texte)
        existant.importer(self.o, self.p)
        existant.identifier(self.o, self.cat)
        msgs = [(a.niveau, a.repere, a.message) for a in existant.controler_existant(self.o, self.cat)]
        self.assertTrue(any(n == "Erreur" and r == "TM_RV11LT01_VOL" and "impaire" in m for n, r, m in msgs))
        self.assertTrue(any(n == "Erreur" and "Chevauchement" in m and "%MW147" in m for n, r, m in msgs))   # REAL 146-147
        self.assertTrue(any(n == "Erreur" and "%MW59" in m for n, r, m in msgs))                            # bit du mot 59
        self.assertEqual(next(x for x in self.o.existantes if x.nom == "TM_RV11LT01_VOL").adresse, "%MW147")

    def test_ecarts_et_non_applicable(self):
        existant.importer(self.o, self.p)
        existant.identifier(self.o, self.cat)
        eq = next(e for e in self.o.equipements if e.type == "MV")
        avant = [e[3] for e in existant.ecarts(self.o, self.cat) if e[5] == eq.ident]
        self.assertIn("TS_HS", avant)
        self.assertNotIn("TC_AUTO", avant)                    # option : jamais un écart
        existant.non_applicable(self.o, eq.ident, "TS_HS")
        apres = [e[3] for e in existant.ecarts(self.o, self.cat) if e[5] == eq.ident]
        self.assertNotIn("TS_HS", apres)

    def test_doublon_en_erreur(self):
        existant.importer(self.o, self.p)
        existant.identifier(self.o, self.cat)
        v = next(x for x in self.o.existantes if x.nom == "DEF_RV11XX99_")
        eq = next(e for e in self.o.equipements if e.type == "MV")
        v.ident_eq, v.cle, v.identification = eq.ident, "TS_OUV", "Confirmée"
        self.assertTrue(any(a.niveau == "Erreur" and "Doublon" in a.message for a in existant.controler_existant(self.o, self.cat)))

    def test_export_et_fichier(self):
        existant.importer(self.o, self.p)
        existant.identifier(self.o, self.cat)
        x = os.path.join(self.d.name, "c.xlsx")
        existant.exporter_correspondance(x, self.o, self.cat)
        self.assertTrue(os.path.getsize(x) > 1000)
        f = os.path.join(self.d.name, "o.ouvrage.json")
        self.o.enregistrer(f)
        o2 = Ouvrage.ouvrir(f)
        self.assertEqual([(a.nom, a.cle) for a in o2.existantes], [(a.nom, a.cle) for a in self.o.existantes])


class TestCatalogueExcel(unittest.TestCase):
    def test_aller_retour(self):
        cat = Catalogue.charger(chemins.fichier_catalogue_origine())
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "c.xlsx")
            catalogue_excel.exporter(cat, p)
            c2, msg = catalogue_excel.importer(p)
        self.assertEqual(c2.signaux, cat.signaux)
        self.assertEqual(c2.types, cat.types)


if __name__ == "__main__":
    unittest.main()
