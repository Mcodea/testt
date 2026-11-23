"""Attributs d'équipement définis par l'utilisateur (lot 4 de la feuille de route du 19/11/2026).

Idée reprise des attributs typés des outils d'ingénierie de données, à la mesure d'OGIAS : l'atelier déclare des
champs (texte, nombre, liste de valeurs, oui / non) pour un ou plusieurs types d'équipement, ou pour tous. Chaque
équipement en porte la valeur (Equipement.attributs). Ces valeurs deviennent des variables des modèles de livrables
(`<#ATTR_CODE#>`) et des colonnes de l'aller-retour Excel.

Règles
- Le code d'un attribut ne change jamais (les modèles et les fichiers l'emploient) ; son type non plus. Le nom, la
  description, l'unité, les types concernés, la valeur par défaut et le caractère obligatoire se modifient.
  Une valeur retirée d'une liste reste lisible sur les équipements qui l'ont, signalée « hors liste » (R-ATT-02).
- Un attribut ne se supprime pas : il s'archive (plus proposé, valeurs conservées).
- Une valeur vide retire la valeur de l'équipement. Un attribut obligatoire sans valeur est signalé (R-ATT-01).
- La valeur par défaut est PROPOSÉE à la saisie, jamais écrite d'office dans un équipement.

Stockage : dossier de données de l'atelier, `attributs_equipements.json`, écriture atomique ; vide au départ.
"""
from __future__ import annotations

import json
import os
import re
import tempfile

from . import chemins

TYPES = {"texte": "Texte", "nombre": "Nombre", "liste": "Liste de valeurs", "oui_non": "Oui / non"}
RE_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,19}")
_cache: dict = {"cle": None, "valeur": []}


class AttributRefuse(ValueError):
    """Saisie contraire à la définition d'un attribut : message affiché tel quel."""


def chemin() -> str:
    return os.path.join(chemins.dossier_donnees(), "attributs_equipements.json")


def lister(actifs_seulement: bool = False) -> list[dict]:
    """Définitions de l'atelier (lecture mise en cache tant que le fichier ne change pas : les contrôles l'appellent
    souvent)."""
    f = chemin()
    try:
        st = os.stat(f)
    except FileNotFoundError:
        return []
    cle = (f, st.st_mtime_ns, st.st_size)
    if _cache["cle"] != cle:
        with open(f, encoding="utf-8") as fh:
            donnees = json.load(fh)
        attributs = donnees.get("attributs") if isinstance(donnees, dict) else None
        if not isinstance(attributs, list):
            raise ValueError("Fichier des attributs d'équipement illisible : aucun écrasement effectué.")
        _cache.update(cle=cle, valeur=attributs)
    liste = [dict(a) for a in _cache["valeur"]]
    return [a for a in liste if not a.get("archive")] if actifs_seulement else liste


def _ecrire(attributs: list[dict]) -> None:
    os.makedirs(os.path.dirname(chemin()), exist_ok=True)
    fd, provisoire = tempfile.mkstemp(prefix=".ogias_attributs_", dir=os.path.dirname(chemin()))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "attributs": attributs}, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(provisoire, chemin())
    finally:
        if os.path.exists(provisoire):
            os.unlink(provisoire)
    _cache["cle"] = None


def trouver(code: str) -> dict | None:
    return next((a for a in lister() if a["code"] == code), None)


def applicables(type_equipement: str, actifs_seulement: bool = True) -> list[dict]:
    return [a for a in lister(actifs_seulement) if not a.get("types") or type_equipement in a["types"]]


def _texte(x, n: int) -> str:
    return " ".join(str(x or "").split())[:n]


