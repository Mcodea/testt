"""Données d'un ouvrage et génération de ses variables.

Repère d'un équipement : LIEU + OUVRAGE + SOUS-ENSEMBLE + TYPE + N°
    exemple : ATMS + RV + 11 + MV + 03  ->  ATMSRV11MV03

Nom d'une variable d'échange : FAMILLE_REPÈRE_CODE
    exemple : TS_ATMSRV11MV03_FER

Nom d'une entrée / sortie physique : POINT_REPÈRE_[ORGANE_]CODE
    exemples : ET_ATMSRV11MV03_FDC_FER (fin de course), ET_ATMSRV11MV03_BP_FER (bouton local),
               ET_ATMSRV11PM01_MA (retour de marche), ST_ATMSRV11MV03_OUV, EA_ATMSRV11LT01_NIV

Deux modes :
    Projet neuf     : on part du catalogue et de la liste des équipements, on génère
                      les E/S de l'automate et les variables de la supervision.
    Projet existant : on part des variables de l'automate (fichier .XSY), on identifie
                      leur équipement et leur fonction, sans les renommer.
"""

import json
import os
import re
import uuid
from datetime import datetime, timezone

from .catalogue import anomalies_interne, est_interne, sens_incoherent
from .regles import texte as texte_regle
from dataclasses import dataclass, field, asdict

# Zones d'adresses de la table d'échange (mots %MW de départ) : valeurs par défaut,
# modifiables dans l'onglet Paramètres de chaque ouvrage.
# Plan mémoire des projets neufs : une plage %MW par famille (premier et dernier mot, inclus).
# Les RTR sont placés en miroir des TR : même rang dans leur plage (TR %MW100 -> RTR %MW4000).
# Valeurs proposées, modifiables dans l'onglet Paramètres de chaque ouvrage.
PLAN_DEFAUT = {"TR": (100, 499), "TS": (1000, 1999), "TC": (2000, 2499), "TM": (2500, 3499),
               "CP": (3500, 3999), "RTR": (4000, 4399)}
ZONES_DEFAUT = {f: d for f, (d, _) in PLAN_DEFAUT.items()}
ZONES_FIN_DEFAUT = {f: fin for f, (_, fin) in PLAN_DEFAUT.items()}
ORDRE_ZONES = ["TR", "TS", "TC", "TM", "CP", "RTR"]      # les TR avant les RTR : le RTR suit son TR

TAILLE_MOTS = {"BOOL": 0, "EBOOL": 0, "INT": 1, "UINT": 1, "WORD": 1, "DINT": 2, "UDINT": 2, "DWORD": 2,
               "REAL": 2, "TIME": 2, "LREAL": 4}

LONGUEUR_MAX_NOM = 32          # Control Expert : 32 caractères pour une variable élémentaire
LONGUEUR_MAX_LIBELLE = 40      # standard de supervision : libellé d'alarme de 40 caractères au plus

RE_NOM = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


@dataclass
class SignalPropre:
    """Signal ajouté à un équipement précis, absent du catalogue."""
    information: str
    famille: str
    code: str
    type_logique: str = "BOOL"
    unite: str = ""
    es: str = "Interne"
    alarme: bool = False
    organe: str = ""


@dataclass
class Equipement:
    sous_ensemble: str
    type: str
    numero: str
    libelle: str = ""
    options: list = field(default_factory=list)
    exclus: list = field(default_factory=list)         # clés FAMILLE_CODE des signaux par défaut retirés
    ajouts: list = field(default_factory=list)         # SignalPropre (en dict dans le fichier)
    adresses: dict = field(default_factory=dict)       # clé FAMILLE_CODE -> adresse %MW de la table d'échange
    adresses_es: dict = field(default_factory=dict)    # clé FAMILLE_CODE -> adresse physique (%I…, %Q…, %IW…)
    ident: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    uf: str = ""                                       # unité fonctionnelle (regroupement, hors repère)
    commentaires: dict = field(default_factory=dict)   # clé FAMILLE_CODE -> commentaire saisi (remplace le texte proposé)
    libelles: dict = field(default_factory=dict)       # clé FAMILLE_CODE -> libellé de supervision saisi
    validees: list = field(default_factory=list)       # clés dont l'adresse d'échange est validée par l'automaticien
    acceptes: list = field(default_factory=list)       # signaux proposés par une règle et acceptés par l'utilisateur
    motifs: dict = field(default_factory=dict)         # clé écartée -> justification écrite par l'automaticien
    traces: dict = field(default_factory=dict)         # « niveau:clé » -> {origine, regle, le, par} (moteur d'adressage)
    es_meta: dict = field(default_factory=dict)        # clé de l'E/S -> {designation, type, raccordement, module, voie, validee}
    modele: str = ""                                   # modèle d'équipement du référentiel SOREP
    lignes_ajoutees: list = field(default_factory=list)  # lignes propres à l'équipement
    lignes_retirees: list = field(default_factory=list)  # identifiants des lignes du modèle retirées
    lignes_modifiees: dict = field(default_factory=dict) # identifiant -> ligne modifiée
    valide: bool = False                               # équipement vérifié par l'automaticien (inventaire)
    local: str = ""                                    # lieu physique (local, armoire…)

    def code_court(self):
        from .modeles import repere_fin
        return repere_fin(self.type, self.numero)


@dataclass
class SousEnsemble:
    code: str
    libelle: str = ""


@dataclass
class UniteFonctionnelle:
    """Regroupement fonctionnel d'équipements (ex. UF01 Alimentation).

    Le code de l'UF n'entre pas dans les repères ; `sous_ensemble` est le code de repère (2 caractères)
    proposé par défaut aux équipements créés dans l'UF (ex. 11). Facultatif.
    """
    code: str
    libelle: str = ""
    sous_ensemble: str = ""


@dataclass
class VariableExistante:
    """Variable lue dans le programme d'un automate existant (mode projet existant)."""
    nom: str
    type_logique: str = ""
    adresse: str = ""
    commentaire: str = ""
    retenue: bool = True            # reprise dans la supervision
    ident_eq: str = ""              # équipement de l'ouvrage
    cle: str = ""                   # signal du catalogue : FAMILLE_CODE
    identification: str = "À identifier"   # Exacte, Probable, Confirmée, À identifier, Hors supervision
    remarque: str = ""
    nature_source: str = "Principale"  # Principale ou Champ DDT
    parent_xsy: str = ""             # Variable DDT racine
    type_parent_xsy: str = ""
    adresse_parent_xsy: str = ""     # Adresse du parent, pas celle du champ
    extract_bit: str = ""            # Attribut du fichier, pas un offset calculé
    chemin_symbolique: str = ""      # Chemin OPC potentiel, non validé
    fichier_source_xsy: str = ""
    empreinte_source_xsy: str = "" # SHA256 de l’export lu, pour traçabilité
    adresse_acquisition: str = ""  # Renseignée séparément : pas déduite du parent DDT
    protocole_acquisition: str = ""  # OPC/OFS, Modbus, etc. : qualification du lien
    acces_verifie: bool = False   # Confirmation documentaire MANUELLE, pas preuve de communication


