"""Registre léger des ouvrages enregistrés, sans base parallèle.

La source de vérité reste chaque fichier .ouvrage.json ; les métadonnées de l'accueil
sont lues depuis ces fichiers. Les importations et duplications sont non destructives.
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import copy
import hashlib
import re
import shutil
import uuid

from . import chemins
from .modele import Ouvrage


@dataclass
class FicheProjet:
    chemin: str
    repere: str
    libelle: str
    mode: str
    automate: str
    statut: str
    revision: str
    date: str
    archive: bool
    equipements: int
    variables_existantes: int
    erreur: str = ""


def repertoire():
    return Path(chemins.dossier_projets())


def _date(date, chemin):
    try:
        return datetime.fromisoformat(date.replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
    except (AttributeError, ValueError):
        return datetime.fromtimestamp(Path(chemin).stat().st_mtime).strftime("%d/%m/%Y %H:%M")


def fiche(chemin):
    chemin = Path(chemin)
    try:
        o = Ouvrage.ouvrir(str(chemin))
        return FicheProjet(str(chemin), o.prefixe() or chemin.stem, o.libelle or "Sans libellé",
                           o.mode, o.automate, o.statut, o.revision,
                           _date(o.modifie_le or o.cree_le, chemin), o.archive,
                           len(o.equipements), len(o.existantes))
    except Exception as exc:
        return FicheProjet(str(chemin), chemin.stem, "Fichier à vérifier", "—", "—",
                           "Illisible", "—", _date("", chemin), False, 0, 0,
                           f"Lecture impossible : {type(exc).__name__}: {exc}")


def lister(dossier=None):
    dossier = Path(dossier) if dossier else repertoire()
    if not dossier.exists():
        return []
    def ordre(f):
        try:
            return (not bool(f.erreur), Path(f.chemin).stat().st_mtime)
        except OSError:
            return (False, 0)
    return sorted((fiche(p) for p in dossier.glob("*.ouvrage.json") if p.is_file()),
                  key=ordre, reverse=True)


def nom_libre(nom, dossier=None):
    dossier = Path(dossier) if dossier else repertoire()
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", nom.strip())[:70].strip("_-") or "ouvrage"
    p = dossier / f"{base}.ouvrage.json"
    n = 2
    while p.exists():
        p = dossier / f"{base}_{n}.ouvrage.json"
        n += 1
    return p


def dupliquer(chemin):
    source = Ouvrage.ouvrir(chemin)
    copie = copy.deepcopy(source)
    copie.ident_projet = uuid.uuid4().hex
    copie.libelle = (copie.libelle or copie.prefixe()) + " (copie)"
    copie.statut = "Brouillon"
    copie.archive = False
    copie.modifie_le = ""
    for eq in copie.equipements:
        eq.ident = uuid.uuid4().hex[:8]
    # Les identifiants des équipements étant renouvelés, les références des variables importées
    # doivent être remappées (pour ne pas perdre les identifications existantes).
    table = {ancien.ident: nouv.ident for ancien, nouv in zip(source.equipements, copie.equipements)}
    for v in copie.existantes:
        v.ident_eq = table.get(v.ident_eq, "")
    dst = nom_libre(Path(chemin).name.removesuffix(".ouvrage.json") + "_copie")
    copie.enregistrer(str(dst))
    return str(dst)


def archiver(chemin, archive=True):
    o = Ouvrage.ouvrir(chemin)
    if o.archive != archive:
        shutil.copy2(chemin, chemin + ".bak")
        o.archive = archive
        o.enregistrer(chemin)


def importer_dossier(source):
    """Copie les fichiers de projets d'un ancien dossier, sans jamais écraser les originaux.

    Accepte un dossier Projets, Donnees ou une racine de version (Projets sous Donnees).
    """
    src = Path(source).resolve()
    if not src.is_dir():
        raise ValueError("Le dossier source est introuvable.")
    dest = repertoire().resolve()
    if src == dest:
        return []
    candidats = list(src.glob("*.ouvrage.json"))
    for chemin in (src / "Projets", src / "Donnees" / "Projets"):
        if chemin.is_dir():
            candidats.extend(chemin.glob("*.ouvrage.json"))
    # Validation intégrale avant la première copie : pas d'import partiel à cause d'un
    # fichier illisible rencontré au milieu du lot.
    candidats = sorted(set(p for p in candidats if p.is_file()))
    for p in candidats:
        Ouvrage.ouvrir(str(p))
    # Un même projet déjà importé ne doit pas réapparaître à chaque mise à jour.
    identifiants = set()
    empreintes = set()
    for p in dest.glob("*.ouvrage.json"):
        try:
            identifiants.add(Ouvrage.ouvrir(str(p)).ident_projet)
            empreintes.add(hashlib.sha256(p.read_bytes()).digest())
        except Exception:
            pass
    ajoutes = []
    for p in candidats:
        if not p.is_file() or p.resolve().parent == dest:
            continue
        projet = Ouvrage.ouvrir(str(p))
        empreinte = hashlib.sha256(p.read_bytes()).digest()
        if projet.ident_projet in identifiants or empreinte in empreintes:
            continue
        cible = nom_libre(p.name.removesuffix(".ouvrage.json"), dest)
        shutil.copy2(p, cible)
        ajoutes.append(str(cible))
        identifiants.add(projet.ident_projet)
        empreintes.add(empreinte)
    return ajoutes


# ====================================================================== corbeille
NOM_CORBEILLE = "Corbeille"


def corbeille(dossier=None):
    return (Path(dossier) if dossier else repertoire()) / NOM_CORBEILLE


def supprimer(chemin):
    """Retire un ouvrage de « Mes ouvrages » en le déplaçant dans la corbeille du dossier Projets.

    Rien n'est effacé du disque : le fichier (et sa sauvegarde .bak éventuelle) est horodaté puis
    rangé dans Projets/Corbeille, d'où `restaurer` peut le remettre. Retourne le chemin dans la corbeille.
    """
    source = Path(chemin)
    if not source.is_file():
        raise ValueError("Le fichier de l'ouvrage est introuvable.")
    dossier = corbeille(source.parent)
    dossier.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = source.name.removesuffix(".ouvrage.json")
    cible = dossier / f"{base}__{horodatage}.ouvrage.json"
    n = 2
    while cible.exists():
        cible = dossier / f"{base}__{horodatage}_{n}.ouvrage.json"
        n += 1
    shutil.move(str(source), str(cible))
    bak = Path(str(source) + ".bak")
    if bak.is_file():
        shutil.move(str(bak), str(cible) + ".bak")
    return str(cible)


def lister_corbeille(dossier=None):
    return lister(corbeille(dossier))


def restaurer(chemin_corbeille, dossier=None):
    """Remet un ouvrage de la corbeille dans le dossier Projets, sans écraser un fichier existant."""
    source = Path(chemin_corbeille)
    if not source.is_file():
        raise ValueError("Le fichier est introuvable dans la corbeille.")
    dest = Path(dossier) if dossier else source.parent.parent
    base = re.sub(r"__\d{8}-\d{6}(_\d+)?$", "", source.name.removesuffix(".ouvrage.json"))
    cible = nom_libre(base, dest)
    shutil.move(str(source), str(cible))
    bak = Path(str(source) + ".bak")
    if bak.is_file():
        shutil.move(str(bak), str(cible) + ".bak")
    return str(cible)
