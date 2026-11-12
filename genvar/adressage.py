"""Moteur d'adressage centralisé : E/S physiques, variables automate, points de télétransmission.

UN seul point d'entrée (`calculer`, puis `appliquer`) ; les règles propres à chaque plateforme sont des
adaptateurs. Les algorithmes déjà qualifiés d'OGIAS sont réutilisés, pas dupliqués :
- E/S physiques Schneider M340 / M580 : `cartes_es.implanter` (voies des cartes déclarées, réserve de voies) ;
- variables de la table d'échange Schneider : `modele.plan_adresses` (plages %MW par famille, BOOL sur un bit,
  INT sur un mot, DINT / REAL sur deux mots alignés, RTR en miroir de son TR) ;
- points de télétransmission : identifiant = nom de la variable (un seul point par variable, jamais deux) ;
  adresse protocolaire = registre du mot (%MW + décalage) SEULEMENT quand la convention est déclarée.

Trois niveaux distincts, jamais confondus :
  physique          équipement · signal · contrôleur · module · voie · adresse %I/%Q/%IW/%QW
  automate          variable de la table d'échange · adresse %MW (une variable interne ne prend aucune voie)
  télétransmission  point (identifiant fonctionnel) · adresse protocolaire · variable source

Règles de fiabilité :
- deux phases : `calculer` ne modifie rien ; `appliquer` exige l'empreinte du plan montré, refuse s'il reste un
  conflit, travaille sur une copie et remet l'ouvrage en l'état à la moindre erreur (rien de partiel) ;
- une adresse validée ne change jamais ; une adresse déjà attribuée n'est pas déplacée ;
- une réservation (voie, plage mémoire, point) n'est jamais utilisée sans décision explicite ;
- rien n'est inventé : si une donnée manque, l'affectation reste « non résolue » avec la donnée manquante ;
- projet existant : aucune réaffectation des adresses historiques ; aucune nouvelle adresse tant que la
  disponibilité de la mémoire n'est pas établie (« disponibilité non vérifiée ») ;
- déterminisme : mêmes données, même plan, même empreinte. Ordre d'affectation documenté :
  physique  : UF, puis équipement (ordre de l'arbre), puis signaux dans l'ordre du référentiel ; les E/S d'un
              équipement restent groupées sur une carte si possible ; cartes par rack puis position ;
              d'abord sans entamer la réserve de voies, sinon en l'entamant (alerte) ;
  automate  : familles TR, TS, TC, TM, CP, RTR ; dans une famille, ordre des équipements et du référentiel ;
              première place libre de la plage (bit, mot, ou double mot aligné).
"""
import copy
import getpass
import hashlib
import math
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime

from . import materiel
from .cartes_es import implanter, controler as controler_cartes, place, cle_module, secours_partageant_une_carte
from .modele import plan_adresses, registre_modbus, _mot

NIVEAUX = ("physique", "automate", "teletransmission")
LIBELLES_NIVEAU = {"physique": "E/S physiques", "automate": "Variables automate", "teletransmission": "Télétransmission"}


class AdressageRefuse(ValueError):
    """Application refusée : plan périmé, conflit bloquant ou erreur ; l'ouvrage n'a pas été modifié."""


@dataclass
class Affectation:
    niveau: str
    ident_eq: str
    repere: str
    cle: str
    nom: str
    nature: str                    # ET/ST/EA/SA, ou famille TS/TM/TC/TR/RTR/CP
    type_logique: str = ""
    controleur: str = ""
    plateforme: str = ""
    module: str = ""
    voie: str = ""
    actuelle: str = ""
    proposee: str = ""
    origine: str = ""              # conservée, proposée, importée, saisie
    etat: str = ""                 # validée, à valider, proposée, non résolue, en conflit
    regle: str = ""
    motif: str = ""                # donnée manquante ou conflit
    validee_le: str = ""
    validee_par: str = ""

    @property
    def adresse(self):
        return self.proposee or self.actuelle