@dataclass
class Ouvrage:
    mode: str = "Neuf"              # « Neuf » ou « Existant »
    lieu: str = ""
    code_ouvrage: str = ""
    numero_ouvrage: str = ""  # 01..99 pour nouveau code ; vide = ouvrage historique conservé
    # Format du repère d'équipement : « 12 » = charte ESB/RESO du 9 novembre 2026
    # (lieu + type d'ouvrage + numéro + type + numéro, SANS sous-ensemble : ATMSRV01HV01).
    # Vide = format enregistré auparavant, conservé sans renommage (historique 12 avec sous-ensemble,
    # ou 14 caractères pour un ouvrage numéroté avant le 9 novembre).
    format_repere: str = ""
    libelle: str = ""
    automate: str = "M580"
    nom_projet: str = ""
    lieu_dans_le_nom: bool = True
    produit_xsy: str = "Control Expert"
    zones: dict = field(default_factory=lambda: dict(ZONES_DEFAUT))           # premier mot de chaque famille
    zones_fin: dict = field(default_factory=lambda: dict(ZONES_FIN_DEFAUT))   # dernier mot (inclus)
    decalage_modbus: int = 0        # registre Modbus = numéro du mot %MW + décalage (0 ou 1 selon la convention)
    sous_ensembles: list = field(default_factory=list)
    equipements: list = field(default_factory=list)
    unites: list = field(default_factory=list)          # UniteFonctionnelle
    libelle_communs: str = ""                           # nom du groupe des équipements hors UF
    modules: list = field(default_factory=list)         # cartes d'E/S déclarées (cartes_es.Module)
    modeles_snapshot: dict = field(default_factory=dict)  # modèles de supervision utilisés (copie figée)
    reserve_min: float = 0.20                           # réserve minimale de voies par module
    racks: list = field(default_factory=list)           # racks retenus : {numero, reference, positions, cpu}
    profil_cartes: str = ""                             # densité des cartes proposées (vide : profil par défaut)
    materiel_valide: bool = False                       # matériel (racks + cartes) validé par l'automaticien
    # Répartition des E/S (B3, B4) : groupes de secours confirmés par l'automaticien, jamais devinés en silence
    groupes_secours: list = field(default_factory=list)          # [[ident, ident, …]] : cartes distinctes
    groupes_secours_refuses: list = field(default_factory=list)  # propositions écartées : [[ident, …]] triés
    separation_secours: bool = True                     # B4 actif (désactivable par ouvrage)
    emplacements_libres_rack: int = 2                   # B3 : emplacements laissés libres par rack
    localisation: str = ""                              # commune / adresse du site
    type_ouvrage: str = ""                              # réservoir, station de pompage…
    environnement: str = "Control Expert"               # Control Expert, Unity Pro, PL7
    communication: str = ""                             # protocole / équipement de télégestion (ex. Modbus TCP, S4W)
    table_tt: list = field(default_factory=list)        # LigneTT : table de télétransmission (projet existant)
    existantes: list = field(default_factory=list)     # VariableExistante (mode existant)
    entrees_physiques_importees: list = field(default_factory=list)  # Sources E/S documentaires, sans modification automate
    ident_projet: str = field(default_factory=lambda: uuid.uuid4().hex)
    revision: str = "A"
    statut: str = "En cours"                 # Brouillon, En cours, À contrôler, Validé
    archive: bool = False
    cree_le: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    modifie_le: str = ""
    catalogue_snapshot: dict = field(default_factory=dict)
    # Moteur d'adressage : réservations explicites, convention protocolaire déclarée, disponibilité établie
    reservations: list = field(default_factory=list)    # {niveau: voie|memoire|protocole, cible, motif, par, le}
    protocole_declare: bool = False     # vrai quand la convention « registre = %MW + décalage » est confirmée
    disponibilite_verifiee: bool = False  # projet existant : l'import couvre toute la mémoire utilisée
    journal_adressage: list = field(default_factory=list)  # applications du moteur : date, auteur, nombres
    # Décisions de référentiel (R7) : {le, par, action, profil, version, equipement, ident_eq, detail, sauvegarde}
    journal_referentiel: list = field(default_factory=list)
    # Confirmations du rapprochement (cahier § 6) : {id, le, par, action, lignes, annule}
    journal_rapprochement: list = field(default_factory=list)
    # Historique utile à la propagation en conception (R6). None : inconnu (fichier antérieur à ces champs).
    deja_valide: bool | None = False
    deja_exporte: bool | None = False

    # ------------------------------------------------------------ repères
    def prefixe(self):
        return f"{self.lieu}{self.code_ouvrage}{self.numero_ouvrage}"

    def charte_12(self):
        """Vrai si l'ouvrage suit la charte du 9 novembre : le sous-ensemble n'entre pas dans le repère."""
        return self.format_repere == "12" and bool(self.numero_ouvrage)

    def repere(self, eq):
        if self.charte_12():
            return f"{self.prefixe()}{eq.code_court()}"
        return f"{self.prefixe()}{eq.sous_ensemble}{eq.code_court()}"

    def repere_nom(self, eq):
        """Repère tel qu'il figure dans le nom (avec ou sans le lieu, selon le paramètre)."""
        if self.lieu_dans_le_nom:
            return self.repere(eq)
        if self.charte_12():
            return f"{self.code_ouvrage}{self.numero_ouvrage}{eq.code_court()}"
        return f"{self.code_ouvrage}{self.numero_ouvrage}{eq.sous_ensemble}{eq.code_court()}"

    def libelle_sous_ensemble(self, code):
        for s in self.sous_ensembles:
            if s.code == code:
                return s.libelle
        return ""

    def equipement(self, ident):
        for e in self.equipements:
            if e.ident == ident:
                return e
        return None

    # ------------------------------------------------------------ fichier
    def vers_dict(self):
        return asdict(self)

    @classmethod
    def depuis_dict(cls, d):
        connus = set(cls.__dataclass_fields__)
        o = cls(**{k: v for k, v in d.items() if k in connus and k not in
                   ("sous_ensembles", "equipements", "zones", "zones_fin", "existantes", "unites", "table_tt",
                    "modules")})
        if "zones" in d and "zones_fin" not in d:
            # fichier de la version 0.3 ou antérieure : on garde ses zones, chacune s'arrête avant la suivante
            o.zones = {f: int(d["zones"].get(f, ZONES_DEFAUT[f])) for f in ORDRE_ZONES}
            o.zones_fin = {}
            for f in ORDRE_ZONES:
                suivants = sorted(x for x in o.zones.values() if x > o.zones[f])
                o.zones_fin[f] = suivants[0] - 1 if suivants else o.zones[f] + 999
        else:
            o.zones = dict(ZONES_DEFAUT); o.zones.update(d.get("zones", {}))
            o.zones_fin = dict(ZONES_FIN_DEFAUT); o.zones_fin.update(d.get("zones_fin", {}))
        for k in ("deja_valide", "deja_exporte"):
            if k not in d:
                setattr(o, k, None)        # fichier antérieur : historique de validation et d'export inconnu
        o.sous_ensembles = [SousEnsemble(**s) for s in d.get("sous_ensembles", [])]
        o.unites = [UniteFonctionnelle(**u) for u in d.get("unites", [])]
        from .cartes_es import Module
        o.modules = [Module(**m) for m in d.get("modules", [])]
        champs_eq = set(Equipement.__dataclass_fields__)
        for e in d.get("equipements", []):
            eq = Equipement(**{k: v for k, v in e.items() if k != "ajouts" and k in champs_eq})
            eq.ajouts = [SignalPropre(**a) for a in e.get("ajouts", [])]
            o.equipements.append(eq)
        o.existantes = [VariableExistante(**x) for x in d.get("existantes", [])]
        for v in o.existantes:          # fichiers de la version 0.2
            v.identification = {"Automatique": "Exacte", "Manuelle": "Confirmée"}.get(v.identification, v.identification)
        from .teletransmission import LigneTT
        champs_tt = set(LigneTT.__dataclass_fields__)
        o.table_tt = [LigneTT(**{k: v for k, v in x.items() if k in champs_tt}) for x in d.get("table_tt", [])]
        return o

    def enregistrer(self, chemin):
        self.modifie_le = datetime.now(timezone.utc).isoformat()
        provisoire = chemin + ".tmp"
        with open(provisoire, "w", encoding="utf-8") as f:
            json.dump({"format": "ouvrage-genvar", "version": 1, "ouvrage": self.vers_dict()},
                      f, ensure_ascii=False, indent=1)
        os.replace(provisoire, chemin)

    @classmethod
    def ouvrir(cls, chemin):
        with open(chemin, encoding="utf-8") as f:
            d = json.load(f)
        return cls.depuis_dict(d["ouvrage"])


