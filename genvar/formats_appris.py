"""Formats d'export appris (orientation du 22/11/2026 : OGIAS ouvert à tout constructeur).

OGIAS n'exporte vers les logiciels des constructeurs que trois natures de fichiers : la liste des E/S physiques (pour
chaque automate), la télétransmission (pour chaque supervision) et l'IHM. Les autres pièces sont des documents
d'études propres à OGIAS. Plutôt que de coder le format de chaque constructeur, l'atelier fait APPRENDRE le format à
OGIAS une fois, à partir d'un vrai fichier exporté par l'outil du constructeur (d'un projet quelconque) :

1. analyse de la structure : encodage, séparateur, guillemets, lignes avant l'en-tête, colonnes ;
2. correspondance colonne → information d'OGIAS, proposée d'après les titres et les valeurs, confirmée par
   l'utilisateur ; une colonne non reconnue reste vide (jamais devinée) ;
3. conversions déclarées : forme de l'adresse (rack / emplacement / voie, ou octet / bit…) et tables de valeurs
   (type, sens) par nature de voie ;
4. export de l'ouvrage dans ce format, RELU aussitôt avec le format pour contrôle : un fichier qui ne se relit pas
   exactement (en-tête, nombre de lignes, noms, adresses) n'est jamais livré ;
5. qualification : un premier essai réel dans le logiciel cible, confirmé par l'utilisateur avec son compte rendu.
   Ensuite chaque export est déclaré « conforme au format qualifié » par le contrôle automatique.

Un format appris ne se modifie pas : pour le changer, on en apprend un autre (rien ne change en silence, et une
qualification reste attachée à la structure qualifiée par son empreinte).

Lot 1 : liste des E/S physiques ; lot 2 : télétransmission (chaque supervision) et IHM, à partir des variables
d'échange de l'ouvrage. Fichiers texte à colonnes (CSV, TXT) et classeurs Excel (.xlsx, ex. tables de variables
exportées par TIA Portal) : le classeur d'exemple sert alors de gabarit, conservé avec son empreinte. Stockage : `formats_appris/index.json` dans le
dossier de données de l'atelier, écriture atomique ; bibliothèque vide au premier accès.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import time
import unicodedata
import uuid

from . import chemins
from . import modeles_livrables as ml

NATURES = {"es_physiques": "Liste des E/S physiques", "teletransmission": "Télétransmission (supervision)",
           "ihm": "Variables d'IHM"}
DESTINATION = {"es_physiques": "automate", "teletransmission": "supervision", "ihm": "ihm"}
FAMILLE_LIVRABLES = {"es_physiques": "automate", "teletransmission": "supervision", "ihm": "supervision"}
SEPARATEURS = {";": "Point-virgule", ",": "Virgule", "\t": "Tabulation", "|": "Barre verticale"}
CHAMPS_ES = {
    "nom": "Nom de l'E/S", "adresse": "Adresse (selon la règle d'adresse)", "type": "Type (table de correspondance)",
    "sens": "Sens (table de correspondance)", "libelle": "Désignation", "repere": "Repère de l'équipement",
    "module": "Module (rack.emplacement)", "voie": "Voie", "variable": "Variable d'échange liée",
    "fixe": "Valeur fixe (celle de l'exemple)", "vide": "Laissée vide",
}
CHAMPS_VAR = {
    "nom": "Nom de la variable", "adresse": "Adresse (selon la règle d'adresse)", "type": "Type (table de correspondance)",
    "sens": "Accès lecture / écriture (table de correspondance)", "libelle": "Libellé de supervision",
    "commentaire": "Commentaire", "unite": "Unité", "alarme": "Alarme (valeurs apprises)", "famille": "Famille (TS, TC…)",
    "repere": "Repère de l'équipement", "variable_es": "E/S liée", "fixe": "Valeur fixe (celle de l'exemple)",
    "vide": "Laissée vide",
}
CHAMPS_NATURE = {"es_physiques": CHAMPS_ES, "teletransmission": CHAMPS_VAR, "ihm": CHAMPS_VAR}
CHAMPS = {**CHAMPS_VAR, **CHAMPS_ES}                     # libellés, pour l'affichage d'un format enregistré
CLES = {"es_physiques": ("ET", "ST", "EA", "SA"), "teletransmission": ("TS", "TC", "TM", "TR", "RTR", "CP"),
        "ihm": ("TS", "TC", "TM", "TR", "RTR", "CP")}
NATURES_VOIE = CLES["es_physiques"]
JETONS_ES = {"ADRESSE": "Adresse d'OGIAS (%I0.3.5)", "RACK": "Rack", "EMPLACEMENT": "Emplacement du module",
             "VOIE": "Voie", "OCTET": "Décalage + emplacement × taille + voie ÷ 8", "BIT": "Voie modulo 8",
             "MOT": "Décalage + emplacement × taille + voie × 2"}
JETONS_VAR = {"ADRESSE": "Adresse automate d'OGIAS (%MW1000.3)", "MOT": "Numéro du mot (1000)",
              "BIT": "Rang du bit (3) : variables TOR seulement",
              "REGISTRE": "Registre de télétransmission : mot + décalage Modbus de l'ouvrage"}
JETONS_NATURE = {"es_physiques": JETONS_ES, "teletransmission": JETONS_VAR, "ihm": JETONS_VAR}
JETONS = JETONS_ES
LIBELLE_SENS = {"es_physiques": "Sens", "teletransmission": "Accès", "ihm": "Accès"}
ECRITURE = ("TC", "TR")                                   # familles écrites par la supervision (commande, consigne)
TAILLE_MAX = 2 * 1024 * 1024
RE_JETON = re.compile(r"\{([A-Z]+)\}")
RE_MW = re.compile(r"^%MW(\d+)(?:\.(\d+))?$", re.I)


def specification(nature: str) -> dict:
    """Ce que l'interface doit savoir d'une nature : clés des tables, contenus possibles, jetons d'adresse."""
    return {"libelle": NATURES[nature], "cles": list(CLES[nature]), "champs": CHAMPS_NATURE[nature],
            "jetons": JETONS_NATURE[nature], "sens": LIBELLE_SENS[nature], "alarme": nature != "es_physiques",
            "destination": DESTINATION[nature]}


