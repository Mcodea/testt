"""Copies horodatées de l'ouvrage avant chaque opération lourde (cahier § 7, V1-7-03).

Une copie contient l'état de l'ouvrage **en mémoire** juste avant l'opération (modifications non encore
enregistrées comprises, référentiel figé compris), au format d'un fichier d'ouvrage. Elle est écrite à côté du
fichier de l'ouvrage, sous le nom `<fichier>.avant-<opération>-<AAAAMMJJ-HHMMSS>-<aléa>`, par remplacement
atomique (jamais de copie à moitié écrite). Les copies avant adoption (`genvar.adoption.sauvegarder`) suivent le
même nommage et sont listées avec les autres ; elles ne sont jamais effacées ici. Pour chaque opération de ce
module, les `CONSERVEES` copies les plus récentes sont gardées.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime

CONSERVEES = 10

LIBELLES = {
    "adressage": "Avant l'adressage",
    "implantation": "Avant l'implantation des E/S",
    "materiel": "Avant le remplacement du matériel",
    "inventaire": "Avant l'application de l'inventaire",
    "rapprochement-lot": "Avant la confirmation en lot",
    "import": "Avant l'import",
    "restauration": "Avant la restauration d'une copie",
    "adoption": "Avant l'adoption du référentiel",
    "annulation-adoption": "Avant l'annulation d'une adoption",
}
_NOM = re.compile(r"\.avant-([a-z-]+?)-(\d{8})-(\d{6})-")
_ANCIEN = re.compile(r"\.avant_adressage_(\d{8})_(\d{6})$")    # copies des versions antérieures


def etat(session) -> str:
    """Contenu d'un fichier d'ouvrage pour l'état courant de la session (sans rien modifier)."""
    d = session.ouvrage.vers_dict()
    d["catalogue_snapshot"] = session.catalogue_fige()
    return json.dumps({"format": "ouvrage-genvar", "version": 1, "ouvrage": d}, ensure_ascii=False, indent=1)


def ecrire(chemin_ouvrage: str, operation: str, contenu: str) -> str:
    """Écrit la copie de façon atomique et renvoie son chemin ; OSError si impossible (rien ne reste)."""
    if operation not in LIBELLES:
        raise ValueError(f"Opération inconnue : {operation}")
    dossier = os.path.dirname(os.path.abspath(chemin_ouvrage))
    prefixe = f"{os.path.basename(chemin_ouvrage)}.avant-{operation}-{datetime.now():%Y%m%d-%H%M%S}-"
    fd, cible = tempfile.mkstemp(prefix=prefixe, dir=dossier)       # nom unique réservé
    os.close(fd)
    fd, provisoire = tempfile.mkstemp(prefix=".ogias-copie-", suffix=".tmp", dir=dossier)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as flux:
            flux.write(contenu)
            flux.flush()
            os.fsync(flux.fileno())
        os.replace(provisoire, cible)
    except BaseException:
        for reste in (provisoire, cible):
            try:
                os.unlink(reste)
            except OSError:
                pass
        raise
    _elaguer(chemin_ouvrage, operation)
    return cible


def _elaguer(chemin_ouvrage, operation):
    base = os.path.basename(chemin_ouvrage)
    miennes = [c for c in lister(chemin_ouvrage)
               if c["operation"] == operation and c["nom"].startswith(f"{base}.avant-{operation}-")]
    for c in miennes[CONSERVEES:]:
        try:
            os.remove(os.path.join(os.path.dirname(os.path.abspath(chemin_ouvrage)), c["nom"]))
        except OSError:
            pass


def lister(chemin_ouvrage: str | None) -> list[dict]:
    """Copies de cet ouvrage, la plus récente d'abord : nom, opération, libellé, date, taille."""
    if not chemin_ouvrage:
        return []
    dossier = os.path.dirname(os.path.abspath(chemin_ouvrage))
    base = os.path.basename(chemin_ouvrage)
    try:
        noms = os.listdir(dossier)
    except OSError:
        return []
    resultat = []
    for nom in noms:
        if not nom.startswith(base + ".avant"):
            continue
        reste = nom[len(base):]
        m = _NOM.match(reste)
        if m:
            operation, jour, heure = m.group(1), m.group(2), m.group(3)
        else:
            a = _ANCIEN.match(reste)
            if not a:
                continue
            operation, jour, heure = "adressage", a.group(1), a.group(2)
        chemin = os.path.join(dossier, nom)
        try:
            info = os.stat(chemin)
        except OSError:
            continue
        resultat.append({"nom": nom, "operation": operation,
                         "libelle": LIBELLES.get(operation, "Copie avant " + operation),
                         "le": f"{jour[:4]}-{jour[4:6]}-{jour[6:]} {heure[:2]}:{heure[2:4]}:{heure[4:]}",
                         "taille": info.st_size, "_ordre": (jour + heure, info.st_mtime_ns)})
    resultat.sort(key=lambda c: c.pop("_ordre"), reverse=True)
    return resultat


def resoudre(chemin_ouvrage: str | None, nom) -> str:
    """Chemin d'une copie de CET ouvrage désignée par son nom seul ; ValueError sinon (aucun autre chemin)."""
    if not chemin_ouvrage:
        raise ValueError("Ouvrage non enregistré : aucune copie horodatée.")
    if not isinstance(nom, str) or not nom or os.path.basename(nom) != nom or nom in (".", ".."):
        raise ValueError("Copie inconnue pour cet ouvrage.")
    if nom not in {c["nom"] for c in lister(chemin_ouvrage)}:
        raise ValueError("Copie inconnue pour cet ouvrage.")
    return os.path.join(os.path.dirname(os.path.abspath(chemin_ouvrage)), nom)