# ====================================================================== variables
@dataclass
class Variable:
    ident_eq: str
    repere: str
    designation: str
    information: str
    famille: str
    code: str
    nom: str
    type_logique: str
    unite: str
    es: str
    alarme: bool
    commentaire: str
    libelle_topkapi: str
    adresse: str
    nom_es: str = ""
    type_es: str = ""
    adresse_es: str = ""
    origine: str = "Catalogue"      # « Catalogue » ou « Propre à l'équipement »
    commentaire_propose: str = ""   # texte du dictionnaire métier, avant saisie éventuelle
    commentaire_saisi: bool = False
    adresse_validee: bool = False
    uf: str = ""
    logique: str = ""               # traitement automate à programmer (vide : acquisition ou commande directe)
    cle_es: str = ""                # clé sous laquelle l'adresse physique est enregistrée (signal ou sa source)

    @property
    def cle(self):
        return f"{self.famille}_{self.code}"


def type_echange(famille, type_catalogue):
    """Type de la variable dans la table d'échange (%MW)."""
    if famille in ("TS", "TC"):
        return "BOOL"                   # bit d'un mot %MW
    if type_catalogue in ("BOOL", "EBOOL"):
        return "INT"
    return type_catalogue


TYPES_POINT = {"ET": ("EBOOL", "BOOL"), "ST": ("EBOOL", "BOOL"), "EA": ("INT", "UINT", "REAL"),
               "SA": ("INT", "UINT", "REAL")}
RACCORDEMENTS = ("Câblé", "Communication")


def type_point_es(es):
    return {"ET": "EBOOL", "ST": "EBOOL", "EA": "INT", "SA": "INT"}.get(es, "")


def suffixe_point(code, organe):
    """FER + FDC -> FDC_FER ; MA + MA -> MA ; DEFTH + DEF -> DEFTH ; NIV sans organe -> NIV."""
    if not organe or code.startswith(organe):
        return code
    return f"{organe}_{code}"


def suffixe_physique(s):
    """Suffixe du nom de l'E/S physique d'un signal : `suffixe_es` s'il est renseigné (collision de clé
    interne, décision D4 du référentiel V2), sinon organe + code (`suffixe_point`)."""
    if s.get("suffixe_es"):
        return s["suffixe_es"]
    return suffixe_point(s["code"], s.get("organe", "") if s.get("es") == "ET" else "")


def information_point(information, organe):
    if organe == "FDC":
        return "Fin de course " + information[:1].lower() + information[1:]
    return information


@dataclass
class PointES:
    """Entrée ou sortie physique de l'automate."""
    ident_eq: str
    repere: str
    point: str               # ET, ST, EA, SA
    nom: str
    type_logique: str
    information: str
    commentaire: str
    adresse: str
    cle: str                 # FAMILLE_CODE du signal du catalogue
    variable: str = ""       # variable d'échange liée (vide pour une E/S locale)
    designation: str = ""    # texte saisi (vide : commentaire proposé)
    raccordement: str = "Câblé"   # « Câblé » (voie d'un module) ou « Communication » (bus, sans adresse %I/%Q)
    module: str = ""         # rack.emplacement du module, ex. 0.3
    voie: str = ""           # numéro de voie sur le module
    validee: bool = False    # E/S validée sur sa voie (étape Matériel : module, voie, adresse)
    contenu_valide: bool = False   # contenu de l'E/S validé (étape Liste des E/S : nature, sens, désignation)
    uf: str = ""
    origine: str = "Catalogue"
    note: str = ""           # commentaire libre de l’automaticien, distinct de la désignation proposée
    sens: str = ""           # état de la voie à 1 (« 1 = Défaut »), R7
    organe1: str = ""        # type d'équipement (R6 : ONDULEUR)
    organe2: str = ""        # domaine du type (R6 : Électricité et automatisme)
    extension: str = ""      # code du signal en minuscules (R3)
    analogique: dict = field(default_factory=dict)  # courant/physique et brut éventuel, validés sur l'équipement
    impulsion: dict = field(default_factory=dict)   # poids, unité et front de comptage


def catalogue_pour_equipement(ouvrage, catalogue, eq):
    """Vue métier du modèle figé dans l'ouvrage, sans mutation du catalogue partagé.

    Les dossiers historiques sans « signaux » continuent d'utiliser l'ancien
    catalogue par type. Deux équipements du même type peuvent ainsi avoir des
    modèles physiques ET de télétransmission différents.
    """
    modele = ouvrage.modeles_snapshot.get(eq.modele, {}) if eq.modele else {}
    if "signaux" not in modele or modele.get("type") != eq.type:
        return catalogue
    import copy
    vue = copy.copy(catalogue)
    signaux = copy.deepcopy(modele["signaux"])
    vue.signaux = [s for s in catalogue.signaux if s["type"] != eq.type] + signaux
    if "regles" in modele:
        vue.regles = copy.deepcopy(modele["regles"])
    vue.types = copy.deepcopy(catalogue.types)
    t = next((t for t in vue.types if t["code"] == eq.type), None)
    if t is not None:
        t["options"] = list(dict.fromkeys(s.get("option", "") for s in signaux
                                               if s.get("presence") == "Option" and s.get("option")))
    return vue


def _base_retenue(catalogue, eq):
    base = []
    for s in catalogue.signaux_du_type(eq.type):
        cle = f"{s['famille']}_{s['code']}"
        if cle in eq.exclus:
            continue
        if s["presence"] in ("Obligatoire", "Par défaut"):
            base.append(s)
        elif s["presence"] == "Option" and s.get("option") in eq.options:
            base.append(s)
    return base


def propositions_regles(catalogue, eq):
    """{clé: regles.Proposition} pour l'équipement (retenues, proposées ou refusées)."""
    from .regles import evaluer
    cles = {f"{s['famille']}_{s['code']}" for s in _base_retenue(catalogue, eq)}
    cles |= {f"{a.famille}_{a.code}" for a in eq.ajouts}
    return evaluer(catalogue, eq, cles)


