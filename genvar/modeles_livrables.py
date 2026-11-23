"""Modèles de livrables à variables (lot 1 de la feuille de route du 19/11/2026).

Idée reprise des « typicals » des outils d'ingénierie de données : le bureau d'études dépose dans OGIAS un FICHIER
TIRÉ DE SON PROPRE OUTIL (ligne d'import de supervision, table d'automate, CSV, texte…) où il a remplacé les valeurs
par des variables `<#NOM#>`. OGIAS remplit ce fichier pour l'ouvrage. Le format vient donc de l'outil du client :
OGIAS n'en invente aucun, et un livrable produit ainsi est « conforme au modèle fourni », jamais « compatible »
sans essai dans l'outil cible.

Syntaxe
- Variable : `<#NOM#>` (majuscules, chiffres, _). Liste et portée : VARIABLES_* ci-dessous.
- Bloc répété : `<#DEBUT_EQUIPEMENTS#>…<#FIN_EQUIPEMENTS#>`, `<#DEBUT_VARIABLES#>…<#FIN_VARIABLES#>`,
  `<#DEBUT_ES#>…<#FIN_ES#>`. Un bloc VARIABLES ou ES placé dans un bloc EQUIPEMENTS ne parcourt que l'équipement.
  Filtre facultatif : `DEBUT_VARIABLES_TS` (famille TS, TC, TM, TR, RTR, CP), `DEBUT_ES_ET` (ET, ST, EA, SA) ;
  `DEBUT_EQUIPEMENTS_PM` (type d'équipement, lettres et chiffres) ; le FIN reprend le même nom.
- Une balise de bloc seule sur sa ligne consomme la ligne entière : le modèle reste lisible sans lignes vides en trop.
- Une variable inconnue, ou utilisée hors de sa portée, est signalée à l'analyse et bloque la génération.

Logiciel cible (lot 8, suite du principe « typicals » du 19/11) : un modèle peut déclarer sa destination (automate,
supervision, IHM) et le logiciel pour lequel il est écrit (TOPKAPI, PcVue…). Le même type d'équipement peut ainsi
avoir une brique par logiciel ; l'ouvrage ne retient que celles de SES logiciels (fiche de l'ouvrage / standard).
Un modèle sans logiciel déclaré sert à tout ouvrage (comportement d'avant). Les noms de logiciels sont ceux que
l'atelier déclare : OGIAS ne les devine pas et ne vérifie pas qu'ils existent. Une brique manquante pour un type
d'équipement de l'ouvrage est signalée, jamais remplacée par celle d'un autre logiciel.

Stockage : dossier de données de l'atelier, `modeles_livrables/` (index JSON + un fichier par modèle), écriture
atomique ; rien n'est supposé au premier accès (bibliothèque vide).
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from xml.sax.saxutils import escape as _xml

from . import chemins

TAILLE_MAX = 2 * 1024 * 1024
ENCODAGES = ("utf-8", "cp1252")
ECHAPPEMENTS = {"aucun": "Aucun (texte brut)", "xml": "XML (& < > \" ')"}
FAMILLES_FILTRE = ("TS", "TC", "TM", "TR", "RTR", "CP")
POINTS_FILTRE = ("ET", "ST", "EA", "SA")

VARIABLES_OUVRAGE = {
    "OUVRAGE": "Repère de l'ouvrage (selon sa charte)", "LIEU": "Code du lieu", "TYPE_OUVRAGE": "Code du type d'ouvrage",
    "NUMERO_OUVRAGE": "Numéro de l'ouvrage", "LIBELLE_OUVRAGE": "Libellé de l'ouvrage", "AUTOMATE": "Automate",
    "SUPERVISION": "Supervision choisie", "IHM": "IHM choisie", "REVISION": "Révision documentaire",
    "STANDARD": "Standard d'ingénierie (nom et version)", "DATE": "Date de génération (JJ/MM/AAAA)",
}
VARIABLES_EQUIPEMENT = {
    "REPERE": "Repère de l'équipement", "REPERE_NOM": "Repère tel qu'il figure dans les noms",
    "EQ_TYPE": "Type d'équipement", "EQ_NUMERO": "Numéro de l'équipement", "EQ_LIBELLE": "Désignation saisie",
    "EQ_DESIGNATION": "Désignation du type", "SOUS_ENSEMBLE": "Sous-ensemble", "UF": "Unité fonctionnelle",
    "LOCAL": "Local", "MODELE": "Modèle d'équipement",
}
VARIABLES_VARIABLE = {
    "NOM": "Nom de la variable", "FAMILLE": "Famille (TS, TC, TM…)", "CODE": "Code du signal", "TYPE": "Type logique",
    "UNITE": "Unité", "LIBELLE": "Libellé de supervision", "INFORMATION": "Information du signal",
    "COMMENTAIRE": "Commentaire", "ADRESSE": "Adresse automate attribuée (%MW), vide tant qu'elle ne l'est pas",
    "REGISTRE_MODBUS": "Registre de télétransmission (adresse + décalage de l'ouvrage)",
    "ADRESSE_VALIDEE": "Oui si l'adresse est validée, sinon Non", "ALARME": "Oui / Non", "NOM_ES": "E/S liée",
}
VARIABLES_ES = {
    "ES_NOM": "Nom de l'E/S", "ES_POINT": "Nature (ET, ST, EA, SA)", "ES_TYPE": "Type logique",
    "ES_ADRESSE": "Adresse physique", "ES_MODULE": "Module (rack.emplacement)", "ES_VOIE": "Voie",
    "ES_DESIGNATION": "Désignation", "ES_RACCORDEMENT": "Câblé ou Communication", "ES_VARIABLE": "Variable d'échange liée",
}
COMPTEUR = {"N": "Rang dans le bloc en cours (1, 2, 3…)"}
DESTINATIONS = {"": "Tout ouvrage", "automate": "Automate", "supervision": "Supervision", "ihm": "IHM"}
_DE = {"automate": "d'automate", "supervision": "de supervision", "ihm": "d'IHM"}
# Logiciel de programmation déjà établi dans OGIAS pour une gamme d'automate (exports Control Expert des M340 / M580).
LOGICIEL_DE_GAMME = {"M340": "Control Expert", "M580": "Control Expert"}
BLOCS = ("EQUIPEMENTS", "VARIABLES", "ES")
RE_TYPE_FILTRE = re.compile(r"[A-Z][A-Z0-9]{0,3}")     # DEBUT_EQUIPEMENTS_PM : seulement les équipements de type PM

RE_BALISE = re.compile(r"<#([A-Z][A-Z0-9_]*)#>")
RE_LIGNE_BLOC = re.compile(r"(?m)^[ \t]*(<#(?:DEBUT|FIN)_[A-Z0-9_]+#>)[ \t]*\r?\n")


class ModeleRefuse(ValueError):
    """Modèle illisible ou incohérent : le message s'affiche tel quel."""


