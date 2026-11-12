"""Référentiels contrôlés pour la fiche ouvrage de l'interface web.

Le fichier utilisateur est distinct des ouvrages et des modèles de signaux.
La livraison ne contient aucun lieu ni ouvrage réel prérempli.
Les valeurs existantes des anciens ouvrages ne sont jamais modifiées par la gestion des listes.
"""
import json
import os
import re
import tempfile
from copy import deepcopy

from genvar import chemins
from genvar.session import RegleMetier

# Registre initial des lieux : les 15 communes ESB / RESO, codes obtenus par la règle de la
# charte de codification (genvar/codification.py), validés le 9 novembre 2026 ; CACH = exception.
# Il s'agit de lieux possibles, et NON de projets ou ouvrages précréés.
COMMUNES_DEFAUT = [
    {"code": "ARCL", "libelle": "Arcueil", "regie": "ESB"},
    {"code": "ATMS", "libelle": "Athis-Mons", "regie": "ESB"},
    {"code": "CACH", "libelle": "Cachan", "regie": "ESB"},
    {"code": "CVLR", "libelle": "Chevilly-Larue", "regie": "ESB"},
    {"code": "FRSN", "libelle": "Fresnes", "regie": "ESB"},
    {"code": "GTLY", "libelle": "Gentilly", "regie": "ESB"},
    {"code": "IVSN", "libelle": "Ivry-sur-Seine", "regie": "ESB"},
    {"code": "KRBC", "libelle": "Le Kremlin-Bicêtre", "regie": "ESB"},
    {"code": "ORLY", "libelle": "Orly", "regie": "ESB"},
    {"code": "VLJF", "libelle": "Villejuif", "regie": "ESB"},
    {"code": "VTSN", "libelle": "Vitry-sur-Seine", "regie": "ESB"},
    {"code": "MRGS", "libelle": "Morangis", "regie": "RESO"},
    {"code": "PVPS", "libelle": "Paray-Vieille-Poste", "regie": "RESO"},
    {"code": "SVOR", "libelle": "Savigny-sur-Orge", "regie": "RESO"},
    {"code": "VSGR", "libelle": "Villeneuve-Saint-Georges", "regie": "RESO"},
]
# Codes proposés par la version précédente (6 novembre), remplacés par la charte s'ils ne sont
# utilisés par aucun ouvrage enregistré.
ANCIENS_CODES = {"ARCU": "ARCL", "ATHM": "ATMS", "CHEV": "CVLR", "FRES": "FRSN", "GENT": "GTLY",
                 "IVRY": "IVSN", "KREM": "KRBC", "VJUI": "VLJF", "VITR": "VTSN", "MORG": "MRGS",
                 "PARV": "PVPS", "SAVI": "SVOR", "VSGE": "VSGR"}
VERSION = 3

# Abréviations génériques d'ouvrages d'eau potable (modifiables par l'utilisateur).
TYPES_DEFAUT = [
    {"code": "RV", "libelle": "Réservoir"},
    {"code": "SP", "libelle": "Station de pompage"},
    {"code": "SR", "libelle": "Station de relevage"},
    {"code": "SS", "libelle": "Station de surpression"},
    {"code": "CV", "libelle": "Chambre de vannes"},
    {"code": "RP", "libelle": "Régulation de pression"},
    {"code": "PC", "libelle": "Poste de comptage"},
    {"code": "ST", "libelle": "Station de traitement"},
    {"code": "CL", "libelle": "Poste de chloration"},
    {"code": "QT", "libelle": "Poste de contrôle qualité"},
]
DEFAUT = {
    "version": VERSION,
    "lieux": COMMUNES_DEFAUT,
    "types_ouvrage": TYPES_DEFAUT,
    "automates": ["M580", "M340", "TSX", "SOFREL S4W"],
    "protocoles": ["Modbus TCP", "SOFREL S4W", "OPC UA", "OPC DA"],
}
GROUPES = ("lieux", "types_ouvrage", "automates", "protocoles")


