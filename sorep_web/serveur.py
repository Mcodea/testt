"""Serveur local de l'interface web OGIAS (bibliothèque standard uniquement).

Lancement : `py -m sorep_web` (ou OGIAS.bat). Le serveur écoute seulement sur 127.0.0.1 et ouvre le
navigateur. Il ne contient aucune règle métier : chaque requête appelle la Session du moteur `genvar`.
Un refus métier (RegleMetier, ValueError) revient en message clair ; toute autre erreur est écrite dans
journal.log et signalée à l'écran, jamais ignorée.
"""
import base64
import copy
import uuid
import json
from collections import Counter
from typing import Any
import mimetypes
import os
import socket
import tempfile
import shutil
import binascii
import threading
import traceback
import webbrowser
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from genvar import chemins, projets, VERSION
from genvar.catalogue import sens_variable
from genvar.modele import Equipement
from genvar.session import Session, RegleMetier
from genvar.inbound import InputKind, InboundError, preview_import, stage_import
from sorep_web import referentiel_ouvrage as ref_ident
from genvar import charte

STATIQUE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
VERROU = threading.Lock()


JOURNAL_TAILLE_MAX = 1_000_000          # octets : au-delà, journal.log devient journal.1.log (V1-7-06)
JOURNAL_ANCIENS = 2                     # journal.1.log et journal.2.log gardés


def _fichier_journal(n=0):
    return os.path.join(chemins.dossier_donnees(), "journal.log" if not n else f"journal.{n}.log")


def journal(texte, niveau="ERREUR"):
    """Journal technique tournant (dossier de données) : démarrages, ouvertures, exports, reprises de verrou et
    erreurs inattendues. Aucune donnée d'ouvrage n'y est écrite volontairement (ni repère, ni nom de fichier)."""
    try:
        f = _fichier_journal()
        os.makedirs(os.path.dirname(f), exist_ok=True)
        if os.path.exists(f) and os.path.getsize(f) > JOURNAL_TAILLE_MAX:
            for n in range(JOURNAL_ANCIENS, 0, -1):
                ancien = _fichier_journal(n - 1)
                if os.path.exists(ancien):
                    os.replace(ancien, _fichier_journal(n))
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} [{niveau}] {texte.rstrip()}\n")
    except OSError:
        pass


def evenement(texte):
    journal(texte, "INFO")


def lire_journal(n=300):
    """Dernières lignes du journal (le plus récent en dernier), anciens fichiers compris si besoin."""
    lignes = []
    for k in range(JOURNAL_ANCIENS, -1, -1):
        try:
            with open(_fichier_journal(k), encoding="utf-8", errors="replace") as fh:
                lignes += fh.read().splitlines()
        except OSError:
            continue
    return lignes[-n:]


def _charte_client(standard):
    """Charte d'un standard au sens de l'ouvrage : None pour la structure OGIAS (comportement d'avant)."""
    from genvar import charte
    c = ((standard or {}).get("briques") or {}).get("charte")
    return None if not c or "ouvrage" not in c or charte.est_ogias(c) else c


def _motifs_identification(c):
    """Motifs et consignes de saisie de l'identification selon une charte (None : charte OGIAS)."""
    from genvar import charte
    if c is not None and ("ouvrage" not in c or charte.est_ogias(c)):
        c = None
    return {champ: {"motif": charte.motif(c, champ), "consigne": charte.consigne(c, champ)}
            for champ in ("lieu", "code_ouvrage", "numero_ouvrage")} | {"longueur_numero": charte.longueur_numero(c)}


