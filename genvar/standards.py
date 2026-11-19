"""Standards d'ingénierie (19/11/2026) : à la création d'un ouvrage, on choisit le standard du client.

Un standard est un ASSEMBLAGE NOMMÉ de briques indépendantes, une par famille :
- référentiel métier : types d'équipements, signaux, règles (bibliothèque existante, versionnée et publiée) ;
- charte de nommage : lieu, code d'ouvrage, repère (une seule pour l'instant : celle d'OGIAS, genvar/charte.py) ;
- plan d'adressage : plages %MW par famille, décalage Modbus ;
- chaîne d'outils : supervision, IHM (l'automate reste choisi par ouvrage : il dépend du site).
Plusieurs clients peuvent partager une brique ; un réglage vient toujours d'une brique identifiée.

À la création, l'ouvrage COPIE les réglages du standard et garde sa référence (nom, version) : un ouvrage déjà créé
n'est jamais modifié quand le standard évolue (décision du 19/11) ; OGIAS signale l'écart.

Étape 1 : le « Standard initial », qui reproduit exactement le comportement d'OGIAS d'avant les standards.
Étape 2 : bibliothèques de plans d'adressage et de chaînes d'outils ; création d'un standard en choisissant une brique
par famille ; nouvelle version d'un standard (motif tracé) ; archivage ; application d'un standard à un ouvrage
existant, après aperçu et confirmation. Une brique ne se modifie pas : on en crée une autre, pour que rien ne change
en silence. Les chartes viendront quand une charte réelle d'un autre maître d'ouvrage servira d'exemple.
"""
from __future__ import annotations

import copy
import re
import unicodedata
import json
import os
import tempfile
import time

from . import charte, chemins
from .modele import ORDRE_ZONES, PLAN_DEFAUT
from .session import RegleMetier, alertes_plages, controler_decalage, controler_plages

VERSION_FICHIER = 2
IDENT_INITIAL = "standard-initial"
STATUTS = ("actif", "archivé")

FAMILLES = {"referentiel": "Référentiel métier", "charte": "Charte de nommage", "adressage": "Plan d'adressage",
            "outils": "Chaîne d'outils"}
# Familles qui ont une bibliothèque de briques (étape 2 ; chartes de nommage le 19/11). Référentiel métier : une seule
# brique, la bibliothèque versionnée existante.
CHOISISSABLES = ("charte", "adressage", "outils")
BRIQUES_FIXES = {
    "referentiel": {"ident": "referentiel-atelier", "nom": "Référentiel publié de l'atelier", "source": "atelier"},
}
NOMS_BRIQUE = {"charte": "charte de nommage", "adressage": "plan d'adressage", "outils": "chaîne d'outils"}


def _briques_initiales() -> dict:
    return {
        "charte": {"ident": "charte-ogias", "nom": "Charte OGIAS (lieu 4, type 2, numéro 2)", **copy.deepcopy(charte.CHARTE_OGIAS)},
        "adressage": {"ident": "adressage-defaut", "nom": "Plan mémoire par défaut",
                      "plages": {f: list(PLAN_DEFAUT[f]) for f in ORDRE_ZONES}, "decalage_modbus": 0},
        "outils": {"ident": "outils-topkapi", "nom": "Supervision TOPKAPI", "supervision": "TOPKAPI", "ihm": ""},
    }


def standard_initial() -> dict:
    """Le comportement d'OGIAS avant les standards, décrit comme un assemblage de briques."""
    return {
        "ident": IDENT_INITIAL, "nom": "Standard initial", "version": 1, "statut": "actif",
        "description": "Réglages d'OGIAS avant l'introduction des standards : référentiel métier publié de l'atelier, "
                       "charte OGIAS, plan mémoire par défaut, supervision TOPKAPI.",
        "briques": {**copy.deepcopy(BRIQUES_FIXES), **_briques_initiales()},
        "cree_le": "", "historique": [],
    }


def chemin() -> str:
    return os.path.join(chemins.dossier_donnees(), "standards_ingenierie.json")


def _maintenant() -> str:
    return time.strftime("%d/%m/%Y %H:%M")


