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

Lot 1 : liste des E/S physiques, fichiers texte à colonnes (CSV, TXT). Stockage : `formats_appris/index.json` dans le
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

NATURES = {"es_physiques": "Liste des E/S physiques"}
DESTINATION = {"es_physiques": "automate"}
SEPARATEURS = {";": "Point-virgule", ",": "Virgule", "\t": "Tabulation", "|": "Barre verticale"}
CHAMPS = {
    "nom": "Nom de l'E/S", "adresse": "Adresse (selon la règle d'adresse)", "type": "Type (table de correspondance)",
    "sens": "Sens (table de correspondance)", "libelle": "Désignation", "repere": "Repère de l'équipement",
    "module": "Module (rack.emplacement)", "voie": "Voie", "variable": "Variable d'échange liée",
    "fixe": "Valeur fixe (celle de l'exemple)", "vide": "Laissée vide",
}
NATURES_VOIE = ("ET", "ST", "EA", "SA")
JETONS = {"ADRESSE": "Adresse d'OGIAS (%I0.3.5)", "RACK": "Rack", "EMPLACEMENT": "Emplacement du module",
          "VOIE": "Voie", "OCTET": "Décalage + emplacement × taille + voie ÷ 8", "BIT": "Voie modulo 8",
          "MOT": "Décalage + emplacement × taille + voie × 2"}
TAILLE_MAX = 2 * 1024 * 1024
RE_JETON = re.compile(r"\{([A-Z]+)\}")


class FormatRefuse(ValueError):
    """Fichier, réglage ou export refusé : le message s'affiche tel quel."""


# --------------------------------------------------------------------------------------------- analyse de l'exemple
def _sans_accent(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


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


def _proposer_champ(titre: str, valeurs: list[str]) -> str:
    t = _sans_accent(titre)
    for champ, indices in INDICES_TITRE:
        if any(i in t for i in indices):
            return champ
    pleines = [v for v in valeurs if v.strip()]
    if not pleines:
        return "vide"
    if all(RE_ADR_SCHNEIDER.match(v) or RE_ADR_OCTET_BIT.match(v) for v in pleines):
        return "adresse"
    if len(set(pleines)) == 1 and len(pleines) == len(valeurs):
        return "fixe"
    return "vide"


def _proposer_adresse(exemple: str) -> dict:
    """Règle d'adresse proposée d'après une adresse de l'exemple (à confirmer)."""
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


def _proposer_table(valeurs: list[str], champ: str) -> dict:
    """Table nature de voie → valeur cible, proposée d'après les valeurs distinctes de la colonne."""
    distinctes = list(dict.fromkeys(v.strip() for v in valeurs if v.strip()))
    if champ == "type":
        tor = next((v for v in distinctes if _sans_accent(v) in ("bool", "ebool", "bit", "digital", "di", "do", "tor")), "")
        ana = next((v for v in distinctes if _sans_accent(v) in ("int", "word", "uint", "dint", "real", "analog", "ai", "ao")), "")
        return {"ET": tor, "ST": tor, "EA": ana, "SA": ana}
    entree = next((v for v in distinctes if _sans_accent(v) in ("input", "in", "entree", "e", "i")), "")
    sortie = next((v for v in distinctes if _sans_accent(v) in ("output", "out", "sortie", "s", "o", "q")), "")
    return {"ET": entree, "EA": entree, "ST": sortie, "SA": sortie}


def _lire(texte: str, separateur: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(texte), delimiter=separateur, quotechar='"'))


