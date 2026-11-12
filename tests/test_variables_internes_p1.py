"""Décision P1 : variables internes déclarées (familles BI, EI, MI, RI).

Variables automate non localisées, documentées, retenues seulement sur sélection de l'utilisateur
(option de l'équipement ou signal propre), exportées en XSY sans adresse ; jamais télétransmises, jamais dans
la table d'échange, aucun %MW, aucune logique ni calcul imposés. Le type logique est celui déclaré pour le
signal, jamais déduit de la famille. Les signaux sont fictifs : le référentiel livré n'en contient aucun.
"""
import copy
import os
import tempfile
import unittest
import zipfile

from genvar import chemins, teletransmission
from genvar.catalogue import FAMILLES_INTERNES, Catalogue
from genvar.formats_control_expert import lire_xsy
from genvar.homonymes import noms_ouvrage
from genvar.modele import Equipement, SignalPropre, controler, generer_internes, generer_points
from genvar.modeles import verifier_signaux_modele
from genvar.regles import evaluer
from genvar.session import RegleMetier, Session

OPTION = "Variables internes (essai)"


def _interne(famille, code, type_logique, information, **extra):
    s = {"type": "MV", "information": information, "famille": famille, "code": code,
         "type_logique": type_logique, "unite": "", "es": "Interne", "alarme": False, "presence": "Option",
         "option": OPTION, "statut": "À valider", "remarque": "", "organe": "", "source": "", "logique": ""}
    s.update(extra)
    return s


class Base(unittest.TestCase):
    def setUp(self):
        self.origine = Catalogue.charger(chemins.fichier_catalogue_origine())
        self.cat = copy.deepcopy(self.origine)
        self.cat.signaux += [_interne("BI", "MEM", "BOOL", "Mémoire fictive d'essai"),
                             _interne("RI", "TPS", "REAL", "Durée de manœuvre mesurée")]
        self.cat.type("MV")["options"] = list(self.cat.type("MV")["options"]) + [OPTION]

    def session(self, options=("Télécommandée",), exclus=()):
        s = Session(self.cat)
        s.nouveau(False)
        s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
        s.ajouter_sous_ensemble("00")
        eq = s.ajouter_equipement(Equipement("00", "MV", "01"))
        eq.options = list(options)
        eq.exclus = list(exclus)
        s.decider_propositions(eq.ident, "retenir")
        return s


class TestSelection(Base):
    def test_referentiel_livre_candidats_bi_de_mv_seulement(self):
        # décision de l'utilisateur du 11/11 : candidats BI de MV ajoutés, DIS = disponible, DSC = discordance
        internes = [s for s in self.origine.signaux if s["famille"] in FAMILLES_INTERNES]
        self.assertEqual([(s["type"], s["famille"], s["code"]) for s in internes],
                         [("MV", "BI", c) for c in ("OUV", "FER", "DOV", "DFE", "DEF", "DIS", "DSC")])
        sens = {s["code"]: s["information"] for s in internes}
        self.assertEqual((sens["DIS"], sens["DSC"]), ("Disponible", "Discordance de position"))
        for s in internes:
            self.assertEqual((s["type_logique"], s["es"], s["presence"], s["option"], s["alarme"], s["logique"]),
                             ("BOOL", "Interne", "Option", "Variables internes", False, ""))
        self.assertIn("Variables internes", self.origine.type("MV")["options"])
        self.assertEqual(self.origine.anomalies(), [])
        self.assertEqual(self.cat.anomalies(), [])

    def test_candidats_bi_livres_non_selectionnes_par_defaut(self):
        s = Session(self.origine)
        s.nouveau(False)
        s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
        s.ajouter_sous_ensemble("00")
        eq = s.ajouter_equipement(Equipement("00", "MV", "01", options=["Télécommandée"]))
        self.assertEqual(s.variables_internes(), [])
        echange = [v.nom for v in s.variables()]
        eq.options.append("Variables internes")
        self.assertEqual([x.nom for x in s.variables_internes()],
                         [f"BI_RV01MV01_{c}" for c in ("OUV", "FER", "DOV", "DFE", "DEF", "DIS", "DSC")])
        self.assertEqual([v.nom for v in s.variables()], echange)     # échange et %MW inchangés

    def test_non_selectionnee_absente_partout(self):
        s = self.session()
        self.assertEqual(generer_internes(s.ouvrage, s.catalogue), [])
        noms = {v.nom for v in s.variables()} | {p.nom for p in s.points()}
        self.assertFalse([n for n in noms if n.split("_", 1)[0] in FAMILLES_INTERNES])

    def test_selection_par_option_puis_retrait_individuel(self):
        s = self.session(("Télécommandée", OPTION))
        internes = {x.nom: x for x in s.variables_internes()}
        self.assertEqual(set(internes), {"BI_RV01MV01_MEM", "RI_RV01MV01_TPS"})
        # type déclaré par signal, jamais déduit de la famille
        self.assertEqual((internes["BI_RV01MV01_MEM"].type_logique, internes["RI_RV01MV01_TPS"].type_logique),
                         ("BOOL", "REAL"))
        s2 = self.session(("Télécommandée", OPTION), exclus=("RI_TPS",))
        self.assertEqual([x.nom for x in s2.variables_internes()], ["BI_RV01MV01_MEM"])

    def test_selection_sans_effet_sur_l_echange_et_les_es(self):
        sans = self.session()
        avec = self.session(("Télécommandée", OPTION))
        self.assertEqual([v.nom for v in avec.variables()], [v.nom for v in sans.variables()])
        self.assertEqual([p.nom for p in avec.points()], [p.nom for p in sans.points()])
        self.assertEqual(len(generer_points(avec.ouvrage, avec.catalogue)), len(sans.points()))

    def test_signal_propre_interne(self):
        s = self.session()
        eq = s.ouvrage.equipements[0]
        with self.assertRaises(RegleMetier):
            Session.verifier_signal_propre(SignalPropre("Essai", "BI", "ESSAI", "BOOL", es="ET"))
        with self.assertRaises(RegleMetier):
            Session.verifier_signal_propre(SignalPropre("Essai", "BI", "ESSAI", "BOOL", alarme=True))
        propre = SignalPropre("Mémoire de défaut", "BI", "MDEF", "BOOL")
        Session.verifier_signal_propre(propre)
        eq.ajouts.append(propre)
        internes = s.variables_internes()
        self.assertEqual([(x.nom, x.origine) for x in internes], [("BI_RV01MV01_MDEF", "Propre à l'équipement")])
        self.assertNotIn("BI_RV01MV01_MDEF", {v.nom for v in s.variables()})

    def test_enregistrement_et_reouverture(self):
        s = self.session(("Télécommandée", OPTION), exclus=("RI_TPS",))
        with tempfile.TemporaryDirectory() as d:
            chemin = os.path.join(d, "o.ouvrage.json")
            s.enregistrer(chemin)
            s2 = Session(self.cat)
            s2.ouvrir(chemin)
        self.assertEqual([x.nom for x in s2.variables_internes()], ["BI_RV01MV01_MEM"])