@dataclass
class Plan:
    affectations: list = field(default_factory=list)
    conflits: list = field(default_factory=list)          # [(niveau, message)] : bloquants
    alertes: list = field(default_factory=list)
    besoins: list = field(default_factory=list)           # simulation de cartes à ajouter (jamais ajoutées)
    empreinte: str = ""

    def synthese(self):
        s = {}
        for n in NIVEAUX:
            a = [x for x in self.affectations if x.niveau == n]
            s[n] = {"total": len(a), "validees": sum(x.etat == "validée" for x in a),
                    "a_valider": sum(x.etat == "à valider" for x in a),
                    "proposees": sum(x.etat == "proposée" for x in a),
                    "non_resolues": sum(x.etat == "non résolue" for x in a),
                    "conflits": sum(x.etat == "en conflit" for x in a) + sum(1 for c in self.conflits if c[0] == n)}
        return s

    def dict(self):
        return {"affectations": [asdict(a) for a in self.affectations], "conflits": self.conflits,
                "alertes": self.alertes, "besoins": self.besoins, "empreinte": self.empreinte,
                "synthese": self.synthese()}


# ---------------------------------------------------------------------------- réservations
RE_VOIES = re.compile(r"^(\d{1,2}\.\d{1,2}|\d{1,2})\s*[:/]\s*(\d{1,3})(?:\s*-\s*(\d{1,3}))?$")
RE_MEMOIRE = re.compile(r"^%MW(\d+)(?:\s*-\s*%?(?:MW)?(\d+))?$", re.I)


def voies_reservees(ouvrage):
    sortie = set()
    for r in ouvrage.reservations:
        if r.get("niveau") != "voie":
            continue
        m = RE_VOIES.match(r.get("cible", "").strip())
        if m:
            k = cle_module(m.group(1))
            for v in range(int(m.group(2)), int(m.group(3) or m.group(2)) + 1):
                sortie.add((k, v))
    return sortie


def plages_reservees(ouvrage):
    sortie = []
    for r in ouvrage.reservations:
        if r.get("niveau") != "memoire":
            continue
        m = RE_MEMOIRE.match(r.get("cible", "").replace(" ", ""))
        if m:
            sortie.append((int(m.group(1)), int(m.group(2) or m.group(1)), r.get("motif", "") or "réservation"))
    return sortie


def verifier_reservation(niveau, cible):
    """Normalise et contrôle une réservation saisie ; lève AdressageRefuse si elle est illisible."""
    cible = (cible or "").strip()
    if niveau == "voie":
        m = RE_VOIES.match(cible)
        if not m or not cle_module(m.group(1)):
            raise AdressageRefuse("Voie réservée : « rack.emplacement:voie » ou « …:première-dernière » (ex. 0.3:12-15).")
        return f"{cle_module(m.group(1))}:{m.group(2)}" + (f"-{m.group(3)}" if m.group(3) else "")
    if niveau == "memoire":
        m = RE_MEMOIRE.match(cible.replace(" ", ""))
        if not m or (m.group(2) and int(m.group(2)) < int(m.group(1))):
            raise AdressageRefuse("Plage mémoire réservée : « %MW1200 » ou « %MW1200-%MW1215 ».")
        return f"%MW{m.group(1)}" + (f"-%MW{m.group(2)}" if m.group(2) else "")
    if niveau == "protocole":
        if not cible:
            raise AdressageRefuse("Point ou adresse protocolaire réservé : identifiant ou registre attendu.")
        return cible
    raise AdressageRefuse("Niveau de réservation : voie, memoire ou protocole.")


# ---------------------------------------------------------------------------- calcul
def _trace(eq, niveau, cle):
    return (eq.traces or {}).get(f"{niveau}:{cle}", {}) if eq else {}


def calculer(session):
    """Plan complet, sans rien modifier. Déterministe."""
    o = session.ouvrage
    plat, remarque = materiel.plateforme(o.automate)
    controleur = o.automate or "non renseigné"
    plan = Plan()
    if remarque:
        plan.alertes.append(remarque)
    eqs = {e.ident: e for e in o.equipements}
    points = session.points()
    _physique(session, plan, plat, controleur, points, eqs)
    variables = session.variables()
    _automate(session, plan, plat, controleur, variables, eqs)
    _teletransmission(session, plan, plat, controleur, eqs)
    texte = "|".join(f"{a.niveau}:{a.ident_eq}:{a.cle}:{a.proposee}:{a.etat}" for a in plan.affectations)
    texte += "|" + "|".join(f"{n}:{m}" for n, m in plan.conflits)
    plan.empreinte = hashlib.sha256(texte.encode("utf-8")).hexdigest()[:16]
    return plan


