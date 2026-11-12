"""Mode projet existant : reprise des variables d'un automate en place.

1. Lecture du fichier .XSY exporté du programme (Control Expert / Unity Pro).
2. Identification automatique de chaque variable à partir de son nom :
       TS_RV11MV03_OUV  ->  sous-ensemble 11, vanne motorisée MV03, signal TS_OUV
   Les noms ne sont jamais modifiés : SOREP les reprend tels quels.
3. Correction manuelle de ce qui n'a pas été reconnu.
4. Contrôle des oublis : signaux du catalogue attendus mais absents de l'automate.
5. Table Excel de correspondance pour l'intégration dans Topkapi.
"""

import re
import unicodedata

from .modele import Equipement, SousEnsemble, VariableExistante, Anomalie, TAILLE_MOTS
from .catalogue import est_interne
from .export_xlsx import ecrire_xlsx

# Préfixe du nom -> famille de la table d'échange.
# DEF, ALA et EVI sont des télésignalisations (défaut, alarme, événement) ; TMC une télémesure calculée.
PREFIXES = {"TS": "TS", "DEF": "TS", "ALA": "TS", "EVI": "TS", "TOR": "TS",
            "TC": "TC", "TM": "TM", "TMC": "TM", "TR": "TR", "RTR": "RTR", "CP": "CP", "CPT": "CP"}
PREFIXES_ES = {"ET", "ST", "EA", "SA"}

# Écritures fréquentes dans les programmes repris -> code du catalogue.
SYNONYMES = {
    "FERME": "FER", "FERMEE": "FER", "FERMETURE": "FER", "OUVERT": "OUV", "OUVERTE": "OUV", "OUVERTURE": "OUV",
    "ENMAR": "MA", "ENMARCHE": "MA", "MARCHE": "MA", "ARRET": "AR",
    "INDISPO": "DISPO", "INDISPONIBLE": "DISPO",
    "MDAUTO": "AUTO", "PILOTAGEAUTO": "AUTO", "MDMANU": "MANU", "PILOTAGEMANU": "MANU",
    "CMDLOCAL": "LOC", "LOCAL": "LOC", "CMDLOCALES": "LOC",
    "DEFGEN": "DEF", "DEFAUT": "DEF", "GENERAL": "DEF",
    "HORSSERVICE": "HS", "CAPTHS": "HS",
    "VALEUR": "VAL", "NIVEAU": "NIV", "DEBIT": "DEB", "PRESSION": "PRE",
}
# Signaux dont le nom repris a la polarité inverse de celle du catalogue.
POLARITE_INVERSE = {"INDISPO", "INDISPONIBLE"}

RE_NOM = re.compile(r"^([A-Za-z]+)_([A-Za-z0-9]+?)(?:_(.*))?$")
RE_REPERE = re.compile(r"^(.*?)([A-Z0-9]{2})([A-Z]{2})(\d{2})$")


def sans_accents(texte):
    t = (texte or "").replace("œ", "oe").replace("Œ", "OE").replace("æ", "ae").replace("Æ", "AE")
    t = unicodedata.normalize("NFD", t)
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower()


# ====================================================================== lecture
def lire_xsy(chemin):
    """Compatibilité historique : seules les variables principales du XSY."""
    from .xsy_ddt import analyser_xsy
    return [v.ligne() for v in analyser_xsy(chemin).parents]


def lire_xsy_detaille(chemin):
    """Analyse complète : variables principales + champs DDT imbriqués.

    Les adresses des champs restent vides : adresse_parent_xsy et chemin_symbolique
    sont fournis séparément. Ce n'est PAS une table Modbus validée.
    """
    from .xsy_ddt import analyser_xsy
    return analyser_xsy(chemin)


def differences_xsy_detaille(ouvrage, analyse):
    """Différences sur l'identité et les métadonnées DDT (sans mutation)."""
    changements = differences_reimport(ouvrage, analyse.lignes)
    existantes = {v.nom: v for v in ouvrage.existantes}
    for champ in analyse.parents + analyse.champs:
        avant = existantes.get(champ.nom)
        if avant is None:
            continue
        for libelle, ancien, nouveau in (
            ('Nature de source', avant.nature_source, champ.nature),
            ('Parent DDT', avant.parent_xsy, champ.parent),
            ('Type du parent', avant.type_parent_xsy, champ.type_parent),
            ('Adresse du parent DDT', avant.adresse_parent_xsy, champ.adresse_parent),
            ('Bit ExtractBit', avant.extract_bit, champ.extract_bit),
            ('Chemin symbolique', avant.chemin_symbolique or avant.nom, champ.chemin_symbolique),
        ):
            if ancien != nouveau:
                changements.append((champ.nom, libelle, ancien, nouveau))
    return changements


