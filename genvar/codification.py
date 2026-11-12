"""Code lieu sur 4 lettres tiré du nom d'une commune (charte de codification ESB / RESO).

Règle (charte, section 2) :
1. Majuscules, accents retirés, tirets et apostrophes remplacés par des espaces.
   On retire les petits mots et les mots génériques d'ouvrage ; « Saint » est conservé.
2. « Consonne suivante » = première consonne après la lettre déjà prise, en sautant H et N,
   sans reprendre une lettre déjà prise dans le mot ; Y compte comme une consonne.
   - 1 mot : initiale + 3 consonnes suivantes ;
   - 2 mots : pour chaque mot, initiale + consonne suivante ;
   - 3 mots ou plus : initiales des 3 premiers mots + consonne suivante du 3e.
3. Secours : si un mot manque de consonnes, on reprend H et N à leur place.
4. Exceptions décidées : écrites dans EXCEPTIONS (nom normalisé → code).

Le code est une PROPOSITION : le registre des lieux décide (unicité, exception notée).
"""
import re
import unicodedata

PETITS_MOTS = {"LE", "LA", "LES", "L", "DE", "DU", "DES", "D", "EN", "SUR", "SOUS", "AU", "AUX", "ET"}
MOTS_GENERIQUES = {"RESERVOIR", "RESERVOIRS", "CHATEAU", "EAU", "STATION", "POMPAGE", "REPRISE", "USINE",
                   "BACHE", "PUITS", "FORAGE", "SURPRESSEUR", "SITE"}
VOYELLES = set("AEIOU")
SAUTEES = set("HN")
# Exceptions validées (charte, section 2) : nom normalisé → code retenu.
EXCEPTIONS = {"CACHAN": "CACH"}


def normaliser(nom):
    """« Le Kremlin-Bicêtre » → « LE KREMLIN BICETRE »."""
    t = unicodedata.normalize("NFKD", str(nom or "")).encode("ascii", "ignore").decode("ascii").upper()
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", t).split())


def mots_significatifs(nom):
    return [m for m in normaliser(nom).split() if m.isalpha() and m not in PETITS_MOTS | MOTS_GENERIQUES]


def _consonnes_suivantes(mot, nombre, avec_h_n=False):
    """Consonnes prises après l'initiale, dans l'ordre, sans reprendre une lettre déjà prise."""
    pris = []
    for lettre in mot[1:]:
        if lettre in VOYELLES or lettre == mot[0] or lettre in pris or (lettre in SAUTEES and not avec_h_n):
            continue
        pris.append(lettre)
        if len(pris) == nombre:
            break
    return pris


def _consonnes(mot, nombre):
    pris = _consonnes_suivantes(mot, nombre)
    if len(pris) < nombre:                                  # règle de secours : H et N repris à leur place
        pris = _consonnes_suivantes(mot, nombre, avec_h_n=True)
    return pris


def code_par_regle(nom):
    """Code obtenu par la seule règle (sans exception). Chaîne vide si la règle ne suffit pas."""
    mots = mots_significatifs(nom)
    if not mots:
        return ""
    if len(mots) == 1:
        lettres = [mots[0][0]] + _consonnes(mots[0], 3)
    elif len(mots) == 2:
        lettres = []
        for m in mots:
            lettres += [m[0]] + _consonnes(m, 1)[:1]
    else:
        lettres = [m[0] for m in mots[:3]] + _consonnes(mots[2], 1)[:1]
    code = "".join(lettres)
    return code if len(code) == 4 else ""


def code_propose(nom):
    """Code proposé pour un lieu : exception validée si elle existe, sinon la règle."""
    return EXCEPTIONS.get(normaliser(nom), "") or code_par_regle(nom)


def variantes(nom, pris=(), nombre=4):
    """Codes libres proches quand le code proposé est déjà pris : dernière lettre remplacée par les
    consonnes suivantes du dernier mot, puis de toutes les consonnes du nom."""
    base = code_propose(nom)
    if len(base) != 4:
        return []
    pris = {str(c).upper() for c in pris}
    mots = mots_significatifs(nom)
    candidats = []
    if mots:
        candidats += _consonnes_suivantes(mots[-1], 26, avec_h_n=True)
    candidats += [l for m in mots for l in m if l not in VOYELLES]
    sortie = []
    for lettre in candidats:
        code = base[:3] + lettre
        if code != base and code not in pris and code not in sortie:
            sortie.append(code)
        if len(sortie) == nombre:
            break
    return sortie


def proposition(nom, pris=()):
    """Proposition complète pour l'interface : code, origine, conflit et variantes libres."""
    pris = {str(c).upper() for c in pris}
    code = code_propose(nom)
    origine = "exception" if normaliser(nom) in EXCEPTIONS else ("règle" if code else "")
    conflit = bool(code) and code in pris
    return {"code": code, "origine": origine, "conflit": conflit,
            "variantes": variantes(nom, pris) if conflit else [],
            "message": ("" if code else "La règle ne donne pas 4 lettres : saisissez le code à la main.")}