def analyser(octets: bytes, nom_fichier: str = "", entete_index: int | None = None) -> dict:
    """Structure du fichier exemple et propositions (rien n'est enregistré)."""
    if not octets or len(octets) > TAILLE_MAX:
        raise FormatRefuse("Fichier vide ou trop volumineux (2 Mo au plus).")
    try:
        texte, encodage = ml.decoder(octets)
    except ml.ModeleRefuse as exc:
        raise FormatRefuse(str(exc)) from None
    if texte.lstrip().startswith("<"):
        raise FormatRefuse("Fichier XML : ce premier lot apprend les fichiers texte à colonnes (CSV, TXT). "
                           "Exportez la liste des E/S en CSV depuis l'outil, ou attendez le lot XML.")
    fin_ligne = "\r\n" if "\r\n" in texte else "\n"
    lignes = texte.split(fin_ligne)
    fin_fichier = bool(lignes) and lignes[-1] == ""
    if fin_fichier:
        lignes = lignes[:-1]
    pleines = [x for x in lignes if x.strip()]
    if len(pleines) < 2:
        raise FormatRefuse("Il faut au moins une ligne d'en-tête et une ligne d'E/S dans l'exemple.")
    # Séparateur : celui qui donne le plus de colonnes sur le bloc final de lignes de même largeur (l'en-tête et les
    # E/S) ; les lignes de commentaire avant l'en-tête n'entrent pas dans ce bloc.
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
                           "verticale, même nombre de colonnes sur chaque ligne d'E/S).")
    if entete_index is None:
        entete_index = debut
    if not 0 <= entete_index < len(lignes) - 1:
        raise FormatRefuse("Ligne d'en-tête hors du fichier.")
    titres = _lire(lignes[entete_index], meilleur)[0]
    donnees = [_lire(x, meilleur)[0] for x in lignes[entete_index + 1:] if x.strip()]
    if not donnees or any(len(r) != len(titres) for r in donnees):
        raise FormatRefuse("Les lignes d'E/S n'ont pas toutes le même nombre de colonnes que l'en-tête : "
                           "choisissez une autre ligne d'en-tête.")
    brutes = [x for x in lignes[entete_index + 1:] if x.strip()]
    guillemets = sum(x.count('"') for x in brutes) >= len(brutes) * len(titres) * 2
    colonnes = []
    for k, titre in enumerate(titres):
        valeurs = [r[k] for r in donnees]
        champ = _proposer_champ(titre, valeurs)
        colonnes.append({"titre": titre, "exemples": list(dict.fromkeys(v for v in valeurs if v))[:3],
                         "champ": champ, "valeur": valeurs[0] if champ == "fixe" else "", "valeurs": valeurs})
    col_adr = next((c for c in colonnes if c["champ"] == "adresse"), None)
    adresse = _proposer_adresse(col_adr["exemples"][0] if col_adr and col_adr["exemples"] else "")
    adresse.update({"decalage": 0, "taille": 4})
    col_type = next((c for c in colonnes if c["champ"] == "type"), None)
    col_sens = next((c for c in colonnes if c["champ"] == "sens"), None)
    alertes = []
    if not col_adr:
        alertes.append("Aucune colonne d'adresse reconnue : choisissez-la, sinon le fichier n'aura pas d'adresse.")
    elif not adresse["reconnue"]:
        alertes.append(f"Forme d'adresse non reconnue (« {col_adr['exemples'][0] if col_adr['exemples'] else ''} ») : "
                       "décrivez-la avec les jetons, sinon l'adresse d'OGIAS est recopiée telle quelle.")
    if not any(c["champ"] == "nom" for c in colonnes):
        alertes.append("Aucune colonne de nom reconnue : choisissez-la.")
    for c in colonnes:
        if c["champ"] == "vide" and any(v.strip() for v in c["valeurs"]):
            alertes.append(f"Colonne « {c['titre']} » non reconnue : elle restera vide (choisissez sinon son contenu).")
    for c in colonnes:
        c.pop("valeurs")
    return {"fichier": os.path.basename(nom_fichier or "")[:120], "encodage": encodage, "fin_ligne": fin_ligne,
            "fin_fichier": fin_fichier, "separateur": meilleur, "guillemets": guillemets,
            "preambule": lignes[:entete_index], "entete": lignes[entete_index], "entete_index": entete_index,
            "colonnes": colonnes, "adresse": adresse,
            "types": _proposer_table([r[colonnes.index(col_type)] for r in donnees] if col_type else [], "type"),
            "sens": _proposer_table([r[colonnes.index(col_sens)] for r in donnees] if col_sens else [], "sens"),
            "lignes_exemple": brutes[:8], "lignes_total": len(brutes), "alertes": alertes,
            "lignes_entete": [{"index": i, "texte": x[:160]} for i, x in enumerate(lignes[:min(len(lignes), 12)])]}


# --------------------------------------------------------------------------------------------- définition
def _texte_court(v, maxi=80) -> str:
    return str(v if v is not None else "")[:maxi]