def signaux_retenus(catalogue, eq):
    """Signaux retenus pour un équipement : catalogue (présence + options), signaux issus des règles
    (auto ou acceptés), puis signaux propres. Renvoie [(signal, origine)]."""
    retenus = [(s, "Catalogue") for s in _base_retenue(catalogue, eq)]
    for cle, p in propositions_regles(catalogue, eq).items():
        if p.etat == "retenu":
            ids = ", ".join(r.get("id", "?") for r in p.regles)
            retenus.append((p.signal, f"Règle {ids}"))
    # ordre du catalogue : l'ordre d'attribution des adresses reste celui du référentiel
    rang = {id(s): i for i, s in enumerate(catalogue.signaux_du_type(eq.type))}
    retenus.sort(key=lambda x: rang.get(id(x[0]), 10 ** 6))
    cles_catalogue = {f"{s['famille']}_{s['code']}" for s, _ in retenus}
    cles_type = {f"{s['famille']}_{s['code']}" for s in catalogue.signaux_du_type(eq.type)}
    for a in eq.ajouts:
        cle = f"{a.famille}_{a.code}"
        if cle in cles_catalogue:
            continue                     # signal entre-temps validé dans le catalogue : le catalogue l'emporte
        retenus.append(({"information": a.information, "famille": a.famille, "code": a.code,
                         "type_logique": a.type_logique, "unite": a.unite, "es": a.es,
                         "alarme": a.alarme, "organe": a.organe},
                        "Catalogue adapté" if cle in cles_type else "Propre à l'équipement"))
    return retenus


def _point_de(s):
    """(point, suffixe du nom) d'un signal porteur d'une E/S physique, ou (None, None)."""
    es = s.get("es") or "Interne"
    if es not in ("ET", "ST", "EA", "SA"):
        return None, None
    return es, suffixe_physique(s)


def generer(ouvrage, catalogue):
    """Liste complète des variables de l'ouvrage, dans l'ordre des équipements."""
    variables = []
    for eq in ouvrage.equipements:
        designation = catalogue.designation(eq.type)
        rep = ouvrage.repere(eq)
        rep_nom = ouvrage.repere_nom(eq)
        court = eq.code_court() if ouvrage.charte_12() else f"{eq.sous_ensemble}{eq.type}{eq.numero}"
        catalogue_eq = catalogue_pour_equipement(ouvrage, catalogue, eq)
        retenus = signaux_retenus(catalogue_eq, eq)
        sources = {f"{x['famille']}_{x['code']}": x for x, _ in retenus if x["famille"] == "ES"}
        props = propositions_regles(catalogue_eq, eq)
        for s, origine in retenus:
            fam, code = s["famille"], s["code"]
            if fam == "ES" or est_interne(fam):
                continue                     # E/S locale ou variable interne : pas de variable d'échange
            cle = f"{fam}_{code}"
            es = s.get("es") or "Interne"
            propose = f"{designation} {eq.code_court()} – {fam} {s['information']}"
            v = Variable(
                ident_eq=eq.ident, repere=rep, designation=designation,
                information=s["information"], famille=fam, code=code,
                nom=f"{fam}_{rep_nom}_{code}",
                type_logique=type_echange(fam, s.get("type_logique", "BOOL")),
                unite=s.get("unite", ""), es=es, alarme=bool(s.get("alarme")),
                commentaire=eq.commentaires.get(cle) or propose,
                libelle_topkapi=eq.libelles.get(cle) or f"{court} — {s['information']}",
                adresse=eq.adresses.get(cle, ""),
                origine=origine,
                commentaire_propose=propose,
                commentaire_saisi=bool(eq.commentaires.get(cle)),
                adresse_validee=bool(eq.adresses.get(cle)) and cle in eq.validees,
                uf=eq.uf,
            )
            # logique automate : celle du signal, plus celle des règles « proposition » qui l'ont fait naître
            textes = [s.get("logique", "")] + [texte_regle(r) for r in props.get(cle).regles
                                                if r.get("mode") == "proposition"] if cle in props else [s.get("logique", "")]
            v.logique = " ".join(dict.fromkeys(t for t in textes if t))
            src = sources.get(s.get("source", "")) if s.get("source") else None
            if src is not None:                 # acquis ou commandé par une E/S physique déclarée à part
                point, suffixe = _point_de(src)
                v.es, v.nom_es, v.type_es = point, f"{point}_{rep_nom}_{suffixe}", type_point_es(point)
                v.cle_es = s["source"]
                v.adresse_es = eq.adresses_es.get(v.cle_es) or eq.adresses_es.get(cle, "")
            elif es in ("ET", "ST", "EA", "SA"):
                v.nom_es = f"{es}_{rep_nom}_{suffixe_physique(s)}"
                v.type_es = type_point_es(es)
                v.cle_es = cle
                v.adresse_es = eq.adresses_es.get(cle, "")
            elif s.get("source"):
                v.es = "Interne"                # source physique non retenue : information calculée
            variables.append(v)
    return variables


def generer_points(ouvrage, catalogue):
    """Entrées-sorties physiques de l'automate : liées à un signal ou locales (famille ES)."""
    from .cartes_es import sens_par_defaut
    points = []
    for eq in ouvrage.equipements:
        designation = catalogue.designation(eq.type)
        rep = ouvrage.repere(eq)
        rep_nom = ouvrage.repere_nom(eq)
        catalogue_eq = catalogue_pour_equipement(ouvrage, catalogue, eq)
        retenus = signaux_retenus(catalogue_eq, eq)
        cles_es = {f"{x['famille']}_{x['code']}" for x, _ in retenus if x["famille"] == "ES"}
        utilisateurs: dict[str, str] = {}
        cles_utilisateurs: dict[str, str] = {}
        for x, _ in retenus:
            if x.get("source") in cles_es:
                utilisateurs.setdefault(x["source"], f"{x['famille']}_{rep_nom}_{x['code']}")
                # compatibilité : adresse physique enregistrée sous la clé du signal fonctionnel
                cles_utilisateurs.setdefault(x["source"], f"{x['famille']}_{x['code']}")
        for s, origine in retenus:
            es = s.get("es") or "Interne"
            if es not in ("ET", "ST", "EA", "SA") or est_interne(s.get("famille")):
                continue
            if s.get("source") in cles_es:
                continue                        # le point physique est porté par sa source (famille ES)
            fam, code = s["famille"], s["code"]
            organe = s.get("organe", "") if es == "ET" else ""
            info = information_point(s["information"], organe)
            cle = f"{fam}_{code}"
            meta = eq.es_meta.get(cle, {})
            propose = f"{designation} {eq.code_court()} – {es} {info}"
            suffixe = suffixe_physique(s)
            points.append(PointES(
                ident_eq=eq.ident, repere=rep, point=es,
                nom=f"{es}_{rep_nom}_{suffixe}",
                type_logique=meta.get("type") or (s.get("type_logique") if fam == "ES" and s.get("type_logique")
                                                  in TYPES_POINT[es] else type_point_es(es)),
                information=info,
                commentaire=meta.get("designation") or propose,
                adresse=eq.adresses_es.get(cle) or eq.adresses_es.get(cles_utilisateurs.get(cle, ""), ""), cle=cle,
                variable=utilisateurs.get(cle, "") if fam == "ES" else f"{fam}_{rep_nom}_{code}",
                designation=meta.get("designation", ""), raccordement=meta.get("raccordement") or "Câblé",
                module=meta.get("module", ""), voie=str(meta.get("voie", "") or ""), validee=bool(meta.get("validee")),
                contenu_valide=bool(meta.get("contenu_valide") or meta.get("validee")),
                uf=eq.uf, origine="Propre à l'équipement" if origine in ("Propre à l'équipement", "Catalogue adapté")
                else ("Règle" if origine.startswith("Règle") else "Catalogue"),
                note=meta.get("note", ""),
                sens=meta.get("sens") or s.get("sens") or sens_par_defaut(es, code, s["information"]),
                organe1=designation, organe2=(catalogue.type(eq.type) or {}).get("domaine", ""),
                extension=suffixe.lower(), analogique=meta.get('analogique') or {},
                impulsion=meta.get('impulsion') or {}))
    return points