def _charger() -> dict:
    """Contenu complet du fichier ; créé au premier accès avec le seul Standard initial (rien d'autre n'est supposé)."""
    f = chemin()
    if not os.path.exists(f):
        initial = standard_initial()
        initial["cree_le"] = _maintenant()
        donnees = {"standards": [initial], "bibliotheque": {k: [copy.deepcopy(v)] for k, v in _briques_initiales().items()}}
        _ecrire(donnees)
        return donnees
    with open(f, encoding="utf-8") as fh:
        donnees = json.load(fh)
    standards = donnees.get("standards") if isinstance(donnees, dict) else None
    if not isinstance(standards, list) or not standards:
        raise ValueError("Fichier des standards d'ingénierie illisible : aucun écrasement effectué.")
    # Fichier de l'étape 1 (sans bibliothèque) : les briques des standards forment la bibliothèque, sans rien perdre.
    # Charte OGIAS décrite par son seul nom avant les chartes réglables : sa structure est complétée.
    biblio = donnees.get("bibliotheque") if isinstance(donnees.get("bibliotheque"), dict) else {}
    for s in standards:
        b = s.setdefault("briques", {}).setdefault("charte", {"nom": _briques_initiales()["charte"]["nom"]})
        if "ouvrage" not in b and b.get("ident", "charte-ogias") == "charte-ogias":
            b.pop("source", None)
            b.update(ident="charte-ogias", **copy.deepcopy(charte.CHARTE_OGIAS))
    for fam in CHOISISSABLES:
        liste = biblio.setdefault(fam, [])
        for s in standards:
            b = s.get("briques", {}).get(fam)
            if not b:
                continue
            if not b.get("ident"):
                b["ident"] = _briques_initiales()[fam]["ident"] if s.get("ident") == IDENT_INITIAL else _ident(b["nom"], liste)
            if not any(x.get("ident") == b["ident"] for x in liste):
                liste.append({k: copy.deepcopy(v) for k, v in b.items()})
    for s in standards:
        for fam, b in BRIQUES_FIXES.items():
            s.setdefault("briques", {}).setdefault(fam, copy.deepcopy(b)).setdefault("ident", b["ident"])
    donnees["bibliotheque"] = biblio
    return donnees


def _ecrire(donnees: dict) -> None:
    dossier = os.path.dirname(chemin())
    os.makedirs(dossier, exist_ok=True)
    fd, provisoire = tempfile.mkstemp(prefix=".ogias_standards_", suffix=".json", dir=dossier)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"version": VERSION_FICHIER, "standards": donnees["standards"],
                       "bibliotheque": donnees["bibliotheque"]}, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(provisoire, chemin())
    finally:
        if os.path.exists(provisoire):
            os.unlink(provisoire)


def lire() -> list[dict]:
    return _charger()["standards"]


def bibliotheque() -> dict[str, list[dict]]:
    return _charger()["bibliotheque"]


def ecrire(standards: list[dict]) -> None:
    """Remplace la liste des standards en gardant la bibliothèque (essais, reprise)."""
    donnees = _charger()
    donnees["standards"] = standards
    _ecrire(donnees)


def trouver(ident: str) -> dict | None:
    return next((s for s in lire() if s.get("ident") == ident), None)


# --- Bibliothèque de briques et standards (étape 2) -------------------------------------------------------------

def _ident(nom: str, existants) -> str:
    base = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")[:40] or "element"
    pris = {x.get("ident") for x in existants}
    ident, n = base, 2
    while ident in pris:
        ident, n = f"{base}-{n}", n + 1
    return ident


def _nom(nom, existants, quoi: str) -> str:
    nom = " ".join(str(nom or "").split())
    if not 3 <= len(nom) <= 60:
        raise RegleMetier(f"Nom {quoi} : 3 à 60 caractères.")
    if any(str(x.get("nom", "")).casefold() == nom.casefold() for x in existants):
        raise RegleMetier(f"Un {quoi} porte déjà le nom « {nom} ».")
    return nom


