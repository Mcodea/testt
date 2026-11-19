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
  le FIN reprend le même nom.
- Une balise de bloc seule sur sa ligne consomme la ligne entière : le modèle reste lisible sans lignes vides en trop.
- Une variable inconnue, ou utilisée hors de sa portée, est signalée à l'analyse et bloque la génération.

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
BLOCS = ("EQUIPEMENTS", "VARIABLES", "ES")

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
            if (b == "VARIABLES" and f in FAMILLES_FILTRE) or (b == "ES" and f in POINTS_FILTRE):
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
                                     "description": DESCRIPTIONS.get(nom, "")})
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


def _portee(nom: str, ouverts: list[str]) -> tuple[str, bool]:
    if nom in VARIABLES_OUVRAGE:
        return "ouvrage", True
    if nom in COMPTEUR:
        return ("bloc", True) if ouverts else ("à utiliser dans un bloc", False)
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
            "SOUS_ENSEMBLE": eq.sous_ensemble, "UF": eq.uf, "LOCAL": eq.local, "MODELE": eq.modele}


def valeurs_variable(session, v) -> dict:
    return {"NOM": v.nom, "FAMILLE": v.famille, "CODE": v.code, "TYPE": v.type_logique, "UNITE": v.unite,
            "LIBELLE": v.libelle_topkapi, "INFORMATION": v.information, "COMMENTAIRE": v.commentaire,
            "ADRESSE": v.adresse, "REGISTRE_MODBUS": session.registre_modbus(v.adresse) if v.adresse else "",
            "ADRESSE_VALIDEE": _oui(v.adresse_validee), "ALARME": _oui(v.alarme), "NOM_ES": v.nom_es}


def valeurs_es(p) -> dict:
    return {"ES_NOM": p.nom, "ES_POINT": p.point, "ES_TYPE": p.type_logique, "ES_ADRESSE": p.adresse,
            "ES_MODULE": p.module, "ES_VOIE": p.voie, "ES_DESIGNATION": p.designation or p.commentaire,
            "ES_RACCORDEMENT": p.raccordement, "ES_VARIABLE": p.variable}


def remplir(texte: str, session, echappement: str = "aucun") -> str:
    """Texte du livrable. Lève ModeleRefuse si le modèle contient une erreur (variable inconnue, bloc mal fermé)."""
    arbre, erreurs, _ = analyser(texte)
    if erreurs:
        raise ModeleRefuse("Modèle à corriger : " + " ".join(erreurs[:5]))
    o = session.ouvrage
    eqs = sorted(o.equipements, key=o.repere)
    par_ident = {e.ident: e for e in eqs}
    rang = {e.ident: i for i, e in enumerate(eqs)}
    variables = sorted(session.variables(), key=lambda v: (rang.get(v.ident_eq, 0), v.nom))
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
                    elements = [(e, {**ctx, **valeurs_equipement(session, e)}, e) for e in eqs]
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


def importer(nom: str, nom_fichier: str, octets: bytes, echappement: str = "aucun", description: str = "") -> dict:
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
    contenu, encodage = decoder(octets)
    if "<#" not in contenu:
        raise ModeleRefuse("Aucune variable <#…#> dans ce fichier : placez d'abord les variables à la place des valeurs.")
    extension = os.path.splitext(os.path.basename(nom_fichier or ""))[1].lstrip(".").lower()
    if not re.fullmatch(r"[a-z0-9$_]{1,8}", extension or ""):
        extension = "txt"
    m = {"ident": uuid.uuid4().hex[:12], "nom": nom, "description": " ".join(str(description or "").split())[:300],
         "extension": extension, "encodage": encodage, "echappement": echappement,
         "fichier_origine": os.path.basename(nom_fichier or "")[:120], "importe_le": time.strftime("%d/%m/%Y %H:%M")}
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


def resume(m: dict) -> dict:
    """Le modèle et l'état de ses variables (analyse), pour l'écran de la bibliothèque."""
    try:
        _, erreurs, emplois = analyser(texte(m["ident"]))
    except (OSError, ModeleRefuse, UnicodeDecodeError) as exc:
        erreurs, emplois = [f"Fichier du modèle illisible : {exc}"], []
    return {**m, "erreurs": erreurs, "variables": emplois}


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