class FormatRefuse(ValueError):
    """Fichier, réglage ou export refusé : le message s'affiche tel quel."""


# --------------------------------------------------------------------------------------------- analyse de l'exemple
def _sans_accent(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


INDICES_VAR = [
    ("alarme", ("alarme", "alarm")),
    ("unite", ("unite", "unit", "eng. unit")),
    ("adresse", ("adresse", "address", "addr", "adr", "registre", "register", "offset")),
    ("type", ("data type", "datatype", "type de donnee", "type")),
    ("sens", ("acces", "access", "lecture", "read", "r/w", "direction")),
    ("commentaire", ("commentaire", "comment")),
    ("libelle", ("libelle", "description", "label", "texte", "text", "designation")),
    ("famille", ("famille", "family")),
    ("repere", ("equipement", "repere", "device", "objet", "object")),
    ("nom", ("nom", "name", "symbol", "symbole", "tag", "mnemonique", "variable", "mnemonic", "item")),
]
INDICES_TITRE = [
    ("adresse", ("adresse", "address", "addr", "adr", "topological")),
    ("type", ("data type", "datatype", "type de donnee", "type")),
    ("sens", ("direction", "sens", "entree/sortie", "in/out", "i/o")),
    ("libelle", ("commentaire", "comment", "description", "libelle", "designation", "label", "texte")),
    ("repere", ("equipement", "repere", "device", "objet", "object")),
    ("module", ("module", "carte", "card", "rack.emplacement")),
    ("voie", ("voie", "channel", "canal")),
    ("variable", ("variable d'echange", "variable liee")),
    ("nom", ("nom", "name", "symbol", "symbole", "tag", "mnemonique", "variable", "mnemonic")),
]
RE_ADR_SCHNEIDER = re.compile(r"^%[IQ]W?\d+\.\d+\.\d+$", re.I)
RE_ADR_OCTET_BIT = re.compile(r"^%?([IQEA])(\d+)\.(\d+)$", re.I)


def _proposer_champ(titre: str, valeurs: list[str], nature: str = "es_physiques") -> str:
    t = _sans_accent(titre)
    for champ, indices in (INDICES_TITRE if nature == "es_physiques" else INDICES_VAR):
        # mots entiers : « Typeobject ID » n'est pas un type, « Hmi Accessible » n'est pas un accès
        if any(re.search(r"(?<![a-z0-9])" + re.escape(i) + r"(?![a-z0-9])", t) for i in indices):
            return champ
    pleines = [v for v in valeurs if v.strip()]
    if not pleines:
        return "vide"
    if nature == "es_physiques" and all(RE_ADR_SCHNEIDER.match(v) or RE_ADR_OCTET_BIT.match(v) for v in pleines):
        return "adresse"
    if nature != "es_physiques" and all(RE_MW.match(v) for v in pleines):
        return "adresse"
    if len(set(pleines)) == 1 and len(pleines) == len(valeurs):
        return "fixe"
    return "vide"


def _proposer_adresse_var(exemple: str) -> dict:
    """Variables : %MW (mot et bit) ou registre numérique ; les variables TOR (TS, TC) portent un bit."""
    bits = ("TS", "TC")
    cles = CLES["teletransmission"]
    if RE_MW.match(exemple or ""):
        return {"reconnue": "%MW mot.bit", "gabarits": {c: "%MW{MOT}.{BIT}" if c in bits else "%MW{MOT}" for c in cles}}
    if re.fullmatch(r"\d+(\.\d+)?", exemple or ""):
        return {"reconnue": "registre", "gabarits": {c: "{REGISTRE}.{BIT}" if c in bits else "{REGISTRE}" for c in cles}}
    return {"reconnue": "", "gabarits": {c: "{ADRESSE}" for c in cles}}


def _proposer_adresse(exemple: str, nature: str = "es_physiques") -> dict:
    """Règle d'adresse proposée d'après une adresse de l'exemple (à confirmer)."""
    if nature != "es_physiques":
        return _proposer_adresse_var(exemple)
    if RE_ADR_SCHNEIDER.match(exemple or ""):
        return {"reconnue": "rack.emplacement.voie",
                "gabarits": {"ET": "%I{RACK}.{EMPLACEMENT}.{VOIE}", "ST": "%Q{RACK}.{EMPLACEMENT}.{VOIE}",
                             "EA": "%IW{RACK}.{EMPLACEMENT}.{VOIE}", "SA": "%QW{RACK}.{EMPLACEMENT}.{VOIE}"}}
    m = RE_ADR_OCTET_BIT.match(exemple or "")
    if m:
        pct = "%" if exemple.startswith("%") else ""
        e, s = ("E", "A") if m.group(1).upper() in "EA" else ("I", "Q")
        return {"reconnue": "octet.bit",
                "gabarits": {"ET": f"{pct}{e}{{OCTET}}.{{BIT}}", "ST": f"{pct}{s}{{OCTET}}.{{BIT}}",
                             "EA": f"{pct}{e}W{{MOT}}", "SA": f"{pct}{s}W{{MOT}}"}}
    return {"reconnue": "", "gabarits": {n: "{ADRESSE}" for n in NATURES_VOIE}}


def _proposer_table_var(distinctes: list[str], champ: str) -> dict:
    def premier(*noms):
        return next((v for v in distinctes if _sans_accent(v) in noms), "")
    if champ == "type":
        tor = premier("bool", "ebool", "bit", "digital", "boolean", "tor")
        reel = premier("real", "float", "float32", "analog", "reel") or premier("int", "word", "integer")
        entier = premier("dint", "long", "int32", "udint") or premier("int", "word", "integer", "uint")
        return {"TS": tor, "TC": tor, "TM": reel, "TR": reel, "RTR": reel, "CP": entier}
    lecture = premier("r", "read", "lecture", "ro", "l", "read only", "input")
    ecriture = premier("w", "rw", "r/w", "write", "ecriture", "read/write", "e", "output")
    return {c: (ecriture if c in ECRITURE else lecture) for c in CLES["teletransmission"]}


def _proposer_alarme(valeurs: list[str]) -> dict:
    distinctes = {_sans_accent(v): v for v in valeurs if v.strip()}
    for oui, non in (("1", "0"), ("true", "false"), ("oui", "non"), ("yes", "no"), ("y", "n"), ("o", "n"), ("x", "")):
        if oui in distinctes and (non in distinctes or not non):
            return {"oui": distinctes[oui], "non": distinctes.get(non, "")}
    return {"oui": "", "non": ""}


def _proposer_table(valeurs: list[str], champ: str, nature: str = "es_physiques") -> dict:
    """Table clé (nature de voie, ou famille de variable) → valeur cible, d'après les valeurs de la colonne."""
    distinctes = list(dict.fromkeys(v.strip() for v in valeurs if v.strip()))
    if nature != "es_physiques":
        return _proposer_table_var(distinctes, champ)
    if champ == "type":
        tor = next((v for v in distinctes if _sans_accent(v) in ("bool", "ebool", "bit", "digital", "di", "do", "tor")), "")
        ana = next((v for v in distinctes if _sans_accent(v) in ("int", "word", "uint", "dint", "real", "analog", "ai", "ao")), "")
        return {"ET": tor, "ST": tor, "EA": ana, "SA": ana}
    entree = next((v for v in distinctes if _sans_accent(v) in ("input", "in", "entree", "e", "i")), "")
    sortie = next((v for v in distinctes if _sans_accent(v) in ("output", "out", "sortie", "s", "o", "q")), "")
    return {"ET": entree, "EA": entree, "ST": sortie, "SA": sortie}


def _lire(texte: str, separateur: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(texte), delimiter=separateur, quotechar='"'))


