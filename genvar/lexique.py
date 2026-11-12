"""Lexique des abréviations du référentiel (V1-3-02, V1-3-03).

Le lexique est un objet du référentiel des modèles (clé « lexique » de referentiel_modeles.json) : il est donc
publié, versionné et archivé avec lui, modifiable dans le brouillon, exporté et importé par Excel.

Une entrée : {"mot": texte source, "abreviation": code, "nature": "Mot" | "Expression", "dictionnaire_es": vrai
si l'abréviation est aussi un code du dictionnaire des E/S}. La clé d'une entrée est son mot normalisé (majuscules, sans accent ni ponctuation).

Proposition d'un suffixe à partir d'un libellé, sans jamais tronquer :
1. code du catalogue ou du dictionnaire des E/S portant exactement ce libellé ;
2. sinon, abréviations du lexique, expressions les plus longues d'abord, mots vides retirés (sauf une lettre
   finale, repère d'un équipement : « API A »), mots inconnus conservés en entier ;
3. un suffixe de plus de 12 caractères reste proposé mais porte l'alerte « suffixe à raccourcir ».
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Mapping

NATURES = ("Mot", "Expression")
LONGUEUR_MAX_SUFFIXE = 12
ALERTE_LONGUEUR = "suffixe à raccourcir"
RE_ABREVIATION = re.compile(r"^[A-Z0-9]+(?:_[A-Z0-9]+)*$")
MOTS_VIDES = frozenset({"DE", "DU", "DES", "LA", "LE", "LES", "EN", "D", "L", "A", "AU", "AUX", "ET", "SUR", "PAR",
                        "POUR"})


def normaliser(texte) -> str:
    """« Défaut d'alimentation 24 V » → « DEFAUT D ALIMENTATION 24 V »."""
    t = unicodedata.normalize("NFKD", str(texte or "").upper())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(m for m in re.split(r"[^A-Z0-9]+", t) if m)


def _oui(valeur) -> bool:
    return valeur is True or str(valeur or "").strip().lower() in ("oui", "o", "x", "1", "vrai", "true")


def entree(mot, abreviation, nature="", dictionnaire_es=False) -> dict:
    """Entrée normalisée ; la nature est déduite du nombre de mots si elle est absente."""
    mot = str(mot or "").strip()
    nature = str(nature or "").strip().capitalize() or ("Expression" if len(normaliser(mot).split()) > 1 else "Mot")
    return {"mot": mot, "abreviation": str(abreviation or "").strip().upper(), "nature": nature,
            "dictionnaire_es": _oui(dictionnaire_es)}


def controler(lexique) -> tuple[list[str], list[str]]:
    """(erreurs, alertes) d'un lexique : entrée vide ou illisible, abréviation invalide, mot en double."""
    erreurs: list[str] = []
    alertes: list[str] = []
    if not isinstance(lexique, list):
        return ["Lexique : liste d'entrées attendue."], []
    vus: dict[str, int] = {}
    for n, e in enumerate(lexique, 1):
        if not isinstance(e, dict):
            erreurs.append(f"Lexique, entrée {n} : objet attendu.")
            continue
        cle = normaliser(e.get("mot"))
        if not cle:
            erreurs.append(f"Lexique, entrée {n} : mot ou expression vide.")
            continue
        if not RE_ABREVIATION.match(str(e.get("abreviation") or "")):
            erreurs.append(f"Lexique « {e.get('mot')} » : abréviation en majuscules et chiffres, séparés par « _ ».")
        if e.get("nature") not in NATURES:
            erreurs.append(f"Lexique « {e.get('mot')} » : nature {' ou '.join(NATURES)}.")
        if cle in vus:
            premiere = lexique[vus[cle] - 1]
            if str(premiere.get("abreviation")) == str(e.get("abreviation")):
                alertes.append(f"Lexique « {e.get('mot')} » : même entrée que l'entrée {vus[cle]}, sans effet.")
            else:
                erreurs.append(f"Lexique « {e.get('mot')} » : deux abréviations pour le même mot "
                               f"(entrée {vus[cle]}).")
        vus.setdefault(cle, n)
        if len(str(e.get("abreviation") or "")) > LONGUEUR_MAX_SUFFIXE:
            alertes.append(f"Lexique « {e.get('mot')} » : abréviation de plus de {LONGUEUR_MAX_SUFFIXE} caractères.")
    return erreurs, alertes


def table(lexique: Iterable[Mapping]) -> dict[tuple[str, ...], str]:
    """{mots normalisés: abréviation} pour la recherche des expressions."""
    sortie: dict[tuple[str, ...], str] = {}
    for e in lexique or ():
        mots = tuple(normaliser(e.get("mot")).split())
        if mots and e.get("abreviation"):
            sortie.setdefault(mots, str(e["abreviation"]).upper())
    return sortie


def abreger(libelle, lexique: Iterable[Mapping] = ()) -> str:
    """Suffixe tiré du libellé par le lexique ; jamais tronqué. Libellé sans mot utile → « INFO »."""
    mots = normaliser(libelle).split()
    tab = table(lexique)
    plus_long = max((len(k) for k in tab), default=1)
    parties, i = [], 0
    while i < len(mots):
        for n in range(min(plus_long, len(mots) - i), 0, -1):
            abreviation = tab.get(tuple(mots[i:i + n]))
            if abreviation:
                parties.append(abreviation)
                i += n
                break
        else:
            if mots[i] not in MOTS_VIDES or i == len(mots) - 1 and len(mots[i]) == 1:   # « API A » : repère
                parties.append(mots[i])
            i += 1
    return "_".join(parties) or "INFO"


def proposer_suffixe(libelle, pris=(), lexique: Iterable[Mapping] = (), codes: Mapping[str, str] | None = None) -> str:
    """Suffixe unique parmi `pris` : code connu pour ce libellé, sinon abréviations du lexique."""
    base = (codes or {}).get(normaliser(libelle)) or abreger(libelle, lexique)
    suffixe, n = base, 2
    while suffixe in pris:
        suffixe, n = f"{base}_{n}", n + 1
    return suffixe


def alerte(suffixe) -> str:
    """« suffixe à raccourcir » au-delà de 12 caractères, sinon chaîne vide."""
    return ALERTE_LONGUEUR if len(str(suffixe or "")) > LONGUEUR_MAX_SUFFIXE else ""


def codes_du_catalogue(catalogue, type_code: str) -> dict[str, str]:
    """{libellé normalisé: code} des signaux du type (catalogue ou dictionnaire des E/S)."""
    sortie: dict[str, str] = {}
    for s in getattr(catalogue, "signaux", None) or []:
        if s.get("type") == type_code and s.get("information") and s.get("code"):
            sortie.setdefault(normaliser(s["information"]), s["code"])
    return sortie