# --------------------------------------------------------------------------------------------- analyse du texte
@dataclass
class Bloc:
    nom: str                      # EQUIPEMENTS, VARIABLES, ES (ou « » pour la racine)
    filtre: str = ""
    enfants: list = field(default_factory=list)   # str (texte) | ("var", NOM) | Bloc


def _bloc_et_filtre(nom: str) -> tuple[str, str] | None:
    for b in BLOCS:
        if nom == b:
            return b, ""
        if nom.startswith(b + "_"):
            f = nom[len(b) + 1:]
            if (b == "VARIABLES" and f in FAMILLES_FILTRE) or (b == "ES" and f in POINTS_FILTRE) \
                    or (b == "EQUIPEMENTS" and RE_TYPE_FILTRE.fullmatch(f)):
                return b, f
    return None


def analyser(texte: str) -> tuple[Bloc, list[str], list[dict]]:
    """(arbre, erreurs, variables employées [{nom, portee, connue, nombre}])."""
    texte = RE_LIGNE_BLOC.sub(lambda m: m.group(1), texte)
    racine = Bloc("")
    pile: list[Bloc] = [racine]
    erreurs: list[str] = []
    emplois: dict[str, dict] = {}
    pos = 0
    for m in RE_BALISE.finditer(texte):
        if m.start() > pos:
            pile[-1].enfants.append(texte[pos:m.start()])
        pos = m.end()
        nom = m.group(1)
        if nom.startswith(("DEBUT_", "FIN_")):
            sens, reste = nom.split("_", 1)
            bf = _bloc_et_filtre(reste)
            if bf is None:
                erreurs.append(f"Bloc inconnu : <#{nom}#> (blocs : {', '.join(BLOCS)}).")
                continue
            if sens == "DEBUT":
                ouverts = [b.nom for b in pile[1:]]
                if bf[0] in ouverts or (bf[0] == "EQUIPEMENTS" and ouverts):
                    erreurs.append(f"Bloc <#{nom}#> mal imbriqué (seuls VARIABLES et ES peuvent être dans EQUIPEMENTS).")
                    continue
                bloc = Bloc(*bf)
                pile[-1].enfants.append(bloc)
                pile.append(bloc)
            else:
                if len(pile) == 1 or (pile[-1].nom, pile[-1].filtre) != bf:
                    erreurs.append(f"<#{nom}#> ne ferme pas le bloc ouvert.")
                    continue
                pile.pop()
            continue
        portees = [b.nom for b in pile[1:]]
        portee, connue = _portee(nom, portees)
        e = emplois.setdefault(nom, {"nom": nom, "portee": portee, "connue": connue, "nombre": 0,
                                     "description": DESCRIPTIONS.get(nom, "") or _description_attribut(nom)})
        e["nombre"] += 1
        if not connue:
            e["connue"] = False
            erreurs.append(f"<#{nom}#> : {portee}.")
        pile[-1].enfants.append(("var", nom))
    if pos < len(texte):
        pile[-1].enfants.append(texte[pos:])
    for b in pile[1:]:
        erreurs.append(f"Bloc <#DEBUT_{b.nom}{'_' + b.filtre if b.filtre else ''}#> jamais fermé.")
    return racine, list(dict.fromkeys(erreurs)), sorted(emplois.values(), key=lambda x: x["nom"])