class Application:
    """État de l'interface : une Session, l'ouvrage ouvert, l'enregistrement automatique."""

    def __init__(self):
        import atexit
        from genvar import verrou
        self.jeton = verrou.nouveau_jeton()          # identité de cet OGIAS pour le verrou d'ouvrage (V1-7-04)
        self.chemin_verrouille = ""
        self.s = Session()
        self.s.garde_enregistrement = self._garde_verrou
        atexit.register(self._liberer_verrou)
        self.ouvert = False
        self.creation_en_attente = False  # session provisoire non enregistrée
        self._inbound_pending = None  # aperçu éphémère, lié à la session courante
        self.dernier_bilan_groupe = None  # génération groupée (lot 6) : produits / non produits, pour l'en-tête
        self.dernier_statut_format = ""   # formats appris (22/11) : statut du dernier export (qualifié ou non)
        self.historique: list[tuple[str, str]] = []   # annulation (V1-4-47) : (état avant, libellé), le plus récent à la fin
        self.refaire: list[tuple[str, str]] = []

    # ------------------------------------------------------------------ verrou d'ouvrage (V1-7-04)
    def _garde_verrou(self, chemin):
        """Avant toute écriture : le fichier doit être verrouillé par cet OGIAS. Un nouveau fichier est verrouillé,
        l'ancien libéré ; un verrou repris par un autre poste interdit l'écriture."""
        from genvar import verrou
        ch = os.path.abspath(chemin)
        if ch == self.chemin_verrouille:
            if not verrou.detient(ch, self.jeton):
                raise RegleMetier(f"Ouvrage repris par {verrou.description(verrou.lire(ch) or {})} : vos "
                                  "modifications ne sont pas enregistrées. Rouvrez l'ouvrage pour continuer.")
            return
        verrou.prendre(ch, self.jeton)
        self._liberer_verrou()
        self.chemin_verrouille = ch

    def _liberer_verrou(self):
        from genvar import verrou
        if self.chemin_verrouille:
            verrou.liberer(self.chemin_verrouille, self.jeton)
        self.chemin_verrouille = ""

    # ------------------------------------------------------------------ annulation Ctrl+Z (V1-4-47)
    HISTORIQUE_MAX = 30
    SANS_HISTORIQUE = {"nouveau", "ouvrir", "fermer", "annuler", "retablir", "supprimer_ouvrage"}
    LIBELLES_ANNULATION = {
        "ajouter_equipement": "ajout d'équipement", "ajouter_equipements_serie": "création en série d'équipements", "rapprochement_action": "rapprochement", "modifier_equipement": "modification d'équipement",
        "supprimer_equipements": "suppression d'équipements", "dupliquer_equipement": "duplication d'équipement", "definir_ordre_export": "ordre d'export", "deplacer": "déplacement d'équipements",
        "valider_equipements": "validation d'équipements", "decider_proposition": "décision sur une proposition",
        "configurer_equipement": "configuration d'équipement", "ligne_equipement": "modification d'équipement",
        "fiche_ouvrage": "fiche de l'ouvrage", "definir": "modification de l'ouvrage", "es_definir": "modification d'E/S",
        "es_valider": "validation d'E/S", "materiel_action": "matériel", "modules": "cartes d'E/S",
        "variables_action": "variables", "adressage_action": "adressage", "grille_appliquer": "grille d'ingénierie",
        "equipement_attribut": "attribut d'équipement", "revisions_action": "indice de l'ouvrage", "restaurer_copie": "restauration d'une copie",
    }

    def _annulable(self):
        return self.ouvert and not self.creation_en_attente and bool(self.s.chemin)

    def _etat_annulable(self):
        """État comparable de l'ouvrage, sans les indices livrés (jamais annulés) ni la date d'enregistrement."""
        d = self.s.ouvrage.vers_dict()
        d.pop("indices", None)
        d.pop("modifie_le", None)
        d["catalogue_snapshot"] = self.s.catalogue_fige()
        return json.dumps(d, ensure_ascii=False, sort_keys=True)

    def appeler(self, nom, donnees):
        """Exécute une commande de l'interface ; si elle a modifié l'ouvrage, l'état d'avant rejoint l'historique."""
        if nom in self.SANS_HISTORIQUE or not self._annulable():
            if nom in ("nouveau", "ouvrir", "fermer"):
                self.historique.clear()
                self.refaire.clear()
            return getattr(self, nom)(donnees)
        cle, avant = (self.s.chemin, self.s.ouvrage.ident_projet), self._etat_annulable()
        resultat = getattr(self, nom)(donnees)
        if self._annulable() and (self.s.chemin, self.s.ouvrage.ident_projet) == cle:
            if self._etat_annulable() != avant:
                self.historique.append((avant, self.LIBELLES_ANNULATION.get(nom, "modification")))
                del self.historique[:-self.HISTORIQUE_MAX]
                self.refaire.clear()
        return resultat

    def _restaurer_etat(self, etat):
        from genvar.catalogue import Catalogue
        from genvar.modele import Ouvrage
        d = json.loads(etat)
        o = Ouvrage.depuis_dict(d)
        o.indices = self.s.ouvrage.indices                 # un indice livré ne change plus, même par Ctrl+Z
        o.modifie_le = self.s.ouvrage.modifie_le
        precedent = (self.s.ouvrage, self.s.catalogue, self.s.modifie)
        self.s.ouvrage = o
        self.s.catalogue = Catalogue(**o.catalogue_snapshot) if o.catalogue_snapshot \
            else copy.deepcopy(self.s._catalogue_commun)
        self.s.modifie = True
        try:
            self._sauver()
        except Exception:                                  # tout ou rien : la mémoire reste égale au fichier
            self.s.ouvrage, self.s.catalogue, self.s.modifie = precedent
            raise
        self.s._oublier_adoption()

    def historique_web(self, _=None):
        return {"annuler": self.historique[-1][1] if self.historique else "",
                "retablir": self.refaire[-1][1] if self.refaire else "",
                "pas": len(self.historique), "max": self.HISTORIQUE_MAX}

    def annuler(self, _):
        if not self._annulable() or not self.historique:
            raise RegleMetier("Rien à annuler.")
        etat, libelle = self.historique.pop()
        courant = self._etat_annulable()
        try:
            self._restaurer_etat(etat)
        except Exception:
            self.historique.append((etat, libelle))
            raise
        self.refaire.append((courant, libelle))
        evenement("Annulation (Ctrl+Z).")
        return {"annule": libelle, **self.historique_web()}

    def retablir(self, _):
        if not self._annulable() or not self.refaire:
            raise RegleMetier("Rien à rétablir.")
        etat, libelle = self.refaire.pop()
        courant = self._etat_annulable()
        try:
            self._restaurer_etat(etat)
        except Exception:
            self.refaire.append((etat, libelle))
            raise
        self.historique.append((courant, libelle))
        return {"retabli": libelle, **self.historique_web()}

    # ------------------------------------------------------------------ outils
    def _sauver(self):
        """Enregistrement automatique après chaque modification (sauvegarde .bak conservée)."""
        if not self.ouvert or self.creation_en_attente:
            return
        o = self.s.ouvrage
        if not self.s.chemin and not (o.lieu and o.code_ouvrage):
            return          # le nom du fichier sera le repère de l'ouvrage : attendre lieu + code
        if not self.s.chemin:
            dossier = projets.repertoire()
            dossier.mkdir(parents=True, exist_ok=True)
            self.s.chemin = str(projets.nom_libre(self.s.nom_fichier_propose() or "ouvrage", dossier))
        self.s.enregistrer(self.s.chemin)

    def _eq(self, ident):
        eq = self.s.ouvrage.equipement(ident)
        if eq is None:
            raise RegleMetier("Équipement introuvable.")
        return eq

    def _fichier_temporaire(self, d):
        nom = os.path.basename(d.get("nom") or "fichier")
        ext = os.path.splitext(nom)[1].lower()
        if ext not in (".xlsx", ".xlsm", ".ods", ".csv", ".txt"):
            raise RegleMetier("Format accepté : .xlsx, .xlsm, .ods ou .csv.")
        dossier = tempfile.mkdtemp(prefix="sorep_")
        chemin = os.path.join(dossier, "import" + ext)
        with open(chemin, "wb") as f:
            f.write(base64.b64decode(d["contenu"]))
        return chemin

    def _fiche_eq(self, e, nb_es_par_eq=None):
        o = self.s.ouvrage
        # Audit du 16/11 : le décompte se faisait en régénérant toutes les E/S pour chaque équipement (coût
        # quadratique : 20 s pour 300 équipements). L'appelant qui liste l'ouvrage fournit le décompte unique.
        if nb_es_par_eq is None:
            nb_es_par_eq = Counter(p.ident_eq for p in self.s.points())
        infos = self.s.informations(e)
        return {"ident": e.ident, "pcf": o.repere(e), "se": e.sous_ensemble, "type": e.type, "numero": e.numero,
                "designation": self.s.designation_type(e.type), "domaine": self.s.domaine_type(e.type),
                "libelle": e.libelle, "uf": e.uf, "modele": e.modele, "local": e.local,
                "nb_infos": len(infos), "valide": e.valide, "nb_es": nb_es_par_eq.get(e.ident, 0),
                "etat": "codé" if (e.type in self.s.modeles["types"] or self.s.catalogue.type(e.type)) else "à coder"}

    # ------------------------------------------------------------------ lectures
    def session_locale(self, _):
        """Nom de session Windows uniquement ; jamais d'identifiant inventé."""
        import getpass
        return {"utilisateur": getpass.getuser() if os.name == "nt" else ""}

    def accueil(self, _):
        return {"version": VERSION, "ouvrages": [f.__dict__ for f in projets.lister() if not f.archive],
                "corbeille": len(projets.lister_corbeille()), "ouvert": self.ouvert,
                "dossier": str(projets.repertoire())}

    def _avancement(self):
        """Résumé des étapes pour la barre d'étapes (jamais bloquant : un échec renvoie un résumé vide)."""
        try:
            o = self.s.ouvrage
            b = self.s.bilan_es() if o.equipements else {}
            return {"es": b.get("total", 0), "contenu_non_valide": b.get("contenu_non_valide", 0),
                    "voies_non_validees": b.get("voies_non_validees", 0), "sans_adresse": b.get("sans_adresse", 0),
                    "cartes": len(o.modules), "materiel_valide": o.materiel_valide}
        except Exception:                                   # noqa: BLE001 — l'affichage ne doit jamais planter
            journal(traceback.format_exc())
            return {}

    def _etats_equipements(self, anomalies=None):
        """État de paramétrage de chaque équipement : validé, configuré (prêt à valider), incomplet
        (paramètre ou décision manquant) ou en erreur (anomalie de recette). Jamais bloquant."""
        try:
            erreurs: dict[str, list[str]] = {}
            for a in (anomalies if anomalies is not None else self.s.anomalies()):
                if (a.niveau == "Erreur" and a.ident_eq and a.etape == "Équipements"
                        and "non décidée" not in a.message):
                    erreurs.setdefault(a.ident_eq, []).append(a.message)
            points = self.s.points()
            sortie = {}
            for e in self.s.ouvrage.equipements:
                manques = self.s.manques_parametrage(e, points)
                attente = len(self.s.propositions_en_attente(e))
                if e.ident in erreurs:
                    etat, detail = "erreur", erreurs[e.ident][0]
                elif e.valide:
                    etat, detail = "validé", ""
                elif manques:
                    etat, detail = "incomplet", manques[0]
                else:
                    etat, detail = "configuré", "Prêt à valider."
                sortie[e.ident] = {"etat_param": etat, "detail_etat": detail, "a_decider": attente,
                                   "nb_erreurs": len(erreurs.get(e.ident, []))}
            return sortie
        except Exception:                                   # noqa: BLE001
            journal(traceback.format_exc())
            return {}

    def ouvrage(self, _):
        if not self.ouvert:
            return {"ouvert": False}
        o = self.s.ouvrage
        etats = self._etats_equipements()
        nb_es = Counter(p.ident_eq for p in self.s.points())
        eqs = [dict(self._fiche_eq(e, nb_es), **etats.get(e.ident, {})) for e in self.s.equipements_tries()]
        return {"ouvert": True, "chemin": self.s.chemin or "",
                "creation_en_attente": self.creation_en_attente,
                "en_conception": self.creation_en_attente or o.statut == "Brouillon",
                "identification": {k: getattr(o, k) for k in ("mode", "lieu", "code_ouvrage", "numero_ouvrage", "libelle", "automate",
                                                               "type_ouvrage", "localisation", "communication",
                                                               "revision", "statut")},
                "prefixe": o.prefixe(),
                "format_repere": o.format_repere,
                # 19/11 : charte de nommage de l'ouvrage (None : charte OGIAS) et motifs de saisie qui en découlent
                "charte_client": o.charte_client(), "charte_motifs": _motifs_identification(o.charte_client()),
                "avancement": self._avancement(),
                "referentiel": {"version_ouvrage": self.s.catalogue.version, "version_outil": self.s._catalogue_commun.version,
                                "ecarts": self.s.ecarts_referentiel(), "adoption": self._apercu_adoption_interface(),
                                "empreinte_adoption": self._empreinte_adoption(),
                                "adoption_annulable": bool(self.s._avant_adoption),
                                "sauvegarde_adoption": os.path.basename(self.s.sauvegarde_adoption),
                                "sauvegarde_annulation_adoption": os.path.basename(self.s.sauvegarde_annulation_adoption)},
                "unites": [{"code": u.code, "libelle": u.libelle, "se": u.sous_ensemble} for u in o.unites],
                "sous_ensembles": [{"code": x.code, "libelle": x.libelle} for x in o.sous_ensembles],
                "libelle_communs": self.s.libelle_communs(), "equipements": eqs,
                "types": self.s.types_disponibles()}

    def parcours_web(self, _):
        """Parcours guidé : pour chaque étape, points bloquants et points à vérifier, avec leur cible."""
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        return {"etapes": self.s.parcours()}

    def listes_ouvrage(self, _):
        """Référentiel métier des listes de la fiche ouvrage, sans données projet."""
        return ref_ident.lire()

    def lieu_proposition(self, q):
        """Code lieu proposé par la charte pour un nom de commune, avec contrôle des doublons."""
        from genvar import codification
        nom = str(q.get("nom", "")).strip()
        ancien = str(q.get("ancien", "")).strip().upper()
        pris = {str(x.get("code", "")).upper() for x in ref_ident.lire()["lieux"] if isinstance(x, dict)}
        pris |= ref_ident.codes_utilises() or set()
        pris.discard(ancien)
        return codification.proposition(nom, pris) if nom else {"code": "", "origine": "", "conflit": False,
                                                                 "variantes": [], "message": ""}

    def listes_ouvrage_action(self, d):
        return ref_ident.modifier(d.get("action"), d.get("groupe"),
                                  d.get("code", ""), d.get("libelle", ""), d.get("ancien", ""), d.get("regie", ""))

    def identifier_type(self, d):
        """Mettre à jour le code et le libellé d'ouvrage ensemble, sans ambiguïté."""
        code = str(d.get("code", "")).strip().upper()
        if code:
            entry = ref_ident.type_par_code(code)
            if entry is None:
                raise RegleMetier("Type d'ouvrage absent du référentiel.")
        else:
            entry = {"code": "", "libelle": ""}
        ancien = self.s.ouvrage.code_ouvrage
        if ancien != code and self.s.ouvrage.equipements and not d.get("confirmer_changement"):
            raise RegleMetier("Ce changement modifiera les repères des équipements : confirmation requise.")
        self.s.definir("type_ouvrage", entry["libelle"])
        self.s.definir("code_ouvrage", code)
        self._sauver()
        return {"code": code, "type_ouvrage": entry["libelle"]}

    def identifier_selection(self, d):
        """Nouvelles listes : valeurs vérifiées côté serveur, sans ressaisie libre."""
        champ = d.get("champ")
        listes = ref_ident.lire()
        if champ == "lieu":
            valeur = str(d.get("valeur", "")).strip().upper()
            autorises = {x["code"] for x in listes["lieux"]}
            if valeur and valeur not in autorises:
                raise RegleMetier("Ce lieu n'est pas déclaré dans le référentiel.")
            if self.s.ouvrage.equipements and valeur != self.s.ouvrage.lieu and not d.get("confirmer_changement"):
                raise RegleMetier("Le changement du lieu modifie les repères : confirmation requise.")
        elif champ == "automate":
            valeur = str(d.get("valeur", "")).strip()
            if valeur and valeur not in listes["automates"]:
                raise RegleMetier("Automate absent du référentiel.")
        elif champ == "communication":
            choix = d.get("valeurs", [])
            if not isinstance(choix, list) or not all(isinstance(x, str) for x in choix):
                raise RegleMetier("Liste de communications invalide.")
            if any(x not in listes["protocoles"] for x in choix):
                raise RegleMetier("Un protocole n'est pas présent dans le référentiel.")
            valeur = ", ".join(dict.fromkeys(choix))
        else:
            raise RegleMetier("Ce champ n'est pas géré par une liste.")
        c = self._charte_cible()
        if champ == "numero_ouvrage" and valeur and not charte.conforme(charte.motif(c, "numero_ouvrage"), valeur):
            raise RegleMetier(f"Numéro d’ouvrage invalide : {charte.consigne(c, 'numero_ouvrage')}.")
        self.s.definir(champ, valeur)
        self._sauver()
        return {"champ": champ, "valeur": valeur}

    def equipement(self, q):
        e = self._eq(q["ident"])
        fiche = self._fiche_eq(e)
        from genvar import modeles
        fiche["informations"] = self.s.informations(e)
        fiche["fonctionnelles"] = self.s.informations_fonctionnelles(e)
        anomalies = self.s.anomalies()
        fiche.update(self._etats_equipements(anomalies).get(e.ident, {}))
        propres = [a for a in anomalies if a.ident_eq == e.ident and a.etape == "Équipements"]
        fiche["erreurs"] = [a.message for a in propres if a.niveau == "Erreur" and "non décidée" not in a.message]
        fiche["alertes"] = [a.message for a in propres if a.niveau == "Alerte"]
        fiche["a_decider"] = sum(1 for x in fiche["fonctionnelles"] if x["etat"] == "proposée")
        from genvar import attributs as at        # attributs de l'atelier applicables (lot 4) et leurs valeurs
        try:
            applicables = at.applicables(e.type)
        except ValueError:
            applicables = []
        codes = {a["code"] for a in applicables}
        fiche["attributs"] = [{**a, "valeur": (e.attributs or {}).get(a["code"], "")} for a in applicables] + [
            {"code": k, "nom": k, "type": "texte", "valeur": v, "archive": True} for k, v in (e.attributs or {}).items()
            if k not in codes]
        fiche["options_es"] = [{"nom": o, "active": o in e.options}
                                for o in self.s.options_equipement(e)]
        presents = {(p.ident_eq, p.cle): p for p in self.s.points()}
        fiche["signaux_es"] = [{"cle": "ES_" + signal["code"], "information": signal["information"],
                                "point": signal["es"], "presence": signal["presence"],
                                "option": signal.get("option", ""),
                                "retenu": (e.ident, "ES_" + signal["code"]) in presents,
                                "disponible": signal.get("presence") != "Option" or signal.get("option") in e.options,
                                "analogique": e.es_meta.get("ES_" + signal["code"], {}).get("analogique"),
                                "impulsion": e.es_meta.get("ES_" + signal["code"], {}).get("impulsion")}
                               for signal in self.s.catalogue_equipement(e).signaux_du_type(e.type)
                               if signal["famille"] == "ES"]
        fiche["es_personnalisees"] = [{"cle": p.cle, "nom": p.nom, "point": p.point,
                                         "analogique": e.es_meta.get(p.cle, {}).get("analogique"),
                                         "impulsion": e.es_meta.get(p.cle, {}).get("impulsion")}
                                        for p in self.s.points() if p.ident_eq == e.ident and
                                        p.cle.startswith('ES_') and
                                        p.cle not in {s['cle'] for s in fiche['signaux_es']}]
        # E/S câblées portées directement par une information (TS_FER d'un disjoncteur : contact câblé)
        fiche["es_portees"] = [{"cle": p.cle, "nom": p.nom, "point": p.point, "information": p.information,
                                "analogique": e.es_meta.get(p.cle, {}).get("analogique")}
                               for p in self.s.points() if p.ident_eq == e.ident and not p.cle.startswith("ES_")
                               and p.cle not in {x["cle"] for x in fiche["es_personnalisees"]}]
        modele_ref = self.s.modeles.get("modeles", {}).get(e.modele) if e.modele else None
        fiche["statut_modele"] = (modele_ref.get("statut", "à valider") if modele_ref else
                                  ("absent" if e.modele else "non sélectionné"))
        fiche["alerte_modele"] = ("Le modèle de référence n'est pas validé : vérifiez ses informations et ses E/S."
                                  if modele_ref and modele_ref.get("statut") != "validé" else
                                  "Modèle absent du référentiel : vérifiez les informations conservées."
                                  if e.modele and not modele_ref else "")
        fiche["roles"], fiche["formats"] = list(modeles.ROLES), list(modeles.FORMATS)
        fiche["adapte"] = bool(e.lignes_ajoutees or e.lignes_retirees or e.lignes_modifiees)
        ref = self.s.modeles["modeles"].get(e.modele)
        fige = self.s.ouvrage.modeles_snapshot.get(e.modele)
        fiche["modele_a_jour"] = not (ref and fige and (ref.get("lignes") != fige.get("lignes") or ref.get("signaux") != fige.get("signaux")))
        return fiche

    def referentiel(self, _):
        from genvar import modeles
        ref = self.s.modeles
        types = []
        for code, t in sorted(ref["types"].items()):
            types.append({"code": code, "motif": modeles.motif(code), "designation": t.get("designation", ""),
                          "domaine": t.get("domaine", ""),
                          "modeles": [{"nom": n, "nb": len(ref["modeles"].get(n, {}).get("signaux", [])),
                                       "statut": ref["modeles"].get(n, {}).get("statut", "à valider")} for n in t["modeles"]]})
        from genvar import audit_referentiel
        audit = [c.dict() for c in audit_referentiel.auditer(self.s._catalogue_commun)]
        return {"origine": ref.get("origine", ""), "version": ref.get("version", ""), "types": types, "audit": audit,
                "version_catalogue": self.s._catalogue_commun.version,
                "domaines": list(modeles.DOMAINES), "roles": list(modeles.ROLES), "formats": list(modeles.FORMATS),
                "types_catalogue": [{"code": t["code"], "designation": t["designation"]} for t in self.s.types_disponibles()
                                    if t["code"] not in ref["types"]]}

    def modele(self, q):
        m = self.s.modeles["modeles"].get(q["nom"])
        if m is None:
            raise RegleMetier("Modèle introuvable.")
        # Les E/S physiques sont définies par le catalogue du type, associé à ce modèle.
        # Ne pas confondre ces propositions avec les lignes de supervision propres au modèle.
        es_type = [{"code": sg["code"], "point": sg.get("es", ""),
                    "information": sg.get("information", ""), "presence": sg.get("presence", ""),
                    "option": sg.get("option", ""), "type_logique": sg.get("type_logique", "")}
                   for sg in self.s.catalogue.signaux_du_type(m["type"])
                   if sg.get("famille") == "ES"]
        signaux = m.get("signaux", [])
        es_type = [{"code": sg["code"], "point": sg.get("es", ""),
                    "information": sg.get("information", ""), "presence": sg.get("presence", ""),
                    "option": sg.get("option", ""), "type_logique": sg.get("type_logique", "")}
                   for sg in signaux if sg.get("famille") == "ES"]
        return {"nom": m["nom"], "type": m["type"], "lignes": m["lignes"],
                "signaux": signaux, "es_type": es_type,
                "statut": m.get("statut", "à valider"), "origine_signaux": m.get("origine_signaux", "")}

    def referentiel_action(self, d):
        """Éditeur des types de modèles, modèles, lignes et signaux de modèle : il travaille TOUJOURS sur une copie
        du brouillon, rangée ensuite dans le brouillon ; la révision publiée n'est jamais écrite ici."""
        depot = self._depot()
        b = depot.brouillon()
        if b is None:
            raise RegleMetier("Référentiel en lecture seule : créez d'abord un brouillon.")
        with self.s.edition_brouillon(b["donnees"]) as ed:
            r = self._referentiel_action(d)
        depot.remplacer_donnees(ed.donnees, f"éditeur des modèles : {d.get('action', '')} {d.get('nom') or d.get('code') or ''}".strip())
        return r

    def _referentiel_action(self, d):
        a, s = d.get("action"), self.s
        if a == "creer_type":
            return {"code": s.creer_type(d["code"], d.get("designation", ""), d.get("domaine", ""))}
        if a == "modifier_type":
            s.modifier_type(d["code"], d.get("designation", ""), d.get("domaine", ""))
        elif a == "supprimer_type":
            s.supprimer_type(d["code"])
        elif a == "creer_modele":
            return {"nom": s.creer_modele(d["type"], d["nom"], bool(d.get("depuis_catalogue")))}
        elif a == "valider_modele":
            s.valider_modele(d["nom"], bool(d.get("valide", True)))
        elif a == "supprimer_modele":
            s.supprimer_modele(d["nom"])
        elif a == "dupliquer_modele":
            return {"nom": s.dupliquer_modele(d["nom"], d.get("nouveau_nom", ""))}
        elif a == "archiver_modele":
            s.archiver_modele(d["nom"], bool(d.get("archive", True)))
        elif a == "archiver_type":
            s.archiver_type(d["code"], bool(d.get("archive", True)))
        elif a == "ajouter_ligne":
            s.ajouter_ligne_modele(d["nom"], d["champs"])
        elif a == "modifier_ligne":
            s.modifier_ligne_modele(d["nom"], d["id"], d["champs"])
        elif a == "supprimer_lignes":
            s.supprimer_lignes_modele(d["nom"], d.get("ids", []))
        elif a == "ajouter_signal":
            s.ajouter_signal_modele(d["nom"], d["champs"])
        elif a == "modifier_signal":
            s.modifier_signal_modele(d["nom"], d["famille"], d["code"], d["champs"])
        elif a == "supprimer_signal":
            s.supprimer_signal_modele(d["nom"], d["famille"], d["code"])
        else:
            raise RegleMetier("Action inconnue.")
        return {}

    def ligne_equipement(self, d):
        a, i = d.get("action"), d["ident_eq"]
        if a == "ajouter":
            self.s.ajouter_ligne_eq(i, d["champs"])
        elif a == "modifier":
            self.s.modifier_ligne_eq(i, d["id"], d["champs"])
        elif a == "supprimer":
            self.s.supprimer_lignes_eq(i, d.get("ids", []))
        elif a == "retablir":
            self.s.retablir_lignes_eq(i)
        elif a == "actualiser":
            self.s.actualiser_modele_eq(i)
        else:
            raise RegleMetier("Action inconnue.")
        self._sauver()
        return {}

    # ------------------------------------------------------------------ étape 2 : liste des E/S
    def es(self, _):
        from genvar.cartes_es import CARTES
        if self.s.ouvrage.mode == 'Neuf' and not self.s.ouvrage.equipements:
            raise RegleMetier('Ajoutez et validez au moins un équipement avant la liste des E/S.')
        if self.s.ouvrage.mode == 'Neuf' and self.s.ouvrage.equipements:
            non_valides = [self.s.ouvrage.repere(e) for e in self.s.ouvrage.equipements if not e.valide]
            if non_valides:
                raise RegleMetier(f"Validez d'abord le paramétrage des {len(non_valides)} équipement(s) "
                                  f"avant la liste des E/S (ex. {non_valides[0]}).")
        pts = self.s.liste_es()
        o = self.s.ouvrage
        rang = {e.ident: i for i, e in enumerate(self.s.equipements_tries())}
        pts.sort(key=lambda p: (rang.get(p.ident_eq, 0), ("ET", "ST", "EA", "SA").index(p.point), p.nom))
        return {"points": [{"ident_eq": p.ident_eq, "cle": p.cle, "pcf": p.repere, "point": p.point, "nom": p.nom,
                            "information": p.information, "designation": p.designation, "commentaire": p.commentaire,
                            "sens": p.sens, "note": p.note, "module": p.module, "voie": p.voie, "adresse": p.adresse,
                            "raccordement": p.raccordement, "validee": p.validee, "contenu_valide": p.contenu_valide,
                            "uf": p.uf,
                            "analogique": o.equipement(p.ident_eq).es_meta.get(p.cle, {}).get('analogique'),
                            "impulsion": o.equipement(p.ident_eq).es_meta.get(p.cle, {}).get('impulsion')} for p in pts],
                "bilan": self.s.bilan_es(), "modules": self.s.bilan_modules(), "racks": o.racks,
                "materiel_valide": o.materiel_valide,
                "reserve_min": o.reserve_min, "cartes": self._cartes_catalogue(CARTES, o.automate),
                "sans_es": [o.repere(e) for e in self.s.equipements_tries() if not any(p.ident_eq == e.ident for p in pts)]}

    def configurer_equipement(self, d):
        a, ident = d.get('action'), d.get('ident_eq')
        if a == 'option':
            self.s.choisir_option_es(ident, d.get('option', ''), bool(d.get('active')))
        elif a == 'selection_es':
            self.s.choisir_es_catalogue(ident, d.get('cle', ''), bool(d.get('retenu')))
        elif a == 'ajouter_es':
            cle = self.s.ajouter_es(ident, d.get('point'), d.get('code'), d.get('designation'), d.get('type_logique'))
            self._sauver()
            return {'cle': cle}
        elif a == 'retirer_es':
            self.s.retirer_es(ident, d.get('cle', ''))
        elif a == 'analogique':
            self.s.definir_analogique(ident, d.get('cle', ''), d.get('params', {}))
        elif a == 'impulsion':
            self.s.definir_impulsion(ident, d.get('cle', ''), d.get('params', {}))
        else:
            raise RegleMetier('Action de configuration inconnue.')
        self._sauver()
        return {}

    def es_definir(self, d):
        """Édite le contenu d'une E/S sans affecter de voie depuis l'étape 2.

        Pour les demandes composites du panneau V0.29, aucune modification en mémoire
        ni sur disque n'est conservée si une validation métier échoue.
        Les anciennes demandes simples continuent à utiliser cette même API.
        """
        champs = {k: d[k] for k in ("designation", "sens", "note", "module", "voie", "validee", "raccordement") if k in d}
        compose = 'analogique' in d or 'valider_contenu' in d
        sauvegarde = copy.deepcopy(self.s.ouvrage) if compose else None
        modifie_avant = self.s.modifie
        try:
            if 'analogique' in d:
                self.s.definir_analogique(d['ident_eq'], d['cle'], d['analogique'], devalider_equipement=False)
            self.s.definir_es(d['ident_eq'], d['cle'], **champs)
            if 'valider_contenu' in d:
                self.s.valider_contenu_es([(d['ident_eq'], d['cle'])], bool(d['valider_contenu']))
        except (RegleMetier, TypeError, ValueError):
            if sauvegarde is not None:
                self.s.ouvrage = sauvegarde
                self.s.modifie = modifie_avant
            raise
        self._sauver()
        return {}

    def es_valider(self, d):
        paires = [(x["ident_eq"], x["cle"]) for x in d.get("paires", []) if isinstance(x, dict)]
        if d.get("niveau") == "contenu":              # étape 2 : contenu de l'E/S
            n = self.s.valider_contenu_es(paires, bool(d.get("valide", True)))
        else:                                          # étape 3 : E/S validée sur sa voie
            n = self.s.valider_es(paires, bool(d.get("valide", True)))
        self._sauver()
        return {"n": n}

    @staticmethod
    def _cartes_catalogue(anciennes, automate=""):
        from genvar import materiel as mat
        try:
            return [{"reference": c["reference"], "nature": c["nature"], "voies": c["voies"]}
                    for c in mat.catalogue_pour(automate)["cartes"]]
        except mat.CatalogueMaterielErreur:
            return [{"reference": r, "nature": n, "voies": v} for r, n, v in anciennes]

    def materiel(self, _):
        """Étape Matériel : plateforme, profils, proposition calculée (si possible) et matériel retenu."""
        from genvar import materiel as mat
        o = self.s.ouvrage
        try:
            cat = mat.catalogue_pour(o.automate)          # gamme déclarée par l'atelier, sinon catalogue livré
        except mat.CatalogueMaterielErreur as exc:
            raise RegleMetier(str(exc)) from exc
        try:
            plat, remarque = mat.plateforme_materiel(o.automate)
        except mat.CatalogueMaterielErreur as exc:      # gamme non décrite : rien d'une autre gamme n'est affiché
            plat, remarque = "Non décrite", str(exc)
        if plat == "STB":                                # modules et profils de la gamme STB seulement
            try:
                cat = mat.catalogue_stb()
            except mat.CatalogueMaterielErreur as exc:
                raise RegleMetier(str(exc)) from exc
        try:
            prop, blocage = self.s.proposer_materiel().dict(), ""
        except RegleMetier as exc:
            prop, blocage = None, str(exc)
        aff, manq, dep = self.s.apercu_implantation() if o.modules else ([], {}, [])
        refs = " ".join(str(r.get("reference", "")) for r in o.racks)
        famille = "S4W" if "S4W" in refs else "M580" if "BME" in refs else "M340" if "BMX" in refs else ""
        if famille and famille != plat:
            remarque = (remarque + " " if remarque else "") + (
                f"Le matériel retenu a été calculé pour un {famille} ; la fiche ouvrage indique maintenant {plat}.")
        return {"plateforme": plat, "remarque_plateforme": remarque, "automate": o.automate,
                "profil": o.profil_cartes or cat["profil_defaut"], "statut_catalogue": cat["statut"],
                "profils": [{"code": k, "libelle": v["libelle"]} for k, v in cat["profils"].items()],
                "cartes_catalogue": [{"reference": c["reference"], "nature": c["nature"], "voies": c["voies"],
                                      "description": c.get("description", ""), "signal": c.get("signal", ""),
                                      "raccordement": c.get("raccordement", ""), "source": c.get("source", "")}
                                     for c in cat["cartes"]],
                "proposition": prop, "blocage": blocage, "racks": o.racks, "materiel_valide": o.materiel_valide,
                "a_placer": len(aff), "manquantes": manq, "reserve_min": o.reserve_min,
                "repartition": self.s.regles_repartition(),
                "config": o.materiel_config or {}, "nomenclature": self.s.nomenclature_materiel(),
                "alimentations": cat.get("alimentations", []), "processeurs": cat.get("processeurs", {}).get(plat, []),
                "communications": cat.get("communication", {}).get(plat, []),
                "cartes_speciales": cat.get("cartes_speciales", []), "remarque_speciales": cat.get("remarque_speciales", "")}

    def materiel_action(self, d):
        a = d.get("action")
        if a == "appliquer":
            self.s.appliquer_materiel(d.get("profil"))
        elif a == "profil":
            from genvar import materiel as mat
            if d.get("profil") not in mat.catalogue_pour(self.s.ouvrage.automate)["profils"]:
                raise RegleMetier("Profil de cartes inconnu.")
            self.s.ouvrage.profil_cartes = d["profil"]
            self.s.ouvrage.materiel_valide = False
            self.s._change(devalider=False)
        elif a == "valider":
            self.s.valider_materiel(bool(d.get("valide", True)))
        elif a == "confirmer_groupe_secours":
            self.s.confirmer_groupe_secours(d.get("membres") or [])
        elif a == "retirer_groupe_secours":
            self.s.retirer_groupe_secours(d.get("membres") or [])
        elif a == "refuser_groupe_secours":
            self.s.refuser_groupe_secours(d.get("membres") or [])
        elif a == "installer_communication":
            self.s.installer_communication(d.get("rack"), d.get("position"), str(d.get("reference", "")))
        elif a == "retirer_communication":
            self.s.retirer_communication(d.get("rack"), d.get("position"))
        elif a == "config":
            self.s.definir_config_materiel(d.get("alimentation"), d.get("processeur"), d.get("communication"),
                                           d.get("cartes"))
        elif a == "regles_repartition":
            self.s.regles_repartition(d.get("separation_secours"), d.get("emplacements_libres_rack"))
        else:
            raise RegleMetier("Action inconnue.")
        self._sauver()
        return {}

    def modules_action(self, d):
        a = d.get("action")
        if a == "ajouter":
            self.s.ajouter_module(d["rack"], d["position"], d["nature"], d["voies"], d.get("reference", ""))
        elif a == "modifier":
            self.s.modifier_module(d["cle"], d["rack"], d["position"], d["nature"], d["voies"], d.get("reference", ""))
        elif a == "supprimer":
            self.s.supprimer_module(d["cle"])
        elif a == "reserve":
            self.s.definir_reserve(float(d["taux"]))
        elif a == "apercu":
            aff, manq, dep = self.s.apercu_implantation()
            return {"affectees": len(aff), "manquantes": manq, "depassements": dep}
        elif a == "implanter":
            n, manq, dep = self.s.implanter_es()
            self._sauver()
            return {"affectees": n, "manquantes": manq, "depassements": dep}
        elif a == "liberer":
            n = self.s.liberer_voies_proposees()
            self._sauver()
            return {"liberees": n}
        else:
            raise RegleMetier("Action inconnue.")
        self._sauver()
        return {}

    def exporter(self, q):
        """(nom de fichier, octets) d'un export Excel."""
        quoi = q.get("quoi")
        evenement(f"Export demandé : {str(quoi)[:40]}.")
        if quoi in ("sauvegarde_adoption", "sauvegarde_annulation_adoption"):
            fichier = getattr(self.s, quoi)
            if not fichier or not os.path.isfile(fichier):
                raise RegleMetier("Sauvegarde introuvable pour cet ouvrage dans cette session.")
            # Le chemin provient seulement de l'adoption courante, jamais d'un paramètre HTTP.
            with open(fichier, "rb") as f:
                return "OGIAS_" + quoi + ".json", f.read()
        if quoi == "modifications" and (q.get("depuis") or q.get("vers")):   # indices choisis (22/11)
            if not self.ouvert or self.creation_en_attente:
                raise RegleMetier("Ouvrez d'abord un ouvrage.")
            dossier_m = tempfile.mkdtemp(prefix="sorep_modifs_")
            c = self.s.comparer_indices(str(q.get("depuis") or ""), str(q.get("vers") or ""))
            nom = f"{self.s.nom_fichier_propose() or 'ouvrage'}_modifications_{c['depuis']}_{c['vers'].split()[0]}.xlsx"
            self.s.exporter_modifications(os.path.join(dossier_m, nom), str(q.get("depuis") or ""), str(q.get("vers") or ""))
            with open(os.path.join(dossier_m, nom), "rb") as f:
                return nom, f.read()
        if quoi == "format_appris":               # formats appris (22/11) : export dans le format d'un constructeur
            if not self.ouvert or self.creation_en_attente:
                raise RegleMetier("Ouvrez d'abord un ouvrage.")
            return self._exporter_ouvrage("format_appris:" + str(q.get("ident") or ""), None, None)
        if quoi == "modele_livrable":             # lot 1 (19/11) : modèle à variables rempli pour l'ouvrage ouvert
            if not self.ouvert or self.creation_en_attente:
                raise RegleMetier("Ouvrez d'abord un ouvrage.")
            from genvar import modeles_livrables as ml
            try:
                return ml.generer(str(q.get("ident") or ""), self.s)
            except ml.ModeleRefuse as exc:
                raise RegleMetier(str(exc)) from None
        dossier = tempfile.mkdtemp(prefix="sorep_export_")
        if quoi == "referentiel":                 # indépendant de l'ouvrage ouvert
            from datetime import datetime
            source = q.get("source") or "publie"
            nom = f"OGIAS_referentiel_{source}_{datetime.now():%Y%m%d_%H%M}.xlsx"
            self.s.exporter_referentiel(os.path.join(dossier, nom), source)
            with open(os.path.join(dossier, nom), "rb") as f:
                return nom, f.read()
        base = self.s.nom_fichier_propose() or "ouvrage"
        if quoi == "dossier_recette":
            nom = f"{base}_dossier_recette.zip"
            self.s.dossier_recette(os.path.join(dossier, nom))
            self._sauver()
            with open(os.path.join(dossier, nom), "rb") as f:
                return nom, f.read()
        if quoi == "generation_groupee":          # lot 6 (19/11) : tous les livrables, rangés, avec journal
            from genvar import generation_groupee as gg
            deja = self.s.ouvrage.deja_exporte
            unitaire = tempfile.mkdtemp(prefix="sorep_groupe_", dir=dossier)
            nom = f"{base}_livrables.zip"
            try:
                self.dernier_bilan_groupe = gg.archive(
                    self.s, os.path.join(dossier, nom), lambda x: self._exporter_ouvrage(x, unitaire, base),
                    q.get("familles"), erreurs_attendues=(RegleMetier, ValueError, OSError))["bilan"]
            except gg.GenerationRefusee as exc:
                raise RegleMetier(str(exc)) from None
            if self.s.ouvrage.deja_exporte is True and deja is not True:
                self._sauver()
            with open(os.path.join(dossier, nom), "rb") as f:
                return nom, f.read()
        deja = self.s.ouvrage.deja_exporte
        nom, octets = self._exporter_ouvrage(quoi, dossier, base)
        if self.s.ouvrage.deja_exporte is True and deja is not True:
            self._sauver()                       # R6 : l'export est mémorisé dans le fichier de l'ouvrage
        return nom, octets

    def _exporter_ouvrage(self, quoi, dossier, base):
        if quoi == "modifications":                      # indices (22/11) : dernier indice livré → état en cours
            c = self.s.comparer_indices()
            nom = f"{base}_modifications_{c['depuis']}_{self.s.ouvrage.revision}.xlsx"
            self.s.exporter_modifications(os.path.join(dossier, nom))
            with open(os.path.join(dossier, nom), "rb") as f:
                return nom, f.read()
        if quoi.startswith("format_appris:"):           # formats appris (22/11) : mêmes refus que l'export Control Expert
            from genvar import formats_appris as fa
            fmt = fa.trouver(quoi.split(":", 1)[1])
            if fmt is None:
                raise RegleMetier("Format appris introuvable.")
            if self.s.ouvrage.mode != "Neuf":
                raise RegleMetier("Projet existant : le programme en place n'est jamais réécrit.")
            self._exigences_format(fmt["nature"])
            try:
                nom, octets, self.dernier_statut_format = fa.exporter(fmt, self.s)
            except fa.FormatRefuse as exc:
                raise RegleMetier(str(exc)) from None
            return nom, octets
        if quoi in ("essais_fat", "essais_sat"):         # cahiers d'essais (lot 3, 19/11)
            from genvar import essais
            nature = quoi[-3:].upper()
            nom = f"{base}_cahier_essais_{nature}.xlsx"
            try:
                essais.exporter(os.path.join(dossier, nom), self.s, nature)
            except essais.EssaiRefuse as exc:
                raise RegleMetier(str(exc)) from None
            with open(os.path.join(dossier, nom), "rb") as f:
                return nom, f.read()
        if quoi == "equipements":                     # aller-retour Excel (19/11)
            if not self.s.ouvrage.equipements:
                raise RegleMetier("Aucun équipement à exporter.")
            nom = f"{base}_equipements_aller_retour.xlsx"
            from genvar.aller_retour import exporter as exporter_equipements
            exporter_equipements(os.path.join(dossier, nom), self.s.ouvrage)
            with open(os.path.join(dossier, nom), "rb") as f:
                return nom, f.read()
        if quoi == "liste_es":
            nom = f"{base}_liste_ES.xlsx"
            self.s.exporter_liste_es(os.path.join(dossier, nom))
        elif quoi == "tele_etudes":
            if self.s.ouvrage.mode != "Neuf":
                raise RegleMetier("Projet existant : utilisez la table de correspondances (variables de contrôle).")
            if not self.s.variables():
                raise RegleMetier("Aucune variable de télétransmission dans cet ouvrage.")
            nom = f"{base}_teletransmission_etudes.xlsx"
            from genvar.export_tele_etudes import exporter as exporter_tele
            exporter_tele(os.path.join(dossier, nom), self.s)
        elif quoi == "es_cartes":
            nom = f"{base}_ES_par_carte.xlsx"
            self.s.exporter_es_cartes(os.path.join(dossier, nom))
        elif quoi == "cartes":
            if not self.s.ouvrage.modules:
                raise RegleMetier("Déclarez d'abord les cartes d'E/S (modules).")
            nom = f"{base}_cartes_ES.xlsx"
            self.s.exporter_cartes_es(os.path.join(dossier, nom))
        elif quoi == "nomenclature":
            nom = f"{base}_nomenclature_materiel.xlsx"
            self.s.exporter_nomenclature(os.path.join(dossier, nom))
        elif quoi == "variables":
            nom = f"{base}_variables_controle.xlsx"
            self.s.exporter_excel(os.path.join(dossier, nom))
        elif quoi == "xsy":
            if self.s.ouvrage.mode != "Neuf":
                raise RegleMetier("Export XSY réservé aux projets neufs.")
            recette = self.recette_web({})
            if recette["erreurs"]:
                raise RegleMetier(f"Export XSY refusé : {recette['erreurs']} erreur(s) à corriger dans la recette.")
            nom = f"{base}_variables_format_CE.xsy"
            self.s.exporter_xsy(os.path.join(dossier, nom))
        elif quoi in ("es_xsy", "es_txt"):
            cables = [p for p in self.s.points() if p.raccordement != "Communication"]
            if not any(p.adresse for p in cables):
                raise RegleMetier("Aucune E/S n'a de voie : implantez les E/S à l'étape Matériel.")
            erreurs = self.s.erreurs_materiel()       # audit du 16/11 : jamais d'adresse impossible exportée
            if erreurs:
                raise RegleMetier(f"Export refusé : {len(erreurs)} erreur(s) de cartes ou de voies (ex. {erreurs[0]})")
            ext = quoi[3:]
            nom = f"{base}_ES_format_CE.{ext}"
            (self.s.exporter_xsy_es if ext == "xsy" else self.s.exporter_txt_es)(os.path.join(dossier, nom))
        elif quoi == "topkapi":
            nom = f"{base}_TOPKAPI_non_qualifie.zip"
            self.s.exporter_topkapi(os.path.join(dossier, nom))
        else:
            raise RegleMetier("Export inconnu.")
        with open(os.path.join(dossier, nom), "rb") as f:
            return nom, f.read()

    # --------------------------------------------------- ingénierie web : données du moteur, sans inférence
    @staticmethod
    def _largeur_variable(type_logique):
        """Affichage uniquement : la taille réelle est contrôlée par le moteur d'adressage."""
        typ = str(type_logique or "").upper()
        if typ in ("BOOL", "EBOOL"):
            return "1 bit"
        if typ in ("REAL", "DINT", "UDINT", "DWORD"):
            return "32 bits"
        if typ in ("LREAL", "LINT", "ULINT"):
            return "64 bits"
        if typ in ("INT", "UINT", "WORD"):
            return "16 bits"
        return "À vérifier"

    def _plan_affectations_par_niveau(self, niveau):
        """Lecture sans effet de bord du moteur unique (aucun calcul n'applique d'adresse)."""
        plan = self.s.plan_adressage()
        return {(a.ident_eq, a.cle): a for a in plan.affectations if a.niveau == niveau}

    @staticmethod
    def _plages_voies(voies):
        """[0, 1, 2, 5] → « 0 à 2, 5 » : voies d'une carte en plages contiguës."""
        nums = sorted({int(v) for v in voies if str(v).isdigit()})
        plages, debut = [], None
        for i, n in enumerate(nums):
            if debut is None:
                debut = n
            if i + 1 == len(nums) or nums[i + 1] != n + 1:
                plages.append(f"{debut}" if debut == n else f"{debut} à {n}")
                debut = None
        return ", ".join(plages)

    def fil_web(self, q):
        """Fil de l'information d'un équipement (refonte, lot 4) : son état à chaque maillon de la chaîne
        équipement → E/S physiques → carte et voies → variables → supervision. Lecture seule ; aucun calcul
        d'adressage n'est lancé (seules les adresses posées et validées sont comptées)."""
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        o = self.s.ouvrage
        eq = o.equipement(str(q.get("ident", "")))
        if eq is None:
            raise RegleMetier("Équipement introuvable.")
        repere = o.repere(eq)
        sortie: dict[str, Any] = {"ident": eq.ident, "repere": repere, "nom_court": o.repere_nom(eq), "mode": o.mode}
        sortie["equipement"] = {"etat": "ok" if eq.valide else "al",
                                "titre": f"Équipement {eq.code_court()}",
                                "detail": "paramétrage validé" if eq.valide else "paramétrage à valider"}
        if o.mode != "Neuf":
            sortie["note"] = "Projet existant : le fil se lit dans le programme en place."
            return sortie
        pts = [p for p in self.s.liste_es() if p.ident_eq == eq.ident] if eq.valide else []
        cables = [p for p in pts if p.raccordement != "Communication"]
        a_valider = sum(1 for p in pts if not p.contenu_valide)
        if not eq.valide:
            es = {"etat": "", "titre": "E/S physiques", "detail": "après validation de l'équipement"}
        elif not pts:
            es = {"etat": "", "titre": "Aucune E/S", "detail": "équipement sans E/S physique"}
        else:
            es = {"etat": "al" if a_valider else "ok", "titre": f"{len(pts)} E/S physique{'s' if len(pts) > 1 else ''}",
                  "detail": f"{a_valider} à valider" if a_valider else "contenu validé"}
        sortie["es"] = es
        par_carte: dict[str, list] = {}
        for p in cables:
            if p.adresse:
                par_carte.setdefault(p.module or "?", []).append(p.voie)
        sans_voie = sum(1 for p in cables if not p.adresse)
        non_validees = sum(1 for p in cables if p.adresse and not p.validee)
        if not cables:
            carte = {"etat": "", "titre": "Carte et voies", "detail": "aucune E/S câblée"}
        else:
            titre = (f"Carte {next(iter(par_carte))} · voie{'s' if len(cables) > 1 else ''} "
                     f"{self._plages_voies(next(iter(par_carte.values())))}" if len(par_carte) == 1
                     else f"{len(par_carte)} cartes · {sum(len(v) for v in par_carte.values())} voies" if par_carte
                     else "Carte et voies")
            carte = {"etat": "al" if sans_voie or non_validees else "ok", "titre": titre,
                     "detail": (f"{sans_voie} E/S sans voie" if sans_voie else
                                f"{non_validees} voie(s) à valider" if non_validees else "voies validées")}
        sortie["carte"] = carte
        variables = [v for v in self.s.variables() if v.ident_eq == eq.ident] if eq.valide else []
        validees = sum(1 for v in variables if v.adresse and v.adresse_validee)
        if not variables:
            var = {"etat": "", "titre": "Variables", "detail": "aucune variable" if eq.valide else "après validation"}
        else:
            var = {"etat": "ok" if validees == len(variables) else "al",
                   "titre": f"{len(variables)} variable{'s' if len(variables) > 1 else ''}",
                   "detail": "adresses validées" if validees == len(variables)
                   else f"{len(variables) - validees} adresse(s) à valider"}
        sortie["variables"] = var
        libelles = sum(1 for v in variables if v.libelle_topkapi)
        sortie["supervision"] = {"etat": "", "titre": "Supervision",
                                 "detail": f"{libelles} libellé{'s' if libelles > 1 else ''}" if libelles else "aucun libellé"}
        if q.get("detail"):
            # Vue « Fil des informations » de la fiche (lot 5a) : une ligne par information, avec sa chaîne.
            lignes, utilisees = [], set()
            for v in variables:
                utilisees.add(v.nom_es)
                lignes.append({"information": v.information, "famille": v.famille, "es": v.nom_es, "voie": v.adresse_es,
                               "variable": v.nom, "type": v.type_logique, "adresse": v.adresse,
                               "libelle": v.libelle_topkapi,
                               "etat": "validée" if v.adresse and v.adresse_validee else "à valider" if v.adresse
                               else "sans adresse"})
            for p in pts:                              # E/S sans variable d'échange (commandes câblées, par exemple)
                if p.nom not in utilisees:
                    lignes.append({"information": p.information, "famille": p.point, "es": p.nom, "voie": p.adresse,
                                   "variable": "", "type": "", "adresse": "", "libelle": "",
                                   "etat": "E/S seule"})
            sortie["lignes"] = lignes
        return sortie

    def activite_recente(self, _):
        """V1-4-33 : faits enregistrés de l'ouvrage ouvert, du plus récent au plus ancien (aucun fait inventé) :
        indices livrés, copies horodatées avant une opération lourde, validations d'adresses (regroupées par instant)."""
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        from genvar import revisions
        o = self.s.ouvrage
        faits = []
        for x in revisions.indices(o):
            faits.append({"quand": str(x.get("le", "")).replace("T", " ")[:19], "nature": "indice",
                          "texte": f"Indice {x['indice']} livré : {x.get('motif', '')}"})
        for c in self.s.copies_horodatees():
            faits.append({"quand": c["le"], "nature": "copie", "texte": c["libelle"]})
        validations: dict = {}
        for e in o.equipements:
            for cle, t in (e.traces or {}).items():
                if t.get("validee_le"):
                    validations.setdefault(t["validee_le"], {"n": 0, "par": t.get("validee_par", ""), "niveau": cle.split(":")[0]})
                    validations[t["validee_le"]]["n"] += 1
        libelle_niveau = {"physique": "voie(s) physique(s)", "automate": "adresse(s) automate"}
        for quand, v in validations.items():
            faits.append({"quand": quand, "nature": "validation",
                          "texte": f"{v['n']} {libelle_niveau.get(v['niveau'], 'adresse(s)')} validée(s)" + (f" par {v['par']}" if v["par"] else "")})
        faits.sort(key=lambda f: f["quand"], reverse=True)
        return {"faits": faits[:8], "total": len(faits)}

    def _ouvrage_existant(self):
        if not self.ouvert or self.creation_en_attente:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        if self.s.ouvrage.mode != "Existant":
            raise RegleMetier("Le rapprochement concerne les projets existants.")
        return self.s.ouvrage

    def rapprochement_web(self, _):
        """V1-6-02, V1-6-05 : table de télétransmission d'un projet existant, une ligne par information attendue, avec la
        source associée, son niveau de confiance et sa raison, et les confirmations (une à une ou en lot, annulables)."""
        o = self._ouvrage_existant()
        from genvar import teletransmission as tt
        candidats = self.s.candidats()
        lignes = []
        for v in self.s.table():
            l = v.ligne
            propositions = candidats.get((l.ident_eq, l.cle), [])
            courante = next((p for p in propositions if p.variable_nom == l.variable_source), None)
            lignes.append({
                "ident_eq": l.ident_eq, "cle": l.cle, "repere": v.repere, "information": v.information,
                "nom_standard": v.nom_standard, "famille": v.famille, "sens": v.sens, "statut": v.statut, "motif": v.motif,
                "variable_source": v.variable_source, "type_source": v.type_source, "adresse_source": v.adresse_source,
                "registre": v.registre, "fonction_validee": l.fonction_validee, "acces_verifie": l.acces_verifie,
                "non_accessible": l.non_accessible, "origine": l.origine_association,
                "confiance": courante.confiance if courante else "", "raison": courante.raison if courante else "",
                "score": courante.score if courante else None,
                "candidats": [{"variable": p.variable_nom, "score": p.score, "confiance": p.confiance, "raison": p.raison,
                               "ambigu": p.ambiguite} for p in propositions[:3]]})
        lots = [{"id": e["id"], "le": e["le"], "par": e.get("par", ""), "n": len(e.get("lignes", []))}
                for e in o.journal_rapprochement if e.get("action") == "confirmation en lot" and not e.get("annule")]
        detectes = [{"cle": f"{d.sous_ensemble}|{d.type}|{d.numero}", "type": d.type, "designation": d.designation,
                     "numero": d.numero, "se": d.sous_ensemble, "noms": list(d.variables[:3])}
                    for d in self.s.equipements_detectes()]
        return {"lignes": lignes, "bilan": tt.bilan(o, self.s.catalogue), "confirmables": len(self.s.confirmables_en_lot()),
                "lots": lots, "detectes": detectes, "variables": len(o.existantes), "equipements": len(o.equipements)}

    def rapprochement_action(self, d):
        """construire, detectes, proposer, associer, dissocier, confirmer, retirer_confirmation, lot, annuler_lot."""
        self._ouvrage_existant()
        d = d or {}
        action, ident, cle = d.get("action"), str(d.get("ident_eq") or ""), str(d.get("cle") or "")
        if action == "construire":
            self.s.construire_table()
        elif action == "detectes":
            demandes = {str(x) for x in d.get("cles") or []}
            choisis = [x for x in self.s.equipements_detectes() if f"{x.sous_ensemble}|{x.type}|{x.numero}" in demandes]
            if not choisis:
                raise RegleMetier("Cochez au moins un équipement détecté.")
            self.s.ajouter_detectes(choisis)
            self.s.construire_table()
        elif action == "proposer":
            self.s.proposer_associations()
        elif action == "associer":
            self.s.associer(ident, cle, str(d.get("variable") or ""))
        elif action == "dissocier":
            self.s.dissocier(ident, cle)
        elif action == "confirmer":
            self.s.valider_fonction(ident, cle, True)
        elif action == "retirer_confirmation":
            self.s.valider_fonction(ident, cle, False)
        elif action == "lot":
            if self.s.confirmer_en_lot() is None:
                raise RegleMetier("Aucune ligne de confiance élevée à confirmer.")
        elif action == "annuler_lot":
            try:
                self.s.annuler_lot(int(d.get("id")))
            except (TypeError, ValueError) as exc:
                raise RegleMetier("Numéro de lot invalide.") from exc
        else:
            raise RegleMetier("Action de rapprochement inconnue.")
        self._sauver()
        return self.rapprochement_web({})

    def recherche_globale(self, q):
        """V1-5-06 : recherche par repère, variable, adresse ou libellé (équipements et variables de l'ouvrage ouvert)."""
        texte = " ".join(str((q or {}).get("q") or "").split()).lower()
        if not self.ouvert or len(texte) < 2:
            return {"resultats": [], "q": texte, "complet": True}
        o = self.s.ouvrage
        trouves = []

        def vise(*champs):
            return next((nom for nom, valeur in champs if texte in str(valeur or "").lower()), "")
        for e in o.equipements:
            critere = vise(("repère", o.repere(e)), ("libellé", e.libelle), ("type", e.type), ("désignation", self.s.catalogue.type(e.type) and self.s.catalogue.type(e.type).get("designation")))
            if critere:
                trouves.append({"nature": "equipement", "ident_eq": e.ident, "titre": o.repere(e), "detail": e.libelle, "critere": critere})
        variables = (self.s.variables() if o.mode != "Existant" else [])
        for v in variables:
            critere = vise(("variable", v.nom), ("libellé", v.libelle_topkapi or v.commentaire), ("adresse", v.adresse),
                           ("voie physique", v.adresse_es), ("repère", v.repere))
            if critere:
                trouves.append({"nature": "variable", "ident_eq": v.ident_eq, "cle": v.cle, "titre": v.nom,
                                "detail": v.adresse or v.libelle_topkapi or v.commentaire or "", "critere": critere})
        for v in (o.existantes if o.mode == "Existant" else []):
            critere = vise(("variable", v.nom), ("libellé", v.commentaire), ("adresse", v.adresse))
            if critere:
                trouves.append({"nature": "variable", "ident_eq": "", "cle": "", "titre": v.nom, "detail": v.adresse or "", "critere": critere})
        return {"resultats": trouves[:30], "total": len(trouves), "q": texte, "complet": len(trouves) <= 30}

    def variables_web(self, _):
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        o = self.s.ouvrage
        if o.mode == "Existant":
            lignes = [{"nom": v.nom, "type": v.type_logique, "largeur": self._largeur_variable(v.type_logique),
                       "adresse": v.adresse, "adresse_proposee": "", "famille": "Historique",
                       "commentaire": v.commentaire, "statut": v.identification,
                       "origine": v.nature_source, "origine_adressage": "importée", "etat_adressage": "à valider",
                       "motif": "Adresse historique en lecture seule ; disponibilité non vérifiée jusqu'à attestation.",
                       "regle": "Conservation du programme existant", "validee": False,
                       "ident_eq": "", "cle": "", "source_es": "", "voie_es": "",
                       "validee_le": "", "validee_par": ""} for v in o.existantes]
            return {"mode": "Existant", "lignes": lignes, "plateforme": o.automate,
                    "disponibilite_verifiee": o.disponibilite_verifiee,
                    "note": "Adresses historiques en lecture seule : aucune réattribution automatique."}
        plan = self._plan_affectations_par_niveau("automate")
        lignes = []
        for v in self.s.variables():
            adr = plan.get((v.ident_eq, v.cle))
            lignes.append({"ident_eq": v.ident_eq, "cle": v.cle, "nom": v.nom,
                           "famille": v.famille, "sens": sens_variable(v.famille), "type": v.type_logique,
                           "largeur": self._largeur_variable(v.type_logique),
                           "adresse": v.adresse, "adresse_proposee": adr.proposee if adr else "",
                           "etat_adressage": adr.etat if adr else "non résolue",
                           "origine_adressage": adr.origine if adr else "",
                           "regle": adr.regle if adr else "", "motif": adr.motif if adr else "",
                           "validee_le": adr.validee_le if adr else "",
                           "validee_par": adr.validee_par if adr else "",
                           "validee": v.adresse_validee, "commentaire": v.commentaire,
                           "libelle": v.libelle_topkapi, "repere": v.repere,
                           "origine": v.origine, "source_es": v.nom_es,
                           "voie_es": v.adresse_es,
                           "source_signal": v.cle_es})
        return {"mode": "Neuf", "lignes": lignes, "plateforme": o.automate,
                "note": "Table d'échange uniquement : les E/S physiques sont affichées comme sources en lecture seule. "
                        "Les adresses proposées ne sont pas appliquées."}

    def variables_action(self, d):
        if self.s.ouvrage.mode != "Neuf":
            raise RegleMetier("Les variables du programme existant ne sont jamais réadressées ici.")
        action = d.get("action")
        ident, cle = d.get("ident_eq", ""), d.get("cle", "")
        if action == "adresse":
            self.s.definir_adresses(ident, cle, adresse=d.get("adresse", ""),
                                    deverrouiller=bool(d.get("confirmer_changement", False)))
        elif action == "textes":
            self.s.definir_textes(ident, cle, commentaire=d.get("commentaire"), libelle=d.get("libelle"))
        elif action == "valider":
            n, refus = self.s.valider_adresses([(x["ident_eq"], x["cle"]) for x in d.get("paires", [])])
            self._sauver()
            return {"validees": n, "refus": refus}
        else:
            raise RegleMetier("Action variable inconnue.")
        self._sauver()
        return {}

    # --------------------------------------------------- moteur d'adressage (trois niveaux, deux phases)
    def adressage_web(self, _):
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        o = self.s.ouvrage
        plan = self.s.plan_adressage().dict()
        from genvar.modele import ORDRE_ZONES, PLAN_DEFAUT, zone
        plan.update(plages={f: zone(o, f) for f in ORDRE_ZONES}, plages_defaut=PLAN_DEFAUT)
        plan.update(mode=o.mode, automate=o.automate, reservations=o.reservations,
                    protocole_declare=o.protocole_declare, decalage=o.decalage_modbus,
                    disponibilite_verifiee=o.disponibilite_verifiee, journal=o.journal_adressage[-10:])
        return plan

    def adressage_action(self, d):
        a = d.get("action")
        if a == "appliquer":
            r = self.s.appliquer_adressage(d.get("empreinte", ""), d.get("niveaux") or ("physique", "automate"))
        elif a == "reserver":
            self.s.ajouter_reservation(d.get("niveau", ""), d.get("cible", ""), d.get("motif", ""))
            r = {}
        elif a == "liberer":
            self.s.retirer_reservation(d.get("niveau", ""), d.get("cible", ""))
            r = {}
        elif a == "protocole":
            self.s.declarer_protocole(bool(d.get("declare")), d.get("decalage", 0) or 0)
            r = {}
        elif a == "disponibilite":
            self.s.declarer_disponibilite(bool(d.get("verifiee")))
            r = {}
        elif a == "plages":                                 # 18/11 : plan mémoire, convention du maître d'ouvrage
            r = {"alertes": self.s.definir_plages(d.get("plages") or {})}
        elif a == "valider":
            r = {"n": self.s.valider_affectations(d.get("niveau", ""), [(x["ident_eq"], x["cle"]) for x in d.get("paires", [])])}
        else:
            raise RegleMetier("Action d'adressage inconnue.")
        self._sauver()
        return r

    def supervision_web(self, _):
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        o = self.s.ouvrage
        if o.mode == "Existant":
            return {"mode": "Existant", "lignes": [], "statut": "À rapprocher",
                    "note": "Télétransmission historique à rapprocher avec le programme source. "
                            "Aucun point ni aucune adresse n'est créé automatiquement."}
        tele = self._plan_affectations_par_niveau("teletransmission")
        variables = self.s.variables()
        par_cle = {(v.ident_eq, v.cle): v for v in variables}
        lignes = []
        for v in variables:
            a = tele.get((v.ident_eq, v.cle))
            retour = ""
            if v.famille in ("TR", "RTR"):
                autre = "RTR" if v.famille == "TR" else "TR"
                suffixe = v.cle.split("_", 1)[1] if "_" in v.cle else ""
                pair = par_cle.get((v.ident_eq, autre + "_" + suffixe))
                retour = pair.nom if pair else ""
            lignes.append({"ident_eq": v.ident_eq, "cle": v.cle, "nom": v.nom,
                "famille": v.famille, "information": v.information,
                "adresse": v.adresse, "adresse_protocole_actuelle": a.actuelle if a else "",
                "adresse_protocole_proposee": a.proposee if a else "",
                "identifiant_point": v.nom, "variable_source": v.nom,
                "etat_adressage": a.etat if a else "non résolue",
                "motif": a.motif if a else "", "regle": a.regle if a else "",
                "origine_adressage": a.origine if a else "", "validee_le": a.validee_le if a else "",
                "validee_par": a.validee_par if a else "", "correspondance": retour,
                "type": v.type_logique, "largeur": self._largeur_variable(v.type_logique),
                "validee": v.adresse_validee, "libelle": v.libelle_topkapi,
                "repere": v.repere})
        return {"mode": "Neuf", "lignes": lignes,
            "statut": "À qualifier dans SOFREL et TOPKAPI",
            "note": "Point fonctionnel, variable source et adresse protocolaire distincts. "
                    "Aucun import S4W-Tools ou TOPKAPI n'est qualifié."}

    def outils_web(self, _):
        """Outils d'ingénierie de l'ouvrage, contraintes qui en découlent (18/11), standard d'origine et écarts (19/11)."""
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        from genvar import standards
        from genvar.outils import resume
        listes = ref_ident.lire()
        ref = self.s.ouvrage.standard or {}
        actuel = standards.trouver(ref.get("ident", "")) if ref else None
        return {**resume(self.s.ouvrage), "supervisions": listes["supervisions"], "ihms": listes["ihm"],
                "standard": {k: ref.get(k) for k in ("ident", "nom", "version", "applique_le")} if ref else None,
                "standard_ecarts": standards.ecarts(self.s.ouvrage),
                "standard_a_evolue": bool(actuel and actuel.get("version") != ref.get("version")),
                "standard_version_actuelle": actuel.get("version") if actuel else None}

    def standards_web(self, _):
        """Standards d'ingénierie de l'atelier, nombre d'ouvrages qui les utilisent, bibliothèque de briques (19/11)."""
        from genvar import charte, standards
        from genvar.modele import ORDRE_ZONES, PLAN_DEFAUT
        compte, emplois = standards.utilisation(), standards.emplois_briques()
        listes = ref_ident.lire()

        def enrichir(f, b):
            b = {**b, "standards": emplois.get(f"{f}:{b['ident']}", 0)}
            if f == "charte":
                b |= {"exemple": charte.exemple(b), "description": charte.decrire(b), "ogias": charte.est_ogias(b)}
            return b
        for s in (liste := standards.lire()):
            if "charte" in s["briques"]:
                s["briques"]["charte"] = enrichir("charte", s["briques"]["charte"])
        return {"standards": [{**s, "ouvrages": compte.get(s["ident"], 0),
                               "motifs": _motifs_identification(s["briques"].get("charte"))}
                              for s in liste],
                "charte_meta": {"segments_ouvrage": charte.SEGMENTS_OUVRAGE, "segments_equipement": charte.SEGMENTS_EQUIPEMENT,
                                "caracteres": {k: v[1] for k, v in charte.CARACTERES.items()},
                                "separateurs": charte.SEPARATEURS, "longueur_max": charte.LONGUEUR_MAX_REPERE},
                "familles": standards.FAMILLES, "choisissables": list(standards.CHOISISSABLES),
                "anterieurs": compte.get("", 0),
                "bibliotheque": {f: [enrichir(f, b) for b in liste] for f, liste in standards.bibliotheque().items()},
                "supervisions": listes["supervisions"], "ihms": listes["ihm"],
                "plages_defaut": {f: list(PLAN_DEFAUT[f]) for f in ORDRE_ZONES}}

    def standards_action(self, d):
        """Bibliothèque et standards (étape 2) : créer une brique, créer un standard, nouvelle version, archiver.
        Aucun ouvrage n'est modifié par ces actions."""
        from genvar import standards
        action = d.get("action")
        alertes: list[str] = []
        if action == "brique":
            famille, contenu = str(d.get("famille") or ""), d.get("contenu") or {}
            if famille == "outils":
                listes = ref_ident.lire()
                for champ, liste, nom in (("supervision", "supervisions", "Supervision"), ("ihm", "ihm", "IHM")):
                    valeur = str(contenu.get(champ) or "").strip()
                    if valeur and valeur not in listes[liste]:
                        raise RegleMetier(f"{nom} absente du référentiel : ajoutez-la d'abord par « Gérer les listes ».")
            _, alertes = standards.creer_brique(famille, str(d.get("nom") or ""), contenu)
        elif action == "creer":
            d["ident"] = standards.creer_standard(str(d.get("nom") or ""), str(d.get("description") or ""), d.get("choix") or {})["ident"]
        elif action == "reviser":
            standards.reviser_standard(str(d.get("ident") or ""), d.get("choix") or {}, d.get("description"), str(d.get("motif") or ""))
        elif action == "statut":
            standards.changer_statut(str(d.get("ident") or ""), str(d.get("statut") or ""))
        else:
            raise RegleMetier("Action inconnue.")
        return {**self.standards_web({}), "ident": d.get("ident", ""), "alertes": alertes}

    def grille_web(self, _):
        """Grille d'ingénierie (lot 5, 19/11) : une ligne par équipement, colonnes descriptives et attributs de
        l'atelier (None = sans objet pour ce type), état de contrôle. Lecture seule."""
        if not self.ouvert or self.creation_en_attente:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        from genvar import attributs
        o = self.s.ouvrage
        try:
            defs = attributs.lister(actifs_seulement=True)
        except ValueError:
            defs = []
        anomalies = self.s.anomalies()
        par_eq: dict[str, list] = {}
        for a in anomalies:
            if a.ident_eq:
                par_eq.setdefault(a.ident_eq, []).append(a)
        lignes = []
        for e in sorted(o.equipements, key=o.repere):
            an = par_eq.get(e.ident, [])
            lignes.append({"ident": e.ident, "repere": o.repere(e), "type": e.type, "designation": self.s.designation_type(e.type),
                           "libelle": e.libelle, "modele": e.modele, "uf": e.uf, "local": e.local, "valide": e.valide,
                           "erreurs": sum(a.niveau == "Erreur" for a in an), "alertes": sum(a.niveau == "Alerte" for a in an),
                           "controles": [f"{a.code} · {a.message}" for a in an][:6],
                           "attributs": {a["code"]: ((e.attributs or {}).get(a["code"], "") if not a.get("types") or e.type in a["types"] else None)
                                         for a in defs}})
        return {"lignes": lignes, "attributs": defs, "ufs": [{"code": u.code, "libelle": u.libelle} for u in o.unites],
                "champs": self.s.CHAMPS_GRILLE}

    def grille_appliquer(self, d):
        idents = d.get("idents") or []
        if not isinstance(idents, list) or not all(isinstance(x, str) for x in idents) or len(idents) > 5000:
            raise RegleMetier("Sélection invalide.")
        r = self.s.appliquer_en_masse(idents, str(d.get("champ") or ""), d.get("valeur", ""))
        if r["modifies"]:
            self._sauver()
        return r

    def attributs_web(self, _):
        """Attributs d'équipement de l'atelier (lot 4, 19/11) et types d'équipement connus."""
        from genvar import attributs
        types = sorted({t for t in self.s.modeles["types"]} | {t["code"] for t in self.s.catalogue.types})
        return {"attributs": attributs.lister(), "types_attribut": attributs.TYPES, "types_equipement": types}

    def attributs_action(self, d):
        from genvar import attributs
        action, code = d.get("action"), str(d.get("code") or "")
        try:
            if action == "creer":
                attributs.creer(d.get("definition") or {})
            elif action == "modifier":
                attributs.modifier(code, d.get("definition") or {})
            elif action in ("archiver", "reactiver"):
                attributs.archiver(code, action == "archiver")
            else:
                raise RegleMetier("Action inconnue.")
        except attributs.AttributRefuse as exc:
            raise RegleMetier(str(exc)) from None
        return self.attributs_web({})

    def equipement_attribut(self, d):
        v = self.s.definir_attribut(str(d.get("ident_eq") or ""), str(d.get("code") or ""), d.get("valeur", ""))
        self._sauver()
        return {"valeur": v}

    def essais_web(self, _):
        """Avancement des cahiers d'essais FAT et SAT (lot 3, 19/11) : résultats reportés, jamais déduits."""
        if not self.ouvert or self.creation_en_attente:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        from genvar import essais
        return {n: essais.etat(self.s, n) for n in essais.NATURES}

    def essais_reporter(self, d):
        """Reporter un cahier rempli. Sans « confirme » : aperçu seulement (rien n'est écrit). Avec : copie de sécurité,
        enregistrement des résultats lus, sauvegarde. Un cahier avec des erreurs n'est pas reporté."""
        if not self.ouvert or self.creation_en_attente:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        from genvar import essais, tableur
        nature = str(d.get("nature") or "")
        if nature not in essais.NATURES:
            raise RegleMetier("Nature d'essai inconnue (FAT ou SAT).")
        if os.path.splitext(str(d.get("nom") or ""))[1].lower() not in (".xlsx", ".xlsm", ".ods"):
            raise RegleMetier("Cahier attendu au format Excel (.xlsx) ou OpenDocument (.ods).")
        try:
            octets = base64.b64decode(str(d.get("contenu") or ""), validate=True)
        except (ValueError, binascii.Error):
            raise RegleMetier("Contenu du fichier invalide.") from None
        if not octets or len(octets) > 15 * 1024 * 1024:
            raise RegleMetier("Fichier vide ou trop volumineux (15 Mo au plus).")
        dossier = tempfile.mkdtemp(prefix="ogias_essais_")
        try:
            chemin = os.path.join(dossier, "cahier" + os.path.splitext(str(d["nom"]))[1].lower())
            with open(chemin, "wb") as fh:
                fh.write(octets)
            try:
                lu = essais.lire(tableur.lire_classeur(chemin), self.s, nature)
            except essais.EssaiRefuse as exc:
                raise RegleMetier(str(exc)) from None
            except Exception as exc:                          # noqa: BLE001 — classeur illisible
                raise RegleMetier(f"Cahier illisible : {exc}") from None
        finally:
            shutil.rmtree(dossier, ignore_errors=True)
        apercu = {"nature": nature, "inchanges": lu["inchanges"], "vides": lu["vides"], "erreurs": lu["erreurs"],
                  "resultats": sorted(({"nom": r["nom"], "avant": r["avant"], "resultat": r["resultat"], "remarque": r["remarque"]}
                                       for r in lu["resultats"].values()),
                                      key=lambda x: (x["resultat"] != "Non conforme", x["nom"]))}   # non-conformités d'abord
        if d.get("confirme") is not True:
            return apercu
        if lu["erreurs"]:
            raise RegleMetier(f"Cahier non reporté : {len(lu['erreurs'])} erreur(s) à corriger dans le fichier.")
        if not lu["resultats"]:
            raise RegleMetier("Aucun résultat nouveau à reporter.")
        self.s.creer_copie("essais")
        n = essais.reporter(self.s, nature, lu["resultats"])
        self._sauver()
        return {**apercu, "reportes": n, "etat": essais.etat(self.s, nature)}

    def _exigences_format(self, nature):
        """Mêmes refus que les exports livrés : E/S implantées et matériel cohérent, ou variables sans conflit."""
        from genvar import formats_appris as fa, adressage
        if nature == "es_physiques":
            if not any(p.adresse for p in fa.points_exportes(self.s)):
                raise RegleMetier("Aucune E/S n'a de voie : implantez les E/S à l'étape Matériel.")
            erreurs = self.s.erreurs_materiel()
            if erreurs:
                raise RegleMetier(f"Export refusé : {len(erreurs)} erreur(s) de cartes ou de voies (ex. {erreurs[0]})")
            return
        if not self.s.variables():
            raise RegleMetier("Aucune variable d'échange dans l'ouvrage.")
        conflits = adressage.calculer(self.s).conflits
        if conflits:
            raise RegleMetier(f"Export refusé : {len(conflits)} conflit(s) d'adressage à résoudre à l'étape Variables "
                              f"(ex. {conflits[0][1]}).")

    def gammes_materiel_web(self, _):
        """Gammes de matériel déclarées par l'atelier (22/11) et gammes livrées, pour l'écran Standards."""
        from genvar import gammes_materiel as gm
        try:
            gammes = [gm.resume(g) for g in gm.lister()]
        except ValueError as exc:
            raise RegleMetier(str(exc)) from None
        o = self.s.ouvrage if self.ouvert else None
        from genvar import materiel as mat
        return {"gammes": [gm.resume(g) for g in gm.livrees()] + gammes, "natures": list(gm.NATURES),
                "statut": gm.STATUT,
                "livrees": ["Schneider Modicon M340", "Schneider Modicon M580", "Schneider Advantys STB",
                            "SOFREL S4W", *(g["nom"] for g in gm.livrees())],
                "ouvrage": ({"automate": o.automate, "gamme": mat.gamme(o.automate) or ""} if o is not None else None)}

    def gammes_materiel_action(self, d):
        """Déclarer, modifier ou supprimer une gamme. Aucun ouvrage n'est modifié."""
        from genvar import gammes_materiel as gm
        action = d.get("action")
        try:
            if action == "enregistrer":
                g = gm.enregistrer(d.get("gamme") or {}, str(d.get("ident") or ""))
                return {**self.gammes_materiel_web({}), "ident": g["ident"]}
            if action == "supprimer":
                gm.supprimer(str(d.get("ident") or ""))
                return self.gammes_materiel_web({})
        except gm.GammeRefusee as exc:
            raise RegleMetier(str(exc)) from None
        raise RegleMetier("Action inconnue.")

    def journal_web(self, _):
        """Journal technique, consultable depuis l'aide (V1-7-06)."""
        return {"lignes": lire_journal(), "dossier": chemins.dossier_donnees(), "taille_max": JOURNAL_TAILLE_MAX,
                "anciens": JOURNAL_ANCIENS}

    def revisions_web(self, q):
        """Indices livrés de l'ouvrage et modifications depuis le dernier (ou entre deux indices choisis)."""
        from genvar import revisions
        if not self.ouvert:
            return {"ouvert": False}
        o = self.s.ouvrage
        liste = revisions.resume_indices(o)
        comparaison = None
        if liste:
            comparaison = self.s.comparer_indices(str((q or {}).get("depuis") or ""), str((q or {}).get("vers") or ""))
        livre = any(x["indice"] == o.revision for x in liste)
        try:
            suivant = revisions.indice_suivant(o.revision) if livre else ""
        except revisions.IndiceRefuse:
            suivant = ""
        return {"ouvert": True, "revision": o.revision, "indices": liste, "livre": livre, "suivant": suivant,
                "comparaison": comparaison, "categories": revisions.CATEGORIES}

    def revisions_action(self, d):
        action = d.get("action")
        if action == "livrer":
            x = self.s.livrer_indice(str(d.get("motif") or ""), str(d.get("auteur") or ""))
            self._sauver()
            return {**self.revisions_web({}), "livre_indice": x["indice"]}
        if action == "suivant":
            self.s.passer_indice_suivant()
            self._sauver()
            return self.revisions_web({})
        raise RegleMetier("Action inconnue.")

    def formats_appris_web(self, _):
        """Formats d'export appris (22/11) : bibliothèque, formats livrés, et pour l'ouvrage ouvert les formats retenus
        selon son automate, avec l'état du contrôle automatique (export relu, sans rien écrire)."""
        from genvar import formats_appris as fa, modeles_livrables as ml
        o = self.s.ouvrage if self.ouvert else None
        formats = []
        for f in fa.lister():
            r = fa.resume(f, o)
            if o is not None and r["retenu"] and o.mode == "Neuf":
                try:
                    self._exigences_format(f["nature"])
                    r["controle"] = {"pret": True, "statut": fa.exporter(f, self.s)[2]}
                except (fa.FormatRefuse, RegleMetier) as exc:
                    r["controle"] = {"pret": False, "statut": str(exc)}
            formats.append(r)
        return {"formats": formats, "livres": fa.FORMATS_LIVRES, "natures": fa.NATURES, "champs": fa.CHAMPS,
                "specs": {n: fa.specification(n) for n in fa.NATURES}, "ouvert": self.ouvert,
                "logiciels_ouvrage": ({dest: ml.logiciels_ouvrage(o, dest) for dest in ("automate", "supervision", "ihm")}
                                      if o is not None else {})}

    def formats_appris_action(self, d):
        """Apprendre un format (analyser, aperçu, enregistrer), qualifier, retirer la qualification, supprimer.
        Aucun ouvrage n'est modifié. La structure vient toujours de l'analyse du fichier par le serveur."""
        from genvar import formats_appris as fa
        action = d.get("action")
        try:
            if action in ("analyser", "apercu", "enregistrer"):
                try:
                    octets = base64.b64decode(str(d.get("contenu") or ""), validate=True)
                except (ValueError, binascii.Error):
                    raise RegleMetier("Contenu du fichier invalide.") from None
                index = d.get("entete_index")
                analyse = fa.analyser(octets, str(d.get("fichier") or ""), int(index) if index not in (None, "") else None,
                                      str(d.get("nature") or "es_physiques"), str(d.get("feuille") or "") or None)
                if action == "analyser":
                    return {"analyse": analyse}
                definition = fa.definir(analyse, d.get("reglages") or {})
                if action == "apercu":
                    if not self.ouvert or self.creation_en_attente or not fa.elements(self.s, analyse["nature"]):
                        return {"analyse": analyse, "apercu": None,
                                "motif": "Ouvrez un ouvrage qui a des " + ("E/S" if analyse["nature"] == "es_physiques"
                                                                           else "variables") + " pour voir l'aperçu."}
                    produit, ecarts = fa.produire(definition, self.s, octets)
                    return {"analyse": analyse, "apercu": fa.apercu_lignes(definition, produit),
                            "refus": fa.controler_ouvrage(definition, self.s), "ecarts": ecarts}
                f = fa.enregistrer(str(d.get("nom") or ""), str(d.get("nature") or ""), str(d.get("logiciel") or ""),
                                   definition, analyse["fichier"], octets)
                return {**self.formats_appris_web({}), "ident": f["ident"]}
            if action == "qualifier":
                fa.qualifier(str(d.get("ident") or ""), str(d.get("version") or ""), str(d.get("compte_rendu") or ""),
                             str(d.get("auteur") or ""))
            elif action == "retirer_qualification":
                fa.retirer_qualification(str(d.get("ident") or ""))
            elif action == "supprimer":
                fa.supprimer(str(d.get("ident") or ""))
            else:
                raise RegleMetier("Action inconnue.")
        except fa.FormatRefuse as exc:
            raise RegleMetier(str(exc)) from None
        return self.formats_appris_web({})

    def modeles_livrables_web(self, _):
        """Bibliothèque des modèles de livrables (lot 1, 19/11) : chaque modèle et l'état de ses variables, plus la
        liste des variables et des blocs qu'OGIAS sait remplir (aide à la rédaction d'un modèle)."""
        from genvar import modeles_livrables as ml
        groupes = [("Ouvrage (partout)", ml.VARIABLES_OUVRAGE), ("Équipement (dans un bloc)", ml.VARIABLES_EQUIPEMENT),
                   ("Variable (bloc VARIABLES)", ml.VARIABLES_VARIABLE), ("E/S (bloc ES)", ml.VARIABLES_ES),
                   ("Compteur (dans un bloc)", ml.COMPTEUR)]
        from genvar import attributs
        try:
            liste_attr = [{"nom": "ATTR_" + a["code"], "description": a["nom"]} for a in attributs.lister(actifs_seulement=True)]
        except ValueError:
            liste_attr = []
        if liste_attr:
            groupes.insert(2, ("Attributs d'équipement de l'atelier (dans un bloc)", {x["nom"]: x["description"] for x in liste_attr}))
        resumes = [ml.resume(m) for m in ml.lister()]
        selection = ml.pour_ouvrage(self.s, resumes) if self.ouvert else {"choix": [], "manques": []}
        retenus = {c["ident"]: c for c in selection["choix"]}
        for r in resumes:                       # lot 8 : retenu ou non pour l'ouvrage ouvert, avec le motif
            c = retenus.get(r["ident"])
            r["retenu"], r["motif_non_retenu"] = (c["retenu"], c["motif"]) if c else (True, "")
        return {"modeles": resumes,
                "destinations": ml.DESTINATIONS, "couverture": ml.couverture(resumes), "manques": selection["manques"],
                "logiciels_ouvrage": ({dest: ml.logiciels_ouvrage(self.s.ouvrage, dest)
                                       for dest in ("automate", "supervision", "ihm")} if self.ouvert else {}),
                "variables": [{"groupe": g, "liste": [{"nom": k, "description": v} for k, v in d.items()]} for g, d in groupes],
                "blocs": {"EQUIPEMENTS": "", "VARIABLES": list(ml.FAMILLES_FILTRE), "ES": list(ml.POINTS_FILTRE)},
                "echappements": ml.ECHAPPEMENTS, "ouvert": self.ouvert,
                # assistant (lot 7) : équipements de l'ouvrage ouvert, candidats « équipement de référence »
                "equipements": ([{"ident": e.ident, "repere": self.s.ouvrage.repere(e), "type": e.type,
                                  "libelle": e.libelle or self.s.designation_type(e.type)}
                                 for e in sorted(self.s.ouvrage.equipements, key=self.s.ouvrage.repere)]
                                if self.ouvert else [])}

    def modeles_livrables_texte(self, q):
        from genvar import modeles_livrables as ml
        return {"texte": ml.texte(str(q.get("ident") or ""))[:200_000]}

    def _assistant_modele(self, d, enregistrer):
        """Lot 7 (19/11) : modèle proposé à partir de l'export d'UN équipement de l'ouvrage ouvert ; enregistré dans la
        bibliothèque seulement sur demande et si le contrôle de reproduction n'est pas en erreur."""
        from genvar import assistant_modele as am, modeles_livrables as ml
        if not self.ouvert:
            raise RegleMetier("Ouvrez l'ouvrage qui contient l'équipement de référence.")
        try:
            octets = base64.b64decode(str(d.get("contenu") or ""), validate=True)
        except (ValueError, binascii.Error):
            raise RegleMetier("Contenu du fichier invalide.") from None
        if not octets or len(octets) > ml.TAILLE_MAX:
            raise RegleMetier("Fichier vide ou trop volumineux (2 Mo au plus).")
        texte, encodage = ml.decoder(octets)
        echappement = str(d.get("echappement") or "") or None
        if echappement is not None and echappement not in ml.ECHAPPEMENTS:
            raise RegleMetier("Échappement inconnu.")
        try:
            r = am.construire(texte, self.s, str(d.get("ident_eq") or ""), [str(x) for x in d.get("refus") or []],
                              echappement)
        except am.AssistantRefuse as exc:
            raise RegleMetier(str(exc)) from None
        r["encodage"] = encodage
        if not enregistrer:
            return r
        if r["verification"]["etat"] == "erreur":
            raise RegleMetier(r["verification"]["message"])
        try:
            corps = r["gabarit"].encode(encodage)
        except UnicodeEncodeError:
            raise RegleMetier(f"Le modèle ne peut pas s'écrire en {encodage}.") from None
        description = (str(d.get("description") or "").strip()
                       or f"Créé par l'assistant depuis {str(d.get('fichier') or 'un export')[:80]} "
                          f"(équipement de référence {r['equipement']}).")
        m = ml.importer(str(d.get("nom") or ""), str(d.get("fichier") or ""), corps, r["echappement"], description,
                        encodage_force=encodage, destination=str(d.get("destination") or ""),
                        logiciel=str(d.get("logiciel") or ""))
        return {"modele": ml.resume(m), **self.modeles_livrables_web({})}

    def modeles_livrables_action(self, d):
        """Importer un modèle (fichier de l'outil avec variables), ajouter l'exemple neutre, déclarer son logiciel cible,
        supprimer. Aucun ouvrage n'est modifié par ces actions."""
        from genvar import modeles_livrables as ml
        action = d.get("action")
        try:
            if action == "importer":
                try:
                    octets = base64.b64decode(str(d.get("contenu") or ""), validate=True)
                except (ValueError, binascii.Error):
                    raise RegleMetier("Contenu du fichier invalide.") from None
                m = ml.importer(str(d.get("nom") or ""), str(d.get("fichier") or ""), octets,
                                str(d.get("echappement") or "aucun"), str(d.get("description") or ""),
                                destination=str(d.get("destination") or ""), logiciel=str(d.get("logiciel") or ""))
            elif action == "cible":                 # lot 8 : destination et logiciel déclarés du modèle
                m = ml.definir_cible(str(d.get("ident") or ""), str(d.get("destination") or ""),
                                     str(d.get("logiciel") or ""))
            elif action in ("assistant", "assistant_enregistrer"):
                return self._assistant_modele(d, action == "assistant_enregistrer")
            elif action == "exemple":
                m = ml.ajouter_exemple()
            elif action == "supprimer":
                ml.supprimer(str(d.get("ident") or ""))
                m = {"ident": ""}
            else:
                raise RegleMetier("Action inconnue.")
        except ml.ModeleRefuse as exc:
            raise RegleMetier(str(exc)) from None
        return {**self.modeles_livrables_web({}), "ident": m["ident"]}

    def apercu_charte(self, d):
        """Aperçu d'une charte en cours de saisie : repères fictifs, ou le motif du refus. Rien n'est écrit."""
        from genvar import charte
        try:
            c = charte.controler(d.get("charte"))
        except RegleMetier as e:
            return {"erreur": str(e)}
        from genvar.standards import AVIS_CHARTE_CLIENT
        return {"exemple": charte.exemple(c), "description": charte.decrire(c), "ogias": charte.est_ogias(c),
                "avis": "" if charte.est_ogias(c) else AVIS_CHARTE_CLIENT}

    def appliquer_standard(self, d):
        """Appliquer un standard (ou la nouvelle version du sien) à l'ouvrage ouvert, sur demande explicite (19/11).
        Sans « confirme » : aperçu seulement, rien n'est écrit. Les adresses validées ne bougent jamais."""
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        from genvar import standards
        choisi = standards.trouver(str(d.get("ident") or ""))
        if choisi is None or choisi.get("statut") != "actif":
            raise RegleMetier("Standard d'ingénierie introuvable ou archivé : choisissez-en un autre.")
        # Changer la charte d'un ouvrage déjà équipé changerait tous ses repères et noms : refusé (19/11).
        from genvar import charte
        if _charte_client(choisi) != charte.de_ouvrage(self.s.ouvrage) and (self.s.ouvrage.equipements or self.s.ouvrage.existantes):
            raise RegleMetier(f"« {choisi['nom']} » emploie une autre charte de nommage que cet ouvrage : appliquée à un "
                              "ouvrage déjà équipé, elle changerait tous ses repères et noms. Rien n'a été modifié.")
        changements = standards.ecarts(self.s.ouvrage, choisi["briques"])
        if d.get("confirme") is not True:
            return {"apercu": changements, "nom": choisi["nom"], "version": choisi["version"]}
        alertes = standards.appliquer(self.s, choisi)
        self.s.modifie = True
        self._sauver()
        return {"applique": changements, "alertes": alertes, "nom": choisi["nom"], "version": choisi["version"]}

    def outils_action(self, d):
        """Choisir la supervision et l'IHM de l'ouvrage, parmi les listes du référentiel (« » : aucune)."""
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        listes = ref_ident.lire()
        o = self.s.ouvrage
        for champ, liste in (("supervision", "supervisions"), ("ihm", "ihm")):
            if champ not in d:
                continue
            valeur = str(d.get(champ) or "").strip()
            if valeur and valeur not in listes[liste] and valeur != getattr(o, champ):
                raise RegleMetier(f"{'Supervision' if champ == 'supervision' else 'IHM'} absente du référentiel : "
                                  "ajoutez-la d'abord par « Gérer les listes ».")
            setattr(o, champ, valeur)
        self.s.modifie = True
        self._sauver()
        return self.outils_web({})

    def reglages_sources(self, _):
        """Ouvrages enregistrés dont on peut reprendre les outils et conventions (hors ouvrage ouvert, illisibles exclus)."""
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        return {"ouvrages": [{"chemin": f.chemin, "repere": f.repere, "libelle": f.libelle, "automate": f.automate}
                             for f in projets.lister() if not f.erreur and f.chemin != (self.s.chemin or "")]}

    def reprendre_reglages(self, d):
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        chemin = str(d.get("chemin") or "")
        autorises = {f.chemin for f in projets.lister() if not f.erreur}
        if chemin not in autorises or chemin == (self.s.chemin or ""):
            raise RegleMetier("Choisissez un autre ouvrage enregistré.")
        from genvar.modele import Ouvrage
        r = self.s.reprendre_reglages(Ouvrage.ouvrir(chemin))
        self._sauver()
        return r

    def regles_web(self, _):
        """Catalogue des règles de cohérence nommées (lecture seule, sans ouvrage ouvert)."""
        from genvar.coherence import REGLES, decrire
        return {"regles": [decrire(c) for c in REGLES]}

    def recette_web(self, _):
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        o = self.s.ouvrage
        controles = []
        # Orientation du 18/11 : chaque contrôle porte sa règle nommée (genvar/coherence.py) ; « regle_detail » donne
        # son titre, la raison et la façon de corriger. « code » reste l'étape pour les anciens appelants.
        from genvar.coherence import decrire
        def ajouter(etape, niveau, texte, ident="", regle=""):
            controles.append({"code": etape, "etape": etape, "niveau": niveau, "message": texte, "ident": ident,
                              "regle": regle, "regle_detail": decrire(regle)})
        if not (o.lieu and o.code_ouvrage and o.libelle):
            ajouter("Ouvrage", "Erreur", "Identification de l'ouvrage incomplète.", regle="R-OUV-01")
        for e in o.equipements:
            if not e.valide:
                ajouter("Équipements", "Erreur", f"{o.repere(e)} : paramétrage non validé.", e.ident, "R-EQ-01")
        if not o.equipements:
            ajouter("Équipements", "Alerte", "Inventaire sans équipement.", regle="R-EQ-02")
        for a in self.s.anomalies_existant() if o.mode == "Existant" else self.s.anomalies():
            ajouter(getattr(a, "etape", "") or "Équipements", a.niveau, f"{a.repere} : {a.message}", a.ident_eq,
                    getattr(a, "code", ""))
        for a in self.s.anomalies_homonymes():           # P8 / R9 : autres ouvrages du même programme automate
            ajouter(a.etape, a.niveau, f"{a.repere} : {a.message}", a.ident_eq, getattr(a, "code", ""))
        if o.mode == "Neuf":
            # Adresses de variables manquantes : déjà signalées par les contrôles (« pas d'adresse »).
            # Les E/S ne sont accessibles qu'après validation de l'inventaire.
            if o.equipements and all(e.valide for e in o.equipements):
                for pt in self.s.points():
                    if pt.raccordement != "Communication" and not pt.adresse:
                        ajouter("Liste des E/S et matériel", "Erreur", f"Voie E/S non renseignée : {pt.nom}", pt.ident_eq,
                                "R-ES-10")
        ordre = {"Ouvrage": 0, "Équipements": 1, "Liste des E/S et matériel": 2, "Variables": 3}
        controles.sort(key=lambda x: (ordre.get(x["etape"], 9), x["niveau"] != "Erreur"))
        erreurs = sum(x["niveau"] == "Erreur" for x in controles)
        alertes = sum(x["niveau"] == "Alerte" for x in controles)
        # 18/11 : synthèse par règle, calculée sur TOUS les constats (avant la limite d'affichage de 500)
        par_regle: dict[tuple[str, str], dict] = {}
        for x in controles:
            g = par_regle.setdefault((x["regle"], x["niveau"]), {"regle": x["regle"], "niveau": x["niveau"],
                                     "etape": x["etape"], "nombre": 0, "exemple": x["message"], "detail": x["regle_detail"]})
            g["nombre"] += 1
        return {"erreurs": erreurs, "alertes": alertes, "controles": controles[:500],
                "par_regle": sorted(par_regle.values(), key=lambda g: (g["niveau"] != "Erreur", -g["nombre"], g["regle"])),
                "tronque": len(controles) > 500, "revision": o.revision,
                "livrables": self._etat_livrables(erreurs),
                "export_qualifie": False,
                "note": "La recette OGIAS est un contrôle interne. Aucun export n'est déclaré industriellement qualifié sans essai réel dans les logiciels cibles."}

    def _etat_livrables(self, erreurs_recette):
        """Retour du 16/11 (16 h 32) : pour chaque livrable de la Recette, prêt ou non et pourquoi — mêmes
        conditions que l'export lui-même, sans rien produire. Un livrable dont le format n'est pas décrit dans
        OGIAS est « non disponible », jamais simulé."""
        o = self.s.ouvrage
        etat: dict[str, Any] = {}
        neuf = o.mode == "Neuf"
        try:
            from genvar import materiel as mat
            gamme = mat.gamme(o.automate) or ""
        except Exception:                                   # noqa: BLE001 — affichage seulement
            gamme = ""

        def poser(code, motif=""):
            etat[code] = {"pret": not motif, "motif": motif}
        pts = self.s.points() if o.equipements else []
        cables = [p for p in pts if p.raccordement != "Communication"]
        err_mat = self.s.erreurs_materiel() if o.modules else []
        variables = self.s.variables() if o.equipements and neuf else []
        ce = gamme in ("M340", "M580")
        es_motif = ("Projet existant : le programme en place n'est jamais réécrit." if not neuf
                    else f"Format Control Expert : source M340 ou M580 requise (source : {o.automate or 'non renseignée'})." if not ce
                    else "Aucune E/S n'a de voie : implantez-les à l'étape Matériel." if not any(p.adresse for p in cables)
                    else f"{len(err_mat)} incohérence(s) de cartes ou de voies (ex. {err_mat[0]})" if err_mat else "")
        poser("es_xsy", es_motif)
        poser("es_txt", es_motif)
        poser("xsy", "Projet existant : le programme en place n'est jamais réécrit." if not neuf
              else "Format Control Expert : source M340 ou M580 requise." if not ce
              else f"{erreurs_recette} erreur(s) de recette à corriger." if erreurs_recette else "")
        poser("topkapi", "Projet existant : table à rapprocher, pas d'import automatique." if not neuf
              else "Aucune variable." if not variables else "")
        poser("tele_etudes", "Aucune variable de télétransmission." if not variables else "")
        poser("es_cartes", "Aucune carte d'E/S : calculez le matériel." if not o.modules
              else f"{len(err_mat)} incohérence(s) de cartes ou de voies." if err_mat else "")
        poser("liste_es", "" if cables else "Aucune E/S câblée.")
        poser("cartes", "" if o.modules else "Aucune carte d'E/S : calculez le matériel.")
        poser("variables", "" if o.equipements or o.existantes else "Aucune variable.")
        poser("nomenclature", "" if o.racks or o.modules else "Matériel non calculé.")
        etat["sofrel_configure"] = gamme == "S4W"
        etat["gamme"] = gamme
        return etat

    def numero_libre(self, q):
        o = self.s.ouvrage
        pris = {e.numero for e in o.equipements
                if e.type == q.get("type") and (not o.se_dans_repere() or e.sous_ensemble == q.get("se"))}
        return {"numero": next((f"{n:02d}" for n in range(1, 100) if f"{n:02d}" not in pris), "")}

    def numero_ouvrage_suggere(self, q):
        """Proposer un numéro sans jamais réutiliser un indice déjà attribué.

        Ce n'est qu'une suggestion : l'unicité est revérifiée à l'enregistrement.
        Les projets archivés et brouillons numérotés réservent aussi leur indice.
        """
        lieu = str(q.get("lieu", "")).strip().upper()
        typ = str(q.get("type", "")).strip().upper()
        c = self._charte_cible(q)
        if not charte.conforme(charte.motif(c, "lieu"), lieu) or not charte.conforme(charte.motif(c, "code_ouvrage"), typ):
            return {"numero": "", "disponible": False}
        # Même lieu et même type, quelle que soit la charte de l'ouvrage existant (19/11).
        existants = [int(f.numero_ouvrage) for f in projets.lister()
                     if not f.erreur and f.lieu == lieu and f.code_ouvrage == typ and f.numero_ouvrage.isdigit()]
        n = charte.longueur_numero(c)
        numero = max(existants, default=0) + 1
        return {"numero": str(numero).zfill(n) if numero < 10 ** n else "", "disponible": numero < 10 ** n}

    def _charte_cible(self, d=None):
        """Charte qui s'applique à l'identification : celle de l'ouvrage ; pour un ouvrage en création, celle du
        standard choisi. None : charte OGIAS (motifs et messages d'avant)."""
        o = self.s.ouvrage
        if o.standard:
            return o.charte_client()
        if self.creation_en_attente or o.statut == "Brouillon":
            from genvar import standards
            try:
                return _charte_client(standards.trouver(str((d or {}).get("standard") or standards.IDENT_INITIAL)))
            except ValueError:
                return None
        return None

    # ------------------------------------------------------------------ actions
    def nouveau(self, d):
        self._clear_inbound()
        self._liberer_verrou()
        self.s.nouveau(lieu_dans_le_nom=(d.get("mode") == "Existant"))   # règle R2 : sans lieu en projet neuf
        self.s.definir("mode", d.get("mode", "Neuf"))
        self.s.definir("automate", "")  # aucun matériel supposé pour un nouvel ouvrage
        self.ouvert = True
        self.creation_en_attente = True
        return {}

    def ouvrir(self, d):
        from genvar import verrou
        self._clear_inbound()
        ch = os.path.abspath(str(d["chemin"]))
        verrou.prendre(ch, self.jeton, forcer=bool(d.get("forcer")))    # VerrouPris : ouvert par un autre OGIAS
        try:
            self.s.ouvrir(d["chemin"])
        except Exception:
            if ch != self.chemin_verrouille:
                verrou.liberer(ch, self.jeton)
            raise
        if ch != self.chemin_verrouille:
            self._liberer_verrou()
            self.chemin_verrouille = ch
        evenement("Ouvrage ouvert" + (" après reprise explicite du verrou d'un autre poste" if d.get("forcer") else "")
                  + f" (mode {self.s.ouvrage.mode}).")
        self.ouvert = True
        self.creation_en_attente = False
        return {}

    def fermer(self, _):
        self._clear_inbound()
        if self.ouvert:
            evenement("Ouvrage fermé.")
        self._liberer_verrou()
        self.ouvert = False
        self.creation_en_attente = False
        self.s.nouveau()
        return {}

    def supprimer_ouvrage(self, d):
        # Seul un ouvrage de « Mes ouvrages » peut aller à la corbeille : jamais un fichier quelconque du disque.
        connus = {os.path.realpath(f.chemin) for f in projets.lister()}
        if os.path.realpath(str(d.get("chemin", ""))) not in connus:
            raise RegleMetier("Ce fichier n'est pas un ouvrage de « Mes ouvrages » : rien n'a été déplacé.")
        from genvar import verrou
        autre = verrou.detenu_par_autre(os.path.abspath(str(d["chemin"])), self.jeton)
        if autre is not None:
            raise RegleMetier(f"Ouvrage ouvert par {verrou.description(autre)} : il ne peut pas aller à la corbeille.")
        if self.s.chemin and os.path.abspath(self.s.chemin) == os.path.abspath(d["chemin"]):
            self.ouvert = False
            self.creation_en_attente = False
            self.s.nouveau()
        projets.supprimer(d["chemin"])
        return {}

    def fiche_ouvrage(self, d):
        """Enregistrer la fiche UNIQUEMENT sur acte utilisateur explicite.

        Validation avant mutation, puis persistance atomique du projet. Le statut
        « En cours » signifie création administrative, PAS validation technique.
        """
        if not self.ouvert:
            raise RegleMetier("Aucun ouvrage ouvert.")
        action = d.get("action")
        if action not in ("brouillon", "creer", "modifier"):
            raise RegleMetier("Action de la fiche inconnue.")
        conception = self.creation_en_attente or self.s.ouvrage.statut == "Brouillon"
        if action == "creer" and not conception:
            raise RegleMetier("Cet ouvrage existe déjà : utilisez Enregistrer les modifications.")
        if action == "modifier" and conception:
            raise RegleMetier("Confirmez d'abord la création de cet ouvrage.")
        champs = d.get("identification")
        if not isinstance(champs, dict):
            raise RegleMetier("Identification de l'ouvrage manquante.")
        ancien = self.s.ouvrage
        liste = ref_ident.lire()
        lieu = str(champs.get("lieu", "")).strip().upper()
        code = str(champs.get("code_ouvrage", "")).strip().upper()
        numero = str(champs.get("numero_ouvrage", "")).strip()
        libelle = str(champs.get("libelle", "")).strip()
        automate = str(champs.get("automate", "")).strip()
        localisation = str(champs.get("localisation", "")).strip()
        revision = str(champs.get("revision", "A")).strip().upper()
        communication = str(champs.get("communication", "")).strip()
        types = {x["code"]: x["libelle"] for x in liste["types_ouvrage"]}
        lieux = {x["code"] for x in liste["lieux"]}
        c = self._charte_cible(d)                    # None : charte OGIAS, messages d'avant inchangés
        if lieu and not charte.conforme(charte.motif(c, "lieu"), lieu):
            raise RegleMetier("Sélectionnez un lieu avec un code de 4 caractères." if c is None else
                              f"Lieu selon la charte du standard : {charte.consigne(c, 'lieu')}.")
        if numero and not charte.conforme(charte.motif(c, "numero_ouvrage"), numero):
            raise RegleMetier("Le numéro d’ouvrage doit être compris entre 01 et 99 (deux chiffres)." if c is None else
                              f"Numéro d'ouvrage selon la charte du standard : {charte.consigne(c, 'numero_ouvrage')}.")
        if code and not charte.conforme(charte.motif(c, "code_ouvrage"), code):
            raise RegleMetier("Sélectionnez un type d'ouvrage (code de 2 lettres)." if c is None else
                              f"Type d'ouvrage selon la charte du standard : {charte.consigne(c, 'code_ouvrage')}.")
        # Ne jamais rendre illisible un ouvrage historique dont une valeur a
        # disparu entre-temps du référentiel utilisateur.
        if lieu and lieu not in lieux and not (self.s.chemin and lieu == ancien.lieu):
            raise RegleMetier("Lieu absent du référentiel.")
        if code and code not in types and not (self.s.chemin and code == ancien.code_ouvrage):
            raise RegleMetier("Code ouvrage absent du référentiel.")
        if automate and automate not in liste["automates"] and not (self.s.chemin and automate == ancien.automate):
            raise RegleMetier("Automate absent du référentiel.")
        protocoles = [x.strip() for x in communication.split(",") if x.strip()]
        if len(protocoles) != len(set(protocoles)):
            raise RegleMetier("Un protocole est renseigné plusieurs fois.")
        if any(x not in liste["protocoles"] for x in protocoles) and not (self.s.chemin and communication == ancien.communication):
            raise RegleMetier("Un protocole est absent du référentiel.")
        if len(libelle) > 150 or len(localisation) > 250:
            raise RegleMetier("Libellé ou localisation trop long.")
        if not charte.conforme(charte.REVISION, revision):
            raise RegleMetier("Révision invalide : 1 à 4 caractères (lettres/chiffres).")
        if action == "creer" and (not lieu or not code or not numero or not libelle):
            raise RegleMetier("Pour créer l'ouvrage, renseignez le lieu, le type d'ouvrage et le libellé.")
        if action == "modifier" and ancien.statut != "Brouillon" and (not lieu or not code or not libelle or (ancien.numero_ouvrage and not numero)):
            raise RegleMetier("L'identification d'un ouvrage créé doit rester complète.")
        changement_code = (lieu, code, numero) != (ancien.lieu, ancien.code_ouvrage, ancien.numero_ouvrage)
        if changement_code and ancien.equipements and not d.get("confirmer_changement"):
            raise RegleMetier("Le nouveau code changerait les repères des équipements : confirmation requise.")
        # Unicité stricte sur le code COMPLET. Les archives réservent le numéro.
        # Un ancien ouvrage à préfixe de 6 caractères reste inchangé (migration explicite).
        # 19/11 : repère selon la charte ; un même lieu + type + numéro reste réservé quelle que soit la charte.
        from types import SimpleNamespace
        identifiant = (charte.prefixe(c, SimpleNamespace(lieu=lieu, code_ouvrage=code, numero_ouvrage=numero))
                       if c is not None else lieu + code + numero)
        if action != "brouillon" and lieu and code:
            for fiche in projets.lister():
                if fiche.chemin == (self.s.chemin or "") or fiche.erreur:
                    continue
                if fiche.repere == identifiant or (numero and (fiche.lieu, fiche.code_ouvrage, fiche.numero_ouvrage) == (lieu, code, numero)):
                    raise RegleMetier("Un ouvrage utilise déjà le code " + (fiche.repere or identifiant) +
                                     ". Choisissez un autre numéro ou ouvrez l’ouvrage existant.")
        # Construire une copie : échec de validation => original inchangé.
        nouveau = copy.deepcopy(ancien)
        changements = {"lieu": lieu, "code_ouvrage": code, "numero_ouvrage": numero, "libelle": libelle,
                       "type_ouvrage": types.get(code, ancien.type_ouvrage if code == ancien.code_ouvrage else ""),
                       "automate": automate, "localisation": localisation,
                       "communication": communication, "revision": revision}
        chemin_initial, modifie_initial = self.s.chemin, self.s.modifie
        self.s.ouvrage = nouveau
        try:
            for champ, valeur in changements.items():
                self.s.definir(champ, valeur)
            if action == "brouillon":
                self.s.definir("statut", "Brouillon")
            elif action == "creer":
                self.s.definir("statut", "En cours")
                if conception and not nouveau.standard:          # jamais sur un ouvrage déjà créé
                    # 19/11 : réglages du standard d'ingénierie choisi, copiés une fois pour toutes à la création
                    from genvar import standards
                    choisi = standards.trouver(str(d.get("standard") or standards.IDENT_INITIAL))
                    if choisi is None or choisi.get("statut") != "actif":
                        raise RegleMetier("Standard d'ingénierie introuvable ou archivé : choisissez-en un autre.")
                    standards.appliquer(self.s, choisi)
            if action == "creer" and conception:
                cible = str(projets.nom_libre(identifiant, projets.repertoire()))
            elif chemin_initial:
                cible = chemin_initial
            else:
                cible = str(projets.nom_libre("Brouillon_" + nouveau.ident_projet[:8], projets.repertoire()))
            self.s.enregistrer(cible)
        except Exception:
            self.s.ouvrage, self.s.chemin, self.s.modifie = ancien, chemin_initial, modifie_initial
            raise
        self.creation_en_attente = False
        if action == "creer":
            evenement("Ouvrage créé.")
        # Conversion brouillon -> ouvrage : l'ancien fichier reste récupérable en corbeille.
        if action == "creer" and chemin_initial and chemin_initial != self.s.chemin:
            projets.supprimer(chemin_initial)
        return {"chemin": self.s.chemin, "statut": self.s.ouvrage.statut,
                "creation_confirmee": action == "creer"}

    def definir(self, d):
        champ = d["champ"]
        if champ not in ("lieu", "code_ouvrage", "numero_ouvrage", "libelle", "automate", "type_ouvrage", "localisation",
                         "communication", "revision"):
            raise RegleMetier("Champ non modifiable.")
        valeur = str(d.get("valeur", "")).strip()
        c = self._charte_cible()
        if c is None:                                 # charte OGIAS : saisie d'avant, écart connu compris
            motifs = {"lieu": charte.LIEU_SAISIE, "code_ouvrage": charte.CODE_OUVRAGE_SAISIE, "numero_ouvrage": charte.NUMERO_OUVRAGE}
            messages = {"lieu": "Le lieu fait 4 caractères (lettres ou chiffres), ex. ATMS.",
                        "code_ouvrage": "Le code ouvrage fait 2 caractères, ex. RV.", "numero_ouvrage": "Numéro d’ouvrage invalide : 01 à 99."}
        else:
            motifs = {k: charte.motif(c, k) for k in ("lieu", "code_ouvrage", "numero_ouvrage")}
            messages = {k: f"Selon la charte de l'ouvrage : {charte.consigne(c, k)}." for k in motifs}
        if champ in motifs and valeur and not charte.conforme(motifs[champ], valeur):
            raise RegleMetier(messages[champ])
        self.s.definir(champ, valeur)
        self._sauver()
        return {}

    def uf(self, d):
        a = d.get("action")
        if a == "ajouter":
            self.s.ajouter_uf(d["code"], d.get("libelle", ""), d.get("se", ""))
        elif a == "modifier":
            self.s.modifier_uf(d["code"], d.get("nouveau_code") or d["code"], d.get("libelle", ""), d.get("se") or None)
        elif a == "supprimer":
            self.s.supprimer_uf(d["code"])
        elif a == "renommer_communs":
            self.s.renommer_communs(d.get("libelle", ""))
        else:
            raise RegleMetier("Action inconnue.")
        self._sauver()
        return {}

    def _equipement_depuis(self, d, base=None):
        se = (d.get("se") or "").strip().upper()
        if not se and self.s.ouvrage.format_repere == "12":
            se = "00"                                   # charte ESB/RESO : le sous-ensemble n'entre pas dans le repère
        if not charte.conforme(charte.SOUS_ENSEMBLE, se):
            raise RegleMetier("Sous-ensemble : 2 caractères (ex. 11, E0, P1).")
        if se not in {x.code for x in self.s.ouvrage.sous_ensembles}:
            self.s.ajouter_sous_ensemble(se, "")
        e = Equipement(se, d.get("type", ""), (d.get("numero") or "").zfill(2), (d.get("libelle") or "")[:32],
                       uf=d.get("uf", ""), modele=d.get("modele", ""), local=d.get("local", ""))
        if base is not None:
            for k in ("options", "exclus", "ajouts", "adresses", "adresses_es", "commentaires", "libelles",
                      "validees", "acceptes", "motifs", "traces", "es_meta"):
                setattr(e, k, getattr(base, k))
        return e

    def ajouter_equipement(self, d):
        if not (self.s.ouvrage.lieu and self.s.ouvrage.code_ouvrage):
            raise RegleMetier("Renseignez d'abord le lieu et le code de l'ouvrage (identification).")
        e = self.s.ajouter_equipement(self._equipement_depuis(d))
        self._sauver()
        return {"ident": e.ident}

    def ajouter_equipements_serie(self, d):
        """V1-5-05 : n équipements d'un même type aux numéros libres suivants (tout ou rien)."""
        if not (self.s.ouvrage.lieu and self.s.ouvrage.code_ouvrage):
            raise RegleMetier("Renseignez d'abord le lieu et le code de l'ouvrage (identification).")
        try:
            quantite = int(d.get("quantite"))
            depart = int(d["depart"]) if str(d.get("depart") or "").strip() else None
        except (TypeError, ValueError) as exc:
            raise RegleMetier("Quantité et numéro de départ : des nombres entiers.") from exc
        modele = self._equipement_depuis({**d, "numero": "01"})
        crees = self.s.ajouter_equipements_en_serie(modele, quantite, depart)
        self._sauver()
        return {"idents": [e.ident for e in crees], "reperes": [self.s.ouvrage.repere(e) for e in crees]}

    def modifier_equipement(self, d):
        base = self._eq(d["ident"])
        self.s.remplacer_equipement(base.ident, self._equipement_depuis(d, base))
        self._sauver()
        return {"ident": base.ident}

    def ordre_export_web(self, q):
        """V1-5-02 (option B) : variables de l'équipement dans l'ordre d'export ; cet ordre ne touche aucune adresse."""
        eq = self._eq(str((q or {}).get("ident") or ""))
        return {"variables": self.s.ordre_export_equipement(eq.ident), "personnalise": bool(eq.ordre_export),
                "repere": self.s.ouvrage.repere(eq)}

    def definir_ordre_export(self, d):
        eq = self._eq(str(d.get("ident") or ""))
        self.s.definir_ordre_export(eq.ident, d.get("cles") or [])
        self._sauver()
        return self.ordre_export_web({"ident": eq.ident})

    def dupliquer_equipement(self, d):
        """V1-5-01 : copie de l'équipement au numéro libre suivant (ou au numéro demandé), sans aucune adresse."""
        copie = self.s.copie_pour_duplication(self._eq(str(d.get("ident") or "")).ident)
        if d.get("numero"):
            copie.numero = str(d["numero"]).strip()
        self.s.ajouter_equipement(copie)
        self._sauver()
        return {"ident": copie.ident, "repere": self.s.ouvrage.repere(copie)}

    def supprimer_equipements(self, d):
        for i in d.get("idents", []):
            self.s.supprimer_equipement(i)
        self._sauver()
        return {}

    # ------------------------------------------------------------------ référentiel : cycle unique (brouillon → publication)
    def _depot(self):
        from genvar.referentiel_depot import Depot
        return Depot()

    def referentiel_cycle(self, _):
        """État de la révision publiée et du brouillon, avec ses contrôles et ses différences."""
        from genvar.referentiel_depot import DepotRefuse
        depot = self._depot()
        e = depot.etat()
        e["revisions"] = depot.revisions()
        e["brouillons_supprimes"] = depot.brouillons_supprimes()
        if e["brouillon"]:
            try:
                e["controles"] = depot.controler()
                e["differences"] = depot.differences()
            except DepotRefuse as exc:
                e["controles"], e["differences"] = {"erreurs": [str(exc)], "alertes": []}, []
        return e

    def referentiel_vue(self, q):
        """Contenu affiché par l'écran Référentiel : révision publiée, ou brouillon avec ses changements marqués."""
        from genvar.referentiel_depot import vue
        depot = self._depot()
        b = depot.brouillon()
        if q.get("source") == "brouillon" and b is not None:
            v = vue(b["donnees"], depot.publie())
            v["source"] = "brouillon"
        else:
            v = vue(depot.publie())
            v["source"] = "publie"
        from genvar import modeles
        v.update(roles=list(modeles.ROLES), formats=list(modeles.FORMATS), domaines=list(modeles.DOMAINES))
        return v

    def referentiel_cycle_action(self, d):
        from genvar.referentiel_depot import DepotRefuse, editer
        from genvar.referentiel_excel import ReferentielInvalide
        depot, a = self._depot(), d.get("action")
        try:
            if a == "creer_brouillon":
                depot.creer_brouillon(d.get("auteur", ""))
            elif a == "abandonner":
                return {"copie": depot.abandonner()}
            elif a == "recuperer_brouillon":
                depot.recuperer_brouillon(d.get("nom", ""))
            elif a == "restaurer":
                depot.restaurer_en_brouillon(int(d["numero"]), d.get("auteur", ""))
            elif a == "editer":
                b = depot.brouillon()
                if b is None:
                    raise RegleMetier("Référentiel en lecture seule : créez d'abord un brouillon.")
                donnees, libelle = editer(b["donnees"], d.get("modification", ""), d.get("cible", ""), d.get("champs") or {})
                depot.remplacer_donnees(donnees, libelle)
            elif a == "importer_apercu":
                nom = os.path.basename(d.get("nom") or "")
                if not nom.lower().endswith(".xlsx"):
                    raise RegleMetier("Choisissez un classeur .xlsx exporté depuis OGIAS.")
                return self.s.analyser_classeur_referentiel(self._fichier_temporaire(d))
            elif a == "importer_appliquer":
                self.s.integrer_classeur_referentiel(d.get("empreinte", ""))
            elif a == "valider":
                b = depot.valider(d.get("auteur", ""))
                return {"empreinte_validee": b["empreinte_validee"]}
            elif a == "publier":
                r = depot.publier(d.get("motif", ""), d.get("empreinte", ""), d.get("auteur", ""))
                self.s._recharger_referentiel()
                return r
            else:
                raise RegleMetier("Action du référentiel inconnue.")
        except (DepotRefuse, ReferentielInvalide, KeyError, ValueError) as exc:
            raise RegleMetier(str(exc)) from exc
        return {}

    def _empreinte_adoption(self):
        from genvar.referentiel_depot import empreinte
        def catalogue(c):
            return {"types": c.types, "signaux": c.signaux, "regles": c.regles, "version": c.version}
        return empreinte({"ouvrage": self.s.ouvrage.vers_dict(), "chemin": self.s.chemin,
                          "ancien": catalogue(self.s.catalogue), "nouveau": catalogue(self.s._catalogue_commun),
                          "correspondances": self.s.modeles.get("correspondances", [])})

    def rapport_impact(self, _):
        """R5 : impact du brouillon du référentiel sur les ouvrages enregistrés (lecture seule)."""
        return self.s.rapport_impact()

    def synchronisation_referentiel(self, _):
        """R2 / R3 : version de chaque profil utilisé et état de synchronisation des équipements (lecture seule)."""
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        return self.s.synchronisation()

    def _apercu_adoption_interface(self):
        """Noms de chaque équipement issus des catalogues effectifs, modèles figés compris."""
        from genvar import adoption
        from genvar.modele import catalogue_pour_equipement
        apercu = self.s.apercu_adoption()
        o = self.s.ouvrage
        for type_ in apercu:
            details = []
            cible = adoption.catalogue_fusionne(self.s.catalogue, self.s._catalogue_commun,
                                                [type_["type"]], {e.type for e in o.equipements})
            for eq in o.equipements:
                if eq.type != type_["type"]:
                    continue
                fige = "signaux" in o.modeles_snapshot.get(eq.modele, {})
                ancien = catalogue_pour_equipement(o, self.s.catalogue, eq)
                nouveau = catalogue_pour_equipement(o, cible, eq)
                a = {f"{s['famille']}_{s['code']}": s for s in ancien.signaux_du_type(eq.type)}
                b = {f"{s['famille']}_{s['code']}": s for s in nouveau.signaux_du_type(eq.type)}
                changements = []
                for r in type_["renommages"]:
                    # Le catalogue global n'adopte pas les signaux propres d'un modèle figé.
                    if fige and r["ancienne"] != r["nouvelle"]:
                        motif = f"Modèle figé {eq.modele} : migration de clé dédiée nécessaire."
                        if motif not in type_["bloquants"]:
                            type_["bloquants"].append(motif)
                        type_["adoptable"] = False
                        continue
                    if r["ancienne"] not in a or r["nouvelle"] not in b:
                        continue
                    avant = [n.replace("<repère>", o.repere_nom(eq)) for n in adoption.noms(a[r["ancienne"]])]
                    apres = [n.replace("<repère>", o.repere_nom(eq)) for n in adoption.noms(b[r["nouvelle"]])]
                    if avant == apres:
                        continue
                    changements.append({"id": f"{eq.ident}:{r['ancienne']}:{r['nouvelle']}",
                                         "ancienne": r["ancienne"], "nouvelle": r["nouvelle"],
                                         "physique": [avant[0], apres[0]], "fonctionnel": [avant[1], apres[1]],
                                         "adresse": eq.adresses.get(r["ancienne"], ""),
                                         "adresse_es": eq.adresses_es.get(r["ancienne"], "")})
                details.append({"ident": eq.ident, "repere": o.repere(eq), "modele": eq.modele,
                                "modele_fige": fige, "renommages": changements,
                                "modifiees": sorted(k for k in set(a) & set(b) if a[k] != b[k]),
                                "ajoutees": sorted(set(b) - set(a)), "retirees": sorted(set(a) - set(b))})
            type_["details_equipements"] = details
        return apercu

    def adopter_referentiel(self, d):
        """Adoption type par type ; un type qui renomme des variables exige la confirmation explicite."""
        d = d or {}
        if d.get("empreinte") is not None and d["empreinte"] != self._empreinte_adoption():
            raise RegleMetier("L'ouvrage ou le référentiel a changé. Fermez puis rouvrez l'aperçu d'adoption.")
        apercu = self._apercu_adoption_interface()
        choisis = d.get("types")
        if choisis is not None and (not isinstance(choisis, list) or not all(isinstance(t, str) for t in choisis)):
            raise RegleMetier("Les types à adopter doivent être une liste de codes.")
        selection = choisis if choisis is not None else [t["type"] for t in apercu if t["adoptable"] and not t["renommages"]]
        for t in apercu:
            if t["type"] in selection and not t["adoptable"]:
                raise RegleMetier(t["bloquants"][0])
        if "confirmations" in d:
            attendues = {r["id"] for t in apercu if t["type"] in (choisis or [])
                         for e in t["details_equipements"] for r in e["renommages"]}
            if (not isinstance(d["confirmations"], list) or not all(isinstance(c, str) for c in d["confirmations"])
                    or not attendues <= set(d["confirmations"])):
                raise RegleMetier("Confirmez chaque renommage des équipements des types cochés.")
        if selection and (self.creation_en_attente or not self.s.chemin or not os.path.isfile(self.s.chemin)):
            raise RegleMetier("Enregistrez l'ouvrage avant l'adoption pour disposer d'une sauvegarde.")
        ecarts = self.s.adopter_referentiel(d.get("types"), d.get("renommages_confirmes") is True)
        if ecarts:
            self._sauver()
        return {"types": [x["type"] for x in ecarts], "sauvegarde": getattr(self.s, "sauvegarde_adoption", "")}

    def apercu_modele(self, q):
        """Aperçu de la reprise contrôlée d'un modèle figé (lecture seule)."""
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        nom = (q or {}).get("nom")
        if not isinstance(nom, str) or nom not in self.s.ouvrage.modeles_snapshot:
            raise RegleMetier("Modèle figé inconnu dans cet ouvrage.")
        return self.s.apercu_modele(nom)

    def adopter_modele(self, d):
        """Reprise contrôlée d'un modèle figé, après sauvegarde ; renommages confirmés explicitement."""
        d = d or {}
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        nom = d.get("nom")
        if not isinstance(nom, str) or nom not in self.s.ouvrage.modeles_snapshot:
            raise RegleMetier("Modèle figé inconnu dans cet ouvrage.")
        if self.creation_en_attente or not self.s.chemin or not os.path.isfile(self.s.chemin):
            raise RegleMetier("Enregistrez l'ouvrage avant l'adoption pour disposer d'une sauvegarde.")
        self.s.adopter_modele(nom, d.get("renommages_confirmes") is True)
        self._sauver()
        return {"sauvegarde": os.path.basename(self.s.sauvegarde_adoption)}

    def apercu_propagation(self, _):
        """R6 : aperçu de l'acceptation en un geste (lecture seule)."""
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        return self.s.apercu_propagation()

    def accepter_propagation(self, d):
        """R6 : acceptation en un geste de l'aperçu affiché (empreinte exigée), après sauvegarde du fichier."""
        d = d or {}
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        if not isinstance(d.get("empreinte"), str):
            raise RegleMetier("Aperçu manquant : affichez l'aperçu avant d'accepter.")
        if self.creation_en_attente or not self.s.chemin or not os.path.isfile(self.s.chemin):
            raise RegleMetier("Enregistrez l'ouvrage avant l'adoption pour disposer d'une sauvegarde.")
        ecarts = self.s.accepter_propagation(d["empreinte"])
        self._sauver()
        return {"types": [x["type"] for x in ecarts], "sauvegarde": os.path.basename(self.s.sauvegarde_adoption)}

    def refuser_mise_a_jour(self, d):
        """R7 : refus motivé et tracé de la mise à jour de profils ; rien n'est adopté."""
        d = d or {}
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        types = d.get("types")
        if not isinstance(types, list) or not all(isinstance(t, str) for t in types) or not types:
            raise RegleMetier("Les types refusés doivent être une liste de codes.")
        self.s.refuser_mise_a_jour(types, d.get("motif") if isinstance(d.get("motif"), str) else "")
        self._sauver()
        return {"journal": self.s.ouvrage.journal_referentiel[-50:]}

    def revenir_au_standard(self, d):
        """R4 : retirer une surcharge locale (une propriété), après confirmation explicite (`confirme`: true)."""
        d = d or {}
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        for k in ("ident_eq", "cle", "propriete"):
            if not isinstance(d.get(k), str):
                raise RegleMetier(f"Paramètre « {k} » manquant.")
        self.s.revenir_au_standard(d["ident_eq"], d["cle"], d["propriete"], d.get("confirme") is True)
        self._sauver()
        return {}

    def annuler_adoption(self, _):
        self.s.annuler_adoption(enregistrer=True)
        return {}

    def copies_ouvrage(self, _):
        """V1-7-03 : copies horodatées de l'ouvrage ouvert, la plus récente d'abord (lecture seule)."""
        if not self.ouvert:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        return {"copies": self.s.copies_horodatees()}

    def restaurer_copie(self, d):
        """V1-7-03 : restaure une copie de CET ouvrage (désignée par son nom seul), après copie de l'état
        courant ; l'enregistrement automatique conserve l'ancien fichier en .bak."""
        d = d or {}
        if not self.ouvert or self.creation_en_attente:
            raise RegleMetier("Ouvrez d'abord un ouvrage.")
        r = self.s.restaurer_copie(d.get("nom"))
        self._sauver()
        return r

    def decider_proposition(self, d):
        """Retenir / écarter (motif obligatoire) / rouvrir une information proposée par une règle."""
        i, dec = d["ident_eq"], d.get("decision", "")
        if d.get("cle"):
            self.s.decider_proposition(i, d["cle"], dec, d.get("motif", ""))
            n = 1
        else:
            n = self.s.decider_propositions(i, dec, d.get("motif", ""), d.get("cles"))
        self._sauver()
        return {"n": n}

    def valider_equipements(self, d):
        n = self.s.valider_equipements(d.get("idents", []), bool(d.get("valide", True)))
        self._sauver()
        return {"n": n}

    def deplacer(self, d):
        self.s.affecter_uf(set(d.get("idents", [])), d.get("uf", ""))
        self._sauver()
        return {}

    def import_inventaire_ancien_desactive(self, d):
        """Interdit l'ancienne API qui permettait l'import partiel non contrôlé.

        Route conservée avec un message JSON explicite pour les anciens clients.
        """
        raise RegleMetier(
            "Ancienne procédure d'import désactivée pour la sécurité des données. "
            "Utilisez la prévisualisation /api/inbound/apercu, puis sa confirmation contrôlée."
        )

    def apercu_inventaire(self, d):
        lignes = self.s.apercu_inventaire(self._fichier_temporaire(d))
        return {"lignes": [l.dict() for l in lignes]}

    def appliquer_inventaire(self, d):
        n = self.s.appliquer_inventaire(d.get("lignes", []))
        self._sauver()
        return {"crees": n}

    def profils_import_web(self, q):
        """V1-5-04 : profils d'import enregistrés (avec les champs associables par nature)."""
        from genvar import profils_import
        return {"profils": profils_import.lister(), "champs": {n: [{"cle": c, "libelle": l, "obligatoire": o} for c, l, o in cs]
                                                                for n, cs in profils_import.CHAMPS.items()}}

    def profils_import_action(self, d):
        """enregistrer / supprimer un profil ; entetes : lignes d'en-tête candidates d'un fichier, pour décrire ses colonnes."""
        from genvar import profils_import
        from genvar.inbound.readers import read_source
        d = d or {}
        action = d.get("action")
        try:
            if action == "enregistrer":
                p = profils_import.enregistrer(d.get("nom"), d.get("nature"), d.get("correspondances"))
                return {**self.profils_import_web({}), "ident": p["ident"]}
            if action == "supprimer":
                profils_import.supprimer(d.get("ident"))
                return self.profils_import_web({})
            if action == "entetes":
                nom = os.path.basename(str(d.get("nom", "")))
                extension = os.path.splitext(nom)[1].lower()
                if extension not in (".csv", ".txt", ".xlsx", ".xlsm", ".ods"):
                    raise RegleMetier("Format accepté : .xlsx, .xlsm, .ods, .csv ou .txt.")
                try:
                    contenu = base64.b64decode(d.get("contenu", ""), validate=True)
                except (ValueError, binascii.Error) as exc:
                    raise RegleMetier("Contenu du fichier invalide.") from exc
                if not contenu or len(contenu) > 15 * 1024 * 1024:
                    raise RegleMetier("Fichier vide ou trop volumineux (15 Mo maximum).")
                dossier = tempfile.mkdtemp(prefix="ogias_profil_")
                try:
                    chemin = os.path.join(dossier, "source" + extension)
                    with open(chemin, "wb") as flux:
                        flux.write(contenu)
                    try:
                        source = read_source(chemin)
                    except InboundError as exc:
                        raise RegleMetier(str(exc)) from exc
                finally:
                    shutil.rmtree(dossier, ignore_errors=True)
                feuilles = [{"nom": t.name, "lignes": [{"index": i, "cellules": [c.strip() for c in r.cells][:40]}
                                                       for i, r in enumerate(t.rows[:15]) if any(c.strip() for c in r.cells)]}
                            for t in source.tables]
                return {"feuilles": feuilles}
        except profils_import.ProfilRefuse as exc:
            raise RegleMetier(str(exc)) from exc
        raise RegleMetier("Action inconnue.")

    def inbound_preview(self, d):
        """Prévisualisation stricte depuis l'UI, sans écriture de projet.

        Un seul aperçu en attente par instance locale. Les aperçus antérieurs sont
        révoqués et leurs copies temporaires sont supprimées.
        """
        self._clear_inbound()
        if not self.ouvert or self.creation_en_attente:
            raise RegleMetier("Créez ou ouvrez un ouvrage avant d'importer des données.")
        try:
            kind = InputKind(d.get("nature", "inventaire"))
        except ValueError as exc:
            raise RegleMetier("Nature d'import inconnue.") from exc
        name = os.path.basename(str(d.get("nom", "")))
        extension = os.path.splitext(name)[1].lower()
        if extension not in (".csv", ".txt", ".xlsx", ".xlsm", ".ods", ".scy"):
            raise RegleMetier("Format non pris en charge par le module Inbound.")
        raw64 = d.get("contenu", "")
        if not isinstance(raw64, str) or len(raw64) > 21_000_000:
            raise RegleMetier("Fichier trop volumineux (limite : 15 Mo).")
        try:
            contents = base64.b64decode(raw64, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise RegleMetier("Contenu du fichier invalide.") from exc
        if not contents or len(contents) > 15 * 1024 * 1024:
            raise RegleMetier("Fichier vide ou trop volumineux (15 Mo maximum).")
        directory = tempfile.mkdtemp(prefix="ogias_inbound_")
        source = os.path.join(directory, "source" + extension)
        try:
            with open(source, "wb") as stream:
                stream.write(contents)
            profil = None
            if d.get("profil"):
                from genvar import profils_import
                profil = profils_import.trouver(d.get("profil"))
                if profil is None or profil["nature"] != kind.value:
                    raise RegleMetier("Profil d'import introuvable pour cette nature.")
            preview = preview_import(source, kind, self.s, profil=profil)
            ticket = uuid.uuid4().hex
            self._inbound_pending = (ticket, preview, directory)
            # Toutes les lignes sont contrôlées ; seules 100 sont transmises par page.
            # Les lignes suivantes (y compris les erreurs) restent consultables.
            result: dict[str, Any] = preview.to_report(include_rows=True, offset=0, limit=100)
            result["lignes_affichees"] = result.pop("lignes")
            total = result["pagination"]["total"]
            result["pagination"]["page"] = 1
            result["pagination"]["pages"] = max(1, (total + 99) // 100)
            result["affichage_partiel"] = total > 100
            result["jeton"] = ticket
            return result
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            raise

    def inbound_page(self, d):
        """Consulte une page de diagnostics du dernier aperçu, sans relire le fichier.

        Le jeton est obligatoire. La pagination ne modifie jamais l'ouvrage.
        """
        pending = self._inbound_pending
        if not pending or d.get("jeton") != pending[0]:
            raise RegleMetier("Aucun aperçu valide : relancez la prévisualisation.")
        try:
            page = int(d.get("page", "1"))
        except (TypeError, ValueError) as exc:
            raise RegleMetier("Numéro de page invalide.") from exc
        preview = pending[1]
        max_pages = max(1, (len(preview.rows) + 99) // 100)
        if not 1 <= page <= max_pages:
            raise RegleMetier("Page hors de l'aperçu disponible.")
        report = preview.to_report(include_rows=True, offset=(page - 1) * 100, limit=100)
        return {"lignes_affichees": report["lignes"], "pagination": {
            **report["pagination"], "page": page, "pages": max_pages}}

    def _clear_inbound(self):
        pending = self._inbound_pending
        self._inbound_pending = None
        if pending:
            shutil.rmtree(pending[2], ignore_errors=True)

    def inbound_apply(self, d):
        """Applique en une seule étape l'aperçu confirmé et enregistre le projet.

        La session d'origine n'est remplacée qu'après validation du moteur ; une
        exception restaure la session et l'aperçu n'est jamais réutilisable.
        """
        pending = self._inbound_pending
        if not pending or d.get("jeton") != pending[0]:
            raise RegleMetier("Aucun aperçu valide : relancez la prévisualisation.")
        if d.get("confirmer") is not True:
            raise RegleMetier("Confirmation explicite requise.")
        if not self.ouvert or self.creation_en_attente:
            raise RegleMetier("Ouvrage non disponible pour l'import.")
        ticket, preview, directory = pending
        try:
            suppressions = d.get("suppressions") or []
            if not isinstance(suppressions, list) or not all(isinstance(x, str) for x in suppressions):
                raise RegleMetier("Liste de suppressions invalide.")
            staged = stage_import(preview, self.s, confirmed=True, suppressions=suppressions)
            if not (staged.created or staged.modified or staged.deleted):
                raise RegleMetier("Aucune nouvelle donnée à intégrer.")
            original = self.s
            original.creer_copie("import")       # V1-7-03 : état d'avant l'import, restaurable
            replacement = staged.session
            replacement.chemin = original.chemin
            replacement.garde_enregistrement = self._garde_verrou
            self.s = replacement
            try:
                self._sauver()
            except Exception:
                self.s = original
                raise
            return {"crees": staged.created, "inchanges": staged.unchanged, "modifies": staged.modified,
                    "supprimes": staged.deleted, "nature": staged.kind.value}
        finally:
            self._clear_inbound()

    def importer_modeles(self, d):
        ajoutes, conflits = self.s.importer_modeles(self._fichier_temporaire(d))
        return {"ajoutes": ajoutes, "conflits": conflits}


ROUTES_GET = {"/api/session-locale": "session_locale", "/api/referentiel/cycle": "referentiel_cycle", "/api/referentiel/vue": "referentiel_vue", "/api/accueil": "accueil", "/api/ouvrage": "ouvrage", "/api/equipement": "equipement",
              "/api/referentiel": "referentiel", "/api/listes-ouvrage": "listes_ouvrage", "/api/modele": "modele", "/api/numero": "numero_libre", "/api/recherche": "recherche_globale", "/api/rapprochement": "rapprochement_web", "/api/activite": "activite_recente",
              "/api/es": "es", "/api/numero-ouvrage": "numero_ouvrage_suggere",
              "/api/lieu-proposition": "lieu_proposition", "/api/inbound/lignes": "inbound_page", "/api/profils-import": "profils_import_web",
              "/api/variables": "variables_web", "/api/adressage": "adressage_web", "/api/materiel": "materiel", "/api/supervision": "supervision_web", "/api/recette": "recette_web", "/api/parcours": "parcours_web", "/api/fil": "fil_web", "/api/regles": "regles_web", "/api/outils": "outils_web", "/api/standards": "standards_web", "/api/grille": "grille_web", "/api/attributs": "attributs_web", "/api/essais": "essais_web", "/api/modeles-livrables": "modeles_livrables_web", "/api/formats-appris": "formats_appris_web", "/api/gammes-materiel": "gammes_materiel_web", "/api/revisions": "revisions_web", "/api/journal": "journal_web", "/api/equipement/ordre-export": "ordre_export_web", "/api/historique": "historique_web", "/api/modeles-livrables/texte": "modeles_livrables_texte", "/api/reglages/sources": "reglages_sources",
              "/api/referentiel/synchronisation": "synchronisation_referentiel", "/api/ouvrage/copies": "copies_ouvrage",
              "/api/referentiel/impact": "rapport_impact", "/api/referentiel/propagation": "apercu_propagation",
              "/api/referentiel/apercu-modele": "apercu_modele"}
ROUTES_POST = {"/api/nouveau": "nouveau", "/api/ouvrir": "ouvrir", "/api/fermer": "fermer",
               "/api/supprimer_ouvrage": "supprimer_ouvrage", "/api/definir": "definir",
               "/api/fiche-ouvrage": "fiche_ouvrage",
               "/api/listes-ouvrage/action": "listes_ouvrage_action", "/api/outils/action": "outils_action", "/api/standards/action": "standards_action", "/api/grille/appliquer": "grille_appliquer", "/api/attributs/action": "attributs_action", "/api/equipement/attribut": "equipement_attribut", "/api/essais/reporter": "essais_reporter", "/api/modeles-livrables/action": "modeles_livrables_action", "/api/formats-appris/action": "formats_appris_action", "/api/gammes-materiel/action": "gammes_materiel_action", "/api/revisions/action": "revisions_action", "/api/annuler": "annuler", "/api/retablir": "retablir", "/api/standards/appliquer": "appliquer_standard", "/api/standards/charte-apercu": "apercu_charte", "/api/reglages/reprendre": "reprendre_reglages",
               "/api/identification/type": "identifier_type",
               "/api/identification/selection": "identifier_selection", "/api/uf": "uf",
               "/api/equipement/ajouter": "ajouter_equipement", "/api/equipement/ajouter-serie": "ajouter_equipements_serie", "/api/equipement/modifier": "modifier_equipement",
               "/api/equipement/supprimer": "supprimer_equipements", "/api/equipement/dupliquer": "dupliquer_equipement", "/api/equipement/ordre-export/definir": "definir_ordre_export", "/api/equipement/deplacer": "deplacer", "/api/equipement/valider": "valider_equipements",
               "/api/equipement/proposition": "decider_proposition",
               "/api/referentiel/adopter": "adopter_referentiel", "/api/referentiel/revenir-au-standard": "revenir_au_standard", "/api/referentiel/adopter-modele": "adopter_modele", "/api/referentiel/accepter-propagation": "accepter_propagation", "/api/referentiel/refuser-mise-a-jour": "refuser_mise_a_jour", "/api/referentiel/annuler-adoption": "annuler_adoption", "/api/ouvrage/restaurer-copie": "restaurer_copie", "/api/adressage/action": "adressage_action",
               "/api/referentiel/cycle/action": "referentiel_cycle_action",
               # Anciennes routes conservées en réponse d'erreur explicite : pas de contournement possible.
               "/api/inventaire/apercu": "import_inventaire_ancien_desactive",
               "/api/inventaire/appliquer": "import_inventaire_ancien_desactive",
               "/api/inbound/apercu": "inbound_preview", "/api/rapprochement/action": "rapprochement_action", "/api/profils-import/action": "profils_import_action", "/api/inbound/appliquer": "inbound_apply",
               "/api/referentiel/importer": "importer_modeles", "/api/referentiel/action": "referentiel_action",
               "/api/equipement/ligne": "ligne_equipement", "/api/equipement/configurer": "configurer_equipement", "/api/es/definir": "es_definir",
               "/api/es/valider": "es_valider", "/api/modules": "modules_action",
               "/api/variables/action": "variables_action", "/api/materiel/action": "materiel_action"}


TAILLE_MAX_REQUETE = 50 * 1024 * 1024      # imports d'Excel ou de PDF compris (base64)


def app_quoi_modele(requete: str) -> bool:
    return parse_qs(requete).get("quoi", [""])[0] == "modele_livrable"


def fabriquer_gestionnaire(app):
    class Gestionnaire(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        # Audit du 16/11 : le serveur écoute sur 127.0.0.1, mais un site ouvert dans le navigateur pouvait lui
        # envoyer des ordres (POST « text/plain » sans contrôle préalable) ou lire ses réponses par rebinding DNS.
        def _origines(self):
            port = self.server.server_port   # type: ignore[attr-defined]
            return {f"127.0.0.1:{port}", f"localhost:{port}"}

        def _hote_refuse(self):
            """Rebinding DNS : seul l'hôte local est servi (un navigateur envoie toujours « Host »)."""
            hote = (self.headers.get("Host") or "").strip().lower()
            if hote and hote not in self._origines():
                self.send_error(421, "Hôte non autorisé")
                return True
            return False

        def _origine_refusee(self):
            """Requête venue d'un autre site : refusée avant toute action."""
            origine = (self.headers.get("Origin") or "").strip().lower()
            if origine and origine.removeprefix("http://") not in self._origines():
                return True
            return (self.headers.get("Sec-Fetch-Site") or "").lower() == "cross-site"

        def _json(self, code, donnees):
            corps = json.dumps(donnees, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corps)

        def _appeler(self, nom, donnees):
            try:
                with VERROU:
                    self._json(200, app.appeler(nom, donnees))
            except (RegleMetier, InboundError, ValueError, KeyError) as ex:
                from genvar.verrou import VerrouPris
                if isinstance(ex, VerrouPris):          # ouvrage ouvert ailleurs : l'interface peut proposer la reprise
                    return self._json(409, {"erreur": str(ex), "verrou": {k: ex.detail.get(k) for k in
                                                                         ("hote", "utilisateur", "depuis", "meme_poste")}})
                self._json(400, {"erreur": str(ex) if not isinstance(ex, KeyError) else f"Donnée manquante : {ex}"})
            except Exception:                                   # noqa: BLE001 — jamais d'échec silencieux
                journal(traceback.format_exc())
                self._json(500, {"erreur": "Erreur inattendue : le détail est enregistré dans journal.log."})

        def do_GET(self):
            if self._hote_refuse():
                return
            if self._origine_refusee():
                return self._json(403, {"erreur": "Requête d'une autre origine refusée."})
            u = urlparse(self.path)
            if u.path == "/api/export":
                try:
                    with VERROU:
                        app.dernier_bilan_groupe = None
                        nom, corps = app.exporter({k: v[0] for k, v in parse_qs(u.query).items()})
                        bilan = app.dernier_bilan_groupe
                except (RegleMetier, ValueError) as ex:
                    return self._json(400, {"erreur": str(ex)})
                except Exception:                               # noqa: BLE001
                    journal(traceback.format_exc())
                    return self._json(500, {"erreur": "Erreur inattendue : le détail est enregistré dans journal.log."})
                self.send_response(200)
                ext = os.path.splitext(nom.lower())[1]
                # Livrable d'un modèle (19/11) : extension libre et encodage du modèle → octets bruts, sans charset supposé.
                self.send_header("Content-Type", {".xsy": "application/xml", ".txt": "text/plain; charset=utf-8",
                                                  ".json": "application/json; charset=utf-8", ".zip": "application/zip",
                                                  ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
                                 .get(ext, "application/octet-stream") if not app_quoi_modele(u.query) else "application/octet-stream")
                self.send_header("Content-Disposition", f'attachment; filename="{nom}"')
                if bilan:
                    self.send_header("X-OGIAS-Bilan", f"{bilan['produits']};{bilan['non_produits']}")
                self.send_header("Content-Length", str(len(corps)))
                self.end_headers()
                self.wfile.write(corps)
                return
            if u.path in ROUTES_GET:
                return self._appeler(ROUTES_GET[u.path], {k: v[0] for k, v in parse_qs(u.query).items()})
            chemin = "index.html" if u.path in ("/", "") else u.path.lstrip("/")
            fichier = os.path.normpath(os.path.join(STATIQUE, chemin))
            if os.path.commonpath([fichier, STATIQUE]) != os.path.normpath(STATIQUE) or not os.path.isfile(fichier):
                self.send_error(404)
                return
            with open(fichier, "rb") as f:
                corps = f.read()
            self.send_response(200)
            self.send_header("Content-Type", (mimetypes.guess_type(fichier)[0] or "application/octet-stream")
                             + ("; charset=utf-8" if fichier.endswith((".html", ".js", ".css")) else ""))
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corps)

        def do_POST(self):
            if self._hote_refuse():
                return
            u = urlparse(self.path)
            if u.path not in ROUTES_POST:
                self.send_error(404)
                return
            if self._origine_refusee():
                return self._json(403, {"erreur": "Requête d'une autre origine refusée."})
            # JSON obligatoire : un autre site ne peut l'envoyer sans contrôle préalable (CORS), que ce serveur refuse.
            if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":
                return self._json(415, {"erreur": "Requête refusée : contenu JSON attendu."})
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return self._json(400, {"erreur": "Longueur de requête invalide."})
            if n < 0:
                return self._json(400, {"erreur": "Longueur de requête invalide."})
            if n > TAILLE_MAX_REQUETE:
                return self._json(413, {"erreur": "Requête trop volumineuse (50 Mo au plus)."})
            try:
                donnees = json.loads(self.rfile.read(n) or b"{}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                return self._json(400, {"erreur": "Requête illisible."})
            if not isinstance(donnees, dict):
                return self._json(400, {"erreur": "Requête illisible : objet JSON attendu."})
            self._appeler(ROUTES_POST[u.path], donnees)
    return Gestionnaire


def port_libre(prefere=8742):
    for p in (prefere, 0):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return s.getsockname()[1]
            except OSError:
                continue


def ouvrir_fenetre(url):
    """Sous Windows, ouvre OGIAS dans une fenêtre d'application Edge ou Chrome (icône OGIAS dans la barre
    des tâches, sans barre d'adresse). À défaut, onglet du navigateur par défaut."""
    if os.name == "nt":
        import shutil
        import subprocess
        candidats = [shutil.which("msedge"), shutil.which("chrome")]
        for base in (os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", ""), os.environ.get("LOCALAPPDATA", "")):
            candidats += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                          os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
        for exe in candidats:
            if exe and os.path.isfile(exe):
                try:
                    subprocess.Popen([exe, f"--app={url}", "--window-size=1440,900"])
                    return
                except OSError:
                    continue
    webbrowser.open(url)


class ServeurLocal(ThreadingHTTPServer):
    """File d'attente de connexions élargie : la page charge une dizaine de feuilles et de scripts à la fois ; avec
    la file par défaut (5), un poste lent pouvait refuser un script (constaté le 18/11 sur la CI Windows)."""
    request_queue_size = 64
    daemon_threads = True


def demarrer(ouvrir_navigateur=True, port=None):
    import platform
    from genvar import VERSION
    evenement(f"Démarrage d'OGIAS {VERSION} (Python {platform.python_version()}, {platform.system()} "
              f"{platform.release()}).")
    app = Application()
    port = port or port_libre()
    serveur = ServeurLocal(("127.0.0.1", port), fabriquer_gestionnaire(app))
    url = f"http://127.0.0.1:{port}/"
    if ouvrir_navigateur:
        threading.Timer(0.6, lambda: ouvrir_fenetre(url)).start()
    return serveur, url, app