def _physique(session, plan, plat, controleur, points, eqs):
    o = session.ouvrage
    cables = [p for p in points if p.raccordement != "Communication"]
    proposees = {}
    if plat == "S4W":
        motif_global = ("SOFREL S4W : la numérotation des voies dans S4W-Tools n'est pas encore connue d'OGIAS "
                        "(fichier de configuration S4W-Tools de référence attendu) ; aucune voie n'est proposée.")
    elif plat == "STB":
        motif_global = ("Îlot Advantys STB : les E/S sont lues par l'automate maître (scrutation Modbus TCP) ; la "
                        "correspondance des voies avec ses mots n'est pas établie dans OGIAS, aucune voie n'est "
                        "proposée.")
    elif not o.modules:
        motif_global = "Aucune carte d'E/S déclarée : calculez puis validez le matériel (étape Matériel)."
    else:
        motif_global = ""
        rang = {e.ident: i for i, e in enumerate(session.equipements_tries())}
        rapport: dict = {}
        groupes = session.groupes_secours_actifs()
        affectations, manquantes, depassements = implanter(points, o.modules, [u.code for u in o.unites], rang,
                                                           o.reserve_min, voies_reservees(o), groupes, rapport)
        motifs = rapport.get("motifs", {})
        for ident, k, deja in rapport.get("secours_non_separes", []):
            rep = o.repere(o.equipement(ident))
            autres = ", ".join(o.repere(o.equipement(i)) for i in deja)
            plan.alertes.append(f"Groupe de secours : {rep} proposé sur la carte {k}, déjà utilisée par {autres} "
                                "(aucune autre carte libre) ; ajoutez une carte pour les séparer.")
        for k, reps in secours_partageant_une_carte(points, o.modules, groupes):
            plan.alertes.append(f"Groupe de secours : la carte {k} porte déjà des E/S de {', '.join(reps)} "
                                "(placements existants, non déplacés).")
        for p, k, v in affectations:
            proposees[(p.ident_eq, p.cle)] = (k, v)
        for k in depassements:
            plan.alertes.append(f"Carte {k} : la réserve de voies minimale ({o.reserve_min:.0%}) est entamée.")
        if manquantes:
            _simuler_besoins(session, plan, manquantes)
    for niveau, rep, msg, ident in controler_cartes(points, o.modules, o.reserve_min) if plat not in ("S4W", "STB") else []:
        if niveau == "Erreur":
            plan.conflits.append(("physique", msg))
    for p in cables:
        eq = eqs.get(p.ident_eq)
        tr = _trace(eq, "physique", p.cle)
        a = Affectation("physique", p.ident_eq, p.repere, p.cle, p.nom, p.point, "", controleur, plat,
                        p.module, str(p.voie or ""), p.adresse, "", validee_le=tr.get("validee_le", ""),
                        validee_par=tr.get("validee_par", ""))
        k, v = place(p)
        if p.adresse or (k and v is not None):
            a.origine = tr.get("origine") or ("importée" if o.mode == "Existant" else "saisie")
            a.etat = "validée" if p.validee else "à valider"
            a.regle = tr.get("regle", "")
        elif (p.ident_eq, p.cle) in proposees:
            k, v = proposees[(p.ident_eq, p.cle)]
            a.module, a.voie = k, str(v)
            a.proposee = session.adresse_module(p.point, k, v)
            a.origine, a.etat = "proposée", "proposée"
            a.regle = motifs.get((p.ident_eq, p.cle)) or (
                f"Première voie {p.point} libre de la carte {k} (cartes par rack et position ; E/S de "
                f"{p.repere} groupées ; réserve de voies respectée si possible).")
        else:
            a.origine, a.etat = "", "non résolue"
            a.motif = motif_global or f"Plus de voie {p.point} libre sur les cartes déclarées (voir besoins)."
        plan.affectations.append(a)


def _simuler_besoins(session, plan, manquantes):
    """Cartes qu'il faudrait AJOUTER (simulation, rien n'est ajouté)."""
    try:
        cat = materiel.catalogue()
        profil = session.ouvrage.profil_cartes if session.ouvrage.profil_cartes in cat["profils"] else cat["profil_defaut"]
        for nature, n in sorted(manquantes.items()):
            ref = cat["profils"][profil][nature]
            voies = int(cat["_cartes"][ref]["voies"])
            utiles = max(1, math.floor(voies * (1 - session.ouvrage.reserve_min)))
            plan.besoins.append({"nature": nature, "manquantes": n, "reference": ref,
                                 "cartes": math.ceil(n / utiles)})
    except materiel.CatalogueMaterielErreur as exc:
        plan.alertes.append(str(exc))


