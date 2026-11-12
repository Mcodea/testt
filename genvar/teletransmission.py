"""Table de télétransmission d'un ouvrage EXISTANT.

Principe (stratégie retenue) : on part des **informations attendues**, pas des variables du
programme.

1. Les équipements réellement présents sont déclarés (ou acceptés parmi ceux détectés dans
   les noms : jamais créés en silence).
2. Chaque information attendue d'un équipement (catalogue + options + signaux propres,
   moins les signaux déclarés non applicables) donne **une ligne** de la table, avec son
   nom standardisé calculé (TS_RV21MV01_OUV).
3. Pour chaque ligne, un moteur de rapprochement unique et déterministe
   (`rapprochement.proposer`, méthode hybride) propose des variables sources, avec les
   raisons de chaque proposition (preuves).
4. Chaque ligne porte **deux validations distinctes** :
     - fonction confirmée par l'automaticien (la variable porte bien cette information) ;
     - accès vérifié (adresse ou tag d'acquisition et protocole contrôlés pour TOPKAPI).
5. Une information introuvable reste dans la table, avec l'état « Sans source » jusqu'à ce
   que l'automaticien la déclare « Non accessible » (avec un motif). Aucune adresse n'est
   inventée, aucune variable source n'est modifiée.

Statuts d'une ligne (couleurs de l'interface) :
    Validée         vert   fonction confirmée + accès vérifié + aucune incohérence
    À compléter     orange source proposée ou associée, une des deux validations manque
    Sans source     orange aucune variable associée, décision à prendre
    Incohérence     rouge  défaut technique démontré (type, sens, doublon, source disparue…)
    Non accessible  gris   décision explicite : l'information n'est pas disponible
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .modele import signaux_retenus, TAILLE_MOTS, Anomalie, registre_modbus, catalogue_pour_equipement
from .catalogue import est_interne
from .rapprochement import CONFIANCE_ELEVEE

STATUTS = ("Validée", "À compléter", "Sans source", "Incohérence", "Non accessible")
COULEUR = {"Validée": "OK", "À compléter": "Alerte", "Sans source": "Alerte",
           "Incohérence": "Erreur", "Non accessible": "Neutre"}

# Sens de communication vu de la supervision.
SENS = {"TS": "Remontée", "TM": "Remontée", "CP": "Remontée", "RTR": "Remontée",
        "TC": "Descente", "TR": "Descente"}
ORDRE_FAMILLES = {"TS": 0, "TM": 1, "CP": 2, "TC": 3, "TR": 4, "RTR": 5}
PROTOCOLES = ("", "Modbus TCP", "Modbus RTU", "OPC / OFS", "SOFREL S4W", "Autre")

RE_ENTREE = re.compile(r"^%I(W|D|F|X)?\d", re.I)
RE_SORTIE = re.compile(r"^%Q(W|D|F|X)?\d", re.I)
RE_MOT = re.compile(r"^%M[WDF](\d+)", re.I)


@dataclass
class LigneTT:
    """Décision de l'automaticien pour une information attendue. Seules les décisions sont
    enregistrées ; les données d'origine (nom, type, adresse source) sont relues dans
    l'inventaire du programme à chaque affichage."""
    ident_eq: str
    cle: str                                  # FAMILLE_CODE
    variable_source: str = ""                 # nom exact dans le programme
    origine_association: str = ""             # « Proposition acceptée » ou « Choix manuel »
    preuves: list = field(default_factory=list)
    fonction_validee: bool = False
    adresse_acquisition: str = ""             # vide : l'adresse source est utilisée
    protocole: str = ""
    acces_verifie: bool = False
    non_accessible: bool = False
    motif_non_accessible: str = ""
    remarque: str = ""
    hors_perimetre: bool = False              # signal plus attendu, conservé car il portait des décisions


@dataclass
class LigneVue:
    """Ligne calculée pour l'affichage et l'export (rien n'est stocké ici)."""
    ligne: LigneTT
    repere: str
    uf: str
    designation: str
    famille: str
    code: str
    information: str
    nom_standard: str
    type_attendu: str
    sens: str
    variable_source: str
    type_source: str
    adresse_source: str
    commentaire_source: str
    adresse_acquisition: str                  # adresse effectivement utilisée pour l'acquisition
    registre: str
    protocole: str
    statut: str
    motif: str
    ordre: tuple = ()