def chemin():
    return os.path.join(chemins.dossier_donnees(), "referentiel_identification.json")


def lire():
    fichier = chemin()
    if not os.path.exists(fichier):
        return deepcopy(DEFAUT)
    try:
        with open(fichier, encoding="utf-8") as f:
            valeurs = json.load(f)
        if not isinstance(valeurs, dict):
            raise ValueError("Le document doit contenir un objet JSON.")
        # Conserver les valeurs enregistrées, ne jamais les remplacer par des valeurs par défaut.
        resultat = deepcopy(DEFAUT)
        for groupe in GROUPES:
            if groupe in valeurs:
                if not isinstance(valeurs[groupe], list):
                    raise ValueError(f"La liste {groupe} est invalide.")
                resultat[groupe] = valeurs[groupe]
        # Une seule migration additive des installations de l'ancienne V0.22 :
        # ne pas écraser les codes ou libellés déjà créés, ni recréer à chaque
        # démarrage une commune que l'utilisateur aura ensuite retirée.
        if valeurs.get("version", 1) < 2:
            codes = {str(x.get("code", "")).casefold() for x in resultat["lieux"] if isinstance(x, dict)}
            noms = {str(x.get("libelle", "")).casefold() for x in resultat["lieux"] if isinstance(x, dict)}
            for ville in COMMUNES_DEFAUT:
                if ville["code"].casefold() not in codes and ville["libelle"].casefold() not in noms:
                    resultat["lieux"].append(deepcopy(ville))
                    codes.add(ville["code"].casefold())
                    noms.add(ville["libelle"].casefold())
            resultat["version"] = 2
        if valeurs.get("version", 1) < VERSION:
            resultat["remplaces"] = _migrer_codes_charte(resultat["lieux"])
            resultat["version"] = VERSION
            ecrire({k: v for k, v in resultat.items() if k != "remplaces"})
        return resultat
    except (OSError, ValueError, TypeError) as exc:
        raise RegleMetier(f"Référentiel d'identification illisible : {exc}. Aucun écrasement effectué.") from exc


def codes_utilises():
    """Codes lieu portés par des ouvrages enregistrés (brouillons et archivés compris).
    None si le dossier des projets ne peut pas être lu : la migration ne remplace alors rien."""
    try:
        from genvar import projets
        return {str(p.repere)[:4].upper() for p in projets.lister() if p.repere}
    except Exception:                                          # noqa: BLE001 — la migration reste prudente
        return None


def _migrer_codes_charte(lieux):
    """Remplace les codes proposés le 6 novembre par ceux de la charte, seulement pour une
    commune de la liste initiale, avec son libellé d'origine, et si aucun ouvrage n'utilise l'ancien
    code. Rien n'est remplacé si l'utilisation des codes ne peut pas être vérifiée."""
    utilises = codes_utilises()
    if utilises is None:
        return []
    libelles = {c["libelle"].casefold(): c for c in COMMUNES_DEFAUT}
    codes = {str(x.get("code", "")).upper() for x in lieux if isinstance(x, dict)}
    remplaces = []
    for x in lieux:
        if not isinstance(x, dict):
            continue
        ancien = str(x.get("code", "")).upper()
        cible = ANCIENS_CODES.get(ancien)
        ref = libelles.get(str(x.get("libelle", "")).casefold())
        if cible and ref and ref["code"] == cible and ancien not in utilises and cible not in codes:
            x["code"] = cible
            codes.discard(ancien)
            codes.add(cible)
            remplaces.append((ancien, cible))
    return remplaces


