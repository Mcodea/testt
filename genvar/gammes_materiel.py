"""Gammes de matériel déclarées par l'atelier (22/11/2026 : chaque client a un automate différent, OGIAS est ouvert).

Le catalogue livré ne décrit que Schneider (M340, M580, Advantys STB) et SOFREL S4W. Pour tout autre automate,
l'atelier DÉCLARE une fois la gamme : le texte qui la reconnaît dans le champ « Automate » de la fiche de l'ouvrage,
ses racks (nombre d'emplacements), les emplacements pris par le processeur, ses cartes d'E/S (référence, nature,
nombre de voies), la carte retenue par défaut pour chaque nature, et facultativement processeurs et alimentations.

OGIAS calcule alors la proposition de racks et de cartes, la nomenclature et les contrôles de cohérence de cette
gamme exactement comme pour une gamme livrée : la gamme est convertie dans la structure du catalogue livré
(`materiel_schneider.json`), sans code propre à un constructeur.

Règles
- Rien n'est deviné : les références sont celles déclarées, avec le statut « déclarée par l'atelier, à vérifier ».
- Une gamme ne peut pas reprendre un texte de reconnaissance d'une gamme livrée ni d'une autre gamme déclarée : un
  automate est toujours reconnu sans ambiguïté.
- Modifier ou supprimer une gamme ne touche aucun ouvrage : les cartes déjà retenues restent dans les ouvrages.

Stockage : `gammes_materiel/index.json` dans le dossier de données de l'atelier, écriture atomique.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid

from . import chemins

NATURES = ("ET", "ST", "EA", "SA")
CODES_LIVRES = ("M340", "M580", "STB", "S4W", "NONDECRITE")
STATUT = "Gamme déclarée par l'atelier : références et capacités à vérifier sur la documentation du constructeur."
RE_CODE = re.compile(r"[A-Z0-9][A-Z0-9_-]{1,11}")


class GammeRefusee(ValueError):
    """Déclaration incohérente : le message s'affiche tel quel."""


def _compact(texte) -> str:
    return re.sub(r"\s+", "", str(texte or "")).upper()


def _texte(v, maxi) -> str:
    return " ".join(str(v if v is not None else "").split())[:maxi]


# --------------------------------------------------------------------------------------------- stockage
def _index() -> str:
    return os.path.join(chemins.dossier_donnees(), "gammes_materiel", "index.json")


def lister() -> list[dict]:
    try:
        with open(_index(), encoding="utf-8") as fh:
            donnees = json.load(fh)
    except FileNotFoundError:
        return []
    gammes = donnees.get("gammes") if isinstance(donnees, dict) else None
    if not isinstance(gammes, list):
        raise ValueError("Index des gammes de matériel illisible : aucun écrasement effectué.")
    return gammes


def _ecrire(gammes: list[dict]) -> None:
    from .modeles_livrables import _ecrire_atomique
    _ecrire_atomique(_index(), (json.dumps({"version": 1, "gammes": gammes}, ensure_ascii=False, indent=1)
                                + "\n").encode("utf-8"))


def trouver(ident: str) -> dict | None:
    return next((g for g in lister() if g.get("ident") == ident), None)


def par_code(code: str) -> dict | None:
    try:
        return next((g for g in lister() if g.get("code") == code), None)
    except ValueError:
        return None


# --------------------------------------------------------------------------------------------- reconnaissance
def reconnaitre(automate: str) -> dict | None:
    """Gamme déclarée dont un texte de reconnaissance figure dans le champ Automate (espaces et casse ignorés)."""
    a = _compact(automate)
    if not a:
        return None
    try:
        gammes = lister()
    except ValueError:
        return None
    return next((g for g in gammes if any(m in a for m in g.get("motifs", []))), None)


