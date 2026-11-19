"""Charte de nommage de l'ouvrage, en un seul endroit (19/11/2026).

Ces règles étaient répétées dans une dizaine d'endroits (moteur, serveur, référentiel d'identification). Elles sont
regroupées ici SANS changer leur effet : c'est le préalable pour les rendre réglables par maître d'ouvrage, le jour
où une charte réelle d'un autre maître d'ouvrage servira d'exemple (rien n'est supposé d'ici là).

Repère d'un ouvrage : lieu (4) + code d'ouvrage (2) + numéro (2), ex. ATMS RV 01.
"""
from __future__ import annotations

import re

LIEU = r"[A-Z0-9]{4}"                        # lieu : 4 lettres majuscules ou chiffres, ex. ATMS
CODE_OUVRAGE = r"[A-Z]{2}"                   # type d'ouvrage : 2 lettres majuscules, ex. RV
NUMERO_OUVRAGE = r"(?:0[1-9]|[1-9][0-9])"    # numéro : 01 à 99
SOUS_ENSEMBLE = r"[A-Z0-9]{2}"               # sous-ensemble : 2 lettres majuscules ou chiffres
REVISION = r"[A-Z0-9]{1,4}"                  # révision documentaire : 1 à 4 caractères

# Saisie champ par champ (API /api/definir) : plus permissive que le reste, telle qu'elle existait. ÉCART CONNU
# (19/11) : un code d'ouvrage avec chiffres y est accepté, puis signalé par R-OUV-03. Conservé à l'identique.
LIEU_SAISIE = r"[A-Za-z0-9]{4}"
CODE_OUVRAGE_SAISIE = r"[A-Za-z0-9]{2}"


def conforme(motif: str, valeur) -> bool:
    return bool(re.fullmatch(motif, str(valeur or "")))


# --- Chartes réglables par client (19/11, standards d'ingénierie) -------------------------------------------------
# Une charte décrit le repère comme une suite de SEGMENTS. Partie « ouvrage » : lieu, type d'ouvrage, numéro, texte
# fixe, dans l'ordre voulu. Partie « équipement » (après le repère de l'ouvrage) : sous-ensemble éventuel, puis le code
# et le numéro de l'équipement, donnés par le motif du référentiel métier (ex. PM01, A01P). Un séparateur optionnel
# se place entre les segments. Étape 1 : OGIAS enregistre, contrôle et montre l'aperçu ; la fabrication des repères
# n'applique encore QUE la structure de la charte OGIAS (voir `applicable`), rien n'est fabriqué autrement en silence.

CARACTERES = {"lettres": ("A-Z", "lettres"), "chiffres": ("0-9", "chiffres"),
              "lettres_chiffres": ("A-Z0-9", "lettres ou chiffres")}
SEGMENTS_OUVRAGE = {"lieu": "Lieu", "type_ouvrage": "Type d'ouvrage", "numero_ouvrage": "Numéro d'ouvrage",
                    "texte": "Texte fixe"}
SEGMENTS_EQUIPEMENT = {"sous_ensemble": "Sous-ensemble", "equipement": "Code et numéro d'équipement", "texte": "Texte fixe"}
SEPARATEURS = {"": "aucun", "_": "« _ »", "-": "« - »", ".": "« . »"}
LONGUEUR_MAX_REPERE = 32

CHARTE_OGIAS = {
    "ouvrage": [{"type": "lieu", "longueur": 4, "caracteres": "lettres_chiffres"},
                {"type": "type_ouvrage", "longueur": 2, "caracteres": "lettres"},
                {"type": "numero_ouvrage", "longueur": 2}],
    "equipement": [{"type": "equipement"}],
    "separateur": "",
}
STRUCTURE = ("ouvrage", "equipement", "separateur")


def _segment(s, permis: dict, partie: str) -> dict:
    from .session import RegleMetier
    t = (s or {}).get("type")
    if t not in permis:
        raise RegleMetier(f"Segment inconnu dans la partie {partie}.")
    if t == "texte":
        v = str(s.get("valeur") or "").strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{1,8}", v):
            raise RegleMetier("Texte fixe : 1 à 8 lettres majuscules ou chiffres.")
        return {"type": t, "valeur": v}
    if t == "equipement":
        return {"type": t}
    try:
        n = int(s.get("longueur"))
    except (TypeError, ValueError):
        raise RegleMetier(f"{permis[t]} : longueur en nombre entier.") from None
    maxi = 4 if t == "numero_ouvrage" else 8
    if not 1 <= n <= maxi:
        raise RegleMetier(f"{permis[t]} : longueur de 1 à {maxi}.")
    if t == "numero_ouvrage":
        return {"type": t, "longueur": n}
    c = s.get("caracteres")
    if c not in CARACTERES:
        raise RegleMetier(f"{permis[t]} : caractères autorisés à préciser.")
    return {"type": t, "longueur": n, "caracteres": c}


