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
# se place entre les segments. Les repères d'un ouvrage sont fabriqués selon la charte copiée de son standard
# (`de_ouvrage`). Un ouvrage à la charte OGIAS (ou antérieur aux standards) garde EXACTEMENT son comportement
# d'avant, formats historiques compris (modele.Ouvrage.prefixe/repere/repere_nom).

CARACTERES = {"lettres": ("A-Z", "lettres"), "chiffres": ("0-9", "chiffres"),
              "lettres_chiffres": ("A-Z0-9", "lettres ou chiffres")}
SEGMENTS_OUVRAGE = {"lieu": "Lieu", "type_ouvrage": "Type d'ouvrage", "numero_ouvrage": "Numéro d'ouvrage",
                    "texte": "Texte fixe"}
SEGMENTS_EQUIPEMENT = {"sous_ensemble": "Sous-ensemble", "equipement": "Code et numéro d'équipement", "texte": "Texte fixe"}
SEPARATEURS = {"": "aucun", "_": "« _ »", "-": "« - »", ".": "« . »"}
LONGUEUR_MAX_REPERE = 32

CHARTE_OGIAS: dict = {
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
    if t == "sous_ensemble":
        # Les sous-ensembles d'OGIAS ont 2 caractères (codes 00, 11, E0…) : format conservé pour toutes les chartes.
        return {"type": t, "longueur": 2, "caracteres": "lettres_chiffres"}
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
        return "00"
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


def est_ogias(c) -> bool:
    """Vrai pour la structure de la charte OGIAS : repères fabriqués comme avant les standards, imports d'inventaire
    disponibles, exports dans leur format connu."""
    return {k: c.get(k) for k in STRUCTURE} == CHARTE_OGIAS


def de_ouvrage(ouvrage) -> dict | None:
    """Charte copiée dans l'ouvrage depuis son standard ; None si l'ouvrage suit la charte OGIAS (ou n'a pas de
    standard) : il garde alors exactement le comportement d'avant."""
    c = ((getattr(ouvrage, "standard", None) or {}).get("briques") or {}).get("charte")
    if not c or "ouvrage" not in c or est_ogias(c):
        return None
    return c


def _valeurs(c, partie: str, ouvrage, eq=None, avec_lieu=True) -> list[str]:
    valeurs = []
    for s in c[partie]:
        t = s["type"]
        if t == "lieu" and not avec_lieu:
            continue
        v = {"texte": s.get("valeur", ""), "lieu": ouvrage.lieu, "type_ouvrage": ouvrage.code_ouvrage,
             "numero_ouvrage": ouvrage.numero_ouvrage,
             "sous_ensemble": getattr(eq, "sous_ensemble", ""),
             "equipement": eq.code_court() if eq is not None else ""}[t]
        if v:
            valeurs.append(v)
    return valeurs


def prefixe(c, ouvrage, avec_lieu=True) -> str:
    """Repère de l'ouvrage selon la charte (segments vides omis : ouvrage pas encore identifié)."""
    return c.get("separateur", "").join(_valeurs(c, "ouvrage", ouvrage, avec_lieu=avec_lieu))


def repere(c, ouvrage, eq, avec_lieu=True) -> str:
    return c.get("separateur", "").join([*_valeurs(c, "ouvrage", ouvrage, avec_lieu=avec_lieu),
                                         *_valeurs(c, "equipement", ouvrage, eq)])


def sous_ensemble_dans_repere(c) -> bool:
    return any(s["type"] == "sous_ensemble" for s in c["equipement"])


# Saisie de l'identification selon la charte. Charte OGIAS : motifs historiques ci-dessus, inchangés. Segment absent
# de la charte : code des listes de l'atelier (1 à 8 lettres majuscules ou chiffres), sans autre contrainte.
CODE_LISTE = r"[A-Z0-9]{1,8}"
CHAMPS = {"lieu": "lieu", "code_ouvrage": "type_ouvrage", "numero_ouvrage": "numero_ouvrage"}


def motif(c, champ: str) -> str:
    """Motif d'un champ d'identification (lieu, code_ouvrage, numero_ouvrage) ; c=None : charte OGIAS."""
    if c is None:
        return {"lieu": LIEU, "code_ouvrage": CODE_OUVRAGE, "numero_ouvrage": NUMERO_OUVRAGE}[champ]
    m = motif_champ(c, CHAMPS[champ])
    return m if m is not None else (r"[0-9]{1,4}" if champ == "numero_ouvrage" else CODE_LISTE)


def consigne(c, champ: str) -> str:
    """Texte de l'attendu pour un champ, pour les messages et l'aide de saisie."""
    if c is None:
        return {"lieu": "4 caractères (lettres majuscules ou chiffres), ex. ATMS",
                "code_ouvrage": "2 lettres majuscules, ex. RV", "numero_ouvrage": "01 à 99"}[champ]
    s = next((x for x in c["ouvrage"] if x["type"] == CHAMPS[champ]), None)
    if s is None:
        return "code de la liste de l'atelier" if champ != "numero_ouvrage" else "1 à 4 chiffres"
    if champ == "numero_ouvrage":
        n = s["longueur"]
        return f"{n} chiffre(s), de {'1'.zfill(n)} à {'9' * n}"
    return f"{s['longueur']} {CARACTERES[s['caracteres']][1]}"


def longueur_numero(c) -> int:
    segments: list = (c or CHARTE_OGIAS)["ouvrage"]
    s = next((x for x in segments if x["type"] == "numero_ouvrage"), None)
    return int(s["longueur"]) if s else 2


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