class RegleTT(ValueError):
    """Opération refusée sur la table ; le message s'affiche tel quel."""


# ====================================================================== construction
def _attendus(ouvrage, catalogue, eq):
    # Ancien dossier : modèle historique sans « signaux » -> comportement conservé.
    # Nouveau dossier : table attendue propre au modèle de chaque équipement.
    cat = catalogue_pour_equipement(ouvrage, catalogue, eq) if ouvrage is not None else catalogue
    for s, origine in signaux_retenus(cat, eq):
        if s.get("famille") in ("ES", "", None) or est_interne(s.get("famille")):
            continue                    # E/S locale ou variable interne déclarée : jamais télétransmise
        yield s, f"{s['famille']}_{s['code']}"


def construire(ouvrage, catalogue):
    """Crée une ligne par information attendue. Conserve toutes les décisions existantes.
    Renvoie (lignes ajoutées, lignes passées hors périmètre)."""
    existantes = {(l.ident_eq, l.cle): l for l in ouvrage.table_tt}
    attendues = set()
    ajoutees = 0
    for eq in ouvrage.equipements:
        for s, cle in _attendus(ouvrage, catalogue, eq):
            attendues.add((eq.ident, cle))
            l = existantes.get((eq.ident, cle))
            if l is None:
                ouvrage.table_tt.append(LigneTT(eq.ident, cle))
                ajoutees += 1
            elif l.hors_perimetre:
                l.hors_perimetre = False
    retirees = 0
    garder = []
    for l in ouvrage.table_tt:
        if (l.ident_eq, l.cle) in attendues:
            garder.append(l)
            continue
        porte_decision = l.variable_source or l.fonction_validee or l.non_accessible or l.acces_verifie
        if porte_decision and ouvrage.equipement(l.ident_eq) is not None:
            if not l.hors_perimetre:
                retirees += 1
            l.hors_perimetre = True
            garder.append(l)            # visible, pour ne rien perdre en silence
        else:
            retirees += 1
            _miroir(ouvrage, l, effacer=True)
    ouvrage.table_tt = garder
    return ajoutees, retirees


def ligne(ouvrage, ident_eq, cle):
    l = next((x for x in ouvrage.table_tt if x.ident_eq == ident_eq and x.cle == cle), None)
    if l is None:
        raise RegleTT("Ligne absente de la table : reconstruire la table.")
    return l


# ====================================================================== statut
def _source(ouvrage, nom):
    return next((v for v in ouvrage.existantes if v.nom == nom), None) if nom else None


def _signal(ouvrage, catalogue, eq, cle):
    cat = catalogue_pour_equipement(ouvrage, catalogue, eq)
    for s, c in _attendus(ouvrage, catalogue, eq):
        if c == cle:
            return s
    for s in cat.signaux_du_type(eq.type, avec_ecartes=True):
        if f"{s['famille']}_{s['code']}" == cle:
            return s
    return None


def _types_compatibles(reel, attendu):
    from .rapprochement import types_compatibles
    return types_compatibles(reel, attendu)