def ecrire(valeurs):
    dossier = os.path.dirname(chemin())
    os.makedirs(dossier, exist_ok=True)
    fd, provisoire = tempfile.mkstemp(prefix=".sorep_ident_", suffix=".json", dir=dossier)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(valeurs, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(provisoire, chemin())
    finally:
        if os.path.exists(provisoire):
            os.unlink(provisoire)


def _valider(groupe, code, libelle=""):
    code = str(code or "").strip().upper() if groupe in ("lieux", "types_ouvrage") else str(code or "").strip()
    libelle = str(libelle or "").strip()
    if groupe == "lieux":
        if not re.fullmatch(r"[A-Z0-9]{4}", code):
            raise RegleMetier("Un code de lieu doit contenir 4 caractères alphanumériques.")
        if not libelle or len(libelle) > 100:
            raise RegleMetier("Le lieu doit avoir un libellé de 1 à 100 caractères.")
    elif groupe == "types_ouvrage":
        if not re.fullmatch(r"[A-Z]{2}", code):
            raise RegleMetier("Un code d'ouvrage doit contenir exactement 2 lettres majuscules.")
        if not libelle or len(libelle) > 100:
            raise RegleMetier("Le type d'ouvrage doit avoir un libellé de 1 à 100 caractères.")
    else:
        if not code or len(code) > 100 or any(c in code for c in "\r\n\t,;"):
            raise RegleMetier("Valeur non valide (1 à 100 caractères, sans virgule ni séparateur).")
    return code, libelle


def modifier(action, groupe, code="", libelle="", ancien="", regie=""):
    if groupe not in GROUPES:
        raise RegleMetier("Liste inconnue.")
    if action not in ("ajouter", "modifier", "supprimer"):
        raise RegleMetier("Action inconnue.")
    valeurs = lire()
    liste = valeurs[groupe]
    if groupe == "lieux":
        regie = str(regie or "Autre").strip().upper()
        if regie not in ("ESB", "RESO", "AUTRE"):
            raise RegleMetier("La régie du lieu doit être ESB, RESO ou Autre.")
    anciens_codes = [(x["code"] if isinstance(x, dict) else x) for x in liste]
    if action == "ajouter":
        code, libelle = _valider(groupe, code, libelle)
        if groupe == "types_ouvrage" and any(x["libelle"].casefold() == libelle.casefold() for x in liste):
            raise RegleMetier("Ce type d'ouvrage existe déjà sous un autre code.")
        if groupe == "lieux" and any(x["libelle"].casefold() == libelle.casefold() for x in liste):
            raise RegleMetier("Cette commune existe déjà sous un autre code.")
        if code.casefold() in [x.casefold() for x in anciens_codes]:
            raise RegleMetier("Cette valeur existe déjà dans le référentiel.")
        liste.append({"code": code, "libelle": libelle, "regie": regie} if groupe == "lieux"
                     else {"code": code, "libelle": libelle} if groupe == "types_ouvrage" else code)
    else:
        if not ancien:
            raise RegleMetier("Valeur d'origine manquante.")
        try:
            index = anciens_codes.index(ancien)
        except ValueError as exc:
            raise RegleMetier("Entrée introuvable dans le référentiel.") from exc
        if action == "supprimer":
            del liste[index]
        else:
            code, libelle = _valider(groupe, code, libelle)
            if groupe == "types_ouvrage" and any(x["libelle"].casefold() == libelle.casefold() for j, x in enumerate(liste) if j != index):
                raise RegleMetier("Ce type d'ouvrage existe déjà sous un autre code.")
            if groupe == "lieux" and any(x["libelle"].casefold() == libelle.casefold() for j, x in enumerate(liste) if j != index):
                raise RegleMetier("Cette commune existe déjà sous un autre code.")
            if code != ancien and code.casefold() in [v.casefold() for j, v in enumerate(anciens_codes) if j != index]:
                raise RegleMetier("Cette valeur existe déjà dans le référentiel.")
            liste[index] = ({"code": code, "libelle": libelle, "regie": regie} if groupe == "lieux"
                            else {"code": code, "libelle": libelle} if groupe == "types_ouvrage" else code)
    ecrire(valeurs)
    return valeurs


def type_par_code(code):
    return next((x for x in lire()["types_ouvrage"] if x["code"] == code), None)