DESCRIPTIONS = {**VARIABLES_OUVRAGE, **VARIABLES_EQUIPEMENT, **VARIABLES_VARIABLE, **VARIABLES_ES, **COMPTEUR}


def _description_attribut(nom: str) -> str:
    if not nom.startswith("ATTR_"):
        return ""
    from . import attributs
    try:
        a = attributs.trouver(nom[5:])
    except ValueError:
        return ""
    return f"Attribut d'équipement : {a['nom']}" if a else ""


def _portee(nom: str, ouverts: list[str]) -> tuple[str, bool]:
    if nom in VARIABLES_OUVRAGE:
        return "ouvrage", True
    if nom in COMPTEUR:
        return ("bloc", True) if ouverts else ("à utiliser dans un bloc", False)
    if nom.startswith("ATTR_"):
        from . import attributs
        try:
            connu = attributs.trouver(nom[5:]) is not None
        except ValueError:
            connu = False
        if not connu:
            return "attribut d'équipement inconnu de l'atelier", False
        return ("équipement", True) if ouverts else ("à utiliser dans un bloc EQUIPEMENTS, VARIABLES ou ES", False)
    if nom in VARIABLES_EQUIPEMENT:
        return ("équipement", True) if ouverts else ("à utiliser dans un bloc EQUIPEMENTS, VARIABLES ou ES", False)
    if nom in VARIABLES_VARIABLE:
        return ("variable", True) if "VARIABLES" in ouverts else ("à utiliser dans un bloc VARIABLES", False)
    if nom in VARIABLES_ES:
        return ("E/S", True) if "ES" in ouverts else ("à utiliser dans un bloc ES", False)
    return "variable inconnue d'OGIAS", False


# --------------------------------------------------------------------------------------------- remplissage
def _oui(b) -> str:
    return "Oui" if b else "Non"


def valeurs_ouvrage(session) -> dict:
    o = session.ouvrage
    ref = o.standard or {}
    return {"OUVRAGE": o.prefixe(), "LIEU": o.lieu, "TYPE_OUVRAGE": o.code_ouvrage, "NUMERO_OUVRAGE": o.numero_ouvrage,
            "LIBELLE_OUVRAGE": o.libelle, "AUTOMATE": o.automate, "SUPERVISION": o.supervision, "IHM": o.ihm,
            "REVISION": o.revision, "STANDARD": f"{ref['nom']} v{ref['version']}" if ref else "",
            "DATE": time.strftime("%d/%m/%Y")}


def valeurs_equipement(session, eq) -> dict:
    o = session.ouvrage
    return {"REPERE": o.repere(eq), "REPERE_NOM": o.repere_nom(eq), "EQ_TYPE": eq.type, "EQ_NUMERO": eq.numero,
            "EQ_LIBELLE": eq.libelle, "EQ_DESIGNATION": session.designation_type(eq.type),
            "SOUS_ENSEMBLE": eq.sous_ensemble, "UF": eq.uf, "LOCAL": eq.local, "MODELE": eq.modele,
            **{f"ATTR_{k}": v for k, v in (getattr(eq, "attributs", None) or {}).items()}}