def evaluer(ouvrage, catalogue, l, usages=None):
    """(statut, motif) d'une ligne. Ne modifie rien."""
    if l.hors_perimetre:
        return "Incohérence", "Information hors périmètre : réexaminer la décision ou reconstruire la table."
    if l.non_accessible:
        if l.variable_source or l.fonction_validee or l.acces_verifie:
            return "Incohérence", "Non accessible contradictoire avec une source ou une validation encore active."
        if not l.motif_non_accessible.strip():
            return "À compléter", "Décision non accessible : motif obligatoire."
        return "Non accessible", l.motif_non_accessible
    if not l.variable_source:
        return "Sans source", "Aucune variable du programme associée : associer un candidat ou déclarer non accessible."
    eq = ouvrage.equipement(l.ident_eq)
    v = _source(ouvrage, l.variable_source)
    if v is None:
        return "Incohérence", f"La variable {l.variable_source} n'existe plus dans l'inventaire importé."
    incoherences = []
    if eq is None:
        incoherences.append("Équipement supprimé.")
    s = _signal(ouvrage, catalogue, eq, l.cle) if eq else None
    if eq is not None and s is None:
        incoherences.append("Signal absent du catalogue de l'équipement.")
    if s is not None and not _types_compatibles(v.type_logique, s.get("type_logique")):
        incoherences.append(f"Types incompatibles : programme {v.type_logique or '?'} / attendu {s.get('type_logique')}.")
    usages = usages if usages is not None else Counter(x.variable_source for x in ouvrage.table_tt
                                                       if x.variable_source and not x.non_accessible)
    if usages.get(l.variable_source, 0) > 1:
        incoherences.append(f"{l.variable_source} est associée à plusieurs informations.")
    famille = l.cle.split("_", 1)[0]
    adresse = (v.adresse or "").strip()
    if SENS.get(famille) == "Descente" and RE_ENTREE.match(adresse):
        incoherences.append(f"Une {famille} (descente) ne peut pas viser une entrée physique {adresse}.")
    m = RE_MOT.match(adresse)
    if (m and TAILLE_MOTS.get((v.type_logique or "").upper()) in (2, 4) and int(m.group(1)) % 2
            and (ouvrage.automate or "").upper() in ("M340", "M580")):
        incoherences.append(f"Valeur 32 bits sur l'adresse impaire {adresse}.")
    if l.hors_perimetre:
        incoherences.append("Information plus attendue pour cet équipement (option ou signal retiré).")
    if incoherences:
        return "Incohérence", " ".join(incoherences)
    manques = []
    if not l.fonction_validee:
        manques.append("fonction à confirmer")
    adresse_effective = (l.adresse_acquisition or
                         (adresse if v.nature_source != "Champ DDT" else ""))
    if l.acces_verifie and not adresse_effective:
        manques.append("adresse/tag d'acquisition absent malgré la validation enregistrée")
    if l.acces_verifie and not (l.protocole or ouvrage.communication):
        manques.append("protocole d'acquisition absent malgré la validation enregistrée")
    if not l.acces_verifie:
        if v.nature_source == "Champ DDT" and not l.adresse_acquisition:
            manques.append("adresse/tag d'acquisition du champ DDT à établir")
        elif RE_ENTREE.match(adresse) or RE_SORTIE.match(adresse):
            manques.append("E/S physique : accès direct TOPKAPI à démontrer")
        else:
            manques.append("accès TOPKAPI (adresse + protocole) à vérifier")
    if manques:
        return "À compléter", "À faire : " + ", ".join(manques) + "."
    return "Validée", "Fonction confirmée et accès vérifié (communication réelle à tester en recette)."


def vue(ouvrage, catalogue, avec_hors_perimetre=True):
    """Lignes calculées, triées par UF, repère puis famille."""
    usages = Counter(x.variable_source for x in ouvrage.table_tt if x.variable_source and not x.non_accessible)
    libelles_uf = {u.code: u.libelle for u in ouvrage.unites}
    rang_eq = {e.ident: i for i, e in enumerate(ouvrage.equipements)}
    lignes = []
    for l in ouvrage.table_tt:
        if l.hors_perimetre and not avec_hors_perimetre:
            continue
        eq = ouvrage.equipement(l.ident_eq)
        famille, code = l.cle.split("_", 1)
        s = _signal(ouvrage, catalogue, eq, l.cle) if eq else None
        v = _source(ouvrage, l.variable_source)
        statut, motif = evaluer(ouvrage, catalogue, l, usages)
        adresse_acq = l.adresse_acquisition or (v.adresse if v and v.nature_source != "Champ DDT" else "")
        rep = ouvrage.repere(eq) if eq else "(équipement supprimé)"
        lignes.append(LigneVue(
            ligne=l, repere=rep,
            uf=(f"{eq.uf} {libelles_uf.get(eq.uf, '')}".strip() if eq and eq.uf else ""),
            designation=catalogue.designation(eq.type) if eq else "",
            famille=famille, code=code, information=(s or {}).get("information", ""),
            nom_standard=f"{famille}_{ouvrage.repere_nom(eq)}_{code}" if eq else "",
            type_attendu=(s or {}).get("type_logique", ""), sens=SENS.get(famille, ""),
            variable_source=l.variable_source, type_source=v.type_logique if v else "",
            adresse_source=v.adresse if v else "", commentaire_source=v.commentaire if v else "",
            adresse_acquisition=adresse_acq,
            registre=registre_modbus(adresse_acq, ouvrage.decalage_modbus) if adresse_acq else "",
            protocole=l.protocole or ouvrage.communication,
            statut=statut, motif=motif,
            ordre=(eq.uf if eq else "~", rang_eq.get(l.ident_eq, 9999), ORDRE_FAMILLES.get(famille, 9), code)))
    lignes.sort(key=lambda x: x.ordre)
    return lignes