def importer_xsy_detaille(ouvrage, analyse):
    """Import transactionnel du contenu analysé + provenance des champs.

    La validation antérieure est invalidée après modification d'un champ DDT,
    notamment si l'adresse du PARENT change. Aucune adresse enfant n'est déduite.
    """
    from .import_sources import verifier_lignes_import
    # Contrôle préalable de toutes les lignes avant mutation.
    verifier_lignes_import(analyse.lignes)
    avant = {v.nom: v for v in ouvrage.existantes}
    modifications_meta = set()
    for champ in analyse.parents + analyse.champs:
        precedent = avant.get(champ.nom)
        if precedent and (
            precedent.nature_source != champ.nature
            or precedent.parent_xsy != champ.parent
            or precedent.type_parent_xsy != champ.type_parent
            or precedent.adresse_parent_xsy != champ.adresse_parent
            or precedent.extract_bit != champ.extract_bit
            or (precedent.chemin_symbolique or precedent.nom) != champ.chemin_symbolique
        ):
            modifications_meta.add(champ.nom)
    total, nouvelles = importer_lignes(ouvrage, analyse.lignes)
    importees = {v.nom: v for v in ouvrage.existantes}
    for champ in analyse.parents + analyse.champs:
        v = importees[champ.nom]
        if champ.nom in modifications_meta:
            # Ne pas effacer une saisie vérifiée : la conserver comme information
            # documentaire, mais obliger à refaire son contrôle.
            v.acces_verifie = False
            if v.identification == 'Confirmée':
                v.identification = 'À identifier'
                v.remarque = 'Métadonnées DDT ou adresse parent modifiées : nouvelle validation nécessaire.'
            if ouvrage.statut == 'Validé':
                ouvrage.statut = 'À contrôler'
        v.nature_source = champ.nature
        v.parent_xsy = champ.parent
        v.type_parent_xsy = champ.type_parent
        v.adresse_parent_xsy = champ.adresse_parent
        v.extract_bit = champ.extract_bit
        v.chemin_symbolique = champ.chemin_symbolique
        v.fichier_source_xsy = analyse.fichier
        v.empreinte_source_xsy = analyse.sha256
        if champ.nature == 'Champ DDT' and champ.nom not in avant:
            # Découverte dans le programme != besoin de supervision.
            v.retenue = False
            v.identification = 'À identifier'
            v.remarque = ('Champ DDT lu sous son chemin symbolique ; adresse protocolaire '
                          'et exposition TOPKAPI non vérifiées.')
    return total, nouvelles


def importer(ouvrage, chemin):
    """Import XSY enrichi : retourne (total, nouvelles) comme auparavant."""
    return importer_xsy_detaille(ouvrage, lire_xsy_detaille(chemin))


def differences_reimport(ouvrage, lignes):
    """Compare sans mutation les données sources avant un réimport.

    Les modifications de type ou d'adresse rendent une correspondance métier
    précédemment confirmée à revalider.
    """
    existantes = {v.nom: v for v in ouvrage.existantes}
    changements = []
    for nom, typ, adr, com in lignes:
        avant = existantes.get(nom)
        if avant is None:
            changements.append((nom, "Nouvelle variable", "", adr))
            continue
        for libelle, ancien, nouveau in (
            ("Type", avant.type_logique, typ),
            ("Adresse", avant.adresse, adr),
            ("Commentaire", avant.commentaire, com),
        ):
            if ancien != nouveau:
                changements.append((nom, libelle, ancien, nouveau))
    return changements


def absentes_reimport(ouvrage, lignes):
    """Noms non retrouvés dans ce fichier ; information seulement.

    Un ouvrage peut être alimenté par plusieurs sources : l'absence ne justifie
    jamais une suppression automatique de la variable du référentiel.
    """
    noms = {ligne[0] for ligne in lignes}
    return sorted(v.nom for v in ouvrage.existantes if v.nom not in noms)