class TestJamaisEchangeNiTeletransmission(Base):
    def test_aucune_adresse_ni_mw(self):
        s = self.session(("Télécommandée", OPTION))
        props, erreurs = s.plan()
        self.assertFalse(erreurs)
        s.appliquer(props)
        eq = s.ouvrage.equipements[0]
        self.assertFalse([c for c in list(eq.adresses) + list(eq.adresses_es) if c.split("_", 1)[0] in FAMILLES_INTERNES])
        self.assertTrue(all(not hasattr(x, "adresse") for x in s.variables_internes()))

    def test_absente_de_la_teletransmission(self):
        s = self.session(("Télécommandée", OPTION))
        teletransmission.construire(s.ouvrage, s.catalogue)
        cles = {l.cle for l in s.ouvrage.table_tt}
        self.assertTrue(cles)
        self.assertFalse([c for c in cles if c.split("_", 1)[0] in FAMILLES_INTERNES])

    def test_absente_de_la_table_d_echange_excel(self):
        s = self.session(("Télécommandée", OPTION))
        props, _ = s.plan(); s.appliquer(props)
        with tempfile.TemporaryDirectory() as d:
            chemin = os.path.join(d, "t.xlsx")
            s.exporter_excel(chemin)
            with zipfile.ZipFile(chemin) as z:
                contenu = "".join(z.read(n).decode("utf-8", "replace") for n in z.namelist() if n.endswith(".xml"))
        self.assertIn("TS_RV01MV01_OUV", contenu)
        self.assertNotIn("BI_RV01MV01_MEM", contenu)
        self.assertNotIn("RI_RV01MV01_TPS", contenu)


class TestExportXSY(Base):
    def _xsy(self, options):
        s = self.session(options)
        props, _ = s.plan(); s.appliquer(props)
        with tempfile.TemporaryDirectory() as d:
            chemin = os.path.join(d, "t.xsy")
            n = s.exporter_xsy(chemin)
            with open(chemin, encoding="utf-8") as f:
                texte = f.read()
            lues = {v.nom: v for v in lire_xsy(chemin)}
        return s, n, texte, lues

    def test_non_selectionnee_absente_du_xsy(self):
        _, _, texte, _ = self._xsy(("Télécommandée",))
        self.assertNotIn("BI_", texte)
        self.assertNotIn("RI_", texte)

    def test_selectionnee_exportee_sans_adresse(self):
        sans, n_sans, _, _ = self._xsy(("Télécommandée",))
        s, n, texte, lues = self._xsy(("Télécommandée", OPTION))
        self.assertEqual(n, n_sans + 2)
        self.assertIn('<variables name="BI_RV01MV01_MEM" typeName="BOOL">', texte)
        self.assertIn('<variables name="RI_RV01MV01_TPS" typeName="REAL">', texte)
        for nom, type_ in (("BI_RV01MV01_MEM", "BOOL"), ("RI_RV01MV01_TPS", "REAL")):
            self.assertEqual((lues[nom].adresse, lues[nom].type), ("", type_))
        # les variables d'échange gardent exactement leurs adresses
        echange = {v.nom: v.adresse for v in s.variables()}
        self.assertEqual({k: lues[k].adresse for k in echange}, echange)


