"""Catalogue des objets (types d'équipement) et de leurs signaux.

Le catalogue d'origine est livré avec l'outil (data/catalogue_defaut.json).
Dès que l'utilisateur le modifie, une copie est enregistrée dans
Donnees/catalogue.json et c'est elle qui est utilisée ensuite.
"""

import json
import re
import os
import shutil

from . import chemins

FAMILLES = ["TS", "TC", "TM", "TR", "RTR", "CP"]          # familles de la table d'échange
# Variables internes déclarées (décision P1) : variables automate non localisées, documentées, retenues
# seulement si l'utilisateur les sélectionne (option de l'équipement ou signal propre) ; jamais
# télétransmises, jamais dans la table d'échange, aucune adresse (%MW ou autre), aucune logique imposée.
# Leur type logique est celui déclaré pour chaque signal : aucun type n'est déduit de la famille.
FAMILLES_INTERNES = ["BI", "EI", "MI", "RI"]
FAMILLES_CATALOGUE = FAMILLES + ["ES"] + FAMILLES_INTERNES  # ES : entrée-sortie locale, sans supervision
SIGNIFICATION_FAMILLES = {
    "TS": "Télésignalisation",
    "TC": "Télécommande",
    "TM": "Télémesure",
    "TR": "Téléréglage",
    "RTR": "Retour de téléréglage",
    "CP": "Télécomptage",
    "ES": "Entrée-sortie locale (sans supervision)",
    **{f: f"Variable interne déclarée {f} (non localisée, non télétransmise)" for f in FAMILLES_INTERNES},
}


def est_interne(famille):
    """Vrai pour une variable interne déclarée (BI, EI, MI, RI)."""
    return famille in FAMILLES_INTERNES


def anomalies_interne(s):
    """Règles d'une variable interne déclarée : jamais retenue sans sélection, jamais physique ni calculée
    à partir d'une E/S imposée, jamais une alarme télétransmise. Liste de messages (vide si conforme)."""
    if not est_interne(s.get("famille")):
        return []
    msg = []
    if (s.get("es") or "Interne") != "Interne":
        msg.append("une variable interne n'est portée par aucune E/S physique (point « Interne »)")
    if s.get("presence") not in ("Option", None, ""):
        msg.append("une variable interne n'est retenue que sur sélection : présence « Option » obligatoire")
    if s.get("source"):
        msg.append("une variable interne n'a pas d'E/S source (aucun calcul imposé)")
    if s.get("alarme"):
        msg.append("une variable interne n'est pas une alarme (jamais télétransmise)")
    if s.get("suffixe_es"):
        msg.append("une variable interne n'a pas de suffixe ES")
    return msg
# Codes d'organe des entrées TOR : ils s'insèrent entre le repère et la fonction (ET_…_FDC_FER)
ORGANES = ["", "BP", "FDC", "MA", "DEF"]
SIGNIFICATION_ORGANES = {"BP": "Bouton", "FDC": "Fin de course", "MA": "Retour de marche", "DEF": "Contact de défaut"}
TYPES_LOGIQUES = ["BOOL", "EBOOL", "INT", "DINT", "REAL"]
POINTS_ES = ["ET", "ST", "EA", "SA", "Interne"]
PRESENCES = ["Obligatoire", "Par défaut", "Option", "Règle"]
# Obligatoire : repris d'office ; son absence est une anomalie.
# Par défaut  : repris d'office ; son absence est un écart à examiner.
# Option      : repris seulement si l'équipement a l'option ; son absence n'est pas signalée.
# Règle       : proposé seulement par une règle fonctionnelle (voir regles.py), retenu d'office (mode auto)
#               ou après acceptation (mode proposition).

# Sens fonctionnel : une entrée sert à lire (TS, TM, CP), une sortie à commander ou régler (TC, TR).
SENS_ES = {"ET": ("TS", "CP", "ES"), "EA": ("TM", "CP", "ES"), "ST": ("TC", "ES"), "SA": ("TR", "ES")}