def valeurs_variable(session, v) -> dict:
    return {"NOM": v.nom, "FAMILLE": v.famille, "CODE": v.code, "TYPE": v.type_logique, "UNITE": v.unite,
            "LIBELLE": v.libelle_topkapi, "INFORMATION": v.information, "COMMENTAIRE": v.commentaire,
            "ADRESSE": v.adresse, "REGISTRE_MODBUS": session.registre_modbus(v.adresse) if v.adresse else "",
            "ADRESSE_VALIDEE": _oui(v.adresse_validee), "ALARME": _oui(v.alarme), "NOM_ES": v.nom_es}


def valeurs_es(p) -> dict:
    return {"ES_NOM": p.nom, "ES_POINT": p.point, "ES_TYPE": p.type_logique, "ES_ADRESSE": p.adresse,
            "ES_MODULE": p.module, "ES_VOIE": p.voie, "ES_DESIGNATION": p.designation or p.commentaire,
            "ES_RACCORDEMENT": p.raccordement, "ES_VARIABLE": p.variable}


def remplir(texte: str, session, echappement: str = "aucun", seulement=None) -> str:
    """Texte du livrable. Lève ModeleRefuse si le modèle contient une erreur (variable inconnue, bloc mal fermé).
    `seulement` (identifiants d'équipement) restreint le remplissage : vérification d'un modèle sur un équipement."""
    arbre, erreurs, _ = analyser(texte)
    if erreurs:
        raise ModeleRefuse("Modèle à corriger : " + " ".join(erreurs[:5]))
    o = session.ouvrage
    eqs = sorted((e for e in o.equipements if seulement is None or e.ident in seulement), key=o.repere)
    par_ident = {e.ident: e for e in eqs}
    rang = {e.ident: i for i, e in enumerate(eqs)}
    def cle_variable(v):
        r = session.rang_export(v)                      # ordre d'export choisi pour l'équipement (V1-5-02)
        return (rang.get(v.ident_eq, 0), r, "") if r is not None else (rang.get(v.ident_eq, 0), -1, v.nom)
    variables = sorted(session.variables(), key=cle_variable)
    points = sorted(session.points(), key=lambda p: (rang.get(p.ident_eq, 0), p.nom))
    esc = (lambda s: _xml(s, {'"': "&quot;", "'": "&apos;"})) if echappement == "xml" else (lambda s: s)
    sortie: list[str] = []

    def parcourir(bloc: Bloc, ctx: dict, eq_courant=None):
        for x in bloc.enfants:
            if isinstance(x, str):
                sortie.append(x)
            elif isinstance(x, tuple):
                sortie.append(esc(str(ctx.get(x[1], ""))))
            else:
                if x.nom == "EQUIPEMENTS":
                    elements = [(e, {**ctx, **valeurs_equipement(session, e)}, e) for e in eqs
                                if not x.filtre or e.type == x.filtre]
                elif x.nom == "VARIABLES":
                    elements = [(v, {**ctx, **valeurs_equipement(session, par_ident[v.ident_eq]), **valeurs_variable(session, v)},
                                 eq_courant) for v in variables
                                if v.ident_eq in par_ident and (eq_courant is None or v.ident_eq == eq_courant.ident)
                                and (not x.filtre or v.famille == x.filtre)]
                else:
                    elements = [(p, {**ctx, **valeurs_equipement(session, par_ident[p.ident_eq]), **valeurs_es(p)},
                                 eq_courant) for p in points
                                if p.ident_eq in par_ident and (eq_courant is None or p.ident_eq == eq_courant.ident)
                                and (not x.filtre or p.point == x.filtre)]
                for n, (_, valeurs, eq) in enumerate(elements, 1):
                    parcourir(x, {**valeurs, "N": n}, eq)
    parcourir(arbre, valeurs_ouvrage(session))
    return "".join(sortie)


# --------------------------------------------------------------------------------------------- bibliothèque
def dossier() -> str:
    return os.path.join(chemins.dossier_donnees(), "modeles_livrables")


def _index_chemin() -> str:
    return os.path.join(dossier(), "index.json")


def _ecrire_atomique(chemin: str, octets: bytes) -> None:
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    fd, provisoire = tempfile.mkstemp(prefix=".ogias_", dir=os.path.dirname(chemin))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(octets)
        os.replace(provisoire, chemin)
    finally:
        if os.path.exists(provisoire):
            os.unlink(provisoire)