def creer_brique(famille: str, nom: str, contenu: dict) -> tuple[dict, list[str]]:
    """Ajoute une brique à la bibliothèque, contrôlée comme une saisie sur un ouvrage. Renvoie (brique, alertes)."""
    if famille not in CHOISISSABLES:
        raise RegleMetier("Famille de brique inconnue.")
    donnees = _charger()
    liste = donnees["bibliotheque"].setdefault(famille, [])
    quoi = NOMS_BRIQUE[famille]
    nom = _nom(nom, liste, quoi)
    alertes: list[str] = []
    if famille == "charte":
        brique = {"nom": nom, **charte.controler(contenu)}
        if not charte.applicable(brique):
            alertes = ["Charte enregistrée. OGIAS ne fabrique pas encore les repères selon une charte différente de "
                       "la charte OGIAS : un standard qui l'emploie ne peut pas encore servir à créer un ouvrage."]
    elif famille == "adressage":
        lues = controler_plages(contenu.get("plages"))
        alertes = alertes_plages(lues)
        brique = {"nom": nom, "plages": {f: list(lues[f]) for f in ORDRE_ZONES},
                  "decalage_modbus": controler_decalage(contenu.get("decalage_modbus", 0) or 0)}
    else:
        brique = {"nom": nom, "supervision": " ".join(str(contenu.get("supervision") or "").split())[:60],
                  "ihm": " ".join(str(contenu.get("ihm") or "").split())[:60]}
    brique = {"ident": _ident(nom, liste), **brique, "cree_le": _maintenant()}
    liste.append(brique)
    _ecrire(donnees)
    return brique, alertes


def _assembler(donnees: dict, choix: dict) -> dict:
    briques = copy.deepcopy(BRIQUES_FIXES)
    for fam in CHOISISSABLES:
        voulu = (choix or {}).get(fam) or ("charte-ogias" if fam == "charte" else "")   # charte : fixe avant le 19/11
        b = next((x for x in donnees["bibliotheque"].get(fam, []) if x.get("ident") == voulu), None)
        if b is None:
            raise RegleMetier(f"{FAMILLES[fam]} : choisissez une brique de la bibliothèque.")
        briques[fam] = {k: copy.deepcopy(v) for k, v in b.items() if k != "cree_le"}
    return briques


def creer_standard(nom: str, description: str, choix: dict) -> dict:
    donnees = _charger()
    nom = _nom(nom, donnees["standards"], "standard")
    standard = {"ident": _ident(nom, donnees["standards"]), "nom": nom, "version": 1, "statut": "actif",
                "description": " ".join(str(description or "").split())[:400],
                "briques": _assembler(donnees, choix), "cree_le": _maintenant(), "historique": []}
    donnees["standards"].append(standard)
    _ecrire(donnees)
    return standard


def reviser_standard(ident: str, choix: dict, description: str, motif: str) -> dict:
    """Nouvelle version d'un standard. Les ouvrages déjà créés gardent leur copie ; OGIAS leur signale l'évolution."""
    donnees = _charger()
    s = next((x for x in donnees["standards"] if x.get("ident") == ident), None)
    if s is None:
        raise RegleMetier("Standard introuvable.")
    motif = " ".join(str(motif or "").split())
    if len(motif) < 5:
        raise RegleMetier("Indiquez le motif de la nouvelle version (5 caractères au moins).")
    briques = _assembler(donnees, choix)
    description = " ".join(str(description if description is not None else s.get("description", "")).split())[:400]
    if briques == s["briques"] and description == s.get("description", ""):
        raise RegleMetier("Aucun changement : la version actuelle est conservée.")
    s.setdefault("historique", []).append({"version": s["version"], "jusqu_au": _maintenant(), "motif": motif,
                                           "briques": {f: s["briques"][f]["nom"] for f in CHOISISSABLES}})
    s.update(version=int(s["version"]) + 1, briques=briques, description=description)
    _ecrire(donnees)
    return s


def changer_statut(ident: str, statut: str) -> dict:
    if statut not in STATUTS:
        raise RegleMetier("État inconnu.")
    donnees = _charger()
    s = next((x for x in donnees["standards"] if x.get("ident") == ident), None)
    if s is None:
        raise RegleMetier("Standard introuvable.")
    if statut == "archivé" and not any(x["statut"] == "actif" for x in donnees["standards"] if x is not s):
        raise RegleMetier("Il faut garder au moins un standard actif pour créer des ouvrages.")
    s["statut"] = statut
    _ecrire(donnees)
    return s


