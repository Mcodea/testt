"""Lancement du Générateur de variables SOREP (double-clic sous Windows).

L'ancienne interface Tkinter a été retirée en V0.9 : ce fichier ouvre l'interface PySide6.
"""
import sys

from genvar_qt.application import lancer

if __name__ == "__main__":
    sys.exit(lancer())