def bilan(ouvrage, catalogue):
    c = Counter(x.statut for x in vue(ouvrage, catalogue))
    return {s: c.get(s, 0) for s in STATUTS} | {"total": sum(c.values())}


def verifier_cloture(ouvrage, catalogue):
    """Retourne les motifs empêchant le statut global « Validé » (projet existant).

    Contrôle de la *table complète*, pas seulement des lignes déjà présentes :
    toutes les informations encore attendues sont présentes exactement une fois.
    Une ligne attendue est close si elle est « Validée » (fonction ET accès)
    ou « Non accessible » avec décision motivée. Les informations explicitement
    « Non applicables » sont exclues de ``signaux_retenus`` via ``eq.exclus``.
    Ne modifie aucune donnée et ne reconstruit jamais la table silencieusement.
    """
    if not ouvrage.table_tt:
        return ["Projet existant : construire la table de télétransmission avant validation."]

    attendues = {(eq.ident, cle) for eq in ouvrage.equipements
                 for _, cle in _attendus(ouvrage, catalogue, eq)}
    if not attendues:
        return ["Projet existant : aucun signal attendu dans le périmètre ; vérifier les équipements et le catalogue."]

    problemes = []
    comptes = Counter((l.ident_eq, l.cle) for l in ouvrage.table_tt)
    doublons = sorted(k for k, n in comptes.items() if n > 1)
    if doublons:
        problemes.append(f"Table de télétransmission : {len(doublons)} doublon(s) de ligne "
                         f"(ex. {doublons[0][1]}).")

    manquantes = sorted(attendues - set(comptes))
    if manquantes:
        eq = ouvrage.equipement(manquantes[0][0])
        rep = ouvrage.repere(eq) if eq else "?"
        problemes.append(f"Table de télétransmission incomplète : {len(manquantes)} information(s) "
                         f"attendue(s) manquante(s) (ex. {rep} / {manquantes[0][1]}). "
                         "Reconstruire la table, puis traiter les nouvelles lignes.")

    anciennes = set(comptes) - attendues
    hors_perimetre = [l for l in ouvrage.table_tt if l.hors_perimetre]
    if anciennes or hors_perimetre:
        problemes.append("Table de télétransmission : des lignes hors périmètre ou devenues "
                         "non attendues sont à examiner avant validation.")

    lignes = vue(ouvrage, catalogue)
    for statut in ("Incohérence", "Sans source", "À compléter"):
        non_closes = [v for v in lignes if (v.ligne.ident_eq, v.ligne.cle) in attendues
                      and v.statut == statut]
        if non_closes:
            premier = non_closes[0]
            problemes.append(f"Table de télétransmission : {len(non_closes)} ligne(s) "
                             f"« {statut} » (ex. {premier.nom_standard or premier.ligne.cle}) : "
                             f"{premier.motif}")
    return problemes


# ====================================================================== candidats
def candidats(ouvrage, catalogue, limite=5):
    """{(ident_eq, cle): [Proposition]} : moteur de rapprochement unique (méthode hybride).
    Une variable déjà associée à une autre ligne est retirée des propositions."""
    from .rapprochement import proposer
    prises = {l.variable_source: (l.ident_eq, l.cle) for l in ouvrage.table_tt
              if l.variable_source and not l.non_accessible}
    brut = proposer(ouvrage, catalogue, "hybride", limite=limite + 5)
    resultat = {}
    for cle, props in brut.items():
        resultat[cle] = [p for p in props if prises.get(p.variable_nom, cle) == cle][:limite]
    return resultat


