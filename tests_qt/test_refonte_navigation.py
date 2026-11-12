"""Recette graphique ciblée de la refonte — nécessite PySide6.

Exécuter sous Windows : py -m unittest discover -s tests_qt -v
Les tests sont marqués ignorés lorsque la bibliothèque Qt est absente ; ne jamais
interpréter un skip comme un succès graphique.
"""
import os
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

try:
    from PySide6.QtWidgets import QApplication, QPushButton
    from PySide6.QtCore import QCoreApplication
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 absent : lancer la recette sur Windows")
class TestRefonteNavigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.prev = os.environ.get('SOREP_DATA_DIR')
        os.environ['SOREP_DATA_DIR'] = cls.tmp.name
        QCoreApplication.setOrganizationName('SOREP-interface-tests')
        QCoreApplication.setApplicationName('Tests-interface')
        cls.app = QApplication.instance() or QApplication([])
        from genvar_qt import style
        style.appliquer(cls.app)

    @classmethod
    def tearDownClass(cls):
        if cls.prev is None:
            os.environ.pop('SOREP_DATA_DIR', None)
        else:
            os.environ['SOREP_DATA_DIR'] = cls.prev
        cls.tmp.cleanup()

    def setUp(self):
        from genvar.session import Session
        from genvar_qt.fenetre import Fenetre
        self.f = Fenetre(Session())
        self.f.show()
        self.app.processEvents()

    def tearDown(self):
        self.f.s.modifie = False
        self.f.close()
        self.app.processEvents()

    def test_accueil_affiche_deux_parcours(self):
        self.assertIs(self.f.pile.currentWidget(), self.f.v_accueil)
        boutons = [x.text() for x in self.f.v_accueil.findChildren(QPushButton)]
        self.assertIn('Créer un projet neuf', boutons)
        self.assertIn('Analyser un ouvrage existant', boutons)
        self.assertTrue(self.f.items['Projet existant'].isHidden())
        self.assertTrue(self.f.items['Variables'].isHidden())
        self.assertFalse(self.f.b_enregistrer_entete.isVisible())

    def test_clic_projet_neuf_ouvre_fiche_et_navigation(self):
        boutons = self.f.v_accueil.findChildren(QPushButton)
        next(b for b in boutons if b.text() == 'Créer un projet neuf').click()
        self.app.processEvents()
        self.assertEqual(self.f.s.ouvrage.mode, 'Neuf')
        self.assertIs(self.f.pile.currentWidget(), self.f.v_ouvrage)
        self.assertFalse(self.f.items['Variables'].isHidden())
        self.assertTrue(self.f.items['Projet existant'].isHidden())
        self.assertIn('Projet neuf', self.f.fil_ariane.text())

    def test_clic_projet_existant_ouvre_fiche_et_navigation(self):
        boutons = self.f.v_accueil.findChildren(QPushButton)
        next(b for b in boutons if b.text() == 'Analyser un ouvrage existant').click()
        self.app.processEvents()
        self.assertEqual(self.f.s.ouvrage.mode, 'Existant')
        self.assertIs(self.f.pile.currentWidget(), self.f.v_ouvrage)
        self.assertFalse(self.f.items['Projet existant'].isHidden())
        self.assertTrue(self.f.items['Plan mémoire'].isHidden())
        self.assertIn('Projet existant', self.f.fil_ariane.text())

    def test_parcours_lateral_numerote_selon_le_mode(self):
        self.f.nouveau_mode('Neuf')
        self.app.processEvents()
        self.assertEqual(self.f.items['Ouvrage'].numero, 1)
        self.assertEqual(self.f.items['Exports'].numero, 6)
        self.assertTrue(self.f.carte_dossier.isVisible())
        self.f.s.modifie = False
        self.f.nouveau_mode('Existant')
        self.app.processEvents()
        self.assertEqual(self.f.items['Projet existant'].numero, 2)
        self.assertEqual(self.f.items['Exports'].numero, 4)
        self.f.accueil()
        self.assertFalse(self.f.carte_dossier.isVisible())

    def test_raccourci_etape_et_etat_enregistrement(self):
        self.f.nouveau_mode('Neuf')
        self.f._aller_etape(2)
        self.assertIs(self.f.pile.currentWidget(), self.f.v_es)          # étape 2 : liste des E/S
        self.f.s.definir('libelle', 'Essai')
        self.f._ouvrage_modifie()
        self.assertIn('non enregistr', self.f.etat_enregistrement.text())

    def test_anciens_actions_import_et_validation_conservees(self):
        textes = [w.text() for w in self.f.v_existant.findChildren(QPushButton)]
        self.assertTrue(any('Importer liste E/S' in texte for texte in textes))
        self.assertTrue(any('Proposer' in texte for texte in textes))
        self.assertTrue(any('Confirmer' in texte for texte in textes))


if __name__ == '__main__':
    unittest.main()