def emplois_briques() -> dict[str, int]:
    """Nombre de standards (version actuelle) qui emploient chaque brique, par identifiant « famille:ident »."""
    compte: dict[str, int] = {}
    for s in lire():
        for fam in CHOISISSABLES:
            cle = f"{fam}:{s['briques'].get(fam, {}).get('ident', '')}"
            compte[cle] = compte.get(cle, 0) + 1
    return compte


# --- Ouvrage -----------------------------------------------------------------------------------------------------

def reference(standard: dict) -> dict:
    """Ce que l'ouvrage garde de son standard : qui, quelle version, quand, et les réglages copiés."""
    return {"ident": standard["ident"], "nom": standard["nom"], "version": standard["version"],
            "applique_le": _maintenant(), "briques": copy.deepcopy(standard["briques"])}


def appliquer(session, standard: dict) -> list[str]:
    """Copie les réglages du standard dans l'ouvrage de la session : à la création, ou plus tard à la demande (après
    aperçu). Tout ou rien. Les adresses déjà validées ne bougent jamais (règle du plan mémoire). Le référentiel métier
    et la charte n'ont qu'une brique : rien à copier. Renvoie les alertes non bloquantes."""
    b = standard["briques"]
    if not charte.applicable(b.get("charte", charte.CHARTE_OGIAS)):
        raise RegleMetier(f"Le standard « {standard['nom']} » emploie la charte « {b['charte'].get('nom', '')} » : OGIAS ne "
                          "fabrique pas encore les repères selon une autre charte que la charte OGIAS. Rien n'a été modifié.")
    avant = copy.deepcopy(session.ouvrage)
    try:
        alertes = session.definir_plages({f: tuple(v) for f, v in b["adressage"]["plages"].items()})
        session.declarer_protocole(True, int(b["adressage"].get("decalage_modbus", 0) or 0))
        session.ouvrage.supervision = b["outils"].get("supervision", "")
        session.ouvrage.ihm = b["outils"].get("ihm", "")
        session.ouvrage.standard = reference(standard)
    except Exception:
        session.ouvrage = avant
        raise
    return alertes


def ecarts(ouvrage, briques: dict | None = None) -> list[str]:
    """Différences entre les réglages actuels de l'ouvrage et des briques : par défaut celles copiées de son standard
    (modifications locales) ; sinon celles d'un standard à appliquer (aperçu de ce qui changerait)."""
    if briques is None:
        briques = (getattr(ouvrage, "standard", None) or {}).get("briques")
    if not briques:
        return []
    from .modele import zone
    b = briques
    sortie = []
    for f in ORDRE_ZONES:
        attendu = tuple(b["adressage"]["plages"].get(f, ()))
        if attendu and zone(ouvrage, f) != attendu:
            sortie.append(f"Plage {f} : %MW{zone(ouvrage, f)[0]} à %MW{zone(ouvrage, f)[1]} "
                          f"(standard : %MW{attendu[0]} à %MW{attendu[1]})")
    if int(ouvrage.decalage_modbus or 0) != int(b["adressage"].get("decalage_modbus", 0) or 0):
        sortie.append(f"Décalage Modbus : {ouvrage.decalage_modbus} (standard : {b['adressage'].get('decalage_modbus', 0)})")
    for champ, nom in (("supervision", "Supervision"), ("ihm", "IHM")):
        if (getattr(ouvrage, champ, "") or "") != (b["outils"].get(champ, "") or ""):
            sortie.append(f"{nom} : {getattr(ouvrage, champ, '') or 'aucune'} (standard : {b['outils'].get(champ, '') or 'aucune'})")
    return sortie


def utilisation() -> dict[str, int]:
    """Nombre d'ouvrages enregistrés par standard (identifiant ; « » pour les ouvrages créés avant les standards)."""
    from . import projets
    from .modele import Ouvrage
    compte: dict[str, int] = {}
    for f in projets.lister():
        if f.erreur:
            continue
        try:
            ident = (Ouvrage.ouvrir(f.chemin).standard or {}).get("ident", "")
        except Exception:                                     # noqa: BLE001 — fichier illisible : non compté
            continue
        compte[ident] = compte.get(ident, 0) + 1
    return compte
