"""Profils d'import Excel / CSV enregistrés et réutilisables (cahier V1-5-04).

Un profil retient, pour une nature d'import, quels libellés d'en-tête du fichier d'un client correspondent à quels
champs d'OGIAS : on le décrit une fois, puis chaque fichier de même forme est reconnu sans nouvelle saisie. Un profil
ne remplace pas la reconnaissance automatique, il l'étend ; il ne contient aucune donnée de l'ouvrage, seulement des
libellés de colonnes. L'aperçu avant import reste obligatoire (le profil ne change que la lecture des colonnes).
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone

from . import chemins
from . import modeles_livrables as ml

# Champs que l'on peut associer à une colonne, par nature d'import : (clé, libellé, obligatoire).
CHAMPS = {
    "inventaire": [("repere", "Repère de l'équipement", True), ("type", "Type", False),
                   ("libelle", "Désignation", False), ("modele", "Modèle", False)],
    "equipements_aller_retour": [("repere", "Repère de l'équipement", True), ("type", "Type", False),
                                 ("libelle", "Désignation", False), ("modele", "Modèle", False),
                                 ("uf", "Unité fonctionnelle", False), ("local", "Local", False)],
    "variables_existantes": [("nom", "Nom de la variable", True), ("adresse", "Adresse", False),
                             ("type", "Type", False), ("commentaire", "Commentaire", False)],
    "liste_es_existante": [("nom", "Nom de l'E/S", True), ("equipement", "Équipement", True),
                           ("fonction", "Fonction", True), ("adresse", "Adresse", False),
                           ("commentaire", "Commentaire", False), ("variable_liee", "Variable liée", False)],
}
MAX_PROFILS = 100
MAX_LIBELLE = 80


class ProfilRefuse(ValueError):
    """Profil refusé ou introuvable : le message dit pourquoi."""


def dossier() -> str:
    return os.path.join(chemins.dossier_donnees(), "profils_import")


def _index() -> str:
    return os.path.join(dossier(), "index.json")


def lister(nature: str | None = None) -> list[dict]:
    if not os.path.exists(_index()):
        return []
    with open(_index(), encoding="utf-8") as fh:
        donnees = json.load(fh)
    profils = donnees.get("profils") if isinstance(donnees, dict) else None
    if not isinstance(profils, list):
        raise ProfilRefuse("Index des profils d'import illisible : aucun écrasement effectué.")
    return [p for p in profils if nature is None or p.get("nature") == nature]


def _ecrire(profils: list[dict]) -> None:
    ml._ecrire_atomique(_index(), (json.dumps({"version": 1, "profils": profils}, ensure_ascii=False, indent=1)
                                   + "\n").encode("utf-8"))


def trouver(ident) -> dict | None:
    if not isinstance(ident, str) or not re.fullmatch(r"[0-9a-f]{12}", ident):
        return None
    return next((p for p in lister() if p.get("ident") == ident), None)


def enregistrer(nom, nature, correspondances) -> dict:
    """`correspondances` : {champ: libellé de colonne du fichier du client}. Refus motivés, rien d'écrit sinon."""
    if nature not in CHAMPS:
        raise ProfilRefuse("Nature d'import inconnue.")
    nom = " ".join(str(nom or "").split())
    if not 3 <= len(nom) <= 60:
        raise ProfilRefuse("Nom du profil : 3 à 60 caractères.")
    if not isinstance(correspondances, dict):
        raise ProfilRefuse("Correspondances de colonnes attendues.")
    permis = {c for c, _, _ in CHAMPS[nature]}
    propres: dict[str, str] = {}
    for champ, libelle in correspondances.items():
        if champ not in permis:
            raise ProfilRefuse(f"Champ inconnu pour cette nature : {champ}.")
        libelle = " ".join(str(libelle or "").split())
        if not libelle:
            continue
        if len(libelle) > MAX_LIBELLE:
            raise ProfilRefuse(f"Libellé de colonne trop long ({MAX_LIBELLE} caractères au plus).")
        propres[champ] = libelle
    manquants = [lib for c, lib, obligatoire in CHAMPS[nature] if obligatoire and c not in propres]
    if manquants:
        raise ProfilRefuse("Colonnes obligatoires à associer : " + ", ".join(manquants) + ".")
    libelles = [x.lower() for x in propres.values()]
    if len(set(libelles)) != len(libelles):
        raise ProfilRefuse("Une même colonne ne peut pas servir à deux champs.")
    profils = lister()
    if len(profils) >= MAX_PROFILS:
        raise ProfilRefuse(f"{MAX_PROFILS} profils au plus : supprimez-en avant d'en créer.")
    if any(p["nature"] == nature and p["nom"].lower() == nom.lower() for p in profils):
        raise ProfilRefuse("Un profil de ce nom existe déjà pour cette nature.")
    profil = {"ident": uuid.uuid4().hex[:12], "nom": nom, "nature": nature, "correspondances": propres,
              "cree_le": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _ecrire([*profils, profil])
    return profil


def supprimer(ident) -> None:
    if trouver(ident) is None:
        raise ProfilRefuse("Profil introuvable.")
    _ecrire([p for p in lister() if p["ident"] != ident])
