"""Capture authentique des fenêtres SOREP PySide6, sur le poste où PySide6 est installé.

Les deux parcours sont montrés avec des données fictives en mémoire. Le programme
n'écrit pas dans les ouvrages de l'utilisateur et ne produit pas de maquette IA.

Exécuter dans le dossier du projet : py capturer_interface_reelle.py
"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QCoreApplication

from genvar_qt import style
from genvar_qt.fenetre import Fenetre


def main():
    QCoreApplication.setOrganizationName("SOREP")
    QCoreApplication.setApplicationName("Capture-interface")
    app = QApplication(sys.argv)
    style.appliquer(app)
    f = Fenetre()
    f.resize(1450, 890)
    f.show()
    dossier = Path(__file__).resolve().parent / 'Captures_interface_reelles'
    dossier.mkdir(exist_ok=True)

    def enregistrer(nom):
        app.processEvents()
        chemin = dossier / nom
        if not f.grab().save(str(chemin), 'PNG'):
            raise OSError(f"Capture impossible : {chemin}")
        print(f"CAPTURE : {chemin}")

    def faire_captures():
        from genvar.modele import Equipement, VariableExistante
        try:
            f.accueil()
            enregistrer('01_Mes_ouvrages.png')
            f.s.nouveau()
            f.s.ouvrage.mode = 'Neuf'
            f.s.ouvrage.lieu = 'F999'            # Données d'illustration, non enregistrées
            f.s.ouvrage.code_ouvrage = 'RV'
            f.s.ouvrage.libelle = 'Réservoir fictif'
            f.s.ajouter_sous_ensemble('11', 'Réservoir 1')
            f.s.ajouter_sous_ensemble('21', 'Station de pompage')
            f.s.ajouter_equipement(Equipement('11', 'PM', '01', options=['Variateur']))
            f.s.ajouter_equipement(Equipement('21', 'MV', '03'))
            f.charger()
            f.aller('Synthèse')
            enregistrer('02_Tableau_de_bord_neuf.png')
            f.s.ajouter_uf('UF01', 'Alimentation')
            f.s.ajouter_uf('UF02', 'Pompage')
            f.s.affecter_uf({f.s.ouvrage.equipements[0].ident}, 'UF01')
            f.s.affecter_uf({f.s.ouvrage.equipements[1].ident}, 'UF02')
            f.aller('Ouvrage')
            enregistrer('03_Fiche_ouvrage.png')
            f.aller('E/S automate')
            enregistrer('04_Liste_ES.png')
            f.aller('Variables')
            enregistrer('04b_Variables.png')
            f.aller('Contrôles')
            enregistrer('05_Controles.png')
            f.aller('Exports')
            enregistrer('06_Exports.png')
            f.aller('Plan mémoire')
            enregistrer('07_Plan_memoire.png')
            f.s.nouveau()
            f.s.ouvrage.mode = 'Existant'
            f.s.ouvrage.lieu = 'F999'
            f.s.ouvrage.code_ouvrage = 'RV'
            f.s.ouvrage.libelle = 'Réservoir fictif à reprendre'
            f.s.ajouter_sous_ensemble('21', 'Station de pompage')
            f.s.ajouter_equipement(Equipement('21', 'MV', '03'))
            eq = f.s.ouvrage.equipements[-1]
            f.s.ouvrage.existantes = [
                VariableExistante('TS_F999RV21MV03_FER', 'BOOL', '%M120', ident_eq=eq.ident, cle='TS_FER',
                                  identification='Exacte', commentaire='Vanne fermée (fictif)'),
                VariableExistante('TM_NIVEAU_RES1', 'REAL', '%MW200', commentaire='Niveau réservoir (fictif)'),
                VariableExistante('DEF_POMPE_2', 'BOOL', '%M131', commentaire='Défaut pompe 2 (fictif)'),
            ]
            f.s.construire_table()
            f.s.proposer_associations()
            f.charger()
            f.aller('Projet existant')
            enregistrer('08_Table_teletransmission.png')
        except Exception as exc:
            print('ERREUR DE CAPTURE :', exc, file=sys.stderr)
        finally:
            f.s.modifie = False
            f.close()
            app.quit()

    QTimer.singleShot(350, faire_captures)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