def importer_lignes(ouvrage, lignes):
    """Import contrôlé de (nom, type, adresse, commentaire), sans modification de source.

    L'identification manuelle déjà confirmée est préservée au réimport.
    """
    from .import_sources import verifier_lignes_import
    lignes, _avertissements = verifier_lignes_import(lignes)
    deja = {v.nom: v for v in ouvrage.existantes}
    nouvelles = 0
    for nom, typ, adr, com in lignes:
        if nom in deja:
            v = deja[nom]
            changement_source = ((v.type_logique, v.adresse, v.commentaire) != (typ, adr, com))
            if changement_source and v.identification == "Confirmée":
                v.identification = "À identifier"
                v.remarque = "Type, adresse ou commentaire source modifié au réimport : nouvelle validation nécessaire."
            if changement_source and ouvrage.statut == "Validé":
                ouvrage.statut = "À contrôler"
            v.type_logique, v.adresse, v.commentaire = typ, adr, com
        else:
            v = VariableExistante(nom, typ, adr, com)
            ouvrage.existantes.append(v)
            deja[nom] = v
            nouvelles += 1
            if ouvrage.statut == "Validé":
                ouvrage.statut = "À contrôler"
    return len(lignes), nouvelles

# ====================================================================== identification
def decouper(nom):
    """TS_RV11MV03_OUV -> ("TS", "RV11MV03", "OUV", ("RV", "11", "MV", "03"))."""
    m = RE_NOM.match(nom or "")
    if not m:
        return None
    prefixe, repere, suffixe = m.group(1).upper(), m.group(2).upper(), (m.group(3) or "").upper()
    r = RE_REPERE.match(repere)
    if not r:
        return prefixe, repere, suffixe, None
    return prefixe, repere, suffixe, (r.group(1), r.group(2), r.group(3), r.group(4))


ETATS_IDENTIFICATION = ["Exacte", "Probable", "Confirmée", "À identifier", "Hors supervision"]
# Exacte       : le code du nom est celui du catalogue (TS_RV11MV03_OUV -> TS_OUV). Reprise sans confirmation.
# Probable     : reconnue par une écriture courante (FERME -> FER) ou par le commentaire. À confirmer.
# Confirmée    : choisie ou confirmée à la main. Jamais modifiée par l'identification automatique.
# À identifier : équipement ou fonction non reconnus, ou plusieurs fonctions possibles (ambiguë).


def _cherche_signal(catalogue, type_code, famille, suffixe, commentaire):
    """Renvoie (signal, niveau, remarque) ; niveau : « Exacte », « Probable » ou « » (non trouvé / ambigu)."""
    candidats = [s for s in catalogue.signaux_du_type(type_code) if s["famille"] == famille]
    if not candidats:
        return None, "", f"Aucun signal {famille} pour le type {type_code} dans le catalogue."
    code = suffixe.replace("_", "")
    for s in candidats:
        if s["code"] == code:
            return s, "Exacte", ""
    if code in SYNONYMES:
        remarque = "Écriture courante " + suffixe + " → " + SYNONYMES[code] + "."
        if code in POLARITE_INVERSE:
            remarque += " Polarité inversée (indisponible / disponible)."
        for s in candidats:
            if s["code"] == SYNONYMES[code]:
                return s, "Probable", remarque
    # Commentaire : on retire le mot de famille en tête (« TS OUVERTE » -> « ouverte »), puis on cherche
    # l'information du catalogue en mots entiers. Une négation (« VANNE NON OUVERTE ») écarte la proposition.
    mots = re.findall(r"[a-z0-9]+", sans_accents(commentaire))
    while mots and mots[0] in ("ts", "tc", "tm", "tmc", "tr", "rtr", "def", "ala", "evi", "cp", "cpt"):
        mots.pop(0)
    if not mots or {"non", "pas", "ne", "sans"} & set(mots):
        return None, "", ""
    texte = " " + " ".join(mots) + " "
    trouves = []
    for s in candidats:
        info = " ".join(re.findall(r"[a-z0-9]+", sans_accents(s["information"])))
        if len(info) > 4 and f" {info} " in texte:
            trouves.append(s)
    # si un libellé en contient un autre (« défaut thermique » et « défaut »), on garde le plus précis
    trouves = [s for s in trouves if not any(t is not s and sans_accents(s["information"]) in sans_accents(t["information"])
                                             for t in trouves)]
    if len(trouves) == 1:
        return trouves[0], "Probable", "Reconnue par le commentaire."
    if len(trouves) > 1:
        return None, "", "Plusieurs fonctions possibles : " + ", ".join(f"{s['famille']}_{s['code']}" for s in trouves) + "."
    return None, "", ""