def proposer_associations(ouvrage, catalogue):
    """Associe la meilleure proposition aux lignes sans source, SANS rien valider.

    Une ligne n'est remplie que si son premier candidat n'est pas ambigu et n'est pas déjà
    pris par une autre ligne. Les lignes déjà décidées (source, non accessible) ne bougent pas.
    Renvoie le nombre d'associations proposées."""
    props = candidats(ouvrage, catalogue, limite=3)
    n = 0
    prises = {l.variable_source for l in ouvrage.table_tt if l.variable_source}
    for l in ouvrage.table_tt:
        if l.variable_source or l.non_accessible or l.hors_perimetre:
            continue
        liste = props.get((l.ident_eq, l.cle), [])
        if not liste or liste[0].ambiguite or liste[0].variable_nom in prises:
            continue
        p = liste[0]
        _associer(ouvrage, l, p.variable_nom, list(p.indices) + [f"Score de classement {p.score}/100 (pas une probabilité)"],
                  "Proposition automatique")
        prises.add(p.variable_nom)
        n += 1
    return n


# ====================================================================== décisions
def _miroir(ouvrage, l, effacer=False):
    """Reflète la décision sur la variable source (lecture seule de ses données d'origine)."""
    v = _source(ouvrage, l.variable_source)
    if v is None:
        return
    if effacer:
        if v.ident_eq == l.ident_eq and v.cle == l.cle:
            v.ident_eq, v.cle = "", ""
            v.identification = "À identifier"
        return
    v.ident_eq, v.cle, v.retenue = l.ident_eq, l.cle, True
    v.identification = "Confirmée" if l.fonction_validee else "Probable"


def _associer(ouvrage, l, nom, preuves, origine):
    if l.variable_source and l.variable_source != nom:
        _miroir(ouvrage, l, effacer=True)
    l.variable_source = nom
    l.preuves = list(preuves)
    l.origine_association = origine
    l.fonction_validee = False
    l.acces_verifie = False
    l.non_accessible = False
    l.motif_non_accessible = ""
    _miroir(ouvrage, l)


def associer(ouvrage, catalogue, ident_eq, cle, nom, preuves=(), origine="Choix manuel"):
    """Associe une variable du programme à une ligne. Les validations sont remises à zéro."""
    l = ligne(ouvrage, ident_eq, cle)
    v = _source(ouvrage, nom)
    if v is None:
        raise RegleTT(f"Variable {nom} introuvable dans l'inventaire.")
    eq = ouvrage.equipement(ident_eq)
    s = _signal(ouvrage, catalogue, eq, cle) if eq else None
    if s is not None and not _types_compatibles(v.type_logique, s.get("type_logique")):
        raise RegleTT(f"Types incompatibles : {nom} est {v.type_logique or '?'}, l'information attend "
                      f"{s.get('type_logique')}. Aucune conversion n'est supposée.")
    autre = next((x for x in ouvrage.table_tt if x is not l and x.variable_source == nom and not x.non_accessible), None)
    if autre is not None:
        eq2 = ouvrage.equipement(autre.ident_eq)
        raise RegleTT(f"{nom} est déjà associée à {ouvrage.repere(eq2) if eq2 else '?'} {autre.cle}. "
                      "La dissocier d'abord.")
    if not preuves:
        preuves = [f"Choix manuel de l'automaticien. Commentaire source : « {v.commentaire} »" if v.commentaire
                   else "Choix manuel de l'automaticien."]
    _associer(ouvrage, l, nom, preuves, origine)
    return l


def dissocier(ouvrage, ident_eq, cle):
    l = ligne(ouvrage, ident_eq, cle)
    _miroir(ouvrage, l, effacer=True)
    l.variable_source, l.preuves, l.origine_association = "", [], ""
    l.fonction_validee = l.acces_verifie = False
    return l


def _tracer(ouvrage, action, lignes, par="", **extra):
    """Ajoute une entrée au journal des confirmations du rapprochement et la renvoie."""
    from datetime import datetime, timezone
    journal = ouvrage.journal_rapprochement
    entree = {"id": max([e.get("id", 0) for e in journal] + [0]) + 1,
              "le": datetime.now(timezone.utc).isoformat(timespec="seconds"), "par": par, "action": action,
              "lignes": lignes, **extra}
    journal.append(entree)
    return entree


