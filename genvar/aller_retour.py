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


def attributs_colonnes(ouvrage) -> list[dict]:
    """Attributs actifs de l'atelier qui concernent au moins un équipement de l'ouvrage (lot 4)."""
    from . import attributs
    try:
        tous = attributs.lister(actifs_seulement=True)
    except ValueError:
        return []
    types = {e.type for e in ouvrage.equipements}
    return [a for a in tous if not a.get("types") or types & set(a["types"])]


def lignes(ouvrage, colonnes=()) -> list[list[str]]:
    return [[ouvrage.repere(e), e.libelle, e.type, e.modele, e.uf, e.local, e.ident,
             *[(e.attributs or {}).get(a["code"], "") if (not a.get("types") or e.type in a["types"]) else "—"
               for a in colonnes]]
            for e in sorted(ouvrage.equipements, key=ouvrage.repere)]


def exporter(chemin, ouvrage) -> None:
    colonnes = attributs_colonnes(ouvrage)
    entetes = [*ENTETES, *[f"{a['nom']}{' (' + a['unite'] + ')' if a.get('unite') else ''} [{a['code']}]" for a in colonnes]]
    lisez = [*LISEZ_MOI, *([["Colonnes d'attributs : « Nom [CODE] ». « — » = sans objet pour ce type. Valeurs contrôlées "
                             "selon la définition de l'attribut (nombre, liste, Oui / Non)."]] if colonnes else [])]
    ecrire_xlsx(chemin, [("Équipements", entetes, lignes(ouvrage, colonnes), [22, 34, 10, 22, 10, 18, 22, *[18] * len(colonnes)]),
                         ("Lisez-moi", ["Aller-retour de la liste des équipements"], lisez, [110])])
