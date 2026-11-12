"""Emplacements des données SOREP.

La distribution vierge démarre dans un espace de travail propre, séparé des
anciens essais : aucun ouvrage ni catalogue utilisateur n'est importé au
lancement. Les données historiques ne sont jamais supprimées.

SOREP_DATA_DIR permet de sélectionner explicitement un autre espace de travail.
"""
import os
import sys


def dossier_programme():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def dossier_ressources():
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS"), "genvar", "data")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def dossier_donnees():
    """Stockage pérenne de l'atelier, non pré-rempli.

    Contrairement aux éditions antérieures, aucun dossier adjacent « Donnees »
    n'est importé automatiquement. L'utilisateur peut choisir une autre racine
    par SOREP_DATA_DIR ou importer manuellement un dossier via « Mes ouvrages ».
    """
    surcharge = os.environ.get("SOREP_DATA_DIR", "").strip()
    if surcharge:
        chemin = os.path.abspath(os.path.expanduser(surcharge))
    elif sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        chemin = os.path.join(base, "SOREP", "GenerateurVariables_Atelier")
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        chemin = os.path.join(base, "SOREP", "GenerateurVariables_Atelier")
    os.makedirs(chemin, exist_ok=True)
    return chemin


def dossier_projets():
    chemin = os.path.join(dossier_donnees(), "Projets")
    os.makedirs(chemin, exist_ok=True)
    return chemin


def dossier_exports():
    chemin = os.path.join(dossier_donnees(), "Exports")
    os.makedirs(chemin, exist_ok=True)
    return chemin


def fichier_catalogue_utilisateur():
    return os.path.join(dossier_donnees(), "catalogue.json")


def fichier_catalogue_origine():
    return os.path.join(dossier_ressources(), "catalogue_defaut.json")