class TestControles(Base):
    def _anomalies(self, **extra):
        cat = copy.deepcopy(self.cat)
        cat.signaux[-1].update(extra)
        return [m for m in cat.anomalies() if "RI_TPS" in m]

    def test_regles_de_declaration(self):
        self.assertTrue(self._anomalies(presence="Par défaut"))
        self.assertTrue(self._anomalies(presence="Obligatoire"))
        self.assertTrue(self._anomalies(es="EA"))
        self.assertTrue(self._anomalies(source="ES_POS"))
        self.assertTrue(self._anomalies(alarme=True))
        self.assertEqual(self._anomalies(), [])

    def test_modele_refuse_une_interne_non_selectionnable(self):
        erreurs = verifier_signaux_modele([_interne("EI", "CPT", "INT", "Compteur", presence="Par défaut")], "MV")
        self.assertTrue(any("sélection" in e for e in erreurs))
        self.assertEqual(verifier_signaux_modele([_interne("MI", "ETAT", "INT", "Mot d'état")], "MV"), [])

    def test_regle_auto_ne_retient_jamais_une_interne(self):
        cat = copy.deepcopy(self.cat)
        cat.regles = list(cat.regles) + [{"id": "ESSAI-P1", "type": "MV", "si": ["TS_OUV"], "propose": ["BI_OUV"],
                                          "mode": "auto"}]
        self.assertTrue(any("ESSAI-P1" in m and "BI_OUV" in m for m in cat.anomalies()))
        eq = Equipement("00", "MV", "01")
        props = evaluer(cat, eq, {"TS_OUV"})
        self.assertEqual(props["BI_OUV"].etat, "proposé")       # jamais retenue sans décision

    def test_nom_trop_long_signale(self):
        s = self.session()
        eq = s.ouvrage.equipements[0]
        eq.ajouts.append(SignalPropre("Essai", "BI", "TRESLONGCODEINTERNE01", "BOOL"))
        nom = s.variables_internes()[0].nom
        self.assertGreater(len(nom), 32)
        self.assertTrue(any(nom in a.message and a.niveau == "Erreur" for a in controler(s.ouvrage, s.catalogue)))

    def test_inscrite_au_controle_des_homonymes(self):
        s = self.session(("Télécommandée", OPTION))
        self.assertIn("BI_RV01MV01_MEM", noms_ouvrage(s.ouvrage, s.catalogue))

    def test_referentiel_excel_aller_retour_sans_perte(self):
        from genvar import modeles, referentiel_excel as rx
        ancien = os.environ.get("SOREP_DATA_DIR")
        with tempfile.TemporaryDirectory() as d:
            os.environ["SOREP_DATA_DIR"] = d
            try:
                ref = modeles.charger()
                chemin = os.path.join(d, "r.xlsx")
                rx.exporter(self.cat, ref, chemin)
                etat, lecture, _ = rx.lire(chemin)
                cat, ref2 = rx.construire(etat, self.cat, ref)
            finally:
                if ancien is None:
                    os.environ.pop("SOREP_DATA_DIR", None)
                else:
                    os.environ["SOREP_DATA_DIR"] = ancien
        self.assertEqual(lecture.erreurs, [])
        self.assertEqual(rx.etat(cat, ref2), rx.etat(self.cat, ref))
        self.assertEqual({(s["famille"], s["code"]) for s in cat.signaux if s["famille"] in FAMILLES_INTERNES},
                         {("BI", "MEM"), ("RI", "TPS")}
                         | {("BI", c) for c in ("OUV", "FER", "DOV", "DFE", "DEF", "DIS", "DSC")})

    def test_ouvrage_sans_interne_inchange_par_l_existence_de_la_famille(self):
        s = Session(self.origine)
        s.nouveau(False)
        s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
        s.ajouter_sous_ensemble("00")
        s.ajouter_equipement(Equipement("00", "MV", "01", options=["Télécommandée"]))
        self.assertEqual(s.variables_internes(), [])
        with tempfile.TemporaryDirectory() as d:
            chemin = os.path.join(d, "a.ouvrage.json")
            s.enregistrer(chemin)
            with open(chemin, encoding="utf-8") as f:
                texte = f.read()
        # la nouvelle famille n'ajoute rien au fichier d'un ouvrage qui ne l'emploie pas
        for famille in FAMILLES_INTERNES:
            self.assertNotIn(f'"{famille}_', texte)


if __name__ == "__main__":
    unittest.main()
