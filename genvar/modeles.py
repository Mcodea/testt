"""Référentiel des modèles d'équipement : type de matériel → modèles → lignes d'information.

Les modèles livrés proviennent des classeurs de référence OGIAS V1 fournis par
l'utilisateur. Ils peuvent être complétés dans le brouillon du référentiel.
Chaque ouvrage conserve ses données figées jusqu'à une adoption explicite.

Une ligne d'information : rôle (TS, TC, TM, TR, RTR, CP, DEF, ALA, EVI), libellé, suffixe du mnémonique,
format (BOOL, INT, DINT, REAL), unité, commentaire. Le mnémonique d'un équipement se calcule :
RÔLE + « _ » + repère sans le lieu + « _ » + suffixe (ex. TS_RV11HV01_OUV).
"""
import copy
import json
import os
import re
import shutil
import uuid
from datetime import datetime
from typing import Any

from . import chemins, lexique as _lexique

ROLES = ("TS", "TC", "TM", "TR", "RTR", "CP", "DEF", "ALA", "EVI")
FORMATS = ("BOOL", "INT", "DINT", "REAL")
DOMAINES = ("Électricité", "Hydraulique", "Sûreté", "Automatisme")
RE_SUFFIXE = re.compile(r"^[A-Z0-9]+(_[A-Z0-9]+)*$")

# Désignation et domaine proposés à la création d'un type (modifiables).
TYPES_CONNUS = {
    "PM": ("Groupe de pompage", "Hydraulique"), "HV": ("Vanne manuelle", "Hydraulique"),
    "MV": ("Vanne motorisée", "Hydraulique"), "PV": ("Vanne de régulation", "Hydraulique"),
    "LT": ("Mesure de niveau", "Hydraulique"), "PT": ("Mesure de pression", "Hydraulique"),
    "TT": ("Mesure de température", "Hydraulique"), "FT": ("Mesure de débit", "Hydraulique"),
    "DA": ("Cuve", "Hydraulique"), "LH": ("Détecteur de niveau", "Hydraulique"),
    "AT": ("Analyseur / détecteur de gaz", "Sûreté"), "XT": ("Détecteur TOR", "Sûreté"),
    "CI": ("Centrale (intrusion ou incendie)", "Sûreté"), "EX": ("Extracteur d'air", "Sûreté"),
    "CM": ("Climatisation", "Sûreté"), "OD": ("Onduleur", "Électricité"),
    "A--P": ("Armoire process", "Électricité"), "AP": ("Automate", "Automatisme"),
    "SC": ("Source automate", "Automatisme"), "LI": ("Liaison de communication", "Automatisme"),
    "SY": ("Synthèse", "Automatisme"), "UF": ("Unité fonctionnelle", "Automatisme"),
}


# ====================================================================== codification
def code_type(cod_typ_mat):
    """« PM-- » → « PM » ; « A--P » reste « A--P » (le numéro se place entre A et P)."""
    t = (cod_typ_mat or "").strip().upper()
    return t[:-2] if t.endswith("--") and "--" not in t[:-2] else t


def motif(code):
    """Motif sur 4 positions : « PM » → « PM-- » ; « A--P » → « A--P »."""
    return code if "--" in code else f"{code}--"


def repere_fin(code, numero):
    """4 derniers caractères du repère : PM + 01 → PM01 ; A--P + 01 → A01P."""
    return motif(code).replace("--", numero, 1)


# ====================================================================== lignes
STATUTS_MODELE = ("à valider", "validé", "archivé")   # archivé : conservé, non proposé aux nouveaux équipements


def nouvelle_ligne(role="TS", libelle="", suffixe="", format="BOOL", unite="", commentaire=""):
    return {"id": uuid.uuid4().hex[:8], "role": role, "libelle": libelle, "suffixe": suffixe,
            "format": format, "unite": unite, "commentaire": commentaire}