def _structure_texte(octets: bytes, entete_index: int | None) -> dict:
    try:
        texte, encodage = ml.decoder(octets)
    except ml.ModeleRefuse as exc:
        raise FormatRefuse(str(exc)) from None
    if texte.lstrip().startswith("<"):
        raise FormatRefuse("Fichier XML : OGIAS apprend les fichiers à colonnes (CSV, TXT) et les classeurs Excel "
                           "(.xlsx). Exportez la liste depuis l'outil dans l'un de ces formats.")
    fin_ligne = "\r\n" if "\r\n" in texte else "\n"
    lignes = texte.split(fin_ligne)
    fin_fichier = bool(lignes) and lignes[-1] == ""
    if fin_fichier:
        lignes = lignes[:-1]
    pleines = [x for x in lignes if x.strip()]
    if len(pleines) < 2:
        raise FormatRefuse("Il faut au moins une ligne d'en-tête et une ligne de données dans l'exemple.")
    # Séparateur : celui qui donne le plus de colonnes sur le bloc final de lignes de même largeur (l'en-tête et les
    # données) ; les lignes de commentaire avant l'en-tête n'entrent pas dans ce bloc.
    meilleur, score, debut = "", (0, 0), 0
    indices = [i for i, x in enumerate(lignes) if x.strip()]
    for sep in SEPARATEURS:
        largeurs = {i: len(_lire(lignes[i], sep)[0]) for i in indices}
        n = largeurs[indices[-1]]
        bloc = 0
        for i in reversed(indices):
            if largeurs[i] != n:
                break
            bloc += 1
        if n > 1 and bloc >= 2 and (n, bloc) > score:
            meilleur, score, debut = sep, (n, bloc), indices[-bloc]
    if not meilleur:
        raise FormatRefuse("Séparateur de colonnes introuvable (point-virgule, virgule, tabulation ou barre "
                           "verticale, même nombre de colonnes sur chaque ligne).")
    if entete_index is None:
        entete_index = debut
    if not 0 <= entete_index < len(lignes) - 1:
        raise FormatRefuse("Ligne d'en-tête hors du fichier.")
    titres = _lire(lignes[entete_index], meilleur)[0]
    donnees = [_lire(x, meilleur)[0] for x in lignes[entete_index + 1:] if x.strip()]
    if not donnees or any(len(r) != len(titres) for r in donnees):
        raise FormatRefuse("Les lignes de données n'ont pas toutes le même nombre de colonnes que l'en-tête : "
                           "choisissez une autre ligne d'en-tête.")
    brutes = [x for x in lignes[entete_index + 1:] if x.strip()]
    return {"type_fichier": "texte", "encodage": encodage, "fin_ligne": fin_ligne, "fin_fichier": fin_fichier,
            "separateur": meilleur, "guillemets": sum(x.count('"') for x in brutes) >= len(brutes) * len(titres) * 2,
            "preambule": lignes[:entete_index], "entete": lignes[entete_index], "entete_index": entete_index,
            "titres": titres, "donnees": donnees, "types_premiere": [None] * len(titres),
            "lignes_exemple": brutes[:8], "lignes_total": len(brutes), "feuille": "", "feuilles": [],
            "lignes_entete": [{"index": i, "texte": x[:160]} for i, x in enumerate(lignes[:min(len(lignes), 12)])]}