def sens_incoherent(famille, es):
    """Message si le point d'E/S ne correspond pas au sens de la famille, sinon chaîne vide.
    Une variable interne déclarée n'a aucun point physique : voir ``anomalies_interne``."""
    if est_interne(famille):
        return ""
    if es in SENS_ES and famille not in SENS_ES[es]:
        return f"un signal {famille} ne peut pas être porté par une {es} (attendu : {', '.join(f for f in SENS_ES[es] if f != 'ES')})"
    return ""
STATUTS = ["Validé", "À valider", "Écarté"]
CATEGORIES = ["Ouvrage", "Source", "Unité fonctionnelle", "Équipement"]
# Domaines d'équipements (champ « famille_biblio » des types) : regroupement d'affichage.
DOMAINES = ["Hydraulique", "Instrumentation", "Électricité et automatisme", "Bâtiment et sécurité", "Structure"]


class Catalogue:
    def __init__(self, types=None, signaux=None, version="", regles=None):
        self.regles = regles or []      # règles fonctionnelles (voir regles.py)
        self.types = types or []        # liste de dict : code, designation, categorie, famille_biblio, options, remarque
        self.signaux = signaux or []    # liste de dict : type, information, famille, code, type_logique, unite, es,
                                        #                 alarme, presence, option, statut, remarque
        self.version = version
        self.chemin = None

    # ------------------------------------------------------------ lecture / écriture
    @classmethod
    def charger(cls, chemin=None):
        """Charge le catalogue de l'utilisateur, ou celui d'origine s'il n'existe pas."""
        if chemin is None:
            chemin = chemins.fichier_catalogue_utilisateur()
            if not os.path.exists(chemin):
                chemin = chemins.fichier_catalogue_origine()
        with open(chemin, encoding="utf-8") as f:
            d = json.load(f)
        cat = cls(d.get("types", []), d.get("signaux", []), d.get("version", ""), d.get("regles", []))
        cat.chemin = chemin
        return cat

    def enregistrer(self, chemin=None):
        chemin = chemin or chemins.fichier_catalogue_utilisateur()
        provisoire = chemin + ".tmp"
        with open(provisoire, "w", encoding="utf-8") as f:
            json.dump({"version": self.version, "types": self.types, "signaux": self.signaux,
                       "regles": self.regles},
                      f, ensure_ascii=False, indent=1)
        os.replace(provisoire, chemin)      # écriture sûre : jamais de fichier à moitié écrit
        self.chemin = chemin

    @staticmethod
    def restaurer_origine():
        """Remplace le catalogue de l'utilisateur par celui livré avec l'outil."""
        cible = chemins.fichier_catalogue_utilisateur()
        if os.path.exists(cible):
            shutil.copy2(cible, cible + ".sauvegarde")
            os.remove(cible)
        return Catalogue.charger(chemins.fichier_catalogue_origine())

    # ------------------------------------------------------------ consultation
    def type(self, code):
        for t in self.types:
            if t["code"] == code:
                return t
        return None

    def codes_types(self):
        return [t["code"] for t in self.types]

    def designation(self, code):
        t = self.type(code)
        return t["designation"] if t else "Type inconnu"

    def signaux_du_type(self, code, avec_ecartes=False):
        return [s for s in self.signaux
                if s["type"] == code and (avec_ecartes or s.get("statut") != "Écarté")]

    def options_du_type(self, code):
        """Options prévues pour le type, dans l'ordre où elles apparaissent."""
        vues: list[str] = []
        t = self.type(code)
        if t:
            vues.extend(o for o in t.get("options", []) if o)
        for s in self.signaux_du_type(code):
            if s.get("presence") == "Option" and s.get("option") and s["option"] not in vues:
                vues.append(s["option"])
        return vues

    # ------------------------------------------------------------ contrôle du catalogue
    def anomalies(self):
        """Erreurs du catalogue lui-même (codes en double, champs vides…)."""
        msg = []
        codes = [t["code"] for t in self.types]
        for c in sorted(set(codes)):
            if codes.count(c) > 1:
                msg.append(f"Type {c} : code utilisé plusieurs fois.")
        # Même si un JSON a été édité hors interface, un type inconnu ne doit
        # jamais être traité comme un mot de 16 bits par défaut.
        from .modele import TAILLE_MOTS
        cles = {}
        for s in self.signaux:
            if s.get("statut") == "Écarté":
                continue
            if s["type"] not in codes:
                msg.append(f"Signal {s['famille']}_{s['code']} : type {s['type']} inconnu.")
            if s.get("type_logique") and s["type_logique"] not in TAILLE_MOTS:
                msg.append(f"Type {s['type']}, signal {s['famille']}_{s['code']} : "
                           f"type logique {s['type_logique']} non pris en charge.")
            for champ in ("information", "famille", "code", "type_logique", "presence"):
                if not s.get(champ):
                    msg.append(f"Type {s['type']}, signal {s.get('code', '?')} : champ « {champ} » vide.")
            if s.get("presence") == "Option" and not s.get("option"):
                msg.append(f"Type {s['type']}, signal {s['code']} : option non précisée.")
            if s.get("famille") == "ES" and s.get("es") not in ("ET", "ST", "EA", "SA"):
                msg.append(f"Type {s['type']}, E/S locale {s['code']} : point ET, ST, EA ou SA obligatoire.")
            sens = sens_incoherent(s.get("famille"), s.get("es"))
            if sens:
                msg.append(f"Type {s['type']}, signal {s['famille']}_{s['code']} : {sens}.")
            if s.get("presence") not in PRESENCES:
                msg.append(f"Type {s['type']}, signal {s['famille']}_{s['code']} : présence « {s.get('presence')} » inconnue.")
            if s.get("source"):
                src = next((x for x in self.signaux if x["type"] == s["type"] and x.get("statut") != "Écarté"
                            and f"{x['famille']}_{x['code']}" == s["source"]), None)
                if src is None or src.get("famille") != "ES":
                    msg.append(f"Type {s['type']}, signal {s['famille']}_{s['code']} : source {s['source']} "
                               "absente ou n'est pas une E/S physique (famille ES).")
                elif sens_incoherent(s.get("famille"), src.get("es")):
                    msg.append(f"Type {s['type']}, signal {s['famille']}_{s['code']} : "
                               f"{sens_incoherent(s.get('famille'), src.get('es'))}.")
            if s.get("organe") and s.get("es") != "ET":
                msg.append(f"Type {s['type']}, signal {s['code']} : un code d'organe ne s'emploie que sur une ET.")
            for m in anomalies_interne(s):
                msg.append(f"Type {s['type']}, signal {s['famille']}_{s['code']} : {m}.")
            if s.get("suffixe_es") and (s.get("es") not in ("ET", "ST", "EA", "SA")
                                        or not re.match(r"^[A-Z0-9]+(_[A-Z0-9]+)*$", s["suffixe_es"])):
                msg.append(f"Type {s['type']}, signal {s['famille']}_{s['code']} : suffixe ES « {s['suffixe_es']} » "
                           "réservé à une E/S physique, en majuscules et chiffres séparés par « _ ».")
            cle = (s["type"], s["famille"], s["code"])
            if cle in cles:
                msg.append(f"Type {s['type']} : {s['famille']}_{s['code']} en double.")
            cles[cle] = True
        from .modele import suffixe_physique
        noms_es: dict = {}
        for s in self.signaux:                         # un nom physique par E/S et par type (collision de suffixe)
            if s.get("statut") != "Écarté" and s.get("es") in ("ET", "ST", "EA", "SA") and not s.get("source"):
                k = (s["type"], s["es"], suffixe_physique(s))
                if k in noms_es:
                    msg.append(f"Type {s['type']} : {s['es']}_…_{k[2]} serait le nom physique de "
                               f"{noms_es[k]} et de {s['famille']}_{s['code']}.")
                noms_es.setdefault(k, f"{s['famille']}_{s['code']}")
        from .regles import anomalies_regles
        msg.extend(anomalies_regles(self))
        return msg