def valider_fonction(ouvrage, ident_eq, cle, valide=True, par=""):
    """Confirmation (ou retrait de confirmation) une par une, tracée dans le journal du rapprochement."""
    l = ligne(ouvrage, ident_eq, cle)
    if valide and not l.variable_source:
        raise RegleTT("Associer d'abord une variable source.")
    avant = l.fonction_validee
    l.fonction_validee = bool(valide)
    _miroir(ouvrage, l)
    if avant != l.fonction_validee:
        _tracer(ouvrage, "confirmation" if valide else "annulation de confirmation",
                [{"ident_eq": ident_eq, "cle": cle, "variable": l.variable_source}], par)
    return l


def confirmables_en_lot(ouvrage, catalogue):
    """Lignes dont la source associée est le premier candidat, de confiance élevée (seuil, non ambigu), et
    dont la fonction n'est pas encore confirmée. Rien n'est modifié. [(LigneTT, Proposition)]."""
    props = candidats(ouvrage, catalogue, limite=1)
    sortie = []
    for l in ouvrage.table_tt:
        if not l.variable_source or l.fonction_validee or l.non_accessible or l.hors_perimetre:
            continue
        liste = props.get((l.ident_eq, l.cle), [])
        if liste and liste[0].variable_nom == l.variable_source and liste[0].confiance == CONFIANCE_ELEVEE:
            sortie.append((l, liste[0]))
    return sortie


def confirmer_en_lot(ouvrage, catalogue, par=""):
    """Confirme en un geste la fonction des lignes de confiance élevée (voir ``confirmables_en_lot``).

    L'accès TOPKAPI n'est pas vérifié par ce geste. Le lot est tracé et annulable (``annuler_lot``).
    Renvoie l'entrée du journal, ou None si aucune ligne n'est confirmable."""
    choisies = confirmables_en_lot(ouvrage, catalogue)
    if not choisies:
        return None
    for l, _ in choisies:
        l.fonction_validee = True
        _miroir(ouvrage, l)
    return _tracer(ouvrage, "confirmation en lot",
                   [{"ident_eq": l.ident_eq, "cle": l.cle, "variable": l.variable_source, "score": p.score,
                     "raison": p.raison} for l, p in choisies], par, annule=False)


def annuler_lot(ouvrage, id_lot, par=""):
    """Annule une confirmation en lot : chaque ligne encore confirmée avec la même source redevient « à
    confirmer » (une ligne modifiée depuis est laissée telle quelle et signalée). Tracé. Renvoie l'entrée."""
    lot = next((e for e in ouvrage.journal_rapprochement
                if e.get("id") == id_lot and e.get("action") == "confirmation en lot"), None)
    if lot is None:
        raise RegleTT(f"Confirmation en lot n° {id_lot} introuvable.")
    if lot.get("annule"):
        raise RegleTT(f"La confirmation en lot n° {id_lot} est déjà annulée.")
    annulees, laissees = [], []
    for x in lot["lignes"]:
        l = next((y for y in ouvrage.table_tt if y.ident_eq == x["ident_eq"] and y.cle == x["cle"]), None)
        if l is not None and l.fonction_validee and l.variable_source == x["variable"]:
            l.fonction_validee = False
            _miroir(ouvrage, l)
            annulees.append(x)
        else:
            laissees.append(x)
    lot["annule"] = True
    return _tracer(ouvrage, "annulation de lot", annulees, par, lot=id_lot, laissees=laissees)