def definir(analyse: dict, reglages: dict) -> dict:
    """Définition du format : la structure analysée par OGIAS + les choix de l'utilisateur (contrôlés)."""
    reglages = reglages or {}
    choix = reglages.get("colonnes") or [c["champ"] for c in analyse["colonnes"]]
    if len(choix) != len(analyse["colonnes"]):
        raise FormatRefuse("Une correspondance par colonne est attendue.")
    colonnes = []
    for c, champ in zip(analyse["colonnes"], choix):
        if champ not in CHAMPS:
            raise FormatRefuse(f"Contenu inconnu pour la colonne « {c['titre']} ».")
        valeur = c["exemples"][0] if champ == "fixe" and c["exemples"] else ""
        colonnes.append({"titre": c["titre"], "champ": champ, "valeur": valeur})
    for unique in ("nom", "adresse"):
        if sum(c["champ"] == unique for c in colonnes) != 1:
            raise FormatRefuse(f"Choisissez exactement une colonne « {CHAMPS[unique]} ».")
    adr = reglages.get("adresse") or analyse["adresse"]
    gabarits = {n: _texte_court((adr.get("gabarits") or {}).get(n, ""), 60) for n in NATURES_VOIE}
    for n, g in gabarits.items():
        inconnus = set(RE_JETON.findall(g)) - set(JETONS)
        if not g or inconnus:
            raise FormatRefuse(f"Règle d'adresse {n} : " + (f"jeton inconnu {', '.join(sorted(inconnus))}." if inconnus
                                                           else "à renseigner."))
    try:
        decalage, taille = int(adr.get("decalage", 0)), int(adr.get("taille", 4))
    except (TypeError, ValueError):
        raise FormatRefuse("Décalage et taille d'emplacement : nombres entiers.") from None
    if not 0 <= decalage <= 65535 or not 1 <= taille <= 256:
        raise FormatRefuse("Décalage de 0 à 65535, taille d'emplacement de 1 à 256 octets.")
    tables = {}
    for t in ("types", "sens"):
        source = reglages.get(t)
        source = source if isinstance(source, dict) else analyse[t]
        tables[t] = {n: _texte_court(source.get(n, ""), 40) for n in NATURES_VOIE}
    return {"encodage": analyse["encodage"], "fin_ligne": analyse["fin_ligne"], "fin_fichier": analyse["fin_fichier"],
            "separateur": analyse["separateur"], "guillemets": bool(analyse["guillemets"]),
            "preambule": analyse["preambule"], "entete": analyse["entete"], "colonnes": colonnes,
            "adresse": {"gabarits": gabarits, "decalage": decalage, "taille": taille}, **tables}


