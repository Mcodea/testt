"""Aller-retour Excel de la liste des équipements (19/11/2026).

Idée reprise de l'import comparé « par repère » des outils d'ingénierie de données : OGIAS exporte la liste, le
client ou un collègue la complète dans Excel, puis elle est réimportée et COMPARÉE à l'ouvrage avant toute écriture
(genvar.inbound, nature « equipements_aller_retour »).

Colonnes : le repère est la clé ; désignation, modèle, UF et local sont modifiables ; une ligne nouvelle crée un
équipement ; l'identifiant OGIAS sert seulement à détecter un repère modifié dans le fichier (refusé : les noms et
adresses en dépendent). Une cellule vidée ne vide rien dans OGIAS.
"""
from __future__ import annotations

from .export_xlsx import ecrire_xlsx

ENTETES = ["Repère", "Désignation", "Type", "Modèle", "UF", "Local", "Identifiant OGIAS (ne pas modifier)"]
LISEZ_MOI = [
    ["Cette liste se réimporte dans OGIAS : Équipements > Importer une liste > « Liste des équipements (aller-retour) »."],
    ["OGIAS compare chaque ligne à l'ouvrage et montre ce qui sera créé, modifié ou retiré AVANT toute écriture."],
    ["Modifiables : Désignation (32 caractères au plus), Modèle (du type, dans le référentiel), UF (existante), Local."],
    ["Nouvelle ligne : nouvel équipement, repère selon la charte de l'ouvrage. Le repère d'une ligne existante ne se modifie pas ici."],
    ["Ligne supprimée du fichier : équipement « obsolète », gardé par défaut ; supprimé seulement sur votre choix explicite."],
    ["Les équipements dont des adresses sont validées ne sont jamais supprimés ni changés de modèle par import."],
    ["Cellule vidée : la valeur d'OGIAS est conservée."],
]


def lignes(ouvrage) -> list[list[str]]:
    return [[ouvrage.repere(e), e.libelle, e.type, e.modele, e.uf, e.local, e.ident]
            for e in sorted(ouvrage.equipements, key=ouvrage.repere)]


def exporter(chemin, ouvrage) -> None:
    ecrire_xlsx(chemin, [("Équipements", ENTETES, lignes(ouvrage), [22, 34, 10, 22, 10, 18, 22]),
                         ("Lisez-moi", ["Aller-retour de la liste des équipements"], LISEZ_MOI, [110])])
