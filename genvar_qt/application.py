"""Démarrage de l'interface PySide6."""

import sys


def lancer(argv=None):
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        message = ("PySide6 n'est pas installé.\n\n"
                   "Dans le terminal de VS Code :\n    py -m pip install -r requirements-qt.txt\n\n"
                   "L'application actuelle reste disponible : lancer.pyw.")
        try:                                    # message visible même lancé par double-clic (.pyw)
            import tkinter.messagebox as mb
            mb.showerror("Générateur de variables SOREP", message)
        except Exception:
            print(message, file=sys.stderr)
        return 1

    from PySide6.QtCore import QCoreApplication
    from . import style
    from .fenetre import Fenetre

    QCoreApplication.setOrganizationName("SOREP")
    QCoreApplication.setApplicationName("Generateur de variables - Atelier")
    argv = sys.argv if argv is None else argv
    app = QApplication.instance() or QApplication(argv)
    _traduire(app)
    style.appliquer(app)
    from pathlib import Path
    from PySide6.QtGui import QIcon
    icone = Path(__file__).resolve().parent / "assets" / "ogias-application.ico"
    if icone.is_file():
        app.setWindowIcon(QIcon(str(icone)))
    fenetre = Fenetre()
    fichiers = [a for a in argv[1:] if a.endswith(".json")]
    if fichiers:
        fenetre.ouvrir(fichiers[0])
    fenetre.show()
    return app.exec()


def _traduire(app):
    """Boutons standard de Qt en français (Oui, Non, Annuler, Fermer…) si les traductions sont livrées."""
    try:
        from PySide6.QtCore import QTranslator, QLibraryInfo, QLocale
        traducteur = QTranslator(app)
        dossier = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if traducteur.load(QLocale(QLocale.Language.French), "qtbase", "_", dossier):
            app.installTranslator(traducteur)
            app._traducteur_qt = traducteur          # conserver une référence
    except Exception:
        pass                                         # interface fonctionnelle même sans traduction