def empreinte(definition: dict) -> str:
    cles = ("encodage", "fin_ligne", "fin_fichier", "separateur", "guillemets", "preambule", "entete", "colonnes",
            "adresse", "types", "sens")
    canon = json.dumps({k: definition[k] for k in cles}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------------- production et relecture
def _jetons(p, adr: dict) -> dict:
    rack, emplacement = (p.module.split(".", 1) + [""])[:2] if p.module else ("", "")
    j = {"ADRESSE": p.adresse, "RACK": rack, "EMPLACEMENT": emplacement, "VOIE": p.voie, "OCTET": "", "BIT": "",
         "MOT": ""}
    if emplacement.isdigit() and str(p.voie).isdigit():
        base = adr["decalage"] + int(emplacement) * adr["taille"]
        v = int(p.voie)
        j.update({"OCTET": str(base + v // 8), "BIT": str(v % 8), "MOT": str(base + v * 2)})
    return j


def adresse_de(p, definition: dict) -> str:
    if not p.adresse:
        return ""
    gabarit = definition["adresse"]["gabarits"].get(p.point, "{ADRESSE}")
    j = _jetons(p, definition["adresse"])
    return RE_JETON.sub(lambda m: j.get(m.group(1), ""), gabarit)


def _valeur(champ: str, col: dict, p, session, definition: dict) -> str:
    if champ == "nom":
        return p.nom
    if champ == "adresse":
        return adresse_de(p, definition)
    if champ == "type":
        return definition["types"].get(p.point) or p.type_logique
    if champ == "sens":
        return definition["sens"].get(p.point) or ("Entrée" if p.point in ("ET", "EA") else "Sortie")
    if champ == "libelle":
        return p.designation or p.commentaire
    if champ == "repere":
        return p.repere
    if champ == "module":
        return p.module
    if champ == "voie":
        return str(p.voie or "")
    if champ == "variable":
        return p.variable
    if champ == "fixe":
        return col["valeur"]
    return ""


def points_exportes(session) -> list:
    """E/S câblées de l'ouvrage (une E/S de communication n'a pas de voie physique)."""
    return [p for p in session.points() if p.raccordement != "Communication"]


def produire_texte(definition: dict, session, points=None) -> str:
    points = points_exportes(session) if points is None else points
    sortie = io.StringIO()
    w = csv.writer(sortie, delimiter=definition["separateur"], quotechar='"', lineterminator=definition["fin_ligne"],
                   quoting=csv.QUOTE_ALL if definition["guillemets"] else csv.QUOTE_MINIMAL)
    for p in points:
        w.writerow([_valeur(c["champ"], c, p, session, definition) for c in definition["colonnes"]])
    fl = definition["fin_ligne"]
    tete = fl.join([*definition["preambule"], definition["entete"]]) + fl
    corps = sortie.getvalue()
    if not definition["fin_fichier"] and corps.endswith(fl):
        corps = corps[:-len(fl)]
    return tete + corps


def relire(definition: dict, texte: str, session, points=None) -> list[str]:
    """Écarts entre le fichier produit, relu avec le format, et les E/S de l'ouvrage ([] : conforme)."""
    points = points_exportes(session) if points is None else points
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
    if len(lues) != len(points):
        ecarts.append(f"{len(lues)} ligne(s) relue(s) pour {len(points)} E/S.")
    i_nom = next(k for k, c in enumerate(definition["colonnes"]) if c["champ"] == "nom")
    i_adr = next(k for k, c in enumerate(definition["colonnes"]) if c["champ"] == "adresse")
    for r, p in zip(lues, points):
        if len(r) != len(definition["colonnes"]):
            ecarts.append(f"{p.nom} : {len(r)} colonne(s) relue(s) au lieu de {len(definition['colonnes'])}.")
        elif r[i_nom] != p.nom or r[i_adr] != adresse_de(p, definition):
            ecarts.append(f"{p.nom} : nom ou adresse relus différents ({r[i_nom]} / {r[i_adr]}).")
        if len(ecarts) >= 10:
            break
    return ecarts


def controler_ouvrage(definition: dict, session) -> list[str]:
    """Refus avant export : adresses en double après conversion, adresse impossible à construire."""
    vues: dict[str, str] = {}
    refus = []
    for p in points_exportes(session):
        if not p.adresse:
            continue
        a = adresse_de(p, definition)
        gabarit = definition["adresse"]["gabarits"].get(p.point, "")
        if any(j in gabarit for j in ("{OCTET}", "{BIT}", "{MOT}")) and not _jetons(p, definition["adresse"])["OCTET"]:
            refus.append(f"{p.nom} : module « {p.module} » ou voie « {p.voie} » non numérique, adresse impossible.")
        elif a in vues:
            refus.append(f"{p.nom} et {vues[a]} : même adresse {a} après conversion (vérifiez la taille d'emplacement).")
        vues.setdefault(a, p.nom)
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


def enregistrer(nom: str, nature: str, logiciel: str, definition: dict, fichier: str = "") -> dict:
    nom = " ".join(str(nom or "").split())
    logiciel = " ".join(str(logiciel or "").split())
    if not 3 <= len(nom) <= 60:
        raise FormatRefuse("Nom du format : 3 à 60 caractères.")
    if nature not in NATURES:
        raise FormatRefuse("Nature de fichier inconnue.")
    if not 2 <= len(logiciel) <= 40:
        raise FormatRefuse("Logiciel ou automate cible : 2 à 40 caractères (ex. TIA Portal, Control Expert, "
                           "Sch - M580).")
    formats = lister()
    if any(f["nom"].casefold() == nom.casefold() for f in formats):
        raise FormatRefuse(f"Un format porte déjà le nom « {nom} ».")
    f = {"ident": uuid.uuid4().hex[:12], "nom": nom, "nature": nature, "logiciel": logiciel,
         "fichier_origine": os.path.basename(fichier or "")[:120], "cree_le": time.strftime("%d/%m/%Y %H:%M"),
         "definition": definition, "empreinte": empreinte(definition), "qualification": None}
    _ecrire([*formats, f])
    return f


def supprimer(ident: str) -> None:
    formats = lister()
    if not any(f["ident"] == ident for f in formats):
        raise FormatRefuse("Format introuvable.")
    _ecrire([f for f in formats if f["ident"] != ident])


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
    texte = produire_texte(d, session)
    ecarts = relire(d, texte, session)
    if ecarts:
        raise FormatRefuse("Export refusé : le fichier produit ne se relit pas avec le format appris ("
                           + " ; ".join(ecarts[:3]) + "). Une valeur contient peut-être le séparateur.")
    try:
        octets = texte.encode(d["encodage"])
    except UnicodeEncodeError as exc:
        raise FormatRefuse(f"Caractère « {texte[exc.start:exc.end]} » impossible à écrire en {d['encodage']}.") from None
    statut = (f"Conforme au format qualifié ({f['logiciel']} {f['qualification']['version']}) : contrôle automatique "
              "réussi." if qualifie(f) else
              f"Conforme au format appris, NON QUALIFIÉ : à importer une fois dans {f['logiciel']} puis confirmer.")
    slug = re.sub(r"[^A-Za-z0-9]+", "_", unicodedata.normalize("NFKD", f["nom"]).encode("ascii", "ignore").decode())
    ext = os.path.splitext(f.get("fichier_origine") or "")[1].lstrip(".").lower()
    ext = ext if re.fullmatch(r"[a-z0-9]{1,5}", ext or "") else "csv"
    return f"{session.nom_fichier_propose() or 'ouvrage'}_{slug.strip('_')[:40] or 'ES'}.{ext}", octets, statut


def resume(f: dict, ouvrage=None) -> dict:
    d = f["definition"]
    r = {k: f[k] for k in ("ident", "nom", "nature", "logiciel", "fichier_origine", "cree_le", "qualification")}
    r.update({"nature_libelle": NATURES.get(f["nature"], f["nature"]), "qualifie": qualifie(f),
              "separateur": SEPARATEURS.get(d["separateur"], d["separateur"]), "encodage": d["encodage"],
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