def _automate(session, plan, plat, controleur, variables, eqs):
    o = session.ouvrage
    motif_global, proposees, erreurs = "", {}, []
    if plat == "S4W":
        motif_global = ("SOFREL S4W : pas de table %MW Schneider ; l'identification des informations dans S4W-Tools "
                        "n'est pas encore connue d'OGIAS.")
    elif o.mode == "Existant" and not o.disponibilite_verifiee:
        motif_global = ("Projet existant : disponibilité non vérifiée. Aucune adresse nouvelle n'est proposée tant que "
                        "l'import ne couvre pas toute la mémoire utilisée (à déclarer explicitement).")
    else:
        props, erreurs = plan_adresses(o, session.catalogue, reservations=plages_reservees(o))
        proposees = {(p.variable.ident_eq, p.variable.cle): p for p in props}
        for e in erreurs:
            plan.conflits.append(("automate", e))
        if o.mode == "Existant":
            occupees = {_mot(v.adresse)[0] for v in o.existantes if _mot(v.adresse)}
            for (ident, cle), p in list(proposees.items()):
                if _mot(p.adresse)[0] in occupees:
                    plan.conflits.append(("automate", f"{p.variable.nom} : {p.adresse} est déjà utilisé par une variable "
                                                      "historique importée."))
                    del proposees[(ident, cle)]
    for v in variables:
        eq = eqs.get(v.ident_eq)
        tr = _trace(eq, "automate", v.cle)
        a = Affectation("automate", v.ident_eq, v.repere, v.cle, v.nom, v.famille, v.type_logique, controleur, plat,
                        actuelle=v.adresse, validee_le=tr.get("validee_le", ""), validee_par=tr.get("validee_par", ""))
        if v.adresse:
            a.origine = tr.get("origine") or ("importée" if o.mode == "Existant" else "saisie")
            a.etat = "validée" if v.adresse_validee else "à valider"
            a.regle = tr.get("regle", "")
        elif (v.ident_eq, v.cle) in proposees:
            p = proposees[(v.ident_eq, v.cle)]
            a.proposee, a.origine, a.etat = p.adresse, "proposée", "proposée"
            a.regle = p.remarque or _regle_memoire(o, v)
        else:
            a.etat = "non résolue"
            a.motif = motif_global or next((e for e in erreurs if v.nom in e), "") or \
                "Aucune place libre dans la plage de la famille (voir conflits)."
        plan.affectations.append(a)


def _regle_memoire(o, v):
    from .modele import zone, TAILLE_MOTS
    debut, fin = zone(o, v.famille)
    taille = TAILLE_MOTS.get(v.type_logique, 1)
    forme = "un bit" if taille == 0 else "un mot" if taille == 1 else f"{taille} mots alignés sur une adresse paire"
    return f"Première place libre de la plage {v.famille} (%MW{debut} à %MW{fin}) ; {v.type_logique} sur {forme}."


def _teletransmission(session, plan, plat, controleur, eqs):
    o = session.ouvrage
    vues = {}
    reserves_points = {r.get("cible", "") for r in o.reservations if r.get("niveau") == "protocole"}
    source = {(a.ident_eq, a.cle): a for a in plan.affectations if a.niveau == "automate"}
    for (ident, cle), va in source.items():
        a = Affectation("teletransmission", ident, va.repere, cle, va.nom, va.nature, va.type_logique, controleur, plat,
                        origine="dérivée")
        if va.nom in vues:
            plan.conflits.append(("teletransmission", f"Point {va.nom} défini deux fois."))
        vues[va.nom] = a
        if va.nom in reserves_points:
            a.etat, a.motif = "en conflit", "identifiant de point réservé"
        elif plat == "S4W":
            a.etat, a.motif = "non résolue", "SOFREL S4W : identification des points S4W-Tools non connue d'OGIAS."
        elif not o.protocole_declare:
            a.etat = "non résolue"
            a.motif = ("Convention protocolaire non déclarée (registre = mot %MW + décalage) : à confirmer dans "
                       "les paramètres de communication de l'ouvrage.")
        elif not va.adresse:
            a.etat, a.motif = "non résolue", "variable source sans adresse"
        else:
            reg = registre_modbus(va.adresse, o.decalage_modbus)
            a.proposee = reg
            a.etat = "validée" if va.etat == "validée" else "proposée"
            a.regle = (f"Registre = mot de {va.adresse} + décalage {o.decalage_modbus} (convention déclarée) ; "
                       f"source {va.nom}.")
            if reg in reserves_points:
                a.etat, a.motif = "en conflit", f"registre {reg} réservé"
        plan.affectations.append(a)
    # paires TR / RTR : correspondance explicite
    for a in [x for x in plan.affectations if x.niveau == "teletransmission" and x.nature == "TR"]:
        rtr = next((x for x in plan.affectations if x.niveau == "teletransmission" and x.nature == "RTR"
                    and x.ident_eq == a.ident_eq and x.cle.split("_", 1)[1] == a.cle.split("_", 1)[1]), None)
        if rtr is None:
            plan.alertes.append(f"{a.nom} : téléréglage sans retour (RTR) correspondant.")
        else:
            a.regle = (a.regle + f" Retour : {rtr.nom}.").strip()


