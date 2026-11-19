"""Standards d'ingénierie (19/11/2026) : à la création d'un ouvrage, on choisit le standard du client.

Un standard est un ASSEMBLAGE NOMMÉ de briques indépendantes, une par famille :
- référentiel métier : types d'équipements, signaux, règles (bibliothèque existante, versionnée et publiée) ;
- charte de nommage : lieu, code d'ouvrage, repère (une seule pour l'instant : celle d'OGIAS, genvar/charte.py) ;
- plan d'adressage : plages %MW par famille, décalage Modbus ;
- chaîne d'outils : supervision, IHM (l'automate reste choisi par ouvrage : il dépend du site).
Plusieurs clients peuvent partager une brique ; un réglage vient toujours d'une brique identifiée.

À la création, l'ouvrage COPIE les réglages du standard et garde sa référence (nom, version) : un ouvrage déjà créé
n'est jamais modifié quand le standard évolue (décision du 19/11) ; OGIAS signale l'écart.

Étape 1 : un seul standard, le « Standard initial », qui reproduit exactement le comportement d'OGIAS d'avant les
standards. Les bibliothèques de plans d'adressage et de chaînes d'outils viennent à l'étape 2, les chartes quand
une charte réelle d'un autre maître d'ouvrage servira d'exemple.
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
import time

from . import chemins
from .modele import ORDRE_ZONES, PLAN_DEFAUT

VERSION_FICHIER = 1
IDENT_INITIAL = "standard-initial"

FAMILLES = {"referentiel": "Référentiel métier", "charte": "Charte de nommage", "adressage": "Plan d'adressage",
            "outils": "Chaîne d'outils"}


def standard_initial() -> dict:
    """Le comportement d'OGIAS avant les standards, décrit comme un assemblage de briques."""
    return {
        "ident": IDENT_INITIAL, "nom": "Standard initial", "version": 1, "statut": "actif",
        "description": "Réglages d'OGIAS avant l'introduction des standards : référentiel métier publié de l'atelier, "
                       "charte OGIAS, plan mémoire par défaut, supervision TOPKAPI.",
        "briques": {
            "referentiel": {"nom": "Référentiel publié de l'atelier", "source": "atelier"},
            "charte": {"nom": "Charte OGIAS (lieu 4, type 2, numéro 2)", "source": "ogias"},
            "adressage": {"nom": "Plan mémoire par défaut", "plages": {f: list(PLAN_DEFAUT[f]) for f in ORDRE_ZONES},
                          "decalage_modbus": 0},
            "outils": {"nom": "Supervision TOPKAPI", "supervision": "TOPKAPI", "ihm": ""},
        },
        "cree_le": "", "historique": [],
    }


def chemin() -> str:
    return os.path.join(chemins.dossier_donnees(), "standards_ingenierie.json")


def lire() -> list[dict]:
    """Standards de l'atelier. Le Standard initial est créé au premier accès (aucun autre n'est supposé)."""
    f = chemin()
    if not os.path.exists(f):
        initial = standard_initial()
        initial["cree_le"] = time.strftime("%d/%m/%Y %H:%M")
        ecrire([initial])
        return [initial]
    with open(f, encoding="utf-8") as fh:
        donnees = json.load(fh)
    standards = donnees.get("standards") if isinstance(donnees, dict) else None
    if not isinstance(standards, list) or not standards:
        raise ValueError("Fichier des standards d'ingénierie illisible : aucun écrasement effectué.")
    return standards


def ecrire(standards: list[dict]) -> None:
    dossier = os.path.dirname(chemin())
    os.makedirs(dossier, exist_ok=True)
    fd, provisoire = tempfile.mkstemp(prefix=".ogias_standards_", suffix=".json", dir=dossier)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"version": VERSION_FICHIER, "standards": standards}, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(provisoire, chemin())
    finally:
        if os.path.exists(provisoire):
            os.unlink(provisoire)


def trouver(ident: str) -> dict | None:
    return next((s for s in lire() if s.get("ident") == ident), None)


def reference(standard: dict) -> dict:
    """Ce que l'ouvrage garde de son standard : qui, quelle version, quand, et les réglages copiés."""
    return {"ident": standard["ident"], "nom": standard["nom"], "version": standard["version"],
            "applique_le": time.strftime("%d/%m/%Y %H:%M"), "briques": copy.deepcopy(standard["briques"])}


def appliquer(session, standard: dict) -> dict:
    """Copie les réglages du standard dans l'ouvrage de la session (création d'ouvrage). Tout ou rien.
    Le référentiel métier et la charte n'ont qu'une brique pour l'instant : rien à copier, l'ouvrage les prend déjà
    comme avant. Renvoie la référence enregistrée dans l'ouvrage."""
    b = standard["briques"]
    avant = copy.deepcopy(session.ouvrage)
    try:
        session.definir_plages({f: tuple(v) for f, v in b["adressage"]["plages"].items()})
        session.declarer_protocole(True, int(b["adressage"].get("decalage_modbus", 0) or 0))
        session.ouvrage.supervision = b["outils"].get("supervision", "")
        session.ouvrage.ihm = b["outils"].get("ihm", "")
        session.ouvrage.standard = reference(standard)
    except Exception:
        session.ouvrage = avant
        raise
    return session.ouvrage.standard


def ecarts(ouvrage) -> list[str]:
    """Différences entre les réglages actuels de l'ouvrage et ceux copiés de son standard (modifications locales)."""
    ref = getattr(ouvrage, "standard", None) or {}
    b = ref.get("briques")
    if not b:
        return []
    from .modele import zone
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
