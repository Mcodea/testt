"""Formats de variables Schneider Electric Control Expert : lecture et écriture.

Référence : exports réels Control Expert V14.1 fournis par l'utilisateur le 9 novembre 2026
(XSY, TXT, SCY ; le XVM est chiffré et n'est pas lisible). Structure reproduite :

XSY  <?xml … standalone="yes"?> / <VariablesExchangeFile> / <fileHeader company product dateTime content
     DTDVersion="41"> / <contentHeader name version dateTime> (+ <comment>) / <dataBlock> /
     <variables name typeName topologicalAddress> <comment/> [<variableInit value/>] [<attribute/>] ;
     une voie de réserve = <variables topologicalAddress typeName> sans nom, commentaire « RESERVE ».
     Indentation par tabulations, fins de ligne CRLF, UTF-8.
TXT  une ligne par variable : nom TAB adresse TAB type TAB "commentaire" TAB (CRLF).
SCY  bloc IEC : NOM AT %ADR : TYPE (*commentaire*); entre VAR_GLOBAL et END_VAR.

Statut : « conforme à l'échantillon » tant que l'import dans Control Expert n'a pas été essayé.
"""
import datetime
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from xml.sax.saxutils import escape, quoteattr

STATUT = "conforme à l'échantillon Control Expert V14.1 (import à essayer)"
TAILLE_MAX = 20 * 1024 * 1024
RE_ADRESSE = re.compile(r"^%(?:I|Q|M|IW|QW|MW|KW|MD|MF|S|SW)[0-9][0-9.]*$", re.I)
RE_NOM = re.compile(r"^[A-Za-z_][A-Za-z0-9_À-ÿ]*$")


class FormatInvalide(ValueError):
    """Fichier illisible ou format non reconnu : rien n'est importé."""


@dataclass
class VariableCE:
    nom: str = ""                 # vide pour une voie de réserve
    adresse: str = ""
    type: str = ""
    commentaire: str = ""
    valeur_init: str = ""


# ---------------------------------------------------------------------------- écriture
def date_ce(maintenant=None):
    t = maintenant or datetime.datetime.now()
    return f"date_and_time#{t.year}-{t.month}-{t.day}-{t.hour}:{t.minute:02d}:{t.second:02d}"


def _verifier(v):
    if v.nom and not RE_NOM.fullmatch(v.nom):
        raise FormatInvalide(f"Nom de variable invalide pour Control Expert : « {v.nom} ».")
    if v.nom and len(v.nom) > 32:
        raise FormatInvalide(f"Nom de plus de 32 caractères : « {v.nom} ».")
    if v.adresse and not RE_ADRESSE.fullmatch(v.adresse):
        raise FormatInvalide(f"Adresse invalide : « {v.adresse} » ({v.nom or 'réserve'}).")
    if not v.type:
        raise FormatInvalide(f"Type manquant pour {v.nom or v.adresse}.")
    if not v.nom and not v.adresse:
        raise FormatInvalide("Une variable sans nom doit avoir une adresse (voie de réserve).")


def xsy(variables, projet, version="0.0.001", commentaire="", produit="OGIAS", maintenant=None):
    """Texte XSY (fins de ligne CRLF) au format de l'export Control Expert."""
    noms = set()
    for v in variables:
        _verifier(v)
        if v.nom:
            if v.nom.upper() in noms:
                raise FormatInvalide(f"Variable en double : {v.nom}.")
            noms.add(v.nom.upper())
    date = date_ce(maintenant)
    l = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', "<VariablesExchangeFile>",
         f'\t<fileHeader company="Schneider Automation" product={quoteattr(produit)} dateTime="{date}" '
         'content="Fichier source variables" DTDVersion="41"></fileHeader>',
         f'\t<contentHeader name={quoteattr(projet)} version={quoteattr(version)} dateTime="{date}">']
    if commentaire:
        l.append(f"\t\t<comment>{escape(commentaire)}</comment>")
    l += ["\t</contentHeader>", "\t<dataBlock>"]
    for v in variables:
        if v.nom:
            attrs = f"name={quoteattr(v.nom)} typeName={quoteattr(v.type)}"
            if v.adresse:
                attrs += f" topologicalAddress={quoteattr(v.adresse.upper())}"
        else:
            attrs = f"topologicalAddress={quoteattr(v.adresse.upper())} typeName={quoteattr(v.type)}"
        l.append(f"\t\t<variables {attrs}>")
        l.append(f"\t\t\t<comment>{escape(v.commentaire)}</comment>")
        if v.valeur_init:
            l.append(f"\t\t\t<variableInit value={quoteattr(v.valeur_init)} />")
        l.append("\t\t</variables>")
    l += ["\t</dataBlock>", "</VariablesExchangeFile>", ""]
    return "\r\n".join(l)