def identifier(ouvrage, catalogue, tout_refaire=False):
    """OBSOLÈTE depuis la V0.9 : l'interface n'appelle plus cette fonction (elle crée des
    équipements sans accord). Le rapprochement passe par teletransmission.candidats /
    proposer_associations, et les équipements détectés sont proposés à l'utilisateur.
    Conservée pour la compatibilité des scripts et des tests historiques.

    Propose l'équipement et le signal de chaque variable qui n'a pas été confirmée à la main.
    Crée au besoin les sous-ensembles et les équipements trouvés dans les noms.
    Ne modifie jamais le nom, le type, l'adresse ni le commentaire de la variable.
    Renvoie le nombre de variables reconnues (exactes + probables)."""
    reconnues = 0
    for v in ouvrage.existantes:
        if v.identification in ("Confirmée", "Manuelle") and not tout_refaire:
            continue
        if v.nature_source == 'Champ DDT':
            # Le chemin symbolique n'a pas la convention historique ; il reste
            # recherchable par l'assistant, sans être automatiquement retenu.
            v.identification = 'À identifier'
            v.remarque = ('Champ DDT : choisir sa fonction métier ; chemin symbolique '
                          'connu mais adresse d’acquisition à vérifier.')
            continue
        d = decouper(v.nom)
        v.ident_eq, v.cle, v.remarque = "", "", ""
        if not d:
            v.identification, v.retenue = "Hors supervision", False
            v.remarque = "Nom sans structure FAMILLE_REPÈRE_FONCTION."
            continue
        prefixe, repere, suffixe, parties = d
        if prefixe in PREFIXES_ES:
            v.identification, v.retenue = "Hors supervision", False
            v.remarque = "Entrée-sortie physique."
            continue
        famille = PREFIXES.get(prefixe)
        if not famille:
            v.identification, v.retenue = "Hors supervision", False
            v.remarque = f"Préfixe {prefixe} : variable interne au programme."
            continue
        v.retenue = True
        if not parties or catalogue.type(parties[2]) is None:
            v.identification = "À identifier"
            v.remarque = "Repère non reconnu." if not parties else f"Type {parties[2]} absent du catalogue."
            continue
        _, se, type_code, num = parties
        if se not in [s.code for s in ouvrage.sous_ensembles]:
            ouvrage.sous_ensembles.append(SousEnsemble(se, ""))
            ouvrage.sous_ensembles.sort(key=lambda s: s.code)
        eq = next((e for e in ouvrage.equipements
                   if (e.sous_ensemble, e.type, e.numero) == (se, type_code, num)), None)
        if eq is None:
            eq = Equipement(se, type_code, num, "")
            ouvrage.equipements.append(eq)
        v.ident_eq = eq.ident
        s, niveau, remarque = _cherche_signal(catalogue, type_code, famille, suffixe, v.commentaire)
        if s:
            v.cle = f"{s['famille']}_{s['code']}"
            v.identification = niveau
            v.remarque = remarque
            reconnues += 1
        else:
            v.identification = "À identifier"
            v.remarque = remarque or "Équipement reconnu, fonction à préciser."
    return reconnues


def confirmer(variables):
    """Confirme des propositions « Probable » (ou « Exacte ») : elles ne bougeront plus."""
    n = 0
    for v in variables:
        if v.identification in ("Exacte", "Probable") and v.cle:
            v.identification = "Confirmée"
            n += 1
    return n


# ====================================================================== contrôles
def information_signal(catalogue, eq, cle):
    if not eq or not cle:
        return ""
    for s in catalogue.signaux_du_type(eq.type, avec_ecartes=True):
        if f"{s['famille']}_{s['code']}" == cle:
            return s["information"]
    return ""


def libelle_topkapi(ouvrage, catalogue, v):
    eq = ouvrage.equipement(v.ident_eq)
    info = information_signal(catalogue, eq, v.cle)
    if eq and info:
        return f"{eq.sous_ensemble}{eq.type}{eq.numero} — {info}"
    return v.commentaire


def ecarts(ouvrage, catalogue):
    """Signaux du catalogue absents de l'automate, équipement par équipement.
    Seuls les signaux « Obligatoire » et « Par défaut » sont comparés ; les options ne le sont pas.
    Un signal déclaré non applicable pour un équipement (retiré de l'équipement) n'est plus listé.
    Renvoie des tuples (niveau, repère, désignation, clé, information, ident_eq)."""
    trouves = {(v.ident_eq, v.cle) for v in ouvrage.existantes if v.retenue and v.cle}
    liste = []
    for eq in ouvrage.equipements:
        for s in catalogue.signaux_du_type(eq.type):
            if s["presence"] not in ("Obligatoire", "Par défaut") or s["famille"] == "ES" or est_interne(s["famille"]):
                continue
            cle = f"{s['famille']}_{s['code']}"
            if cle in eq.exclus or (eq.ident, cle) in trouves:
                continue
            niveau = "Obligatoire absent" if s["presence"] == "Obligatoire" else "À examiner"
            liste.append((niveau, ouvrage.repere(eq), catalogue.designation(eq.type), cle, s["information"], eq.ident))
    liste.sort(key=lambda x: (x[0] != "Obligatoire absent", x[1]))
    return liste