@dataclass
class VariableInterne:
    """Variable interne déclarée (décision P1) : non localisée, jamais télétransmise, sans adresse."""
    ident_eq: str
    repere: str
    designation: str
    information: str
    famille: str
    code: str
    nom: str
    type_logique: str
    commentaire: str
    origine: str = "Catalogue"
    uf: str = ""

    @property
    def cle(self):
        return f"{self.famille}_{self.code}"


def generer_internes(ouvrage, catalogue):
    """Variables internes déclarées et sélectionnées (option de l'équipement ou signal propre).

    Le type logique est celui du signal, jamais déduit de la famille ; aucune adresse n'est produite."""
    internes = []
    for eq in ouvrage.equipements:
        designation = catalogue.designation(eq.type)
        rep = ouvrage.repere(eq)
        rep_nom = ouvrage.repere_nom(eq)
        for s, origine in signaux_retenus(catalogue_pour_equipement(ouvrage, catalogue, eq), eq):
            fam, code = s["famille"], s["code"]
            if not est_interne(fam):
                continue
            cle = f"{fam}_{code}"
            internes.append(VariableInterne(
                ident_eq=eq.ident, repere=rep, designation=designation, information=s["information"],
                famille=fam, code=code, nom=f"{fam}_{rep_nom}_{code}", type_logique=s.get("type_logique") or "",
                commentaire=eq.commentaires.get(cle) or f"{designation} {eq.code_court()} – {s['information']}",
                origine=origine, uf=eq.uf))
    return internes


# ====================================================================== adresses
def _mot(adresse):
    """%MW1002.5 -> (1002, 5) ; %MW1400 -> (1400, None)."""
    m = re.match(r"^%MW(\d+)(?:\.(\d+))?$", adresse or "")
    if not m:
        return None
    bit = int(m.group(2)) if m.group(2) is not None else None
    if bit is not None and not 0 <= bit < 16:
        return None
    return int(m.group(1)), bit


def _occupation(adresse, type_logique):
    """Mots (et bits) occupés par une adresse."""
    p = _mot(adresse)
    if not p:
        return set()
    mot, bit = p
    if bit is not None:
        return {(mot, bit)}
    taille = max(1, TAILLE_MOTS.get(type_logique, 1))
    return {(mot + i, None) for i in range(taille)}


class Memoire:
    """Occupation de la mémoire %MW : mots entiers et bits de mots."""

    def __init__(self):
        self.mots = {}        # mot -> nom de la variable qui l'occupe en entier
        self.bits = {}        # (mot, bit) -> nom
        self.mots_a_bits = {} # mot -> nom d'une variable qui en occupe un bit

    def conflit(self, adresse, type_logique):
        """Nom de la variable déjà présente à cet endroit, ou chaîne vide."""
        p = _mot(adresse)
        if not p:
            return ""
        mot, bit = p
        if bit is not None:
            return self.mots.get(mot, "") or self.bits.get((mot, bit), "")
        for m in range(mot, mot + max(1, TAILLE_MOTS.get(type_logique, 1))):
            if m in self.mots or m in self.mots_a_bits:
                return self.mots.get(m) or self.mots_a_bits[m]
        return ""

    def occuper(self, adresse, type_logique, nom):
        p = _mot(adresse)
        if not p:
            return
        mot, bit = p
        if bit is not None:
            self.bits[(mot, bit)] = nom
            self.mots_a_bits.setdefault(mot, nom)
        else:
            for m in range(mot, mot + max(1, TAILLE_MOTS.get(type_logique, 1))):
                self.mots[m] = nom

    def premier_bit(self, debut, fin):
        for m in range(debut, fin + 1):
            if m in self.mots:
                continue
            for b in range(16):
                if (m, b) not in self.bits:
                    return f"%MW{m}.{b}"
        return ""

    def mots_libres(self, mot, taille):
        return all(m not in self.mots and m not in self.mots_a_bits for m in range(mot, mot + taille))

    def premier_mot(self, debut, fin, taille, accepte=lambda m: True):
        m = debut + (debut % 2 if taille == 2 else 0)
        pas = 2 if taille == 2 else 1
        while m + taille - 1 <= fin:
            if self.mots_libres(m, taille) and accepte(m):
                return m
            m += pas
        return None


def zone(ouvrage, famille):
    """(premier mot, dernier mot) de la plage de la famille."""
    debut = int(ouvrage.zones.get(famille, ZONES_DEFAUT[famille]))
    fin = ouvrage.zones_fin.get(famille)
    return debut, int(fin) if fin is not None else debut + 999


def fin_de_zone(ouvrage, famille):
    return zone(ouvrage, famille)[1]


@dataclass
class Proposition:
    variable: "Variable"
    adresse: str
    remarque: str = ""