def lister() -> list[dict]:
    if not os.path.exists(_index_chemin()):
        return []
    with open(_index_chemin(), encoding="utf-8") as fh:
        donnees = json.load(fh)
    modeles = donnees.get("modeles") if isinstance(donnees, dict) else None
    if not isinstance(modeles, list):
        raise ValueError("Index des modèles de livrables illisible : aucun écrasement effectué.")
    return modeles


def _ecrire_index(modeles: list[dict]) -> None:
    _ecrire_atomique(_index_chemin(), (json.dumps({"version": 1, "modeles": modeles}, ensure_ascii=False, indent=2)
                                       + "\n").encode("utf-8"))


def _fichier(ident: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{12}", ident or ""):
        raise ModeleRefuse("Modèle introuvable.")
    return os.path.join(dossier(), ident + ".modele")


def decoder(octets: bytes) -> tuple[str, str]:
    """(texte, encodage) : UTF-8 (avec ou sans BOM) sinon Windows-1252, comme les fichiers des outils Windows."""
    if b"\x00" in octets[:4096]:
        raise ModeleRefuse("Fichier binaire : seuls les modèles texte (CSV, TXT, XML, SCL…) sont pris en charge "
                           "pour l'instant ; les documents Word viendront avec les cahiers d'essais.")
    try:
        return octets.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return octets.decode("cp1252", errors="strict"), "cp1252"


def trouver(ident: str) -> dict | None:
    return next((m for m in lister() if m.get("ident") == ident), None)


def texte(ident: str) -> str:
    m = trouver(ident)
    if m is None:
        raise ModeleRefuse("Modèle introuvable.")
    with open(_fichier(ident), "rb") as fh:
        return decoder(fh.read())[0]


def _cible_controlee(destination, logiciel) -> tuple[str, str]:
    destination = str(destination or "").strip()
    logiciel = " ".join(str(logiciel or "").split())
    if destination not in DESTINATIONS:
        raise ModeleRefuse("Destination inconnue (automate, supervision, IHM ou tout ouvrage).")
    if not destination:
        if logiciel:
            raise ModeleRefuse("Choisissez la destination (automate, supervision ou IHM) du logiciel déclaré.")
        return "", ""
    if not 2 <= len(logiciel) <= 40:
        raise ModeleRefuse("Logiciel cible : 2 à 40 caractères (ex. TOPKAPI, PcVue, Control Expert).")
    return destination, logiciel


def importer(nom: str, nom_fichier: str, octets: bytes, echappement: str = "aucun", description: str = "",
             encodage_force: str | None = None, destination: str = "", logiciel: str = "") -> dict:
    """`encodage_force` : encodage du fichier d'origine quand le modèle a été construit par l'assistant (un modèle
    devenu purement ASCII après substitution ne permet plus de le reconnaître)."""
    nom = " ".join(str(nom or "").split())
    if not 3 <= len(nom) <= 60:
        raise ModeleRefuse("Nom du modèle : 3 à 60 caractères.")
    modeles = lister()
    if any(m["nom"].casefold() == nom.casefold() for m in modeles):
        raise ModeleRefuse(f"Un modèle porte déjà le nom « {nom} ».")
    if not octets or len(octets) > TAILLE_MAX:
        raise ModeleRefuse("Fichier vide ou trop volumineux (2 Mo au plus).")
    if echappement not in ECHAPPEMENTS:
        raise ModeleRefuse("Échappement inconnu.")
    destination, logiciel = _cible_controlee(destination, logiciel)
    contenu, encodage = decoder(octets)
    if encodage_force is not None:
        if encodage_force not in ENCODAGES:
            raise ModeleRefuse("Encodage inconnu.")
        contenu, encodage = octets.decode(encodage_force), encodage_force
    if "<#" not in contenu:
        raise ModeleRefuse("Aucune variable <#…#> dans ce fichier : placez d'abord les variables à la place des valeurs.")
    extension = os.path.splitext(os.path.basename(nom_fichier or ""))[1].lstrip(".").lower()
    if not re.fullmatch(r"[a-z0-9$_]{1,8}", extension or ""):
        extension = "txt"
    m = {"ident": uuid.uuid4().hex[:12], "nom": nom, "description": " ".join(str(description or "").split())[:300],
         "extension": extension, "encodage": encodage, "echappement": echappement,
         "fichier_origine": os.path.basename(nom_fichier or "")[:120], "importe_le": time.strftime("%d/%m/%Y %H:%M"),
         "destination": destination, "logiciel": logiciel}
    _ecrire_atomique(_fichier(m["ident"]), octets)
    _ecrire_index([*modeles, m])
    return m


def supprimer(ident: str) -> None:
    modeles = lister()
    if not any(m["ident"] == ident for m in modeles):
        raise ModeleRefuse("Modèle introuvable.")
    _ecrire_index([m for m in modeles if m["ident"] != ident])
    try:
        os.unlink(_fichier(ident))
    except FileNotFoundError:
        pass


def definir_cible(ident: str, destination: str, logiciel: str) -> dict:
    """Change la destination et le logiciel déclarés d'un modèle (le fichier du modèle n'est pas touché)."""
    destination, logiciel = _cible_controlee(destination, logiciel)
    modeles = lister()
    m = next((x for x in modeles if x.get("ident") == ident), None)
    if m is None:
        raise ModeleRefuse("Modèle introuvable.")
    m["destination"], m["logiciel"] = destination, logiciel
    _ecrire_index(modeles)
    return m


def types_couverts(arbre: Bloc) -> list[str]:
    """Types d'équipement que le modèle produit : ["*"] s'il parcourt tous les équipements (bloc EQUIPEMENTS sans
    filtre, ou blocs VARIABLES / ES hors d'un bloc EQUIPEMENTS, ou aucun bloc), sinon les filtres EQUIPEMENTS_<TYPE>."""
    types: set[str] = set()
    tous = False
    for x in arbre.enfants:
        if isinstance(x, Bloc):
            if x.nom == "EQUIPEMENTS" and x.filtre:
                types.add(x.filtre)
            else:
                tous = True
    return ["*"] if tous or not types else sorted(types)


def resume(m: dict) -> dict:
    """Le modèle et l'état de ses variables (analyse), pour l'écran de la bibliothèque."""
    try:
        arbre, erreurs, emplois = analyser(texte(m["ident"]))
        types = types_couverts(arbre)
    except (OSError, ModeleRefuse, UnicodeDecodeError) as exc:
        erreurs, emplois, types = [f"Fichier du modèle illisible : {exc}"], [], []
    return {"destination": "", "logiciel": "", **m, "erreurs": erreurs, "variables": emplois, "types": types}


def _cle(logiciel: str) -> str:
    return " ".join(str(logiciel or "").split()).casefold()


def logiciels_ouvrage(ouvrage, destination: str) -> list[str]:
    """Noms sous lesquels l'ouvrage désigne son logiciel pour cette destination (vide : rien de déclaré).
    Automate : l'automate saisi et, pour une gamme connue, son logiciel de programmation (M580 → Control Expert)."""
    if destination == "supervision":
        noms = [getattr(ouvrage, "supervision", "")]
    elif destination == "ihm":
        noms = [getattr(ouvrage, "ihm", "")]
    elif destination == "automate":
        from .outils import gamme_automate
        noms = [getattr(ouvrage, "automate", ""), LOGICIEL_DE_GAMME.get(gamme_automate(ouvrage) or "", "")]
    else:
        return []
    return [n.strip() for n in noms if (n or "").strip()]


def retenu(m: dict, ouvrage) -> tuple[bool, str]:
    """(retenu pour l'ouvrage, motif si non retenu)."""
    destination, logiciel = m.get("destination") or "", m.get("logiciel") or ""
    if not destination:
        return True, ""
    siens = logiciels_ouvrage(ouvrage, destination)
    if any(_cle(n) == _cle(logiciel) for n in siens):
        return True, ""
    de = _DE[destination]
    if not siens:
        return False, f"Modèle {de} {logiciel} : l'ouvrage ne déclare aucun logiciel {de}."
    return False, f"Modèle {de} {logiciel} : l'ouvrage utilise {' / '.join(siens)}."


def pour_ouvrage(session, resumes: list[dict] | None = None) -> dict:
    """Modèles retenus ou écartés pour l'ouvrage et briques manquantes.

    Manque : un type d'équipement de l'ouvrage qu'aucun modèle sans erreur de la destination ne couvre, alors que la
    bibliothèque contient au moins un modèle pour le logiciel de l'ouvrage dans cette destination (sinon l'atelier
    n'emploie pas de modèle pour ce logiciel et rien n'est attendu)."""
    o = session.ouvrage
    resumes = [resume(m) for m in lister()] if resumes is None else resumes
    choix = []
    for r in resumes:
        ok, motif = retenu(r, o)
        choix.append({"ident": r["ident"], "nom": r["nom"], "retenu": ok, "motif": motif})
    par_type: dict[str, int] = {}
    for e in o.equipements:
        if e.type:
            par_type[e.type] = par_type.get(e.type, 0) + 1
    manques = []
    for destination in ("automate", "supervision", "ihm"):
        siens = {_cle(n) for n in logiciels_ouvrage(o, destination)}
        candidats = [r for r in resumes if r.get("destination") == destination and _cle(r.get("logiciel", "")) in siens]
        if not candidats:
            continue
        sains = [r for r in candidats if not r["erreurs"]]
        couverts = {t for r in sains for t in r["types"]}
        if "*" in couverts:
            continue
        logiciel = candidats[0]["logiciel"]
        for type_eq, n in sorted(par_type.items()):
            if type_eq not in couverts:
                manques.append({"destination": destination, "logiciel": logiciel, "type": type_eq, "equipements": n,
                                "message": f"Aucun modèle {_DE[destination]} {logiciel} sans erreur "
                                           f"ne couvre le type {type_eq} ({n} équipement(s))."})
    return {"choix": choix, "manques": manques}


def couverture(resumes: list[dict] | None = None) -> list[dict]:
    """Complétude de la bibliothèque : pour chaque destination et logiciel déclarés, les types couverts par des
    modèles sans erreur (« * » : tous) et le nombre de modèles en erreur."""
    resumes = [resume(m) for m in lister()] if resumes is None else resumes
    groupes: dict[tuple[str, str], dict] = {}
    for r in resumes:
        if not r.get("destination"):
            continue
        cle = (r["destination"], _cle(r["logiciel"]))
        g = groupes.setdefault(cle, {"destination": r["destination"], "logiciel": r["logiciel"], "types": set(),
                                     "modeles": 0, "en_erreur": 0})
        g["modeles"] += 1
        if r["erreurs"]:
            g["en_erreur"] += 1
        else:
            g["types"].update(r["types"])
    ordre = list(DESTINATIONS)
    return [{**g, "types": ["*"] if "*" in g["types"] else sorted(g["types"])}
            for g in sorted(groupes.values(), key=lambda g: (ordre.index(g["destination"]), _cle(g["logiciel"])))]


def generer(ident: str, session) -> tuple[str, bytes]:
    """(nom de fichier, octets) du livrable rempli pour l'ouvrage de la session, dans l'encodage du modèle."""
    m = trouver(ident)
    if m is None:
        raise ModeleRefuse("Modèle introuvable.")
    rempli = remplir(texte(ident), session, m.get("echappement", "aucun"))
    try:
        octets = rempli.encode(m.get("encodage", "utf-8"))
    except UnicodeEncodeError as exc:
        raise ModeleRefuse(f"Caractère « {rempli[exc.start:exc.end]} » impossible à écrire dans l'encodage du modèle "
                           f"({m['encodage']}) : corrigez la donnée ou fournissez un modèle en UTF-8.") from None
    slug = unicodedata.normalize("NFKD", m["nom"]).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^A-Za-z0-9]+", "_", slug).strip("_")[:40] or "livrable"
    base = session.nom_fichier_propose() or "ouvrage"
    return f"{base}_{slug}.{m['extension']}", octets


EXEMPLE_NOM = "Exemple - liste des variables (CSV)"
EXEMPLE = ("Repère;Variable;Famille;Type;Adresse automate;Registre Modbus;Libellé\r\n"
           "<#DEBUT_VARIABLES#>\r\n"
           "<#REPERE#>;<#NOM#>;<#FAMILLE#>;<#TYPE#>;<#ADRESSE#>;<#REGISTRE_MODBUS#>;<#LIBELLE#>\r\n"
           "<#FIN_VARIABLES#>\r\n")


def ajouter_exemple() -> dict:
    """Modèle neutre de démonstration (CSV propre à OGIAS, format d'aucun outil) pour essayer le principe."""
    return importer(EXEMPLE_NOM, "exemple_liste_variables.csv", EXEMPLE.encode("utf-8"),
                    description="Exemple neutre d'OGIAS : une ligne par variable. Ce n'est le format d'aucun outil.")