def oublis(ouvrage, catalogue):
    """Compatibilité : (repère, désignation, clé, information, ident_eq)."""
    return [e[1:] for e in ecarts(ouvrage, catalogue)]


def non_applicable(ouvrage, ident_eq, cle):
    """Déclare un signal du catalogue non applicable pour un équipement : il ne sera plus attendu."""
    eq = ouvrage.equipement(ident_eq)
    if eq and cle not in eq.exclus:
        eq.exclus.append(cle)


def bilan(ouvrage):
    from collections import Counter
    c = Counter(v.identification for v in ouvrage.existantes)
    return {"total": len(ouvrage.existantes), "retenues": sum(1 for v in ouvrage.existantes if v.retenue),
            **{k: c.get(k, 0) for k in ETATS_IDENTIFICATION}}


def doublons_identification(ouvrage):
    """Deux variables retenues identifiées comme le même signal du même équipement."""
    vus: dict[tuple[str, str], str] = {}
    doublons = []
    for v in ouvrage.existantes:
        if v.retenue and v.cle and v.ident_eq:
            k = (v.ident_eq, v.cle)
            if k in vus:
                doublons.append((vus[k], v.nom))
            vus[k] = v.nom
    return doublons


def _occupation(adresse, type_logique):
    """Mots et bits occupés par une adresse %MW lue dans le programme (sans rien modifier)."""
    m = re.match(r"^%MW(\d+)(?:\.(\d+))?$", (adresse or "").upper())
    if not m:
        return None
    mot = int(m.group(1))
    if m.group(2) is not None:
        return {"bits": {(mot, int(m.group(2)))}, "mots": set()}
    # Impossible de déduire la taille occupée par un DDT ou un type inconnu.
    # Ne pas supposer un mot : cela produirait de fausses conclusions de collision.
    taille = TAILLE_MOTS.get((type_logique or "").upper())
    if taille is None:
        return None
    return {"bits": set(), "mots": {mot + i for i in range(max(1, taille))}}


def controler_existant(ouvrage, catalogue):
    """Anomalies du projet existant. Les adresses lues sont contrôlées, jamais corrigées."""
    anomalies = []
    err = lambda rep, msg: anomalies.append(Anomalie("Erreur", rep, msg))
    alerte = lambda rep, msg: anomalies.append(Anomalie("Alerte", rep, msg))
    for a, b in doublons_identification(ouvrage):
        err(a, f"Doublon d'identification : {a} et {b} sont rattachées au même signal du même équipement.")
    mots: dict[int, str] = {}
    bits: dict[tuple[int, int], str] = {}
    for v in ouvrage.existantes:
        typ = (v.type_logique or "").upper()
        occ = _occupation(v.adresse, typ)
        if occ is None:
            continue
        if typ in ("BOOL", "EBOOL") and occ["mots"]:
            alerte(v.nom, f"{typ} placé sur le mot entier {v.adresse} : vérifier l'adresse dans le programme (bit manquant ?).")
        if (TAILLE_MOTS.get(typ) in (2, 4) and occ["mots"]
                and (ouvrage.automate or "").upper() in ("M340", "M580")
                and min(occ["mots"]) % 2):
            err(v.nom, f"{typ} sur l'adresse impaire {v.adresse} : refusé sur {ouvrage.automate} (adresse paire obligatoire).")
        for m in occ["mots"]:
            if m in mots:
                err(v.nom, f"Chevauchement : le mot %MW{m} est aussi utilisé par {mots[m]}.")
            mots.setdefault(m, v.nom)
        for bt in occ["bits"]:
            if bt in bits:
                err(v.nom, f"Chevauchement : le bit %MW{bt[0]}.{bt[1]} est aussi utilisé par {bits[bt]}.")
            bits.setdefault(bt, v.nom)
    for (m, b), nom in bits.items():
        if m in mots and mots[m] != nom:
            err(nom, f"Chevauchement : %MW{m}.{b} est un bit du mot %MW{m} utilisé par {mots[m]}.")
    if ouvrage.table_tt:
        # La table de télétransmission est la référence : elle remplace la qualification
        # variable par variable et la liste des écarts (une ligne « Sans source » les couvre).
        from .teletransmission import anomalies as anomalies_tt
        anomalies.extend(anomalies_tt(ouvrage, catalogue))
        return anomalies
    # Les identifications « Exacte » restent non validées tant que l'utilisateur
    # n'a pas confirmé. Une incohérence démontrée est bloquante.
    from .qualification import qualifications
    qualifs = qualifications(ouvrage, catalogue)
    for v in ouvrage.existantes:
        q = qualifs[id(v)]
        if q.niveau == "À confirmer":
            alerte(v.nom, q.motif)
        elif q.niveau == "Incohérence":
            err(v.nom, q.motif)
    for e in ecarts(ouvrage, catalogue):
        if e[0] == "Obligatoire absent":
            err(e[1], f"Signal obligatoire absent de l'automate : {e[3]} ({e[4]}).")
    return anomalies