def _cellule(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _ouvrir_classeur(octets: bytes):
    import openpyxl
    try:
        return openpyxl.load_workbook(io.BytesIO(octets))
    except Exception as exc:                                 # noqa: BLE001 — fichier fourni : refus motivé
        raise FormatRefuse(f"Classeur Excel illisible ({exc.__class__.__name__}).") from None


def _lignes_feuille(ws) -> list[list]:
    lignes = [list(r) for r in ws.iter_rows(values_only=True)]
    largeur = max((max((i + 1 for i, v in enumerate(r) if v not in (None, "")), default=0) for r in lignes), default=0)
    return [(r + [None] * largeur)[:largeur] for r in lignes]


def _structure_xlsx(octets: bytes, entete_index: int | None, feuille: str | None) -> dict:
    wb = _ouvrir_classeur(octets)
    noms = wb.sheetnames
    if feuille and feuille not in noms:
        raise FormatRefuse(f"Feuille « {feuille} » absente du classeur.")
    if not feuille:                          # la feuille qui a le plus de lignes remplies
        feuille = max(noms, key=lambda n: sum(1 for r in _lignes_feuille(wb[n]) if any(v not in (None, "") for v in r)))
    lignes = _lignes_feuille(wb[feuille])
    pleines = [i for i, r in enumerate(lignes) if any(v not in (None, "") for v in r)]
    if len(pleines) < 2:
        raise FormatRefuse(f"Feuille « {feuille} » : il faut au moins une ligne d'en-tête et une ligne de données.")
    if entete_index is None:                 # première ligne la plus remplie
        largeur = max(sum(v not in (None, "") for v in lignes[i]) for i in pleines)
        entete_index = next(i for i in pleines if sum(v not in (None, "") for v in lignes[i]) == largeur)
    if not 0 <= entete_index < len(lignes) - 1:
        raise FormatRefuse("Ligne d'en-tête hors de la feuille.")
    n = max((i + 1 for i, v in enumerate(lignes[entete_index]) if v not in (None, "")), default=0)
    titres = [_cellule(v) for v in lignes[entete_index][:n]]
    typees = [r[:n] for r in lignes[entete_index + 1:] if any(v not in (None, "") for v in r)]
    if not typees:
        raise FormatRefuse("Aucune ligne de données sous l'en-tête choisi.")
    donnees = [[_cellule(v) for v in r] for r in typees]
    return {"type_fichier": "xlsx", "encodage": "", "fin_ligne": "", "fin_fichier": False, "separateur": "",
            "guillemets": False, "preambule": [[_cellule(v) for v in r] for r in lignes[:entete_index]],
            "entete": titres, "entete_index": entete_index, "titres": titres, "donnees": donnees,
            "types_premiere": [v if isinstance(v, (bool, int, float)) else None for v in typees[0]],
            "lignes_exemple": [" | ".join(r) for r in donnees[:8]], "lignes_total": len(donnees),
            "feuille": feuille, "feuilles": noms,
            "lignes_entete": [{"index": i, "texte": " | ".join(_cellule(v) for v in r)[:160]}
                              for i, r in enumerate(lignes[:min(len(lignes), 12)])]}


def analyser(octets: bytes, nom_fichier: str = "", entete_index: int | None = None,
             nature: str = "es_physiques", feuille: str | None = None) -> dict:
    """Structure du fichier exemple (texte à colonnes ou classeur Excel) et propositions pour la nature demandée.
    Rien n'est enregistré."""
    if nature not in NATURES:
        raise FormatRefuse("Nature de fichier inconnue.")
    if not octets or len(octets) > TAILLE_MAX:
        raise FormatRefuse("Fichier vide ou trop volumineux (2 Mo au plus).")
    s = _structure_xlsx(octets, entete_index, feuille) if octets[:4] == b"PK\x03\x04" \
        else _structure_texte(octets, entete_index)
    titres, donnees = s["titres"], s["donnees"]
    colonnes = []
    for k, titre in enumerate(titres):
        valeurs = [r[k] for r in donnees]
        champ = _proposer_champ(titre, valeurs, nature)
        valeur = s["types_premiere"][k] if s["types_premiere"][k] is not None else valeurs[0]
        colonnes.append({"titre": titre, "exemples": list(dict.fromkeys(v for v in valeurs if v))[:3],
                         "champ": champ, "valeur": valeur if champ == "fixe" else "", "valeurs": valeurs,
                         "valeur_exemple": valeur})
    col_adr = next((c for c in colonnes if c["champ"] == "adresse"), None)
    adresse = _proposer_adresse(col_adr["exemples"][0] if col_adr and col_adr["exemples"] else "", nature)
    adresse.update({"decalage": 0, "taille": 4})
    col_type = next((c for c in colonnes if c["champ"] == "type"), None)
    col_sens = next((c for c in colonnes if c["champ"] == "sens"), None)
    col_alarme = next((c for c in colonnes if c["champ"] == "alarme"), None)
    alertes = []
    if not col_adr:
        alertes.append("Aucune colonne d'adresse reconnue : choisissez-la, sinon le fichier n'aura pas d'adresse.")
    elif not adresse["reconnue"]:
        alertes.append(f"Forme d'adresse non reconnue (« {col_adr['exemples'][0] if col_adr['exemples'] else ''} ») : "
                       "décrivez-la avec les jetons, sinon l'adresse d'OGIAS est recopiée telle quelle.")
    if not any(c["champ"] == "nom" for c in colonnes):
        alertes.append("Aucune colonne de nom reconnue : choisissez-la.")
    if nature != "es_physiques" and col_adr and adresse["reconnue"] == "%MW mot.bit" \
            and not any(re.search(r"\.\d+$", v) for v in col_adr["exemples"]):
        alertes.append("Les adresses de l'exemple n'ont pas de bit : vérifiez la règle des variables TOR (TS, TC).")
    for c in colonnes:
        if c["champ"] == "vide" and any(v.strip() for v in c["valeurs"]):
            alertes.append(f"Colonne « {c['titre']} » non reconnue : elle restera vide (choisissez sinon son contenu).")
    def valeurs_de(col):
        return [r[colonnes.index(col)] for r in donnees] if col else []
    types = _proposer_table(valeurs_de(col_type), "type", nature)
    sens = _proposer_table(valeurs_de(col_sens), "sens", nature)
    alarme = _proposer_alarme(valeurs_de(col_alarme))
    for c in colonnes:
        c.pop("valeurs")
    sortie = {k: v for k, v in s.items() if k not in ("titres", "donnees", "types_premiere")}
    sortie.update({"nature": nature, "fichier": os.path.basename(nom_fichier or "")[:120], "colonnes": colonnes,
                   "adresse": adresse, "types": types, "sens": sens, "alarme": alarme, "alertes": alertes})
    return sortie


# --------------------------------------------------------------------------------------------- définition
def _texte_court(v, maxi=80) -> str:
    return str(v if v is not None else "")[:maxi]


def definir(analyse: dict, reglages: dict) -> dict:
    """Définition du format : la structure analysée par OGIAS + les choix de l'utilisateur (contrôlés)."""
    reglages = reglages or {}
    nature = analyse.get("nature", "es_physiques")
    champs, cles = CHAMPS_NATURE[nature], CLES[nature]
    choix = reglages.get("colonnes") or [c["champ"] for c in analyse["colonnes"]]
    if len(choix) != len(analyse["colonnes"]):
        raise FormatRefuse("Une correspondance par colonne est attendue.")
    colonnes = []
    for c, champ in zip(analyse["colonnes"], choix):
        if champ not in champs:
            raise FormatRefuse(f"Contenu inconnu pour la colonne « {c['titre']} ».")
        valeur = c.get("valeur_exemple", c["exemples"][0] if c["exemples"] else "") if champ == "fixe" else ""
        colonnes.append({"titre": c["titre"], "champ": champ, "valeur": valeur})
    for unique in ("nom", "adresse"):
        if sum(c["champ"] == unique for c in colonnes) != 1:
            raise FormatRefuse(f"Choisissez exactement une colonne « {champs[unique]} ».")
    adr = reglages.get("adresse") or analyse["adresse"]
    gabarits = {n: _texte_court((adr.get("gabarits") or {}).get(n, ""), 60) for n in cles}
    for n, g in gabarits.items():
        inconnus = set(RE_JETON.findall(g)) - set(JETONS_NATURE[nature])
        if not g or inconnus:
            raise FormatRefuse(f"Règle d'adresse {n} : " + (f"jeton inconnu {', '.join(sorted(inconnus))}." if inconnus
                                                           else "à renseigner."))
    try:
        decalage, taille = int(adr.get("decalage", 0)), int(adr.get("taille", 4))
    except (TypeError, ValueError):
        raise FormatRefuse("Décalage et taille d'emplacement : nombres entiers.") from None
    if not 0 <= decalage <= 65535 or not 1 <= taille <= 256:
        raise FormatRefuse("Décalage de 0 à 65535, taille d'emplacement de 1 à 256 octets.")
    tables: dict = {}
    for t in ("types", "sens"):
        source = reglages.get(t)
        source = source if isinstance(source, dict) else analyse[t]
        tables[t] = {n: _texte_court(source.get(n, ""), 40) for n in cles}
    alarme = reglages.get("alarme")
    alarme = alarme if isinstance(alarme, dict) else (analyse.get("alarme") or {})
    autres = reglages.get("autres_feuilles") or "vider"
    if autres not in ("vider", "conserver"):
        raise FormatRefuse("Autres feuilles du classeur : « vider » ou « conserver ».")
    tables["autres_feuilles"] = autres if analyse.get("type_fichier") == "xlsx" else ""
    tables["alarme"] = {k: _texte_court(alarme.get(k, ""), 40) for k in ("oui", "non")}
    return {"nature": nature, "type_fichier": analyse.get("type_fichier", "texte"), "feuille": analyse.get("feuille", ""),
            "encodage": analyse["encodage"], "fin_ligne": analyse["fin_ligne"], "fin_fichier": analyse["fin_fichier"],
            "separateur": analyse["separateur"], "guillemets": bool(analyse["guillemets"]),
            "preambule": analyse["preambule"], "entete": analyse["entete"], "colonnes": colonnes,
            "adresse": {"gabarits": gabarits, "decalage": decalage, "taille": taille}, **tables}


def empreinte(definition: dict) -> str:
    cles = ("nature", "type_fichier", "feuille", "gabarit_sha256", "encodage", "fin_ligne", "fin_fichier",
            "separateur", "guillemets", "preambule", "entete", "colonnes", "adresse", "types", "sens", "alarme",
            "autres_feuilles")
    canon = json.dumps({k: definition.get(k) for k in cles}, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------------- production et relecture
def _nature(definition: dict) -> str:
    return definition.get("nature", "es_physiques")


def cle_de(x, nature: str) -> str:
    return x.point if nature == "es_physiques" else x.famille


def _jetons(x, definition: dict, session=None) -> dict:
    if _nature(definition) != "es_physiques":
        m = RE_MW.match(x.adresse or "")
        registre = session.registre_modbus(x.adresse).split(".")[0] if (m and session is not None) else ""
        return {"ADRESSE": x.adresse, "MOT": m.group(1) if m else "", "BIT": (m.group(2) or "") if m else "",
                "REGISTRE": registre}
    adr = definition["adresse"]
    rack, emplacement = (x.module.split(".", 1) + [""])[:2] if x.module else ("", "")
    j = {"ADRESSE": x.adresse, "RACK": rack, "EMPLACEMENT": emplacement, "VOIE": x.voie, "OCTET": "", "BIT": "",
         "MOT": ""}
    if emplacement.isdigit() and str(x.voie).isdigit():
        base = adr["decalage"] + int(emplacement) * adr["taille"]
        v = int(x.voie)
        j.update({"OCTET": str(base + v // 8), "BIT": str(v % 8), "MOT": str(base + v * 2)})
    return j


def adresse_de(x, definition: dict, session=None) -> str:
    if not x.adresse:
        return ""
    gabarit = definition["adresse"]["gabarits"].get(cle_de(x, _nature(definition)), "{ADRESSE}")
    j = _jetons(x, definition, session)
    return RE_JETON.sub(lambda m: j.get(m.group(1), ""), gabarit)


def _valeur(champ: str, col: dict, x, session, definition: dict) -> str:
    nature = _nature(definition)
    cle = cle_de(x, nature)
    if champ == "nom":
        return x.nom
    if champ == "adresse":
        return adresse_de(x, definition, session)
    if champ == "fixe":
        return col["valeur"]
    if champ == "repere":
        return x.repere
    if nature == "es_physiques":
        if champ == "type":
            return definition["types"].get(cle) or x.type_logique
        if champ == "sens":
            return definition["sens"].get(cle) or ("Entrée" if cle in ("ET", "EA") else "Sortie")
        if champ == "libelle":
            return x.designation or x.commentaire
        if champ == "module":
            return x.module
        if champ == "voie":
            return str(x.voie or "")
        if champ == "variable":
            return x.variable
        return ""
    if champ == "type":
        return definition["types"].get(cle) or x.type_logique
    if champ == "sens":
        return definition["sens"].get(cle) or ("Écriture" if cle in ECRITURE else "Lecture")
    if champ == "libelle":
        return x.libelle_topkapi
    if champ == "commentaire":
        return x.commentaire
    if champ == "unite":
        return x.unite
    if champ == "alarme":
        a = definition.get("alarme") or {}
        oui, non = str(a.get("oui") or ""), str(a.get("non") or "")
        return (oui or "Oui") if x.alarme else (non if oui else "Non")
    if champ == "famille":
        return x.famille
    if champ == "variable_es":
        return x.nom_es
    return ""


def points_exportes(session) -> list:
    """E/S câblées de l'ouvrage (une E/S de communication n'a pas de voie physique)."""
    return [p for p in session.points() if p.raccordement != "Communication"]


def elements(session, nature: str) -> list:
    """Ce que le fichier énumère : E/S câblées, ou variables d'échange (télétransmission, IHM)."""
    return points_exportes(session) if nature == "es_physiques" else list(session.variables_export())


def produire_texte(definition: dict, session, items=None) -> str:
    items = elements(session, _nature(definition)) if items is None else items
    sortie = io.StringIO()
    w = csv.writer(sortie, delimiter=definition["separateur"], quotechar='"', lineterminator=definition["fin_ligne"],
                   quoting=csv.QUOTE_ALL if definition["guillemets"] else csv.QUOTE_MINIMAL)
    for x in items:
        w.writerow([_valeur(c["champ"], c, x, session, definition) for c in definition["colonnes"]])
    fl = definition["fin_ligne"]
    tete = fl.join([*definition["preambule"], definition["entete"]]) + fl
    corps = sortie.getvalue()
    if not definition["fin_fichier"] and corps.endswith(fl):
        corps = corps[:-len(fl)]
    return tete + corps


def relire(definition: dict, texte: str, session, items=None) -> list[str]:
    """Écarts entre le fichier produit, relu avec le format, et les données de l'ouvrage ([] : conforme)."""
    items = elements(session, _nature(definition)) if items is None else items
    fl = definition["fin_ligne"]
    lignes = texte.split(fl)
    if definition["fin_fichier"] and lignes and lignes[-1] == "":
        lignes = lignes[:-1]
    n_tete = len(definition["preambule"]) + 1
    ecarts = []
    if lignes[:n_tete] != [*definition["preambule"], definition["entete"]]:
        ecarts.append("Les lignes d'en-tête ne sont pas celles du format appris.")
    corps = [x for x in lignes[n_tete:] if x != ""]
    lues = list(csv.reader(io.StringIO(fl.join(corps)), delimiter=definition["separateur"], quotechar='"'))
    quoi = "E/S" if _nature(definition) == "es_physiques" else "variable(s)"
    if len(lues) != len(items):
        ecarts.append(f"{len(lues)} ligne(s) relue(s) pour {len(items)} {quoi}.")
    i_nom = next(k for k, c in enumerate(definition["colonnes"]) if c["champ"] == "nom")
    i_adr = next(k for k, c in enumerate(definition["colonnes"]) if c["champ"] == "adresse")
    for r, x in zip(lues, items):
        if len(r) != len(definition["colonnes"]):
            ecarts.append(f"{x.nom} : {len(r)} colonne(s) relue(s) au lieu de {len(definition['colonnes'])}.")
        elif r[i_nom] != x.nom or r[i_adr] != adresse_de(x, definition, session):
            ecarts.append(f"{x.nom} : nom ou adresse relus différents ({r[i_nom]} / {r[i_adr]}).")
        if len(ecarts) >= 10:
            break
    return ecarts


def _valeur_cellule(champ: str, col: dict, x, session, definition: dict):
    v = col["valeur"] if champ == "fixe" else _valeur(champ, col, x, session, definition)
    return None if v == "" else v


def produire_xlsx(definition: dict, session, gabarit: bytes, items=None) -> bytes:
    """Le classeur d'exemple sert de gabarit : en-tête et lignes au-dessus conservés, lignes de données remplacées par
    celles de l'ouvrage. Les autres feuilles sont vidées sous leur première ligne (« vider », défaut : rien d'un autre
    projet ne part avec le livrable) ou conservées telles quelles (« conserver »)."""
    items = elements(session, _nature(definition)) if items is None else items
    wb = _ouvrir_classeur(gabarit)
    if definition["feuille"] not in wb.sheetnames:
        raise FormatRefuse(f"Feuille « {definition['feuille']} » absente du gabarit.")
    ws = wb[definition["feuille"]]
    tete = len(definition["preambule"]) + 1
    if ws.max_row > tete:
        ws.delete_rows(tete + 1, ws.max_row - tete)
    for i, x in enumerate(items):
        for j, col in enumerate(definition["colonnes"]):
            ws.cell(row=tete + 1 + i, column=j + 1, value=_valeur_cellule(col["champ"], col, x, session, definition))
    if definition.get("autres_feuilles", "vider") == "vider":
        for autre in wb.worksheets:
            if autre.title != definition["feuille"] and autre.max_row > 1:
                autre.delete_rows(2, autre.max_row - 1)
    sortie = io.BytesIO()
    wb.save(sortie)
    return sortie.getvalue()


def lignes_xlsx(definition: dict, octets: bytes) -> list[list[str]]:
    wb = _ouvrir_classeur(octets)
    if definition["feuille"] not in wb.sheetnames:
        return []
    n = len(definition["colonnes"])
    return [[_cellule(v) for v in (list(r) + [None] * n)[:n]] for r in wb[definition["feuille"]].iter_rows(values_only=True)]


def relire_xlsx(definition: dict, octets: bytes, session, items=None) -> list[str]:
    items = elements(session, _nature(definition)) if items is None else items
    lignes = lignes_xlsx(definition, octets)
    tete = len(definition["preambule"]) + 1
    ecarts = []
    attendu = [[*(r + [""] * len(definition["colonnes"]))[:len(definition["colonnes"])]] for r in definition["preambule"]]
    if [r for r in lignes[:tete - 1]] != attendu or lignes[tete - 1:tete] != [definition["entete"]]:
        ecarts.append("Les lignes d'en-tête de la feuille ne sont pas celles du format appris.")
    lues = [r for r in lignes[tete:] if any(r)]
    quoi = "E/S" if _nature(definition) == "es_physiques" else "variable(s)"
    if len(lues) != len(items):
        ecarts.append(f"{len(lues)} ligne(s) relue(s) pour {len(items)} {quoi}.")
    i_nom = next(k for k, c in enumerate(definition["colonnes"]) if c["champ"] == "nom")
    i_adr = next(k for k, c in enumerate(definition["colonnes"]) if c["champ"] == "adresse")
    for r, x in zip(lues, items):
        if r[i_nom] != x.nom or r[i_adr] != adresse_de(x, definition, session):
            ecarts.append(f"{x.nom} : nom ou adresse relus différents ({r[i_nom]} / {r[i_adr]}).")
        if len(ecarts) >= 10:
            break
    return ecarts


def produire(definition: dict, session, gabarit: bytes | None = None) -> tuple[bytes, list[str]]:
    """(octets, écarts de relecture) dans le type de fichier du format."""
    if definition.get("type_fichier") == "xlsx":
        if not gabarit:
            raise FormatRefuse("Gabarit Excel du format absent.")
        octets = produire_xlsx(definition, session, gabarit)
        return octets, relire_xlsx(definition, octets, session)
    texte = produire_texte(definition, session)
    ecarts = relire(definition, texte, session)
    try:
        return texte.encode(definition["encodage"]), ecarts
    except UnicodeEncodeError as exc:
        raise FormatRefuse(f"Caractère « {texte[exc.start:exc.end]} » impossible à écrire en "
                           f"{definition['encodage']}.") from None


def apercu_lignes(definition: dict, octets: bytes, maxi: int = 9) -> list[str]:
    if definition.get("type_fichier") == "xlsx":
        return [" | ".join(r) for r in lignes_xlsx(definition, octets)[:len(definition["preambule"]) + maxi]]
    texte = octets.decode(definition["encodage"])
    return texte.split(definition["fin_ligne"])[:len(definition["preambule"]) + maxi]


def controler_ouvrage(definition: dict, session) -> list[str]:
    """Refus avant export : donnée manquante, adresse impossible à construire, adresses en double après conversion."""
    nature = _nature(definition)
    items = elements(session, nature)
    refus = []
    if nature != "es_physiques":
        sans = [x.nom for x in items if not x.adresse]
        if sans:
            refus.append(f"{len(sans)} variable(s) sans adresse (ex. {sans[0]}) : attribuez les adresses à l'étape "
                         "Variables.")
    vues: dict[str, str] = {}
    for x in items:
        if not x.adresse:
            continue
        a = adresse_de(x, definition, session)
        gabarit = definition["adresse"]["gabarits"].get(cle_de(x, nature), "")
        j = _jetons(x, definition, session)
        manque = [k for k in RE_JETON.findall(gabarit) if not j.get(k)]
        if manque:
            refus.append(f"{x.nom} : adresse impossible avec la règle {gabarit} ({', '.join(manque)} sans valeur pour "
                         f"{x.adresse}).")
        elif a in vues:
            refus.append(f"{x.nom} et {vues[a]} : même adresse {a} après conversion"
                         + (" (vérifiez la taille d'emplacement)." if nature == "es_physiques" else "."))
        vues.setdefault(a, x.nom)
        if len(refus) >= 5:
            break
    return refus


# --------------------------------------------------------------------------------------------- bibliothèque
def dossier() -> str:
    return os.path.join(chemins.dossier_donnees(), "formats_appris")


def _index() -> str:
    return os.path.join(dossier(), "index.json")


def lister() -> list[dict]:
    if not os.path.exists(_index()):
        return []
    with open(_index(), encoding="utf-8") as fh:
        donnees = json.load(fh)
    formats = donnees.get("formats") if isinstance(donnees, dict) else None
    if not isinstance(formats, list):
        raise ValueError("Index des formats appris illisible : aucun écrasement effectué.")
    return formats


def _ecrire(formats: list[dict]) -> None:
    ml._ecrire_atomique(_index(), (json.dumps({"version": 1, "formats": formats}, ensure_ascii=False, indent=1)
                                   + "\n").encode("utf-8"))


def trouver(ident: str) -> dict | None:
    return next((f for f in lister() if f.get("ident") == ident), None)


def _gabarit_chemin(ident: str) -> str:
    if not isinstance(ident, str) or not re.fullmatch(r"[0-9a-f]{12}", ident):
        raise FormatRefuse("Format introuvable.")
    return os.path.join(dossier(), ident + ".xlsx")


def gabarit(f: dict) -> bytes | None:
    """Classeur d'exemple d'un format Excel, contrôlé par son empreinte (None pour un format texte)."""
    d = f["definition"]
    if d.get("type_fichier") != "xlsx":
        return None
    try:
        with open(_gabarit_chemin(f["ident"]), "rb") as fh:
            octets = fh.read()
    except OSError:
        raise FormatRefuse("Gabarit Excel du format introuvable : apprenez de nouveau le format.") from None
    if hashlib.sha256(octets).hexdigest() != d.get("gabarit_sha256"):
        raise FormatRefuse("Gabarit Excel du format modifié hors d'OGIAS : apprenez de nouveau le format.")
    return octets


def enregistrer(nom: str, nature: str, logiciel: str, definition: dict, fichier: str = "",
                gabarit_octets: bytes | None = None) -> dict:
    nom = " ".join(str(nom or "").split())
    logiciel = " ".join(str(logiciel or "").split())
    if not 3 <= len(nom) <= 60:
        raise FormatRefuse("Nom du format : 3 à 60 caractères.")
    if nature not in NATURES or definition.get("nature", "es_physiques") != nature:
        raise FormatRefuse("Nature de fichier inconnue.")
    if not 2 <= len(logiciel) <= 40:
        raise FormatRefuse("Logiciel cible : 2 à 40 caractères (ex. TIA Portal, Control Expert, TOPKAPI, PcVue).")
    formats = lister()
    if any(f["nom"].casefold() == nom.casefold() for f in formats):
        raise FormatRefuse(f"Un format porte déjà le nom « {nom} ».")
    ident = uuid.uuid4().hex[:12]
    if definition.get("type_fichier") == "xlsx":
        if not gabarit_octets:
            raise FormatRefuse("Classeur d'exemple absent.")
        definition = {**definition, "gabarit_sha256": hashlib.sha256(gabarit_octets).hexdigest()}
        ml._ecrire_atomique(_gabarit_chemin(ident), gabarit_octets)
    f = {"ident": ident, "nom": nom, "nature": nature, "logiciel": logiciel,
         "fichier_origine": os.path.basename(fichier or "")[:120], "cree_le": time.strftime("%d/%m/%Y %H:%M"),
         "definition": definition, "empreinte": empreinte(definition), "qualification": None}
    _ecrire([*formats, f])
    return f


def supprimer(ident: str) -> None:
    formats = lister()
    if not any(f["ident"] == ident for f in formats):
        raise FormatRefuse("Format introuvable.")
    _ecrire([f for f in formats if f["ident"] != ident])
    try:
        os.unlink(_gabarit_chemin(ident))
    except FileNotFoundError:
        pass


def qualifier(ident: str, version: str, compte_rendu: str, auteur: str = "") -> dict:
    """Premier essai réel confirmé par l'utilisateur : le format devient « qualifié » pour sa structure actuelle."""
    version = " ".join(str(version or "").split())[:60]
    compte_rendu = " ".join(str(compte_rendu or "").split())[:600]
    if len(compte_rendu) < 15:
        raise FormatRefuse("Décrivez l'essai réel (15 caractères au moins) : fichier importé, logiciel, résultat.")
    if not version:
        raise FormatRefuse("Indiquez la version du logiciel cible essayée.")
    formats = lister()
    f = next((x for x in formats if x["ident"] == ident), None)
    if f is None:
        raise FormatRefuse("Format introuvable.")
    f["qualification"] = {"le": time.strftime("%d/%m/%Y %H:%M"), "version": version, "compte_rendu": compte_rendu,
                          "auteur": " ".join(str(auteur or "").split())[:60], "empreinte": f["empreinte"]}
    _ecrire(formats)
    return f


def retirer_qualification(ident: str) -> dict:
    formats = lister()
    f = next((x for x in formats if x["ident"] == ident), None)
    if f is None:
        raise FormatRefuse("Format introuvable.")
    f["qualification"] = None
    _ecrire(formats)
    return f


def qualifie(f: dict) -> bool:
    q = f.get("qualification")
    return isinstance(q, dict) and q.get("empreinte") == empreinte(f["definition"])


def retenu(f: dict, ouvrage) -> tuple[bool, str]:
    return ml.retenu({"destination": DESTINATION[f["nature"]], "logiciel": f["logiciel"]}, ouvrage)


def exporter(f: dict, session) -> tuple[str, bytes, str]:
    """(nom de fichier, octets, statut) ; refuse tout fichier qui ne se relit pas exactement."""
    d = f["definition"]
    refus = controler_ouvrage(d, session)
    if refus:
        raise FormatRefuse("Export refusé : " + " ; ".join(refus))
    octets, ecarts = produire(d, session, gabarit(f))
    if ecarts:
        raise FormatRefuse("Export refusé : le fichier produit ne se relit pas avec le format appris ("
                           + " ; ".join(ecarts[:3]) + "). Une valeur contient peut-être le séparateur.")
    statut = (f"Conforme au format qualifié ({f['logiciel']} {f['qualification']['version']}) : contrôle automatique "
              "réussi." if qualifie(f) else
              f"Conforme au format appris, NON QUALIFIÉ : à importer une fois dans {f['logiciel']} puis confirmer.")
    slug = re.sub(r"[^A-Za-z0-9]+", "_", unicodedata.normalize("NFKD", f["nom"]).encode("ascii", "ignore").decode())
    ext = os.path.splitext(f.get("fichier_origine") or "")[1].lstrip(".").lower()
    ext = "xlsx" if d.get("type_fichier") == "xlsx" else ext if re.fullmatch(r"[a-z0-9$]{1,5}", ext or "") else "csv"
    return f"{session.nom_fichier_propose() or 'ouvrage'}_{slug.strip('_')[:40] or 'ES'}.{ext}", octets, statut


def resume(f: dict, ouvrage=None) -> dict:
    d = f["definition"]
    r = {k: f[k] for k in ("ident", "nom", "nature", "logiciel", "fichier_origine", "cree_le", "qualification")}
    r.update({"nature_libelle": NATURES.get(f["nature"], f["nature"]), "qualifie": qualifie(f),
              "cles": list(CLES[f["nature"]]), "libelle_sens": LIBELLE_SENS[f["nature"]],
              "alarme": d.get("alarme") or {"oui": "", "non": ""},
              "separateur": SEPARATEURS.get(d["separateur"], d["separateur"]), "encodage": d["encodage"],
              "type_fichier": d.get("type_fichier", "texte"), "feuille": d.get("feuille", ""),
              "autres_feuilles": d.get("autres_feuilles", ""),
              "colonnes": [{"titre": c["titre"], "champ": c["champ"], "champ_libelle": CHAMPS[c["champ"]],
                            "valeur": c["valeur"]} for c in d["colonnes"]],
              "adresse": d["adresse"], "types": d["types"], "sens": d["sens"]})
    if ouvrage is not None:
        r["retenu"], r["motif_non_retenu"] = retenu(f, ouvrage)
    return r


FORMATS_LIVRES = [
    {"nom": "Control Expert — E/S (XSY)", "nature": "es_physiques", "logiciel": "Control Expert", "export": "es_xsy"},
    {"nom": "Control Expert — E/S (TXT)", "nature": "es_physiques", "logiciel": "Control Expert", "export": "es_txt"},
]
