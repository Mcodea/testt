"""Test de fumée de l'interface PySide6, sans écran (plateforme Qt « offscreen »).

    py -m unittest discover -s tests_qt -v

Ignoré si PySide6 n'est pas installé. Vérifie que les écrans se construisent, que les
tableaux montrent bien ce que le moteur calcule, et que les actions passent par la Session.
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PySide6.QtCore import Qt, QSettings, QCoreApplication
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
except ImportError:                                    # PySide6 absent : rien à tester
    QApplication = None

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, SignalPropre
from genvar.session import Session


@unittest.skipIf(QApplication is None, "PySide6 n'est pas installé")
class TestInterfaceQt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reglages = tempfile.mkdtemp()
        cls.ancien_dossier = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = cls.reglages
        QCoreApplication.setOrganizationName("Regie ESB-RSO essai")
        QCoreApplication.setApplicationName("Generateur essai")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, cls.reglages)
        cls.app = QApplication.instance() or QApplication([])
        from genvar_qt import style
        style.appliquer(cls.app)

    @classmethod
    def tearDownClass(cls):
        if cls.ancien_dossier is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = cls.ancien_dossier

    def setUp(self):
        from genvar_qt.fenetre import Fenetre
        s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s.definir("lieu", "XT25"); s.definir("code_ouvrage", "RV")
        s.ajouter_sous_ensemble("11", "Réservoir 1")
        s.ajouter_sous_ensemble("21", "Station")
        s.ajouter_equipement(Equipement("11", "PM", "01", options=["Variateur"]))
        s.ajouter_equipement(Equipement("21", "MV", "03",
                                        ajouts=[SignalPropre("Essai", "TS", "ESSAI", "BOOL", es="ET", organe="FDC")]))
        s.modifie = False
        self.s = s
        self.f = Fenetre(s)
        self.f.show()
        self.app.processEvents()

    def tearDown(self):
        self.s.modifie = False                       # pas de question « Enregistrer ? » à la fermeture
        self.f.close()
        self.app.processEvents()

    def test_ecran_ouvrage(self):
        vo = self.f.v_ouvrage
        self.assertEqual(vo.prefixe.text(), "XT25RV")
        self.assertEqual(vo.t_se.modele.rowCount(), 2)
        self.assertEqual(vo.t_eq.modele.rowCount(), 2)
        vo.recherche.setText("MV03")
        self.assertEqual(vo.t_eq.nombre_visible(), 1)
        vo.recherche.clear()
        vo.f_se.setCurrentIndex(vo.f_se.findData("11"))
        self.assertEqual(vo.t_eq.nombre_visible(), 1)

    def test_saisie_identification(self):
        vo = self.f.v_ouvrage
        vo.lieu.selectAll()
        QTest.keyClicks(vo.lieu, "m126")               # le validateur met en majuscules
        self.assertEqual(vo.lieu.text(), "M126")
        self.assertEqual(self.s.ouvrage.lieu, "M126")
        self.assertTrue(self.s.modifie)
        self.assertTrue(self.f.windowTitle().startswith("*"))

    def test_ecran_variables(self):
        self.f.aller("Variables")
        self.app.processEvents()
        vv = self.f.v_variables
        self.assertEqual(vv.t.modele.rowCount(), len(self.s.variables()))
        noms = {vv.t.modele.data(vv.t.modele.index(r, 2)) for r in range(vv.t.modele.rowCount())}
        self.assertEqual(noms, {v.nom for v in self.s.variables()})
        vv.f_famille.setCurrentIndex(vv.f_famille.findData("TS"))
        self.assertEqual(vv.t.nombre_visible(), sum(1 for v in self.s.variables() if v.famille == "TS"))
        vv.f_famille.setCurrentIndex(0)

    def test_attribution_par_la_session(self):
        vv = self.f.v_variables
        props, erreurs = self.s.plan()
        self.assertTrue(props and not erreurs)
        self.s.appliquer(props)
        vv.rafraichir()
        attendu = {v.nom: v.adresse for v in self.s.variables()}
        for r in range(vv.t.modele.rowCount()):
            v = vv.t.modele.objet(r)
            self.assertEqual(v.adresse, attendu[v.nom])
        self.assertEqual(vv.i_sans.valeur.text(), "0")

    def test_dialogue_equipement(self):
        from genvar_qt.dialogues import DialogueEquipement
        eq = self.s.ouvrage.equipements[1]
        d = DialogueEquipement(self.f, self.s, eq, "essai", eq.ident)
        lignes = self.s.signaux_proposes(d.eq)
        self.assertEqual(d.table.rowCount(), len(lignes) + len(eq.ajouts))
        self.assertEqual(d.repere.text(), "XT25RV21MV03")
        # décocher un signal du catalogue par défaut : passe par Session.basculer_signal
        r = next(i for i, (s, retenu, pres, actif) in enumerate(lignes) if retenu and s["presence"] == "Par défaut")
        d.table.item(r, 0).setCheckState(Qt.CheckState.Unchecked)
        cle = f"{lignes[r][0]['famille']}_{lignes[r][0]['code']}"
        self.assertIn(cle, d.eq.exclus)
        self.assertNotIn(cle, eq.exclus)               # l'original ne change qu'après OK
        d.reject()

    def test_fiche_equipement_propositions(self):
        from genvar_qt.dialogues import DialogueEquipement
        eq = self.s.ouvrage.equipements[1]                         # MV03 : deux fins de course
        d = DialogueEquipement(self.f, self.s, eq, "essai", eq.ident)
        lignes = self.s.signaux_proposes(d.eq)
        r = next(i for i, (sig, retenu, pres, actif) in enumerate(lignes) if sig["code"] == "DISC")
        self.assertIn("Proposé", d.table.item(r, 5).text())
        self.assertEqual(d.table.item(r, 0).checkState(), Qt.CheckState.Unchecked)
        d.table.item(r, 0).setCheckState(Qt.CheckState.Checked)    # accepter la proposition
        self.assertIn("TS_DISC", d.eq.acceptes)
        self.assertNotIn("TS_DISC", eq.acceptes)                   # l'original ne change qu'après OK
        self.assertEqual(d.table.item(0, 1).text(), "E/S physique")  # E/S physiques en tête
        d.reject()

    def test_referentiel_editable(self):
        self.f.aller("Catalogue")
        self.app.processEvents()
        vc = self.f.v_catalogue
        self.assertGreater(vc.liste.count(), 40)
        self.assertGreater(vc.t_sig.modele.rowCount(), 0)

    def test_bandeau_a_faire(self):
        from PySide6.QtWidgets import QPushButton
        for e in self.s.ouvrage.equipements:                       # écarter les propositions en attente
            for cle, p in self.s.propositions(e).items():
                if p.etat == "proposé":
                    self.s.refuser_proposition(e, cle)
        self.s.definir("libelle", "Essai")
        self.f.aller("Variables")
        self.app.processEvents()
        bandeau = self.f.guides["Variables"]
        self.assertTrue(bandeau.isVisible())
        textes = [b.text() for b in bandeau.findChildren(QPushButton)]
        self.assertIn("Attribuer les adresses", textes)
        self.f.aller("Contrôles")
        self.app.processEvents()
        self.assertTrue(self.f.v_controles.c_groupes.isVisible())

    def test_arborescence(self):
        vo = self.f.v_ouvrage
        self.s.ajouter_uf("UF01", "Stockage")
        self.s.affecter_uf({self.s.ouvrage.equipements[0].ident}, "UF01")
        vo.rafraichir()
        racine = vo.arbre.topLevelItem(0)
        textes = [racine.child(i).text(0) for i in range(racine.childCount())]
        self.assertTrue(textes[0].startswith("UF01"))
        self.assertTrue(any("communs" in t for t in textes))
        self.assertTrue(textes[-1].endswith("Ajouter une unité fonctionnelle"))
        eq = racine.child(0).child(0)
        self.assertTrue(eq.text(0).startswith("XT25RV11PM01"))
        self.assertGreater(eq.childCount(), 3)                     # E/S et signaux sous l'équipement
        vo._action_arbre("deplacer", ([self.s.ouvrage.equipements[1].ident], "UF01"))
        self.assertEqual(self.s.ouvrage.equipements[1].uf, "UF01")

    def test_explorateur_ouvrage(self):
        self.f.aller("Ouvrage")
        self.app.processEvents()
        vo = self.f.v_ouvrage
        eq = self.s.ouvrage.equipements[0]
        vo._action_arbre("choisir_ouvrage", None)
        self.assertEqual(vo.vue_courante(), "ident")
        self.assertEqual(vo.pile_droite.currentIndex(), 0)
        vo._action_arbre("choisir_eq", eq.ident)
        self.assertEqual(vo.vue_courante(), "eq")
        self.assertEqual(vo.p_titre.text(), self.s.ouvrage.repere(eq))
        vo._action_arbre("filtrer_uf", "")
        self.assertEqual(vo.vue_courante(), "eqs")
        self.assertTrue(vo.arbre.isVisible())                     # l'arborescence reste toujours visible

    def test_suppression_ouvrage(self):
        from genvar import projets
        projets.repertoire().mkdir(parents=True, exist_ok=True)
        chemin = str(projets.repertoire() / "essai_suppr.ouvrage.json")
        self.s.enregistrer(chemin)
        self.f.supprimer_ouvrage(chemin)
        self.assertFalse(os.path.exists(chemin))
        self.assertFalse(self.s.chemin)
        self.assertTrue(any("essai_suppr" in x.chemin for x in projets.lister_corbeille()))

    def test_liste_es_et_pdf(self):
        self.f.aller("E/S automate")
        self.app.processEvents()
        ve = self.f.v_es
        self.assertEqual(ve.t.modele.rowCount(), len(self.s.points()))
        ve.t.selectRow(0)
        self.app.processEvents()
        self.assertTrue(ve.d_nom.text().startswith(("ET_", "ST_", "EA_", "SA_")))
        ve.d_module.setText("0.3"); ve.d_voie.setText("2")
        self.assertIn("%", ve.d_apercu.text())
        chemin = os.path.join(self.reglages, "liste_es.pdf")
        ve.ecrire_pdf(chemin)
        with open(chemin, "rb") as f:
            self.assertEqual(f.read(4), b"%PDF")

    def test_dialogue_plan(self):
        from genvar_qt.dialogues import DialoguePlan
        props, erreurs = self.s.plan()
        d = DialoguePlan(self.f, self.s, props, erreurs, False)
        d.reject()

    def test_navigation(self):
        self.assertIs(self.f.pile.currentWidget(), self.f.v_accueil)
        self.assertEqual(set(self.f.vues), {
            "Mes ouvrages", "Synthèse", "Ouvrage", "Variables", "E/S automate",
            "Projet existant", "Plan mémoire", "Contrôles", "Exports", "Catalogue"})
        for nom in self.f.vues:
            if (nom == "Projet existant" and self.s.ouvrage.mode != "Existant"):
                continue
            self.f.aller(nom)
            self.app.processEvents()
            self.assertIs(self.f.pile.currentWidget(), self.f.vues[nom])

    def test_statut_valide_declasse_visible_apres_modification(self):
        # L'utilisateur ne doit pas voir « Validé » quand une modification
        # vient de remettre le projet à contrôler dans le moteur.
        self.s.ouvrage.statut = "Validé"
        self.f.v_ouvrage.charger()
        self.assertEqual(self.f.v_ouvrage.statut.currentText(), "Validé")
        self.s.definir("libelle", "Nouvelle désignation")
        self.f._ouvrage_modifie()
        self.assertEqual(self.s.ouvrage.statut, "À contrôler")
        self.assertEqual(self.f.v_ouvrage.statut.currentText(), "À contrôler")

    def test_actions_existant_disponibles(self):
        from PySide6.QtWidgets import QPushButton
        boutons = [b.text() for b in self.f.v_existant.findChildren(QPushButton)]
        self.assertTrue(any("liste E/S" in b for b in boutons))
        self.assertTrue(any("Construire" in b for b in boutons))
        self.assertTrue(any("Proposer" in b for b in boutons))

    def test_table_teletransmission_affichee(self):
        from genvar.modele import VariableExistante
        self.s.ouvrage.mode = "Existant"
        self.s.ouvrage.existantes = [VariableExistante('TS_XT25RV21MV03_FER', 'BOOL', '%MW1000.0')]
        self.s.construire_table()
        self.s.proposer_associations()
        self.f.charger()
        self.f.aller("Projet existant")
        self.app.processEvents()
        vx = self.f.v_existant
        self.assertEqual(vx.t_inv.modele.rowCount(), 1)
        self.assertEqual(vx.t.modele.rowCount(), len(self.s.ouvrage.table_tt))
        ligne = next(x for x in vx.lignes if x.variable_source)
        self.assertEqual(ligne.statut, "À compléter")
        vx.t.selectionner(lambda x: x is ligne)
        self.app.processEvents()
        self.assertIn("TS_XT25RV21MV03_FER", vx.d_source.text())

    def test_registre_projets_et_synthese(self):
        import pathlib
        from genvar import chemins
        cible = pathlib.Path(chemins.dossier_projets()) / "projet_essai.ouvrage.json"
        self.s.enregistrer(str(cible))
        self.f.accueil()
        self.assertGreaterEqual(self.f.v_accueil.table.rowCount(), 1)
        self.f.aller("Synthèse")
        self.assertIn("XT25RV", self.f.v_synthese.titre.text())

    def test_vues_metier_sans_placeholder(self):
        self.f.aller("E/S automate")
        self.assertIs(self.f.pile.currentWidget(), self.f.v_es)
        self.assertGreater(self.f.v_es.t.modele.rowCount(), 0)
        self.f.aller("Plan mémoire")
        self.assertIs(self.f.pile.currentWidget(), self.f.v_parametres)
        self.assertIn("TR", self.f.v_parametres.debuts)
        self.f.aller("Contrôles")
        self.assertIs(self.f.pile.currentWidget(), self.f.v_controles)
        self.f.aller("Exports")
        self.assertIs(self.f.pile.currentWidget(), self.f.v_exports)


if __name__ == "__main__":
    unittest.main()