def plan_adresses(ouvrage, catalogue, tout_refaire=False, reservations=()):
    """Calcule, sans rien modifier, les adresses à donner aux variables qui n'en ont pas.

    Règles :
    - chaque famille reste dans sa plage ; une plage pleine est une erreur (aucune adresse hors zone) ;
    - les adresses déjà attribuées ne bougent pas ; les nouvelles prennent la première place libre ;
    - un BOOL (TS, TC) occupe un bit, 16 par mot ; un INT un mot ; un REAL ou un DINT deux mots, sur une adresse paire ;
    - un RTR occupe le même rang dans sa plage que son TR (TR %MW102 -> RTR %MW4002).
    Renvoie (propositions, erreurs).
    """
    variables = generer(ouvrage, catalogue)
    mem = Memoire()
    erreurs_depart = []
    # Empêcher l'allocation dans un plan de plages incohérent. Les zones
    # doivent être distinctes même lorsqu'aucune variable n'est encore créée.
    plages: list[tuple[str, int, int]] = []
    for famille in ORDRE_ZONES:
        debut, fin = zone(ouvrage, famille)
        if debut < 0 or fin < debut:
            erreurs_depart.append(f"Plage {famille} invalide : %MW{debut} à %MW{fin}.")
        for autre, a, b in plages:
            if max(debut, a) <= min(fin, b):
                erreurs_depart.append(f"Plages {famille} et {autre} chevauchantes.")
        plages.append((famille, debut, fin))
    reserves = {}
    for debut_r, fin_r, motif_r in reservations:      # plages mémoire réservées (mots entiers)
        for m in range(int(debut_r), int(fin_r) + 1):
            reserves[m] = motif_r
    for v in variables:
        if v.adresse and _mot(v.adresse) and _mot(v.adresse)[0] in reserves and not (tout_refaire and not v.adresse_validee):
            erreurs_depart.append(f"{v.nom} : {v.adresse} est dans une plage réservée ({reserves[_mot(v.adresse)[0]]}).")
    for v in variables:
        if v.type_logique not in TAILLE_MOTS:
            erreurs_depart.append(f"Type logique inconnu pour {v.nom} : {v.type_logique}.")
            continue
        if not v.adresse or (tout_refaire and not v.adresse_validee):
            continue
        p = _mot(v.adresse)
        if p is None:
            erreurs_depart.append(f"Adresse existante incorrecte pour {v.nom}: {v.adresse}.")
            continue
        if (v.type_logique == "BOOL") != (p[1] is not None):
            erreurs_depart.append(f"Type/adresse incohérents pour {v.nom}: {v.adresse}.")
        taille = max(1, TAILLE_MOTS.get(v.type_logique, 1))
        if taille == 2 and p[0] % 2:
            erreurs_depart.append(f"Adresse de départ impaire pour {v.nom}: {v.adresse}.")
        debut, fin = zone(ouvrage, v.famille)
        if p[0] < debut or p[0] + (taille - 1 if p[1] is None else 0) > fin:
            erreurs_depart.append(f"Adresse de {v.nom} hors plage {v.famille}: {v.adresse}.")
        deja = mem.conflit(v.adresse, v.type_logique)
        if deja:
            erreurs_depart.append(f"Chevauchement existant entre {v.nom} et {deja} ({v.adresse}).")
        mem.occuper(v.adresse, v.type_logique, v.nom)
    # Adresses conservées pour des signaux retirés : réservées, pour qu'un signal remis retrouve
    # sa place et qu'aucune autre variable ne la prenne en silence.
    if not tout_refaire:
        for eq in ouvrage.equipements:
            retenus = {f"{x['famille']}_{x['code']}": x for x, _ in signaux_retenus(catalogue, eq)}
            types_cat = {f"{x['famille']}_{x['code']}": x for x in catalogue.signaux_du_type(eq.type, avec_ecartes=True)}
            for cle, adr in eq.adresses.items():
                if cle in retenus or not _mot(adr):
                    continue
                s_cat = types_cat.get(cle)
                tl = type_echange(cle.split("_", 1)[0], s_cat.get("type_logique", "BOOL")) if s_cat else (
                    "BOOL" if _mot(adr)[1] is not None else "INT")
                if not mem.conflit(adr, tl):
                    mem.occuper(adr, tl, f"(réservée pour {ouvrage.repere(eq)} {cle})")
    # Les paires déjà affectées doivent être cohérentes AVANT de calculer
    # les éventuelles nouvelles adresses : aucune "réparation" silencieuse.
    if not tout_refaire:
        assoc = {(v.ident_eq, v.famille, v.code): v for v in variables
                 if v.famille in ("TR", "RTR")}
        for rtr in (v for v in variables if v.famille == "RTR"):
            tr = assoc.get((rtr.ident_eq, "TR", rtr.code))
            if not tr:
                continue
            if tr.type_logique != rtr.type_logique:
                erreurs_depart.append(f"TR/RTR de types différents : {tr.nom} / {rtr.nom}.")
            if tr.adresse and rtr.adresse:
                at, ar = _mot(tr.adresse), _mot(rtr.adresse)
                if at and ar:
                    miroir = zone(ouvrage, "RTR")[0] + at[0] - zone(ouvrage, "TR")[0]
                    if ar[0] != miroir:
                        erreurs_depart.append(f"Paire TR/RTR non alignée : {tr.nom} {tr.adresse} / "
                                              f"{rtr.nom} {rtr.adresse} (attendu %MW{miroir}).")
    if erreurs_depart:
        return [], erreurs_depart
    for m, motif_r in reserves.items():
        mem.mots.setdefault(m, f"(réservé : {motif_r})")
    # Une adresse validée par l'automaticien n'est jamais recalculée, même en réattribution complète.
    adresse = {v.nom: ("" if tout_refaire and not v.adresse_validee else v.adresse) for v in variables}
    paires = {(v.ident_eq, v.famille, v.code): v for v in variables if v.famille in ("TR", "RTR")}
    a_traiter = [v for v in variables if not adresse[v.nom]]
    a_traiter.sort(key=lambda v: ORDRE_ZONES.index(v.famille))
    tr_debut, tr_fin = zone(ouvrage, "TR")
    rtr_debut, rtr_fin = zone(ouvrage, "RTR")
    propositions, erreurs = [], []
    # Pendant un plan, l'occupation ne peut qu'augmenter. Les mots précédant
    # le dernier bit trouvé sont donc toujours pleins : ne pas les reparcourir.
    # Le curseur reste local au calcul ; aucune adresse ni réservation ne change.
    curseurs_bits: dict[str, int] = {}
    for v in a_traiter:
        debut, fin = zone(ouvrage, v.famille)
        taille = max(1, TAILLE_MOTS.get(v.type_logique, 1))
        choix, remarque = "", ""
        if v.type_logique == "BOOL":
            choix = mem.premier_bit(curseurs_bits.get(v.famille, debut), fin)
            if choix:
                curseurs_bits[v.famille] = int(choix[3:].split(".")[0])
        elif v.famille == "RTR" and (v.ident_eq, "TR", v.code) in paires:
            tr = paires[(v.ident_eq, "TR", v.code)]
            p = _mot(adresse[tr.nom])
            if p:
                miroir = rtr_debut + (p[0] - tr_debut)
                if (miroir >= debut and miroir + taille - 1 <= rtr_fin
                        and (taille != 2 or miroir % 2 == 0)
                        and mem.mots_libres(miroir, taille)):
                    choix = f"%MW{miroir}"
                    remarque = f"Même rang que {tr.nom}."
            if not choix:
                erreurs.append(f"Miroir TR/RTR indisponible pour {v.nom} : adapter les plages ou les réservations.")
                continue
        elif v.famille == "TR" and (v.ident_eq, "RTR", v.code) in paires:
            rtr = paires[(v.ident_eq, "RTR", v.code)]
            p = _mot(adresse[rtr.nom])
            if p:                         # le RTR a déjà une adresse : le TR se place en face
                miroir = tr_debut + (p[0] - rtr_debut)
                if (debut <= miroir and miroir + taille - 1 <= fin
                        and (taille != 2 or miroir % 2 == 0)
                        and mem.mots_libres(miroir, taille)):
                    choix = f"%MW{miroir}"
                else:
                    erreurs.append(f"Miroir TR/RTR indisponible pour {v.nom} : le RTR occupe déjà une autre place.")
                    continue
            else:                         # TR sans adresse : prendre une place dont le miroir RTR est libre
                m = mem.premier_mot(debut, fin, taille,
                    lambda m: (rtr_debut + (m - tr_debut) + taille - 1 <= rtr_fin
                               and (taille != 2 or (rtr_debut + (m - tr_debut)) % 2 == 0)
                               and mem.mots_libres(rtr_debut + (m - tr_debut), taille)))
                if m is None:
                    erreurs.append(f"Plage TR pleine pour une paire TR/RTR : {v.nom} reste sans adresse.")
                    continue
                choix = f"%MW{m}"
        else:
            m = mem.premier_mot(debut, fin, taille)
            choix = f"%MW{m}" if m is not None else ""
        if not choix:
            erreurs.append(f"Plage {v.famille} pleine (%MW{debut} à %MW{fin}) : {v.nom} reste sans adresse.")
            continue
        mem.occuper(choix, v.type_logique, v.nom)
        adresse[v.nom] = choix
        propositions.append(Proposition(v, choix, remarque))
    return propositions, erreurs