# --------------------------------------------------------------------------------------------- contrôle
def controler(brut: dict, ident_modifie: str = "") -> dict:
    """Déclaration contrôlée et normalisée ; lève GammeRefusee avec un message précis."""
    from . import materiel
    code = _compact(brut.get("code"))
    if not RE_CODE.fullmatch(code) or code in CODES_LIVRES:
        raise GammeRefusee("Code de la gamme : 2 à 12 caractères (lettres majuscules, chiffres, - ou _), différent "
                           "des gammes livrées (M340, M580, STB, S4W). Ex. S7-1500.")
    nom = _texte(brut.get("nom"), 60)
    if len(nom) < 3:
        raise GammeRefusee("Nom de la gamme : 3 caractères au moins (ex. Siemens S7-1500).")
    constructeur = _texte(brut.get("constructeur"), 40)
    if len(constructeur) < 2:
        raise GammeRefusee("Constructeur : 2 caractères au moins.")
    motifs = list(dict.fromkeys(_compact(m) for m in (brut.get("motifs") or []) if _compact(m)))
    if not motifs or any(len(m) < 3 for m in motifs):
        raise GammeRefusee("Texte de reconnaissance : au moins un, de 3 caractères ou plus (ex. S7-1500), tel qu'il "
                           "figure dans le champ Automate des ouvrages.")
    for m in motifs:
        livree = materiel.gamme_livree(m)
        if livree:
            raise GammeRefusee(f"Le texte « {m} » est déjà reconnu comme la gamme livrée {livree}.")
    autres = [g for g in lister() if g.get("ident") != ident_modifie]
    for g in autres:
        if g["code"] == code:
            raise GammeRefusee(f"Une gamme porte déjà le code {code}.")
        commun = [m for m in motifs if any(m in x or x in m for x in g.get("motifs", []))]
        if commun:
            raise GammeRefusee(f"Le texte « {commun[0]} » recoupe celui de la gamme {g['code']} : un automate doit "
                               "être reconnu sans ambiguïté.")
    try:
        cpu = int(brut.get("emplacements_cpu", 1))
    except (TypeError, ValueError):
        raise GammeRefusee("Emplacements du processeur : nombre entier.") from None
    if not 0 <= cpu <= 4:
        raise GammeRefusee("Emplacements pris par le processeur dans le rack local : de 0 à 4.")
    racks = []
    for r in brut.get("racks") or []:
        ref = _texte(r.get("reference"), 40)
        try:
            positions = int(r.get("positions"))
        except (TypeError, ValueError):
            raise GammeRefusee(f"Rack « {ref} » : nombre d'emplacements entier.") from None
        if not ref or not cpu < positions <= 64:
            raise GammeRefusee(f"Rack « {ref or '?'} » : référence et emplacements (plus que le processeur, 64 au "
                               "plus) requis.")
        racks.append({"reference": ref, "positions": positions})
    if not racks:
        raise GammeRefusee("Déclarez au moins un rack (ou châssis, ou embase) avec son nombre d'emplacements.")
    cartes, vues = [], set()
    for c in brut.get("cartes") or []:
        ref = _texte(c.get("reference"), 40)
        nature = str(c.get("nature") or "").strip().upper()
        try:
            voies = int(c.get("voies"))
        except (TypeError, ValueError):
            raise GammeRefusee(f"Carte « {ref} » : nombre de voies entier.") from None
        if not ref or nature not in NATURES or not 1 <= voies <= 128:
            raise GammeRefusee(f"Carte « {ref or '?'} » : référence, nature (ET, ST, EA, SA) et 1 à 128 voies requises.")
        if _compact(ref) in vues:
            raise GammeRefusee(f"Carte « {ref} » déclarée deux fois.")
        vues.add(_compact(ref))
        cartes.append({"reference": ref, "nature": nature, "voies": voies,
                       "description": _texte(c.get("description"), 80)})
    if not cartes:
        raise GammeRefusee("Déclarez au moins une carte d'E/S.")
    defaut = {}
    for n, ref in (brut.get("defaut") or {}).items():
        if n not in NATURES or not ref:
            continue
        carte = next((c for c in cartes if _compact(c["reference"]) == _compact(ref)), None)
        if carte is None or carte["nature"] != n:
            raise GammeRefusee(f"Carte par défaut {n} « {ref} » : absente des cartes déclarées ou d'une autre nature.")
        defaut[n] = carte["reference"]
    for n in NATURES:                    # une seule carte d'une nature : elle est la carte par défaut
        candidates = [c["reference"] for c in cartes if c["nature"] == n]
        if n not in defaut and len(candidates) == 1:
            defaut[n] = candidates[0]
        elif n not in defaut and candidates:
            raise GammeRefusee(f"Plusieurs cartes {n} déclarées : choisissez celle retenue par défaut.")

    def simples(cle):
        return [{"reference": _texte(x.get("reference"), 40), "description": _texte(x.get("description"), 80)}
                for x in brut.get(cle) or [] if _texte(x.get("reference"), 40)]
    return {"code": code, "nom": nom, "constructeur": constructeur, "motifs": motifs, "emplacements_cpu": cpu,
            "racks": sorted(racks, key=lambda r: r["positions"]), "cartes": cartes, "defaut": defaut,
            "processeurs": simples("processeurs"), "alimentations": simples("alimentations"),
            "remarque": _texte(brut.get("remarque"), 300)}