def verifier_ligne(champs):
    """Normalise et contrôle une ligne ; lève ValueError avec un message clair."""
    l = {k: str(champs.get(k, "") or "").strip() for k in ("role", "libelle", "suffixe", "format", "unite", "commentaire")}
    l["role"], l["suffixe"], l["format"] = l["role"].upper(), l["suffixe"].upper(), (l["format"] or "BOOL").upper()
    if l["role"] not in ROLES:
        raise ValueError(f"Rôle « {l['role']} » inconnu : {', '.join(ROLES)}.")
    if not l["libelle"]:
        raise ValueError("Le libellé de la ligne est obligatoire.")
    if not RE_SUFFIXE.match(l["suffixe"]):
        raise ValueError("Suffixe du mnémonique : lettres majuscules et chiffres, séparés par un « _ » simple (ex. DEF_POS).")
    if l["format"] not in FORMATS:
        raise ValueError(f"Format : {', '.join(FORMATS)}.")
    return l


def lignes_depuis_catalogue(catalogue, code_type_):
    """Lignes de départ issues des signaux du référentiel SOREP (catalogue) du type : TS, TC, TM, TR, RTR, CP."""
    lignes = []
    for s in catalogue.signaux_du_type(code_type_):
        if s["famille"] not in ROLES:
            continue
        fmt = s.get("type_logique", "BOOL")
        fmt = "BOOL" if fmt in ("BOOL", "EBOOL") else (fmt if fmt in FORMATS else "INT")
        lignes.append(nouvelle_ligne(s["famille"], s["information"], s["code"], fmt, s.get("unite", ""),
                                     "Issu du référentiel SOREP du type"))
    return lignes


# ====================================================================== stockage
def vide():
    return {"version": "", "origine": "Référentiel SOREP (construit dans l'outil)", "types": {}, "modeles": {},
            "lexique": [], "dictionnaire_es": [], "correspondances": []}


def fichier_origine():
    """Modèles de départ livrés avec l'outil (à valider par SOREP)."""
    return os.path.join(chemins.dossier_ressources(), "referentiel_modeles.json")


def fichier_utilisateur():
    return os.path.join(chemins.dossier_donnees(), "referentiel_modeles.json")


def charger():
    f = fichier_utilisateur()
    if os.path.isfile(f):
        with open(f, encoding="utf-8") as fh:
            ref = json.load(fh)
        if all("lignes" in m for m in ref.get("modeles", {}).values()):
            return ref
        # ancien format (V0.19, noms repris d'une base tierce) : écarté, conservé en .ancien
        os.replace(f, f + ".ancien")
    o = fichier_origine()
    if os.path.isfile(o):
        with open(o, encoding="utf-8") as fh:
            return json.load(fh)
    return vide()