def adresse_topkapi(adresse_mw, decalage=0):
    """%MW400.10 → « 400$A » (format .$$t relevé) ; %MW2100 → « 2100 »."""
    p = _mot(adresse_mw)
    if not p:
        return ""
    return f"{p[0] + int(decalage)}" + (f"${p[1]:X}" if p[1] is not None else "")


# ---------------------------------------------------------------------------- application
def auteur():
    try:
        return os.environ.get("USERNAME") or getpass.getuser()
    except Exception:                                  # noqa: BLE001
        return ""


def appliquer(session, empreinte, niveaux=("physique", "automate")):
    """Applique le plan montré (même empreinte) ; tout ou rien. Renvoie {niveau: nombre}."""
    plan = calculer(session)
    if plan.empreinte != empreinte:
        raise AdressageRefuse("Le plan a changé depuis l'aperçu (données modifiées) : recalculez avant d'appliquer.")
    bloquants = [m for n, m in plan.conflits if n in niveaux]
    if bloquants:
        raise AdressageRefuse(f"{len(bloquants)} conflit(s) à résoudre avant toute application (ex. {bloquants[0]}).")
    o = session.ouvrage
    copie = copy.deepcopy(o)                       # la copie horodatée sur disque est faite par la session
    maintenant, qui = datetime.now().strftime("%Y-%m-%d %H:%M:%S"), auteur()
    compte = {n: 0 for n in niveaux}
    try:
        for a in plan.affectations:
            if a.etat != "proposée" or a.niveau not in niveaux:
                continue
            eq = o.equipement(a.ident_eq)
            if a.niveau == "physique":
                meta = dict(eq.es_meta.get(a.cle, {}))
                if meta.get("validee"):
                    raise AdressageRefuse(f"{a.nom} : E/S validée, elle ne peut pas être déplacée.")
                meta.update(module=a.module, voie=a.voie, validee=False)
                eq.es_meta[a.cle] = meta
                eq.adresses_es[a.cle] = a.proposee
            elif a.niveau == "automate":
                if a.cle in eq.validees or eq.adresses.get(a.cle):
                    raise AdressageRefuse(f"{a.nom} : une adresse existe déjà, elle n'est jamais écrasée.")
                eq.adresses[a.cle] = a.proposee
            else:
                continue
            eq.traces[f"{a.niveau}:{a.cle}"] = {"origine": "proposée", "regle": a.regle, "le": maintenant, "par": qui}
            compte[a.niveau] += 1
        o.journal_adressage.append({"le": maintenant, "par": qui, "empreinte": empreinte, **compte})
        apres = calculer(session)
        if apres.conflits:
            raise AdressageRefuse("Contrôle après application en échec : " + apres.conflits[0][1])
    except Exception:
        session.ouvrage = copie                        # rien de partiel
        raise
    if any(compte.values()):
        session._change(devalider=False)
    return compte


def tracer_validation(session, niveau, paires, valide=True):
    """Date et auteur de validation (ou retrait) des affectations, quand ils sont disponibles."""
    maintenant, qui = datetime.now().strftime("%Y-%m-%d %H:%M:%S"), auteur()
    for ident, cle in paires:
        eq = session.ouvrage.equipement(ident)
        if eq is None:
            continue
        t = dict(eq.traces.get(f"{niveau}:{cle}", {}))
        if valide:
            t.update(validee_le=maintenant, validee_par=qui)
        else:
            t.pop("validee_le", None); t.pop("validee_par", None)
        eq.traces[f"{niveau}:{cle}"] = t