def enregistrer(brut: dict, ident: str = "") -> dict:
    gammes = lister()
    g = controler(brut, ident)
    if ident:
        ancienne = next((x for x in gammes if x["ident"] == ident), None)
        if ancienne is None:
            raise GammeRefusee("Gamme introuvable.")
        ancienne.update(g)
        ancienne["modifiee_le"] = time.strftime("%d/%m/%Y %H:%M")
        g = ancienne
    else:
        g.update({"ident": uuid.uuid4().hex[:12], "cree_le": time.strftime("%d/%m/%Y %H:%M")})
        gammes.append(g)
    _ecrire(gammes)
    _vider_cache()
    return g


def supprimer(ident: str) -> None:
    gammes = lister()
    if not any(g["ident"] == ident for g in gammes):
        raise GammeRefusee("Gamme introuvable.")
    _ecrire([g for g in gammes if g["ident"] != ident])
    _vider_cache()


def _vider_cache() -> None:
    from . import materiel
    for cle in [k for k in materiel._CACHE if k.startswith("atelier:")]:
        materiel._CACHE.pop(cle, None)


# --------------------------------------------------------------------------------------------- catalogue
def catalogue(code: str) -> dict:
    """Catalogue de la gamme déclarée, dans la structure du catalogue livré (lu par le calcul du matériel)."""
    g = par_code(code)
    if g is None:
        from .materiel import CatalogueMaterielErreur
        raise CatalogueMaterielErreur(f"Gamme {code} introuvable dans les gammes déclarées par l'atelier.")
    cartes = [{**c, "source": "déclarée par l'atelier"} for c in g["cartes"]]
    return {
        "statut": STATUT, "cartes": cartes,
        "profils": {"atelier": {"libelle": "Cartes par défaut de la gamme", **g["defaut"]}},
        "profil_defaut": "atelier",
        "plateformes": {code: {"racks": g["racks"], "positions_cpu": list(range(g["emplacements_cpu"]))}},
        "cartes_speciales": [], "remarque_speciales": "",
        "alimentations": [{"reference": a["reference"], "description": a["description"] or "Alimentation"}
                          for a in g["alimentations"]],
        "processeurs": {code: [{"reference": p["reference"], "description": p["description"] or "Processeur"}
                               for p in g["processeurs"]]},
        "communication": {code: []},
        "extension": {"regle": "liaison d'extension selon la documentation du constructeur."},
        "_cartes": {c["reference"]: c for c in cartes}, "_atelier": True, "_constructeur": g["constructeur"],
    }


def resume(g: dict) -> dict:
    par_nature = {n: sum(1 for c in g["cartes"] if c["nature"] == n) for n in NATURES}
    return {**g, "statut": STATUT, "cartes_par_nature": par_nature}