def appliquer_plan(ouvrage, propositions, tout_refaire=False):
    if tout_refaire:
        for eq in ouvrage.equipements:
            for cle in [c for c in eq.adresses if c not in eq.validees]:
                del eq.adresses[cle]
    for p in propositions:
        ouvrage.equipement(p.variable.ident_eq).adresses[p.variable.cle] = p.adresse
    return len(propositions)


def attribuer_adresses(ouvrage, catalogue, tout_refaire=False):
    """Calcule et applique le plan d'adresses. Renvoie le nombre d'adresses attribuées."""
    propositions, erreurs = plan_adresses(ouvrage, catalogue, tout_refaire)
    if erreurs:
        raise ValueError("Plan d'adressage incomplet : " + " | ".join(erreurs[:5]))
    return appliquer_plan(ouvrage, propositions, tout_refaire)


def registre_modbus(adresse, decalage=0):
    """%MW1000.3 -> « 1000.3 » (+ décalage) : registre du protocole, distinct de l'adresse automate."""
    p = _mot(adresse)
    if not p:
        return ""
    return f"{p[0] + int(decalage)}" + (f".{p[1]}" if p[1] is not None else "")


# ====================================================================== contrôles
@dataclass
class Anomalie:
    niveau: str          # « Erreur » ou « Alerte »
    repere: str
    message: str
    ident_eq: str = ""
    etape: str = "Équipements"   # étape du parcours où l'anomalie se corrige