def definir_acces(ouvrage, ident_eq, cle, adresse_acquisition=None, protocole=None, verifie=None):
    """Renseigne l'accès TOPKAPI. « Vérifié » exige une adresse effective ET un protocole."""
    l = ligne(ouvrage, ident_eq, cle)
    v = _source(ouvrage, l.variable_source)
    nouvelle_adr = l.adresse_acquisition if adresse_acquisition is None else adresse_acquisition.strip()
    nouveau_proto = l.protocole if protocole is None else protocole.strip()
    # Une confirmation porte sur l'adresse effective ET le protocole effectivement examinés.
    # Leur modification ultérieure annule la preuve documentaire, sauf nouvelle validation
    # explicite dans le même geste (verifie=True).
    changement = (nouvelle_adr != l.adresse_acquisition or nouveau_proto != l.protocole)
    nouveau_verifie = ((False if changement else l.acces_verifie)
                      if verifie is None else bool(verifie))
    if nouveau_verifie:
        if v is None:
            raise RegleTT("Associer d'abord une variable source.")
        effective = nouvelle_adr or (v.adresse if v.nature_source != "Champ DDT" else "")
        if not effective:
            raise RegleTT("Accès vérifié : renseigner l'adresse ou le tag d'acquisition (l'adresse d'un parent "
                          "DDT n'est jamais recopiée).")
        if not (nouveau_proto or ouvrage.communication):
            raise RegleTT("Accès vérifié : préciser le protocole (ligne ou ouvrage).")
    l.adresse_acquisition, l.protocole, l.acces_verifie = nouvelle_adr, nouveau_proto, nouveau_verifie
    return l


def declarer_non_accessible(ouvrage, ident_eq, cle, motif):
    motif = (motif or "").strip()
    if not motif:
        raise RegleTT("Indiquer pourquoi l'information n'est pas accessible (ex. absente du programme, "
                      "non câblée, à créer lors des travaux).")
    l = ligne(ouvrage, ident_eq, cle)
    _miroir(ouvrage, l, effacer=True)
    l.variable_source, l.preuves, l.origine_association = "", [], ""
    l.fonction_validee = l.acces_verifie = False
    l.non_accessible, l.motif_non_accessible = True, motif
    return l


def reouvrir(ouvrage, ident_eq, cle):
    l = ligne(ouvrage, ident_eq, cle)
    l.non_accessible, l.motif_non_accessible = False, ""
    return l


def non_applicable(ouvrage, catalogue, ident_eq, cle):
    """Le signal n'existe pas sur cet équipement : il sort des informations attendues."""
    eq = ouvrage.equipement(ident_eq)
    if eq is None:
        raise RegleTT("Équipement introuvable.")
    l = ligne(ouvrage, ident_eq, cle)
    if l.variable_source:
        raise RegleTT("Dissocier d'abord la variable source.")
    if cle not in eq.exclus:
        eq.exclus.append(cle)
    # Décision explicite confirmée dans l'interface : une information qui est
    # « Non applicable » ne peut pas rester simultanément « Non accessible ».
    # La référence eq.exclus conserve l'exclusion dans l'ouvrage sauvegardé.
    l.non_accessible = False
    l.motif_non_accessible = ""
    l.fonction_validee = False
    l.acces_verifie = False
    construire(ouvrage, catalogue)


# ====================================================================== équipements détectés
@dataclass
class EquipementDetecte:
    sous_ensemble: str
    type: str
    numero: str
    designation: str
    variables: list

    @property
    def code(self):
        return f"{self.sous_ensemble}{self.type}{self.numero}"


def equipements_detectes(ouvrage, catalogue):
    """Équipements trouvés dans les noms normalisés (FAMILLE_[LIEU]OUVRAGE SE TYPE N°_…) et pas
    encore déclarés. Ce sont des PROPOSITIONS : rien n'est créé sans accord."""
    from .existant import decouper, PREFIXES
    declares = {(e.sous_ensemble, e.type, e.numero) for e in ouvrage.equipements}
    trouves: dict[tuple[str, str, str], list[str]] = {}
    for v in ouvrage.existantes:
        d = decouper(v.nom)
        if not d or not d[3] or d[0] not in PREFIXES:
            continue
        _, se, typ, num = d[3]
        if catalogue.type(typ) is None or (se, typ, num) in declares:
            continue
        trouves.setdefault((se, typ, num), []).append(v.nom)
    return [EquipementDetecte(se, t, n, catalogue.designation(t), sorted(noms))
            for (se, t, n), noms in sorted(trouves.items())]


