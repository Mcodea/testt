"""Dictionnaire des codes des E/S physiques (V1-3-11 à V1-3-14).

Objet du référentiel des modèles (clé « dictionnaire_es » de referentiel_modeles.json), à côté du lexique : il est
publié, versionné et archivé avec lui, modifiable dans le brouillon, exporté et importé par Excel.

Une entrée : {"code", "nature" (ET, ST, EA, SA), "categorie", "libelle", "teletransmission", "types": [...]}.
Clé d'une entrée : NATURE.CODE (ex. « ET.NIV »). Un même code peut exister dans deux natures avec le même sens
(NIV en ET « Niveau atteint » et en EA « Niveau ») : la clé tient compte de la nature.

Contrôles :
- erreur : code hors format (2 à 9 caractères, A–Z, 0–9, « _ ») ; nature inconnue ; libellé vide ;
  même NATURE.CODE défini deux fois avec deux libellés (un même code avec deux sens) ;
- alerte : même NATURE.CODE répété à l'identique ; deux codes pour un même libellé ;
  code d'une E/S du catalogue absent du dictionnaire (code non standard) ;
  code nouveau (absent du dictionnaire livré) qui ne fait pas exactement 3 lettres (décision P3).
"""
from __future__ import annotations

import re
from typing import Iterable, Mapping

from .lexique import normaliser

NATURES = ("ET", "ST", "EA", "SA")
RE_CODE = re.compile(r"^[A-Z0-9_]{2,9}$")
RE_TROIS_LETTRES = re.compile(r"^[A-Z]{3}$")


def cle(entree: Mapping) -> str:
    return f"{str(entree.get('nature') or '').upper()}.{str(entree.get('code') or '').upper()}"


def entree(code, nature, libelle="", categorie="", teletransmission="", types=()) -> dict:
    if isinstance(types, str):
        types = [t for t in re.split(r"[;,]", types)]
    return {"code": str(code or "").strip().upper(), "nature": str(nature or "").strip().upper(),
            "categorie": str(categorie or "").strip(), "libelle": str(libelle or "").strip(),
            "teletransmission": str(teletransmission or "").strip().upper(),
            "types": [str(t).strip().upper() for t in types or () if str(t).strip()]}


def controler(dictionnaire) -> tuple[list[str], list[str]]:
    """(erreurs, alertes) propres au dictionnaire."""
    if not isinstance(dictionnaire, list):
        return ["Dictionnaire des E/S : liste d'entrées attendue."], []
    erreurs: list[str] = []
    alertes: list[str] = []
    vus: dict[str, Mapping] = {}
    par_libelle: dict[tuple[str, str], list[str]] = {}
    for n, e in enumerate(dictionnaire, 1):
        if not isinstance(e, dict):
            erreurs.append(f"Dictionnaire des E/S, entrée {n} : objet attendu.")
            continue
        k = cle(e)
        if not RE_CODE.match(str(e.get("code") or "")):
            erreurs.append(f"Dictionnaire des E/S, code « {e.get('code')} » : 2 à 9 caractères, majuscules, "
                           "chiffres et « _ ».")
        if e.get("nature") not in NATURES:
            erreurs.append(f"Dictionnaire des E/S, code {e.get('code')} : nature {', '.join(NATURES)}.")
        if not str(e.get("libelle") or "").strip():
            erreurs.append(f"Dictionnaire des E/S, code {k} : libellé standard obligatoire.")
        if k in vus:
            if normaliser(vus[k].get("libelle")) == normaliser(e.get("libelle")):
                alertes.append(f"Dictionnaire des E/S, code {k} : répété à l'identique.")
            else:
                erreurs.append(f"Dictionnaire des E/S, code {k} : un même code avec deux sens "
                               f"(« {vus[k].get('libelle')} » et « {e.get('libelle')} »).")
            continue
        vus[k] = e
        libelle = normaliser(e.get("libelle"))
        if libelle:
            par_libelle.setdefault((str(e.get("nature")), libelle), []).append(str(e.get("code")))
    for (nature, _), codes in par_libelle.items():
        if len(codes) > 1:
            alertes.append(f"Dictionnaire des E/S ({nature}) : deux codes pour un même libellé : {', '.join(codes)}.")
    return erreurs, alertes


def codes_non_standard(signaux: Iterable[Mapping], dictionnaire: Iterable[Mapping]) -> list[str]:
    """Alertes : codes physiques des E/S du catalogue absents du dictionnaire (un message par code)."""
    from .modele import suffixe_point
    connus = {cle(e) for e in dictionnaire or ()}
    if not connus:
        return []
    manquants: dict[str, list[str]] = {}
    for s in signaux or ():
        if s.get("es") in NATURES:
            k = f"{s['es']}.{suffixe_point(s.get('code', ''), s.get('organe', ''))}"
            if k not in connus and s.get("type") not in manquants.setdefault(k, []):
                manquants[k].append(str(s.get("type")))
    return [f"Code non standard {k} (types {', '.join(sorted(t))}) : absent du dictionnaire des E/S."
            for k, t in sorted(manquants.items()) if t]


def codes_hors_regle_3_lettres(dictionnaire, reference) -> list[str]:
    """Alertes P3 : codes absents du dictionnaire `reference` (livré) qui ne font pas exactement 3 lettres.
    Les codes existants ne sont jamais concernés ; un code composé reste admis si l'information l'exige."""
    connus = {cle(e) for e in reference or () if isinstance(e, dict)}
    vus: set[str] = set()
    alertes = []
    for e in dictionnaire or ():
        if not isinstance(e, dict):
            continue
        k = cle(e)
        if k in connus or k in vus or RE_TROIS_LETTRES.match(str(e.get("code") or "")):
            continue
        vus.add(k)
        alertes.append(f"Dictionnaire des E/S, code {k} : nouveau code hors règle des 3 lettres (décision P3) ; "
                       "admis seulement si l'information exige un code composé.")
    return alertes