def controler(ouvrage, catalogue, variables=None):
    if variables is None:
        variables = generer(ouvrage, catalogue)
    anomalies = []
    etape = ["Équipements"]
    err = lambda rep, msg, ident="": anomalies.append(Anomalie("Erreur", rep, msg, ident, etape[0]))
    alerte = lambda rep, msg, ident="": anomalies.append(Anomalie("Alerte", rep, msg, ident, etape[0]))

    # --- ouvrage
    if not re.match(r"^[A-Z0-9]{4}$", ouvrage.lieu or ""):
        err("Ouvrage", "Le lieu doit faire 4 caractères (lettres majuscules ou chiffres), ex. ATMS.")
    if not re.match(r"^[A-Z]{2}$", ouvrage.code_ouvrage or ""):
        err("Ouvrage", "Le code de l'ouvrage doit faire 2 lettres majuscules, ex. RV.")
    if ouvrage.numero_ouvrage and not re.fullmatch(r"(?:0[1-9]|[1-9][0-9])", ouvrage.numero_ouvrage):
        err("Ouvrage", "Numéro d’ouvrage invalide : 01 à 99.")
    codes_se = [s.code for s in ouvrage.sous_ensembles]
    for s in ouvrage.sous_ensembles:
        if not re.match(r"^[A-Z0-9]{2}$", s.code):
            err("Ouvrage", f"Sous-ensemble « {s.code} » : 2 caractères (lettres majuscules ou chiffres).")
        if codes_se.count(s.code) > 1:
            err("Ouvrage", f"Sous-ensemble {s.code} déclaré plusieurs fois.")

    # --- équipements
    reperes = {}
    for eq in ouvrage.equipements:
        rep = ouvrage.repere(eq)
        modele = ouvrage.modeles_snapshot.get(eq.modele, {}) if eq.modele else {}
        if "signaux" in modele:
            from .modeles import verifier_signaux_modele
            for probleme in verifier_signaux_modele(modele["signaux"], eq.type):
                err(rep, f"Modèle {eq.modele} : {probleme}", eq.ident)
        if catalogue.type(eq.type) is None:
            err(rep, f"Type {eq.type} absent du catalogue.", eq.ident)
        if eq.sous_ensemble not in codes_se:
            err(rep, f"Sous-ensemble {eq.sous_ensemble} non déclaré dans l'ouvrage.", eq.ident)
        if not re.match(r"^\d{2}$", eq.numero or ""):
            err(rep, "Le numéro doit faire 2 chiffres (01 à 99).", eq.ident)
        if rep in reperes:
            err(rep, "Repère utilisé par deux équipements.", eq.ident)
        reperes[rep] = True
        catalogue_eq = catalogue_pour_equipement(ouvrage, catalogue, eq)
        for opt in eq.options:
            if opt not in catalogue_eq.options_du_type(eq.type):
                alerte(rep, f"Option « {opt} » inconnue pour le type {eq.type}.", eq.ident)
        adaptes = {f"{x.famille}_{x.code}" for x in eq.ajouts}
        for s in catalogue_eq.signaux_du_type(eq.type):
            if (s["presence"] == "Obligatoire" and f"{s['famille']}_{s['code']}" in eq.exclus
                    and f"{s['famille']}_{s['code']}" not in adaptes):
                alerte(rep, f"Signal obligatoire retiré : {s['famille']}_{s['code']} ({s['information']}).", eq.ident)
        props = propositions_regles(catalogue_eq, eq)
        for cle, p in sorted(props.items()):
            if p.etat == "proposé":
                err(rep, f"Information attendue non décidée : {cle} « {p.signal.get('information', '')} » "
                         f"(proposée par {', '.join(r.get('id', '?') for r in p.regles)}). "
                         "Retenez-la ou écartez-la avec un motif dans la fiche de l'équipement.", eq.ident)
            elif p.etat == "refusé" and not (getattr(eq, "motifs", {}) or {}).get(cle):
                alerte(rep, f"Information {cle} « {p.signal.get('information', '')} » écartée sans motif écrit.",
                       eq.ident)
        for cle in eq.acceptes:
            if cle not in props or props[cle].etat != "retenu":
                alerte(rep, f"Signal {cle} accepté mais sa règle n'est plus satisfaite (E/S retirée ?) : "
                            "il n'est plus généré.", eq.ident)
        retenues = {f"{x['famille']}_{x['code']}" for x, _ in signaux_retenus(catalogue_eq, eq)}
        for cle in sorted(set(eq.adresses) - retenues):
            alerte(rep, f"Adresse {eq.adresses[cle]} conservée pour {cle}, signal non retenu : "
                        "elle sera réutilisée s'il revient, sinon la libérer.", eq.ident)
        for a in eq.ajouts:
            sens = sens_incoherent(a.famille, a.es)
            if sens:
                err(rep, f"Signal propre {a.famille}_{a.code} : {sens}.", eq.ident)
            for m in anomalies_interne({"famille": a.famille, "es": a.es, "alarme": a.alarme}):
                err(rep, f"Signal propre {a.famille}_{a.code} : {m}.", eq.ident)

    # --- variables et entrées-sorties
    points = generer_points(ouvrage, catalogue)
    noms: dict[str, bool] = {}
    adresses_es: dict[str, str] = {}
    internes = generer_internes(ouvrage, catalogue)
    controles_noms = ([(v.repere, v.ident_eq, v.nom) for v in variables] + [(p.repere, p.ident_eq, p.nom) for p in points]
                      + [(x.repere, x.ident_eq, x.nom) for x in internes])
    for rep_, ident, nom in controles_noms:
        if len(nom) > LONGUEUR_MAX_NOM:
            err(rep_, f"{nom} : {len(nom)} caractères, {LONGUEUR_MAX_NOM} au plus.", ident)
        if not RE_NOM.match(nom) or "__" in nom or nom.endswith("_"):
            err(rep_, f"{nom} : caractères non autorisés (lettres, chiffres, _ simple).", ident)
        if nom in noms:
            err(rep_, f"{nom} : nom en double.", ident)
        noms[nom] = True
    for x in internes:
        if x.type_logique not in TAILLE_MOTS:
            err(x.repere, f"{x.nom} : type logique « {x.type_logique} » non pris en charge pour une variable "
                          "interne.", x.ident_eq)
    # --- informations attendues ou sans source (contrôle de conception, par équipement)
    from .audit_referentiel import CODES_CALCULES, TYPES_INTERNES
    par_eq: dict[str, list[PointES]] = {}
    for p in points:
        par_eq.setdefault(p.ident_eq, []).append(p)
    for eq in ouvrage.equipements:
        rep = ouvrage.repere(eq)
        retenus = signaux_retenus(catalogue_pour_equipement(ouvrage, catalogue, eq), eq)
        fonct = [(s, o) for s, o in retenus if s.get("famille") != "ES" and not est_interne(s.get("famille"))]
        pts = par_eq.get(eq.ident, [])
        if not pts:
            sans_source = [f"{s['famille']}_{s['code']}" for s, o in fonct
                           if s.get("code") in CODES_CALCULES and o == "Catalogue"]
            if sans_source:
                alerte(rep, f"{', '.join(sans_source)} : information(s) calculée(s) sans E/S de retour ni d'ordre "
                            "pour les calculer. Ajoutez les E/S (fins de course, commande) ou retirez-les.", eq.ident)
            if ouvrage.mode == "Neuf" and fonct and eq.type not in TYPES_INTERNES:
                alerte(rep, f"Aucune E/S physique pour {len(fonct)} information(s) transmise(s) : ajoutez les E/S "
                            "câblées (E/S personnalisées) ou confirmez une liaison par communication.", eq.ident)
    non_validees = [p for p in points if not p.validee]
    etape[0] = "Liste des E/S et matériel"
    if non_validees:
        alerte("Liste des E/S", f"{len(non_validees)} E/S non validée(s) dans la liste des E/S "
                                f"(ex. {non_validees[0].nom}).")
    for p in points:
        if p.raccordement == "Communication":
            continue                            # information transmise par bus : pas d'adresse %I / %Q
        if not p.adresse:
            alerte(p.repere, f"{p.nom} : adresse physique à renseigner.", p.ident_eq)
            continue
        if p.adresse in adresses_es:
            err(p.repere, f"{p.nom} : adresse {p.adresse} déjà utilisée par {adresses_es[p.adresse]}.", p.ident_eq)
        adresses_es[p.adresse] = p.nom
        attendu = {"ET": "%I", "ST": "%Q", "EA": "%IW", "SA": "%QW"}[p.point]
        a = p.adresse.upper()
        if not a.startswith(attendu) or (p.point in ("ET", "ST") and a.startswith(attendu + "W")):
            alerte(p.repere, f"{p.nom} : une {p.point} s'adresse en {attendu}…", p.ident_eq)
    from .cartes_es import controler as controler_cartes
    for niveau, rep_, msg, ident in controler_cartes(points, ouvrage.modules, ouvrage.reserve_min):
        (err if niveau == "Erreur" else alerte)(rep_, msg, ident)
    etape[0] = "Variables"
    mem = Memoire()
    for v in variables:
        if v.type_logique not in TAILLE_MOTS:
            err(v.repere, f"{v.nom} : type logique « {v.type_logique} » inconnu ; "
                           "aucune occupation mémoire fiable ne peut être calculée.", v.ident_eq)
            continue
        if not v.adresse:
            err(v.repere, f"{v.nom} : pas d'adresse dans la table d'échange.", v.ident_eq)
        else:
            p = _mot(v.adresse)
            if not p:
                err(v.repere, f"{v.nom} : adresse « {v.adresse} » non reconnue (format %MW, bit de 0 à 15).", v.ident_eq)
                continue
            if (v.type_logique == "BOOL") != (p[1] is not None):
                err(v.repere, f"{v.nom} : un BOOL doit être adressé en %MWn.bit, une valeur numérique en %MWn.", v.ident_eq)
            deja = mem.conflit(v.adresse, v.type_logique)
            if deja:
                err(v.repere, f"{v.nom} : {v.adresse} chevauche {deja}.", v.ident_eq)
            mem.occuper(v.adresse, v.type_logique, v.nom)
            debut, fin = zone(ouvrage, v.famille)
            taille = max(1, TAILLE_MOTS.get(v.type_logique, 1))
            if p[0] < debut or p[0] + (taille - 1 if p[1] is None else 0) > fin:
                err(v.repere, f"{v.nom} : {v.adresse} hors de la plage {v.famille} (%MW{debut} à %MW{fin}).", v.ident_eq)
            if TAILLE_MOTS.get(v.type_logique) == 2 and p[0] % 2:
                err(v.repere, f"{v.nom} : variable 32 bits sur une adresse impaire (refusé sur M340 / M580).", v.ident_eq)
        if v.famille == "RTR" and v.adresse:
            tr = next((x for x in variables if x.ident_eq == v.ident_eq and x.famille == "TR" and x.code == v.code), None)
            if tr and tr.adresse and _mot(tr.adresse) and _mot(v.adresse):
                attendu = zone(ouvrage, "RTR")[0] + _mot(tr.adresse)[0] - zone(ouvrage, "TR")[0]
                if _mot(v.adresse)[0] != attendu:
                    err(v.repere, f"{v.nom} : {v.adresse} n'est pas en miroir de {tr.nom} ({tr.adresse} → %MW{attendu} attendu).", v.ident_eq)
                if v.type_logique != tr.type_logique:
                    err(v.repere, f"{v.nom} / {tr.nom} : types TR/RTR différents sans conversion déclarée.", v.ident_eq)
        if len(v.libelle_topkapi) > LONGUEUR_MAX_LIBELLE:
            alerte(v.repere, f"Libellé Topkapi de {len(v.libelle_topkapi)} caractères (40 au plus) : {v.libelle_topkapi}", v.ident_eq)
    non_validees = [v for v in variables if v.adresse and not v.adresse_validee]
    if non_validees:
        alerte("Adresses", f"{len(non_validees)} adresse(s) d'échange proposée(s), pas encore validée(s) "
                           f"par l'automaticien (ex. {non_validees[0].nom}).")
    return anomalies