def controler(c) -> dict:
    """Charte contrôlée et normalisée (segments connus, longueurs, unicité), ou RegleMetier."""
    from .session import RegleMetier
    if not isinstance(c, dict):
        raise RegleMetier("Charte de nommage attendue.")
    ouvrage = [_segment(s, SEGMENTS_OUVRAGE, "ouvrage") for s in c.get("ouvrage") or []]
    equipement = [_segment(s, SEGMENTS_EQUIPEMENT, "équipement") for s in c.get("equipement") or []]
    for partie, liste, uniques in (("ouvrage", ouvrage, ("lieu", "type_ouvrage", "numero_ouvrage")),
                                   ("équipement", equipement, ("sous_ensemble", "equipement"))):
        for u in uniques:
            if sum(s["type"] == u for s in liste) > 1:
                raise RegleMetier(f"Partie {partie} : un seul segment « {(SEGMENTS_OUVRAGE | SEGMENTS_EQUIPEMENT)[u]} ».")
    if not any(s["type"] in ("type_ouvrage", "numero_ouvrage") for s in ouvrage):
        raise RegleMetier("Le repère de l'ouvrage doit contenir au moins le type d'ouvrage ou son numéro.")
    if sum(s["type"] == "equipement" for s in equipement) != 1:
        raise RegleMetier("Le repère de l'équipement doit contenir le code et le numéro d'équipement.")
    sep = c.get("separateur", "")
    if sep not in SEPARATEURS:
        raise RegleMetier("Séparateur non pris en charge.")
    normale = {"ouvrage": ouvrage, "equipement": equipement, "separateur": sep}
    if len(exemple(normale)["equipement"]) > LONGUEUR_MAX_REPERE:
        raise RegleMetier(f"Repère d'équipement trop long : {LONGUEUR_MAX_REPERE} caractères au plus.")
    return normale


def _valeur_exemple(s) -> str:
    t = s["type"]
    if t == "texte":
        return s["valeur"]
    if t == "equipement":
        return "PM01"
    if t == "numero_ouvrage":
        return "1".zfill(s["longueur"])
    if t == "sous_ensemble":
        base = "00000000" if s["caracteres"] == "chiffres" else "A0000000"
    else:
        base = {"lieu": "XTSTXTST", "type_ouvrage": "RVRVRVRV"}[t]
        if s["caracteres"] == "chiffres":
            base = "12345678"
    return base[: s["longueur"]]


def exemple(c) -> dict:
    """Repères fictifs d'aperçu (lieu XTST, réservoir RV, pompe PM01) selon la charte."""
    sep = c.get("separateur", "")
    ouvrage = sep.join(_valeur_exemple(s) for s in c["ouvrage"])
    return {"ouvrage": ouvrage, "equipement": sep.join([ouvrage, *(_valeur_exemple(s) for s in c["equipement"])])}


def motif_champ(c, champ: str) -> str | None:
    """Motif de saisie d'un champ d'identification selon la charte (None : champ absent de la charte)."""
    s = next((x for x in c.get("ouvrage", []) if x["type"] == champ), None)
    if s is None:
        return None
    if champ == "numero_ouvrage":
        n = s["longueur"]
        return rf"(?!0{{{n}}})[0-9]{{{n}}}"
    return f"[{CARACTERES[s['caracteres']][0]}]{{{s['longueur']}}}"


def applicable(c) -> bool:
    """Vrai si OGIAS sait déjà fabriquer les repères selon cette charte : c'est le cas de la structure OGIAS."""
    return {k: c.get(k) for k in STRUCTURE} == CHARTE_OGIAS


def decrire(c) -> list[str]:
    def texte(s):
        if s["type"] == "texte":
            return f"texte fixe « {s['valeur']} »"
        if s["type"] == "equipement":
            return "code et numéro d'équipement (référentiel métier)"
        nom = (SEGMENTS_OUVRAGE | SEGMENTS_EQUIPEMENT)[s["type"]].lower()
        if s["type"] == "numero_ouvrage":
            return f"{nom} sur {s['longueur']} chiffre(s)"
        return f"{nom} : {s['longueur']} {CARACTERES[s['caracteres']][1]}"
    return [*(texte(s) for s in c["ouvrage"]), *(texte(s) for s in c["equipement"]),
            f"séparateur : {SEPARATEURS[c.get('separateur', '')]}"]