# ====================================================================== export
def exporter_correspondance(chemin, ouvrage, catalogue):
    ent = ["Variable automate", "Type", "Adresse", "Commentaire automate", "Supervision", "Identification",
           "Repère", "Équipement", "Signal du catalogue", "Information", "Libellé Topkapi", "Remarque", "État métier", "Motif qualification", "Nature source", "Parent DDT", "Adresse parent (non transposable)", "ExtractBit", "Chemin symbolique", "Source XSY", "Adresse acquisition (vérifiée document.)", "Protocole", "Contrôle documentaire"]
    from .qualification import qualifications
    qualifs = qualifications(ouvrage, catalogue)
    lignes = []
    for v in ouvrage.existantes:
        eq = ouvrage.equipement(v.ident_eq)
        lignes.append([v.nom, v.type_logique, v.adresse, v.commentaire, "Oui" if v.retenue else "Non", v.identification,
                       ouvrage.repere(eq) if eq else "", catalogue.designation(eq.type) if eq else "", v.cle,
                       information_signal(catalogue, eq, v.cle), libelle_topkapi(ouvrage, catalogue, v) if v.retenue else "",
                       v.remarque, qualifs[id(v)].niveau, qualifs[id(v)].motif,
                       v.nature_source, v.parent_xsy, v.adresse_parent_xsy, v.extract_bit,
                       v.chemin_symbolique, v.fichier_source_xsy, v.adresse_acquisition,
                       v.protocole_acquisition, "Oui" if v.acces_verifie else "Non"])
    liste_ecarts = ecarts(ouvrage, catalogue)
    e_ent = ["Niveau", "Repère", "Équipement", "Signal attendu", "Information"]
    e_lig = [list(e[:5]) for e in liste_ecarts]
    anomalies = controler_existant(ouvrage, catalogue)
    from .qualification import qualifications
    qualifs = qualifications(ouvrage, catalogue)
    c_ent = ["Niveau", "Variable ou repère", "Message"]
    c_lig = [[a.niveau, a.repere, a.message] for a in anomalies]
    b = bilan(ouvrage)
    r_ent = ["Rubrique", "Valeur"]
    r_lig = [["Lieu", ouvrage.lieu], ["Ouvrage", ouvrage.code_ouvrage], ["Libellé", ouvrage.libelle],
             ["Automate", ouvrage.automate], ["Variables lues", b["total"]], ["Reprises en supervision", b["retenues"]],
             ["Identification exacte", b["Exacte"]], ["Identification probable (à confirmer)", b["Probable"]],
             ["Identification confirmée", b["Confirmée"]], ["À identifier", b["À identifier"]],
             ["Hors supervision", b["Hors supervision"]], ["Écarts avec le catalogue", len(liste_ecarts)],
             ["Erreurs", sum(1 for a in anomalies if a.niveau == "Erreur")],
             ["Alertes", sum(1 for a in anomalies if a.niveau == "Alerte")]]
    ecrire_xlsx(chemin, [
        ("Correspondance", ent, lignes, [28, 8, 12, 36, 10, 14, 16, 22, 12, 28, 34, 36, 18, 65, 17, 23, 25, 12, 40, 22, 32, 18, 20]),
        ("Écarts", e_ent, e_lig, [18, 16, 26, 14, 34]),
        ("Contrôles", c_ent, c_lig, [9, 26, 90]),
        ("Ouvrage", r_ent, r_lig, [36, 40]),
    ])
