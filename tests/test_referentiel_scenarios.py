"""Scénarios du référentiel V1 : E/S physiques, règles fonctionnelles, propositions, adresses.

Neuf ouvrages fictifs représentatifs. Pour chacun : signaux attendus, propositions automatiques,
dépendances, types, adresses, commentaires, modifications / suppressions, sauvegarde et
réouverture, exports. Ces tests vérifient la cohérence de l'outil, PAS le fonctionnement réel
dans Control Expert ou TOPKAPI.
"""
import os
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.session import Session


class Base(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier
        s = self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s.definir("lieu", "F999"); s.definir("code_ouvrage", "RV"); s.definir("libelle", "Ouvrage fictif")
        s.ajouter_sous_ensemble("11", "Réservoir")

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    # outils
    def eq(self, type_, numero="01", options=(), exclus=(), uf=""):
        e = Equipement("11", type_, numero, options=list(options), exclus=list(exclus), uf=uf)
        self.s.ajouter_equipement(e)
        return self.s.ouvrage.equipements[-1]

    def noms(self, e):
        return {v.nom: v for v in self.s.variables() if v.ident_eq == e.ident}

    def points(self, e):
        return {p.nom: p for p in self.s.points() if p.ident_eq == e.ident}

    def props(self, e):
        return self.s.propositions(e)

    def sans_doublon(self):
        noms = [v.nom for v in self.s.variables()] + [p.nom for p in self.s.points()]
        self.assertEqual(len(noms), len(set(noms)), "noms en double")

    def adresser(self):
        props, err = self.s.plan()
        self.assertFalse(err, err)
        self.s.appliquer(props)
        return {v.nom: v.adresse for v in self.s.variables()}

    def reouvrir(self):
        chemin = os.path.join(self.dossier, "o.ouvrage.json")
        self.s.enregistrer(chemin)
        s2 = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s2.ouvrir(chemin)
        return s2


class TestVannes(Base):
    def test_1_vanne_un_seul_fin_de_course(self):
        mv = self.eq("MV", exclus=["ES_FDC_FER"])
        n = self.noms(mv)
        self.assertIn("TS_F999RV11MV01_OUV", n)
        self.assertNotIn("TS_F999RV11MV01_FER", n)              # sa source est retirée : pas de TS fermée
        self.assertEqual(n["TS_F999RV11MV01_OUV"].nom_es, "ET_F999RV11MV01_OUV")
        p = self.props(mv)
        self.assertNotIn("TS_DISC", p)                          # une seule fin de course : pas de discordance
        self.assertEqual(p["TS_OUV"].etat, "retenu")
        self.assertIn("MV-01", p["TS_OUV"].raison)
        self.assertIn("ET_F999RV11MV01_OUV", self.points(mv))
        self.assertNotIn("ET_F999RV11MV01_FER", self.points(mv))
        self.sans_doublon()

    def test_2_vanne_deux_fins_de_course(self):
        mv = self.eq("MV")
        p = self.props(mv)
        for cle in ("TS_OUV", "TS_FER"):
            self.assertEqual(p[cle].etat, "retenu")
        for cle in ("TS_DISC", "TS_INT"):
            self.assertEqual(p[cle].etat, "proposé")            # exige une logique : à accepter
            self.assertIn("analyse fonctionnelle", p[cle].logique)          # D5 : aucun algorithme imposé
            self.assertNotIn("t_disc", p[cle].logique.lower())
        self.assertIn("à retenir ou écarter", p["TS_DISC"].logique)          # D5 : choix de l'utilisateur
        n = self.noms(mv)
        self.assertNotIn("TS_F999RV11MV01_DISC", n)             # proposé ≠ généré
        Session.accepter_proposition(mv, "TS_DISC")
        n = self.noms(mv)
        self.assertIn("TS_F999RV11MV01_DISC", n)
        self.assertTrue(n["TS_F999RV11MV01_DISC"].logique)       # signalé « logique automate à programmer »
        self.assertEqual(n["TS_F999RV11MV01_DISC"].es, "Interne")
        Session.refuser_proposition(mv, "TS_INT")
        self.assertEqual(self.props(mv)["TS_INT"].etat, "refusé")
        self.sans_doublon()

    def test_3_vanne_commandes_et_temps_de_manoeuvre(self):
        mv = self.eq("MV", options=["Télécommandée"])
        p = self.props(mv)
        self.assertEqual(p["TC_OUV"].etat, "retenu")
        for cle in ("TS_MNV", "TS_DEFTPS", "TS_DEFMNV", "TM_TPS"):
            self.assertEqual(p[cle].etat, "proposé")
            self.assertIn("MV-06", p[cle].raison)
        self.assertIn("analyse fonctionnelle", p["TS_DEFTPS"].logique)       # D5 : texte d'origine archivé
        n = self.noms(mv)
        self.assertEqual(n["TC_F999RV11MV01_OUV"].nom_es, "ST_F999RV11MV01_OUV")
        # sortie seule (sans retour de position) : pas de surveillance du temps de manœuvre
        mv2 = self.eq("MV", "02", options=["Télécommandée"], exclus=["ES_FDC_OUV", "ES_FDC_FER"])
        p2 = self.props(mv2)
        self.assertNotIn("TS_DEFTPS", p2)
        self.assertEqual(p2["TC_OUV"].etat, "retenu")
        self.sans_doublon()


class TestPompes(Base):
    def test_4_pompe_demarrage_direct(self):
        pm = self.eq("PM")
        n = self.noms(pm)
        for nom in ("TS_F999RV11PM01_MA", "TS_F999RV11PM01_DEFTH", "CP_F999RV11PM01_HF", "CP_F999RV11PM01_NDEM"):
            self.assertIn(nom, n)
        self.assertNotIn("TM_F999RV11PM01_FREQ", n)
        self.assertEqual(n["CP_F999RV11PM01_HF"].type_logique, "DINT")
        self.assertIn("retour de marche", n["CP_F999RV11PM01_HF"].logique)
        self.assertEqual(self.points(pm)["ET_F999RV11PM01_MA"].variable, "TS_F999RV11PM01_MA")
        self.sans_doublon()

    def test_5_pompe_sur_variateur(self):
        pm = self.eq("PM", options=["Variateur", "Télécommandée"])
        n = self.noms(pm)
        for nom in ("TM_F999RV11PM01_FREQ", "TR_F999RV11PM01_FREQ", "RTR_F999RV11PM01_FREQ", "TS_F999RV11PM01_DEFVAR",
                    "TC_F999RV11PM01_MA"):
            self.assertIn(nom, n)
        self.assertEqual(n["TR_F999RV11PM01_FREQ"].nom_es, "SA_F999RV11PM01_FREQ")
        self.assertEqual(n["TM_F999RV11PM01_FREQ"].type_logique, "REAL")
        p = self.props(pm)
        self.assertEqual(p["RTR_FREQ"].etat, "retenu")
        self.assertIn("GEN-01", p["RTR_FREQ"].raison)
        self.assertEqual(p["TS_DEFDEM"].etat, "proposé")           # commande + retour → défaut démarrage proposé
        a = self.adresser()
        tr, rtr = a["TR_F999RV11PM01_FREQ"], a["RTR_F999RV11PM01_FREQ"]
        self.assertEqual(int(tr[3:]) % 2, 0)                       # REAL : adresse paire
        self.assertEqual(int(rtr[3:]) - 4000, int(tr[3:]) - 100)   # miroir TR / RTR
        self.sans_doublon()


class TestMesures(Base):
    def test_6_cuve_mesure_et_seuils(self):
        cu = self.eq("CU", options=["Mesure de niveau", "Contacts de niveau"])
        p = self.props(cu)
        self.assertEqual(p["TM_NIV"].etat, "retenu")
        self.assertEqual(p["TS_DEFMES"].etat, "retenu")
        self.assertEqual(p["TS_H"].etat, "retenu")                 # contact physique présent → TS directe
        self.assertEqual(p["TM_VOL"].etat, "proposé")              # volume : géométrie nécessaire
        self.assertIn("analyse fonctionnelle", p["TM_VOL"].logique)          # D5 : texte d'origine archivé
        self.assertEqual(p["TS_DISCMES"].etat, "proposé")
        self.assertEqual(p["TS_INCOH"].etat, "proposé")
        n = self.noms(cu)
        self.assertEqual(n["TS_F999RV11CU01_H"].nom_es, "ET_F999RV11CU01_PH")
        self.assertEqual(n["TM_F999RV11CU01_NIV"].nom_es, "EA_F999RV11CU01_NIV")
        # cuve avec mesure seule : seuils calculés proposés, pas de contact
        cu2 = self.eq("CU", "02", options=["Mesure de niveau"])
        p2 = self.props(cu2)
        self.assertEqual(p2["TS_H"].etat, "proposé")
        self.assertIn("analyse fonctionnelle", p2["TS_H"].logique)           # D5 : texte d'origine archivé
        Session.accepter_proposition(cu2, "TS_H")
        v = self.noms(cu2)["TS_F999RV11CU02_H"]
        self.assertEqual(v.es, "Interne")                          # pas de contact : information calculée
        self.sans_doublon()

    def test_7_debitmetre_totalisation(self):
        ft = self.eq("FT", options=["Sortie impulsions câblée"])
        p = self.props(ft)
        self.assertEqual(p["CP_VOL"].etat, "retenu")
        self.assertEqual({r["id"] for r in p["CP_VOL"].regles}, {"FT-03", "FT-04"})
        n = self.noms(ft)
        self.assertEqual(n["CP_F999RV11FT01_VOL"].nom_es, "ET_F999RV11FT01_IMP")
        self.assertEqual(n["TM_F999RV11FT01_DEB"].nom_es, "EA_F999RV11FT01_DEB")
        ft2 = self.eq("FT", "02")                                  # sans impulsions : intégration seulement proposée
        self.assertEqual(self.props(ft2)["CP_VOL"].etat, "proposé")
        self.sans_doublon()


class TestStructureEtFiabilite(Base):
    def test_8_ouvrage_une_seule_uf(self):
        self.s.ajouter_uf("UF01", "Station")
        for t in ("CU", "LT", "MV"):
            self.eq(t, uf="UF01")
        self.assertEqual({e.uf for e in self.s.ouvrage.equipements}, {"UF01"})
        self.assertEqual(len(self.s.ouvrage.unites), 1)
        self.sans_doublon()

    def test_9_ouvrage_plusieurs_uf_et_commun(self):
        self.s.ajouter_uf("UF01", "Stockage"); self.s.ajouter_uf("UF02", "Distribution")
        self.eq("CU", options=["Mesure de niveau"], uf="UF01")
        self.eq("LT", uf="UF01"); self.eq("MV", uf="UF01")
        self.eq("PM", "01", uf="UF02"); self.eq("PM", "02", uf="UF02")
        self.eq("FT", uf="UF02", options=["Sortie impulsions câblée"]); self.eq("PT", uf="UF02")
        self.eq("AR")                                              # commun à l'ouvrage : sans UF
        self.assertEqual(sum(1 for e in self.s.ouvrage.equipements if not e.uf), 1)
        for e in self.s.ouvrage.equipements:
            self.s.decider_propositions(e.ident, "retenir")
        noms_avant = [v.nom for v in self.s.variables()]
        self.adresser()
        self.sans_doublon()
        b = self.s.bilan()
        self.assertEqual(b["erreurs"], 0, [x.message for x in self.s.anomalies() if x.niveau == "Erreur"])
        # sauvegarde / réouverture : mêmes variables, adresses, UF, règles
        s2 = self.reouvrir()
        self.assertEqual([(v.nom, v.adresse, v.uf, v.logique) for v in s2.variables()],
                         [(v.nom, v.adresse, v.uf, v.logique) for v in self.s.variables()])
        self.assertEqual(noms_avant, [v.nom for v in s2.variables()])
        # exports
        xsy = os.path.join(self.dossier, "o.xsy")
        s2.exporter_xsy(xsy)
        ET.parse(xsy)
        xlsx = os.path.join(self.dossier, "o.xlsx")
        s2.exporter_excel(xlsx)
        with zipfile.ZipFile(xlsx) as z:
            self.assertIn("Logique automate", z.read("xl/worksheets/sheet1.xml").decode("utf-8"))

    def test_modifications_sans_doublon_ni_glissement_d_adresses(self):
        mv = self.eq("MV", options=["Télécommandée"])
        pm = self.eq("PM")
        a1 = self.adresser()
        # retirer puis remettre une fin de course : la TS revient à la même adresse
        Session.basculer_signal(mv, next(s for s in self.s.catalogue.signaux_du_type("MV") if s["code"] == "FDC_FER"))
        self.assertNotIn("TS_F999RV11MV01_FER", self.noms(mv))
        self.assertIn("TS_FER", self.s.adresses_orphelines(mv))
        self.adresser()                                            # un ajout ailleurs ne prend pas la place réservée
        self.eq("PM", "02")
        a2 = self.adresser()
        self.assertNotIn(a1["TS_F999RV11MV01_FER"], {v for k, v in a2.items()})
        Session.basculer_signal(mv, next(s for s in self.s.catalogue.signaux_du_type("MV") if s["code"] == "FDC_FER"))
        a3 = {v.nom: v.adresse for v in self.s.variables()}
        self.assertEqual(a3["TS_F999RV11MV01_FER"], a1["TS_F999RV11MV01_FER"])
        for nom, adr in a1.items():                                # aucune adresse déjà attribuée n'a bougé
            self.assertEqual(a3.get(nom), adr)
        # accepter une proposition puis retirer sa condition : alerte, pas de variable orpheline
        Session.accepter_proposition(mv, "TS_DISC")
        self.assertIn("TS_F999RV11MV01_DISC", self.noms(mv))
        Session.basculer_signal(mv, next(s for s in self.s.catalogue.signaux_du_type("MV") if s["code"] == "FDC_OUV"))
        self.assertNotIn("TS_F999RV11MV01_DISC", self.noms(mv))
        self.assertTrue(any("n'est plus satisfaite" in x.message for x in self.s.anomalies()))
        # commentaire saisi conservé au fil des modifications
        self.s.definir_textes(pm.ident, "TS_MA", commentaire="Pompe 1 en marche (contacteur KM1)")
        self.eq("LT")
        self.assertEqual(self.noms(pm)["TS_F999RV11PM01_MA"].commentaire, "Pompe 1 en marche (contacteur KM1)")
        self.sans_doublon()

    def test_referentiel_coherent(self):
        self.assertEqual(self.s.catalogue.anomalies(), [])
        types = {t["code"] for t in self.s.catalogue.types}
        for code in ("CU", "MV", "PM", "FT", "LT", "PT", "AT", "TT", "AR", "AU", "LI", "SP", "CL", "RP", "KM"):
            self.assertIn(code, types)
        self.assertTrue(all(len(c) == 2 for c in types))           # le repère suppose un type sur 2 lettres
        self.assertGreater(len(self.s.catalogue.signaux_du_type("CU")), 10)

    def test_catalogue_modifie_ne_change_pas_un_ouvrage_enregistre(self):
        self.eq("MV")
        chemin = os.path.join(self.dossier, "o.ouvrage.json")
        self.s.enregistrer(chemin)
        avant = [v.nom for v in self.s.variables()]
        cat = Catalogue.charger(chemins.fichier_catalogue_origine())
        cat.regles = [r for r in cat.regles if r["id"] != "MV-01"]   # le catalogue partagé évolue
        s2 = Session(cat)
        s2.ouvrir(chemin)                                          # l'ouvrage garde SA copie du référentiel
        self.assertEqual([v.nom for v in s2.variables()], avant)

    def test_echange_excel_du_referentiel(self):
        from genvar import catalogue_excel
        chemin = os.path.join(self.dossier, "cat.xlsx")
        catalogue_excel.exporter(self.s.catalogue, chemin)
        c2, _ = catalogue_excel.importer(chemin)
        self.assertEqual(len(c2.regles), len(self.s.catalogue.regles))
        mv = next(s for s in c2.signaux if s["type"] == "MV" and s["famille"] == "TS" and s["code"] == "OUV")
        self.assertEqual(mv["source"], "ES_FDC_OUV")


if __name__ == "__main__":
    unittest.main()