def ajouter_detectes(ouvrage, detectes):
    from .modele import Equipement, SousEnsemble
    n = 0
    for d in detectes:
        if not any(s.code == d.sous_ensemble for s in ouvrage.sous_ensembles):
            ouvrage.sous_ensembles.append(SousEnsemble(d.sous_ensemble, ""))
            ouvrage.sous_ensembles.sort(key=lambda s: s.code)
        if not any((e.sous_ensemble, e.type, e.numero) == (d.sous_ensemble, d.type, d.numero)
                   for e in ouvrage.equipements):
            ouvrage.equipements.append(Equipement(d.sous_ensemble, d.type, d.numero, ""))
            n += 1
    return n


# ====================================================================== contrôles et export
def anomalies(ouvrage, catalogue):
    """Anomalies de la table : rouge = Erreur ; lignes orange regroupées en alertes."""
    resultat = []
    lignes = vue(ouvrage, catalogue)
    for x in lignes:
        if x.statut == "Incohérence":
            resultat.append(Anomalie("Erreur", x.repere, f"{x.nom_standard or x.ligne.cle} : {x.motif}", x.ligne.ident_eq))
    sans = [x for x in lignes if x.statut == "Sans source"]
    incompletes = [x for x in lignes if x.statut == "À compléter"]
    if sans:
        resultat.append(Anomalie("Alerte", "Télétransmission",
                                 f"{len(sans)} information(s) sans source : associer une variable ou déclarer "
                                 f"non accessible (ex. {sans[0].nom_standard})."))
    if incompletes:
        resultat.append(Anomalie("Alerte", "Télétransmission",
                                 f"{len(incompletes)} ligne(s) à compléter : fonction et/ou accès TOPKAPI "
                                 f"à valider (ex. {incompletes[0].nom_standard})."))
    return resultat


def exporter(chemin, ouvrage, catalogue):
    from .export_xlsx import ecrire_xlsx
    lignes = vue(ouvrage, catalogue)
    ent = ["Statut", "UF", "Repère", "Équipement", "Famille", "Information", "Nom standardisé", "Sens",
           "Variable source", "Type source", "Adresse source", "Adresse / tag acquisition", "Registre Modbus",
           "Protocole", "Fonction confirmée", "Accès vérifié", "Motif / reste à faire", "Preuves",
           "Commentaire source", "Remarque"]
    lig = [[x.statut, x.uf, x.repere, x.designation, x.famille, x.information, x.nom_standard, x.sens,
            x.variable_source, x.type_source, x.adresse_source, x.adresse_acquisition, x.registre, x.protocole,
            "Oui" if x.ligne.fonction_validee else "Non", "Oui" if x.ligne.acces_verifie else "Non",
            x.motif, " | ".join(x.ligne.preuves), x.commentaire_source, x.ligne.remarque] for x in lignes]
    utilisees = {l.variable_source for l in ouvrage.table_tt if l.variable_source}
    inv_ent = ["Variable", "Type", "Adresse", "Commentaire", "Origine"]
    inv = [[v.nom, v.type_logique, v.adresse, v.commentaire, v.nature_source]
           for v in ouvrage.existantes if v.nom not in utilisees]
    b = Counter(x.statut for x in lignes)
    an = anomalies(ouvrage, catalogue)
    res = [["Ouvrage", f"{ouvrage.prefixe()} {ouvrage.libelle}"], ["Automate", ouvrage.automate],
           ["Protocole par défaut", ouvrage.communication or "(non renseigné)"],
           ["Lignes de la table", len(lignes)]] + [[s, b.get(s, 0)] for s in STATUTS] + [
           ["Variables du programme non utilisées", len(inv)],
           ["Avertissement", "Table de travail. Le format d'import TOPKAPI doit être établi et vérifié sur un "
                             "fichier réel avant tout import automatique."]]
    ecrire_xlsx(chemin, [
        ("Télétransmission", ent, lig, [14, 18, 16, 22, 8, 30, 28, 11, 26, 9, 13, 18, 11, 13, 10, 10, 50, 60, 36, 24]),
        ("Inventaire non utilisé", inv_ent, inv, [28, 9, 14, 44, 14]),
        ("Contrôles", ["Niveau", "Repère", "Message"], [[a.niveau, a.repere, a.message] for a in an], [9, 24, 100]),
        ("Synthèse", ["Rubrique", "Valeur"], res, [36, 70]),
    ])
    return len(lignes)