def txt(variables):
    """Texte TXT (tabulations, CRLF) au format de l'export Control Expert."""
    for v in variables:
        _verifier(v)
    return "".join(f'{v.nom}\t{v.adresse.upper()}\t{v.type}\t"{v.commentaire}"\t'
                   f'{"(" + v.valeur_init + ")" if v.valeur_init else ""}\r\n' for v in variables)


def reserve(adresse, type_):
    return VariableCE("", adresse, type_, " RESERVE ")


# ---------------------------------------------------------------------------- lecture
def _texte(chemin):
    with open(chemin, "rb") as f:
        data = f.read(TAILLE_MAX + 1)
    if len(data) > TAILLE_MAX:
        raise FormatInvalide("Fichier trop volumineux (plus de 20 Mo).")
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise FormatInvalide("Encodage non reconnu (UTF-8 ou Windows-1252 attendu).")


def lire_xsy(chemin):
    try:
        racine = ET.fromstring(_texte(chemin).encode("utf-8"))
    except ET.ParseError as exc:
        raise FormatInvalide(f"XSY illisible : {exc}.") from exc
    if racine.tag != "VariablesExchangeFile":
        raise FormatInvalide("Ce fichier n'est pas un export de variables Control Expert (VariablesExchangeFile).")
    sortie = []
    for x in racine.iter("variables"):
        init = x.find("variableInit")
        sortie.append(VariableCE(x.get("name", ""), x.get("topologicalAddress", ""), x.get("typeName", ""),
                                 (x.findtext("comment") or ""), init.get("value", "") if init is not None else ""))
    return sortie


def lire_txt(chemin):
    sortie = []
    for i, ligne in enumerate(_texte(chemin).splitlines(), 1):
        if not ligne.strip():
            continue
        c = ligne.split("\t")
        if len(c) < 3:
            raise FormatInvalide(f"Ligne {i} : au moins nom, adresse et type séparés par des tabulations attendus.")
        com = c[3].strip() if len(c) > 3 else ""
        if len(com) >= 2 and com[0] == com[-1] == '"':
            com = com[1:-1]
        init = c[4].strip() if len(c) > 4 else ""
        if init.startswith("(") and init.endswith(")"):
            init = init[1:-1]
        sortie.append(VariableCE(c[0].strip(), c[1].strip(), c[2].strip(), com, init))
    return sortie


RE_SCY = re.compile(r"^\s*(?P<nom>[A-Za-z_][\wÀ-ÿ]*)?\s*(?:AT\s+(?P<adr>%[\w.]+))?\s*:\s*(?P<type>[^:(;]+?)"
                    r"\s*(?:\(\*(?P<com>.*?)\*\))?\s*(?::=\s*(?P<init>.*?))?\s*;\s*$")


def lire_scy(chemin):
    texte = _texte(chemin)
    if "VAR_GLOBAL" not in texte:
        raise FormatInvalide("SCY sans bloc VAR_GLOBAL : format non reconnu.")
    bloc = texte.split("VAR_GLOBAL", 1)[1].split("END_VAR", 1)[0]
    sortie = []
    for ligne in bloc.splitlines():
        m = RE_SCY.match(ligne)
        if m and (m.group("nom") or m.group("adr")):
            init = (m.group("init") or "").strip()
            if init.startswith("(") and init.endswith(")"):
                init = init[1:-1]
            sortie.append(VariableCE(m.group("nom") or "", m.group("adr") or "", m.group("type").strip(),
                                     m.group("com") or "", init))
    return sortie


def lire(chemin):
    """Variables d'un export Control Expert (.xsy, .txt, .scy). Le .xvm, chiffré, est refusé."""
    ext = str(chemin).lower().rsplit(".", 1)[-1]
    if ext == "xvm":
        raise FormatInvalide("Le format XVM est chiffré par Control Expert : exportez les variables en XSY, TXT ou SCY.")
    lecteurs = {"xsy": lire_xsy, "txt": lire_txt, "scy": lire_scy}
    if ext not in lecteurs:
        raise FormatInvalide("Format attendu : .xsy, .txt ou .scy (export des variables de Control Expert).")
    return lecteurs[ext](chemin)