def _normaliser_definition(d: dict, ancien: dict | None = None) -> dict:
    nom = _texte(d.get("nom"), 60)
    if len(nom) < 2:
        raise AttributRefuse("Nom de l'attribut : 2 à 60 caractères.")
    type_ = ancien["type"] if ancien else str(d.get("type") or "")
    if type_ not in TYPES:
        raise AttributRefuse("Type d'attribut inconnu (texte, nombre, liste, oui / non).")
    types = sorted({_texte(t, 8).upper() for t in (d.get("types") or []) if _texte(t, 8)})
    valeurs: list[str] = []
    if type_ == "liste":
        valeurs = list(dict.fromkeys(_texte(v, 40) for v in (d.get("valeurs") or []) if _texte(v, 40)))
        if not valeurs:
            raise AttributRefuse("Une liste de valeurs doit en proposer au moins une.")
    out = {"nom": nom, "type": type_, "description": _texte(d.get("description"), 200),
           "unite": _texte(d.get("unite"), 12) if type_ == "nombre" else "", "types": types, "valeurs": valeurs,
           "obligatoire": bool(d.get("obligatoire")), "defaut": ""}
    if str(d.get("defaut") or "").strip():
        out["defaut"] = valider(out, d.get("defaut"))
    return out


def creer(d: dict) -> dict:
    code = str(d.get("code") or "").strip().upper()
    if not RE_CODE.fullmatch(code):
        raise AttributRefuse("Code de l'attribut : une lettre puis lettres, chiffres ou _ (20 au plus), ex. PUISSANCE_KW.")
    attributs = lister()
    if any(a["code"] == code for a in attributs):
        raise AttributRefuse(f"Le code {code} existe déjà.")
    a = {"code": code, **_normaliser_definition(d), "archive": False}
    _ecrire([*attributs, a])
    return a


def modifier(code: str, d: dict) -> dict:
    """Nom, description, unité, types concernés, valeurs de liste, défaut, obligatoire. Code et type inchangés."""
    attributs = lister()
    i = next((k for k, a in enumerate(attributs) if a["code"] == code), None)
    if i is None:
        raise AttributRefuse("Attribut introuvable.")
    ancien = attributs[i]
    attributs[i] = {"code": code, **_normaliser_definition(d, ancien), "archive": ancien.get("archive", False)}
    _ecrire(attributs)
    return attributs[i]


def archiver(code: str, archive: bool = True) -> dict:
    attributs = lister()
    a = next((x for x in attributs if x["code"] == code), None)
    if a is None:
        raise AttributRefuse("Attribut introuvable.")
    a["archive"] = bool(archive)
    _ecrire(attributs)
    return a


def valider(a: dict, valeur) -> str:
    """Valeur normalisée selon la définition (chaîne ; « » = pas de valeur) ou AttributRefuse."""
    v = _texte(valeur, 120)
    if not v:
        return ""
    t = a["type"]
    if t == "nombre":
        try:
            n = float(v.replace(",", ".").replace(" ", ""))
        except ValueError:
            raise AttributRefuse(f"{a['nom']} : un nombre est attendu (ex. 7,5).") from None
        return (str(int(n)) if n.is_integer() else repr(n)).replace(".", ",")
    if t == "oui_non":
        m = {"OUI": "Oui", "O": "Oui", "VRAI": "Oui", "1": "Oui", "YES": "Oui", "NON": "Non", "N": "Non",
             "FAUX": "Non", "0": "Non", "NO": "Non"}.get(v.upper())
        if m is None:
            raise AttributRefuse(f"{a['nom']} : Oui ou Non.")
        return m
    if t == "liste":
        trouve = next((x for x in a.get("valeurs", []) if x.casefold() == v.casefold()), None)
        if trouve is None:
            raise AttributRefuse(f"{a['nom']} : valeur hors liste (« {v} ») ; valeurs : {', '.join(a.get('valeurs', []))}.")
        return trouve
    return v


def manquants(eq) -> list[dict]:
    """Attributs obligatoires actifs, applicables au type de l'équipement, sans valeur."""
    valeurs = getattr(eq, "attributs", None) or {}
    return [a for a in applicables(eq.type) if a.get("obligatoire") and not valeurs.get(a["code"])]


def hors_liste(eq) -> list[str]:
    """Valeurs d'attribut liste qui ne figurent plus dans la liste (valeur conservée, signalée)."""
    sortie = []
    for code, v in (getattr(eq, "attributs", None) or {}).items():
        a = trouver(code)
        if a and a["type"] == "liste" and v and v not in a.get("valeurs", []):
            sortie.append(f"{a['nom']} : « {v} »")
    return sortie