def enregistrer(ref):
    f = fichier_utilisateur()
    os.makedirs(os.path.dirname(f), exist_ok=True)
    if os.path.isfile(f):
        shutil.copy2(f, f + ".bak")
    ref["version"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    tmp = f + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(ref, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, f)


# ====================================================================== import d'une base (au choix de l'utilisateur)
COLONNES_REQUISES = ("COD_TYP_MAT", "NOM_MODELE", "COD_ROLE")
ROLES_BASE = {"TS": "TS", "TC": "TC", "TM": "TM", "TMC": "TM", "TR": "TR", "RTR": "RTR", "CPT": "CP",
              "DEF": "DEF", "ALA": "ALA", "EVI": "EVI"}
FORMATS_BASE = {"L": "BOOL", "I": "INT", "D": "DINT", "F": "REAL", "E": "INT"}


def _entete(cellule):
    t = str(cellule or "").replace("\r", "\n")
    morceaux = [m.strip() for m in re.split(r"\n| / ", t) if m.strip()]
    return morceaux[-1].upper() if morceaux else ""


def trouver_table(feuilles):
    for nom, lignes in feuilles.items():
        for i, ligne in enumerate(lignes[:15]):
            noms = [_entete(c) for c in ligne]
            if all(c in noms for c in COLONNES_REQUISES):
                return nom, {n: k for k, n in enumerate(noms) if n}, lignes[i + 1:]
    raise ValueError("Aucune feuille avec les colonnes COD_TYP_MAT, NOM_MODELE et COD_ROLE.")


MOTS_VIDES = _lexique.MOTS_VIDES


def _suffixe_propose(libelle, pris, lexique=None, codes=None):
    """Suffixe tiré du libellé, jamais tronqué : code connu du catalogue ou du dictionnaire des E/S, sinon
    abréviations du lexique (genvar/lexique.py). Plus de 12 caractères : voir lexique.alerte."""
    return _lexique.proposer_suffixe(libelle, pris, lexique_livre() if lexique is None else lexique, codes)


def lexique_livre():
    """Lexique du référentiel livré (lecture seule)."""
    try:
        with open(fichier_origine(), encoding="utf-8") as fh:
            return json.load(fh).get("lexique", [])
    except (OSError, ValueError):
        return []


def extraire(feuilles, origine="", renommer=None, lexique=None, catalogue=None):
    """Modèles tirés d'une base de supervision fournie par l'utilisateur, au format SOREP (rôle, libellé, suffixe,
    format). `renommer` : {ancien nom: nouveau nom} pour ne pas reprendre les noms d'origine. Aucune donnée
    d'ouvrage ni numéro de signification n'est repris ; un suffixe absent est proposé à partir du libellé."""
    _, col, lignes = trouver_table(feuilles)
    g = lambda r, c: (str(r[col[c]]).strip() if c in col and col[c] < len(r) else "")
    renommer = renommer or {}
    ref = vide()
    vus = {}
    for r in lignes:
        ancien, typ, role = g(r, "NOM_MODELE"), code_type(g(r, "COD_TYP_MAT")), ROLES_BASE.get(g(r, "COD_ROLE"))
        if not ancien or not typ or not role:
            continue
        nom_modele = renommer.get(ancien, ancien)
        designation, domaine = TYPES_CONNUS.get(typ, ("", ""))
        t = ref["types"].setdefault(typ, {"code": typ, "designation": designation, "domaine": domaine, "modeles": []})
        if nom_modele not in t["modeles"]:
            t["modeles"].append(nom_modele)
        m = ref["modeles"].setdefault(nom_modele, {"nom": nom_modele, "type": typ, "statut": "à valider", "lignes": []})
        eqpt, mnemo = g(r, "COD_EQPT"), g(r, "MNEMO_VAR")
        suffixe = ""
        if eqpt and mnemo:
            x = re.match(rf"^[A-Z0-9]+_{re.escape(eqpt[4:])}_?(.*)$", mnemo)
            suffixe = x.group(1) if x else ""
        libelle = re.sub(rf"^(?:{g(r, 'COD_ROLE')}|{role})\s+", "", g(r, "LIB_SIGNIF")).strip()
        if not libelle:
            continue                                  # élément sans signification : rien d'exploitable
        cle = (nom_modele, role, libelle)
        if cle in vus:
            continue
        pris = {l["suffixe"] for l in m["lignes"] if l["role"] == role}
        commentaire = ""
        if not suffixe or not RE_SUFFIXE.match(suffixe) or suffixe in pris:
            suffixe = _suffixe_propose(libelle, pris, lexique, _lexique.codes_du_catalogue(catalogue, typ))
            commentaire = "; ".join(x for x in ("suffixe proposé à partir du libellé : à vérifier",
                                                _lexique.alerte(suffixe)) if x)
        vus[cle] = True
        m["lignes"].append(nouvelle_ligne(role, libelle.capitalize(), suffixe, FORMATS_BASE.get(g(r, "TYP_VAR"), "BOOL"),
                                          g(r, "COD_UNIT_PHY"), commentaire))
    ref["origine"] = origine
    return ref


def fusionner(actuel, nouveau):
    """Ajoute types et modèles ; un modèle déjà présent n'est jamais écrasé (listé dans « conflits »)."""
    ref = copy.deepcopy(actuel)
    ajoutes, conflits = [], []
    for nom, m in nouveau["modeles"].items():
        if nom in ref["modeles"]:
            conflits.append(nom)
        else:
            ref["modeles"][nom] = m
            ajoutes.append(nom)
    for code, t in nouveau["types"].items():
        cible = ref["types"].setdefault(code, {**t, "modeles": []})
        for nom in t["modeles"]:
            if nom not in cible["modeles"]:
                cible["modeles"].append(nom)
    return ref, ajoutes, conflits


# ===================================================== modèles autonomes (référentiel OGIAS)
def completer_signaux(ref, catalogue):
    """Prépare EN MÉMOIRE le référentiel historique, sans réécrire les fichiers utilisateur.

    Les modèles anciens avaient « lignes » (télétransmission descriptive) mais leurs
    E/S étaient partagées par type. Chaque modèle acquiert une copie indépendante des
    signaux ES/TS/TM/... du type. L'adoption par un ouvrage est EXPLICITE : sa copie
    historique dans modeles_snapshot n'est jamais remplacée lors de l'ouverture.
    """
    for m in ref.get("modeles", {}).values():
        if "signaux" not in m:
            m["signaux"] = copy.deepcopy(catalogue.signaux_du_type(m["type"], avec_ecartes=True))
            m["origine_signaux"] = "copie du catalogue de type, à vérifier"
        # Un signal n'a pas d'adresse, d'échelle ou de facteur d'impulsion dans le modèle.
    return ref


def verifier_signaux_modele(signaux, code_type):
    """Contrôle d'un ensemble complet, sans modifier le modèle ni deviner de liaison."""
    from .catalogue import FAMILLES_CATALOGUE, PRESENCES, TYPES_LOGIQUES, anomalies_interne, sens_incoherent
    erreurs, cles = [], set()
    for s in signaux:
        famille = s.get("famille", "")
        code = s.get("code", "")
        cle = f"{famille}_{code}"
        if famille not in FAMILLES_CATALOGUE:
            erreurs.append(f"Famille inconnue : {famille}.")
        if not RE_SUFFIXE.fullmatch(code):
            erreurs.append(f"Code de signal invalide : {code}.")
        if not s.get("information", "").strip():
            erreurs.append(f"{cle} : libellé obligatoire.")
        if s.get("presence") not in PRESENCES:
            erreurs.append(f"{cle} : présence invalide.")
        if s.get("presence") == "Option" and not s.get("option"):
            erreurs.append(f"{cle} : préciser l'option.")
        if s.get("type_logique") not in TYPES_LOGIQUES:
            erreurs.append(f"{cle} : type logique invalide.")
        if famille == "ES" and s.get("es") not in ("ET", "ST", "EA", "SA"):
            erreurs.append(f"{cle} : point physique ET, ST, EA ou SA obligatoire.")
        if famille == "ES" and s.get("source"):
            erreurs.append(f"{cle} : une E/S physique ne peut pas avoir une E/S source.")
        if s.get("alarme") and famille != "TS":
            erreurs.append(f"{cle} : une alarme doit être une TS.")
        incoherent = sens_incoherent(famille, s.get("es", "Interne"))
        if incoherent:
            erreurs.append(f"{cle} : {incoherent}.")
        if s.get("organe") and s.get("es") != "ET":
            erreurs.append(f"{cle} : sens d'un contact TOR seulement sur ET.")
        for m in anomalies_interne(s):
            erreurs.append(f"{cle} : {m}.")
        if cle in cles:
            erreurs.append(f"{cle} : doublon dans le modèle.")
        cles.add(cle)
    sources = {f"{s['famille']}_{s['code']}": s for s in signaux
               if s.get("famille") == "ES"}
    for s in signaux:
        src = s.get("source", "")
        if src and (src not in sources or
                    sens_incoherent(s.get("famille"), sources[src].get("es"))):
            erreurs.append(f"{s.get('famille')}_{s.get('code')} : source physique {src} absente ou incohérente.")
    return erreurs


def verifier_signal_saisi(champs, code_type):
    """Garde uniquement les métadonnées génériques : jamais de valeur d'installation."""
    champs = dict(champs)
    for interdit in ("adresse", "adresses", "analogique", "impulsion", "signal_min", "signal_max",
                     "phys_min", "phys_max", "brut_min", "brut_max", "poids", "voie", "module"):
        if interdit in champs:
            raise ValueError(f"{interdit} relève du paramétrage dans l'inventaire, pas du modèle.")
    s: dict[str, Any] = {k: str(champs.get(k) or "").strip() for k in
         ("famille", "code", "information", "es", "presence", "option", "type_logique",
          "unite", "source", "logique", "organe", "statut", "remarque")}
    for k in ("famille", "code", "es", "type_logique"):
        s[k] = s[k].upper() if k != "es" or s[k].upper() in ("ET", "ST", "EA", "SA") else s[k]
    s["type"] = code_type
    s["alarme"] = champs.get("alarme") is True
    s["es"] = s["es"] or "Interne"
    s["presence"] = s["presence"] or "Par défaut"
    s["statut"] = s["statut"] or "À valider"
    problemes = verifier_signaux_modele([s], code_type)
    if problemes and not (len(problemes) == 1 and "source physique" in problemes[0]):
        raise ValueError(problemes[0])
    return s
