"""Assistant de rapprochement *non destructif* pour les ouvrages existants.

Trois stratégies évaluables indépendamment :
- programme : nom conforme FAMILLE_REPERE_FONCTION uniquement ;
- catalogue : interrogation du programme depuis chaque signal attendu ;
- hybride : combine les deux méthodes et utilise, facultativement, une liste d'E/S.

Un score n'est ni une probabilité de vérité, ni une validation métier. Aucune
proposition n'est écrite dans le programme ou l'ouvrage sans validation explicite.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
import unicodedata

from . import existant
from .catalogue import est_interne

METHODES = ("programme", "catalogue", "hybride")

# Seuil de confiance (cahier § 6) : réglé pour qu'AUCUNE proposition fausse connue des jeux de validation
# (validation/hybride : jeu initial et jeu difficile, trois méthodes, tous les candidats, signaux absents
# compris) n'atteigne ce score ; la plus haute observée est 79. La précision passe avant le rappel : sous le
# seuil, ou si le premier candidat est ambigu, la ligne est « à rapprocher manuellement ». Mesure et preuve :
# tests/test_seuil_confiance_rapprochement.py et validation/hybride/SEUIL_CONFIANCE.md. Ne jamais l'abaisser
# sans relancer cette mesure. Un score reste un classement, pas une probabilité.
SEUIL_CONFIANCE = 80
CONFIANCE_ELEVEE = "élevée"
A_RAPPROCHER = "à rapprocher manuellement"

# Vocabulaire métier réutilisable ; des mots trop génériques (ex. "état", "valeur")
# ne suffisent jamais à établir une fonction.
SYNONYMES_FONCTION = {
    "OUV": ("ouv", "ouvert", "ouverte", "ouverture", "fdc_ouv", "fin_course_ouvert"),
    "FER": ("fer", "ferme", "fermee", "fermeture", "fdc_fer", "fin_course_ferme"),
    "MA": ("ma", "marche", "en_marche", "run", "running"),
    "AR": ("ar", "arret", "stop"),
    "DEF": ("def", "defaut", "fault", "anomalie"),
    "PRE": ("pre", "pression", "pressure"),
    "DEB": ("deb", "debit", "flow"),
    "NIV": ("niv", "niveau", "level"),
    "AUTO": ("auto", "automatique"),
    "MANU": ("manu", "manuel", "manuelle"),
    "LOC": ("loc", "local", "locale"),
    "POS": ("pos", "position"),
    "HS": ("hs", "hors_service"),
    "DISPO": ("dispo", "disponible"),
    "REARM": ("rearm", "rearmement", "reset"),
    "VOL": ("vol", "volume", "totalise"),
    "FREQ": ("freq", "frequence"),
    "INT": ("intensite", "courant"),
    "TPS": ("temps", "duree"),
    "HF": ("heures_fonctionnement", "heures", "hours"),
    "NDEM": ("nombre_demarrages", "demarrages", "start_count"),
}


def normaliser(texte):
    s = unicodedata.normalize("NFKD", str(texte or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def morceaux(texte):
    return set(filter(None, normaliser(texte).split("_")))


def contient_expression(texte, expr):
    v, e = "_" + normaliser(texte) + "_", "_" + normaliser(expr) + "_"
    return bool(e != "__" and e in v)


def indices_fonction(texte, code, info):
    """Renvoie (qualité, justification). Ne certifie aucune chaîne fonctionnelle."""
    clauses = [code] + list(SYNONYMES_FONCTION.get(code, ()))
    clauses += [info] if len(normaliser(info)) > 4 else []
    matched = []
    for term in clauses:
        if contient_expression(texte, term):
            matched.append(term)
    if not matched:
        return 0, ""
    best = max(matched, key=lambda w: len(normaliser(w)))
    # Le code seul est moins significatif qu'une expression de métier.
    return (23 if len(normaliser(best)) <= 3 else 34), f"Fonction évoquée par « {best} »"


def alias_equipement(eq, ouvrage):
    n = str(int(eq.numero)) if eq.numero.isdigit() else eq.numero
    aliases = {eq.type + eq.numero, eq.type + n,
               ouvrage.repere_nom(eq), ouvrage.repere(eq)}
    abrevs = {"MV": ("v", "vanne"), "PM": ("p", "pompe"),
              "FT": ("ft", "debitmetre"), "PT": ("pt", "pression"),
              "LT": ("lt", "niveau"), "EV": ("ev", "electrovanne")}
    for pre in abrevs.get(eq.type, ()):
        aliases.update((pre + n, pre + eq.numero, pre + "_" + n))
    return {normaliser(x) for x in aliases if x}


def equipement_dans_texte(texte, eq, ouvrage):
    normalized = normaliser(texte)
    compact = normalized.replace("_", "")
    for alias in alias_equipement(eq, ouvrage):
        if not alias:
            continue
        if contient_expression(texte, alias):
            return True
        # Tolérance sûre pour un repère au milieu d'un symbole compact : exige
        # un alias d'au moins trois caractères et des limites non numériques.
        a = alias.replace("_", "")
        if len(a) >= 3 and re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![0-9])", compact):
            return True
        if len(a) >= 3 and compact.startswith(a) and (len(compact) == len(a) or not compact[len(a)].isdigit()):
            return True
    return False


def types_compatibles(reel, attendu):
    reel, attendu = (reel or "").upper(), (attendu or "").upper()
    return bool(reel and attendu and (reel == attendu or {reel, attendu} <= {"BOOL", "EBOOL"}))


def adresse_physique(adresse):
    return bool(re.match(r"^%(?:I|Q)(?:W|D|F|X)?\d", str(adresse or ""), re.I))


def hint_famille(v):
    name, comment = normaliser(v.nom), normaliser(v.commentaire)
    pre = name.split("_")[0] if name else ""
    if pre in existant.PREFIXES:
        return existant.PREFIXES[pre], "préfixe"
    txt = f"_{name}_{comment}_"
    if "_retour_consigne_" in txt or "_recopie_consigne_" in txt:
        return "RTR", "lexique retour consigne"
    if any(f"_{x}_" in txt for x in ("cmd", "commande", "ordre", "demande")):
        return "TC", "lexique commande"
    if any(f"_{x}_" in txt for x in ("consigne", "setpoint", "reglage")):
        return "TR", "lexique consigne"
    if any(f"_{x}_" in txt for x in ("retour", "fdc", "fin_course", "recopie", "feedback")):
        return "TS", "lexique retour d'état"
    if any(f"_{x}_" in txt for x in ("volume", "compteur", "index", "totalise")):
        return "CP", "lexique télécomptage"
    return "", ""


@dataclass(frozen=True)
class Proposition:
    variable_nom: str
    ident_eq: str
    cle: str
    methode: str
    score: int
    indices: tuple[str, ...]
    ambiguite: bool = False

    @property
    def confiance(self) -> str:
        """« élevée » (confirmable en lot) ou « à rapprocher manuellement » ; jamais appliquée seule."""
        return CONFIANCE_ELEVEE if self.score >= SEUIL_CONFIANCE and not self.ambiguite else A_RAPPROCHER

    @property
    def raison(self) -> str:
        return " ; ".join(self.indices)


@dataclass(frozen=True)
class EntreePhysiqueSource:
    nom: str
    adresse: str = ""
    equipement: str = ""     # ex. MV03 ou V3, éventuellement RV11MV03
    fonction: str = ""       # ex. fin de course fermée
    commentaire: str = ""
    variable_liee: str = ""  # renseigné seulement si lien vérifié dans la source


def _signaux_attendus(ouvrage, catalogue):
    for eq in ouvrage.equipements:
        for s in catalogue.signaux_du_type(eq.type):
            if s.get("famille") in ("ES", "") or est_interne(s.get("famille")):
                continue
            cle = s["famille"] + "_" + s["code"]
            if cle in eq.exclus:
                continue
            yield eq, s, cle


def _score_programme(v, eq, s, ouvrage):
    d = existant.decouper(v.nom)
    if not d or not d[3]:
        return 0, []
    famille, repere, suffixe, parties = d
    # type / sous-ensemble / numéro à respecter ; lieu et code ouvrage
    # peuvent avoir des variations sur les projets repris.
    _avant, se, typ, numero = parties
    if (typ, numero, se) != (eq.type, eq.numero, eq.sous_ensemble):
        return 0, []
    if existant.PREFIXES.get(famille) != s["famille"]:
        return 0, []
    if suffixe.replace("_", "") == s["code"]:
        return 96, ["Nom normalisé : famille, repère et fonction cohérents"]
    synonym = existant.SYNONYMES.get(suffixe.replace("_", ""), "")
    if synonym == s["code"]:
        return 76, ["Nom normalisé et synonyme de fonction"]
    return 0, []


def _score_catalogue(v, eq, s, ouvrage):
    nom_et_commentaire = v.nom + " " + v.commentaire
    if not equipement_dans_texte(nom_et_commentaire, eq, ouvrage):
        return 0, []
    q_nom, idx_nom = indices_fonction(v.nom, s["code"], s["information"])
    q_com, idx_com = indices_fonction(v.commentaire, s["code"], s["information"])
    q = max(q_nom, q_com)
    if not q:
        return 0, []
    hint, nature = hint_famille(v)
    if hint and hint != s["famille"]:
        return 0, []
    score = 30 + q + (10 if hint == s["famille"] else 0)
    ind = ["Repère équipement trouvé", idx_nom if q_nom >= q_com else idx_com]
    if hint:
        ind.append(f"Famille {hint} suggérée par {nature}")
    else:
        ind.append("Famille non démontrée : proposition à examiner")
    return score, ind


def _score_entrees(v, eq, s, ouvrage, entrees):
    score, indices = 0, []
    # Les E/S importées sont traitées ici comme des indices d'acquisition.
    # Elles ne prouvent ni une télécommande, ni une consigne de réglage.
    if s['famille'] not in ('TS', 'TM'):
        return 0, []
    for es in entrees:
        if not isinstance(es, EntreePhysiqueSource):
            es = EntreePhysiqueSource(**es)
        if not equipement_dans_texte(es.equipement or es.nom, eq, ouvrage):
            continue
        q, _ = indices_fonction(es.fonction + " " + es.commentaire, s["code"], s["information"])
        if not q:
            continue
        nom_lie = normaliser(es.variable_liee) == normaliser(v.nom) if es.variable_liee else False
        # Un repère E/S cité dans le commentaire de la variable est un indice,
        # JAMAIS une preuve de lien logique automate sans références croisées.
        citation = es.nom and (contient_expression(v.commentaire, es.nom) or contient_expression(v.nom, es.nom))
        if nom_lie:
            bonus = 36
            raison = f"Lien déclaré avec E/S {es.nom} (à vérifier)"
        elif citation:
            bonus = 29
            raison = f"E/S {es.nom} citée dans la variable ; relation logique à vérifier"
        elif equipement_dans_texte(v.nom + " " + v.commentaire, eq, ouvrage):
            bonus = 5
            raison = f"E/S {es.nom} concordante sur l'équipement (indice faible)"
        else:
            continue
        if bonus > score:
            score, indices = bonus, [raison]
    return score, indices


def proposer(ouvrage, catalogue, methode="hybride", entrees=None, limite=5, seuil=55):
    """Propose, sans mutation, des candidats par (ident_eq, FAMILLE_CODE).

    Ne décide jamais quel signal doit être supervisé et n'établit jamais seul
    l'accessibilité TOPKAPI. Les sources physiques %I/%Q sont conservées dans
    l'inventaire mais exclues des propositions d'échange par défaut.
    """
    if methode not in METHODES:
        raise ValueError(f"Méthode inconnue : {methode}")
    entrees = entrees if entrees is not None else getattr(ouvrage, "entrees_physiques_importees", [])
    sorties = {}
    for eq, signal, cle in _signaux_attendus(ouvrage, catalogue):
        choix = []
        for v in ouvrage.existantes:
            if adresse_physique(v.adresse):
                continue
            if not types_compatibles(v.type_logique, signal.get("type_logique")):
                continue
            a, ia = _score_programme(v, eq, signal, ouvrage)
            b, ib = _score_catalogue(v, eq, signal, ouvrage)
            if methode == "programme":
                score, indices = a, ia
            elif methode == "catalogue":
                score, indices = b, ib
            else:
                c, ic = _score_entrees(v, eq, signal, ouvrage, entrees)
                score, indices = max(a, b), ia if a >= b else ib
                if c and score:
                    score = min(100, score + c)
                    indices = indices + ic
                elif c >= 29 and hint_famille(v)[0] in ('', signal['famille']):
                    # Un lien E/S nommé et une fonction compatible sont utiles même
                    # sans nomenclature exploitable, mais doivent rester proposés.
                    score = 57 if c == 29 else 72
                    indices = ic + ["Fonction associée d'après la liste E/S"]
                elif c:
                    score = 0
            if score >= seuil:
                choix.append(Proposition(v.nom, eq.ident, cle, methode, score, tuple(indices)))
        choix.sort(key=lambda x: (-x.score, x.variable_nom))
        # Deux candidats à moins de 8 points sont considérés ambigus.
        if len(choix) > 1 and choix[0].score - choix[1].score < 8:
            choix = [Proposition(**{**asdict(p), "ambiguite": True}) for p in choix]
        sorties[(eq.ident, cle)] = choix[:limite]
    return sorties


def appliquer_choix(ouvrage, catalogue, nom, ident_eq, cle):
    """Association manuelle explicite depuis l'interface ; conserve la source.

    Ne change pas automatiquement l'état en « Confirmée » si la correspondance
    reste techniquement non qualifiable ; les contrôles existants tranchent.
    """
    v = next((x for x in ouvrage.existantes if x.nom == nom), None)
    eq = ouvrage.equipement(ident_eq)
    if v is None or eq is None:
        raise ValueError("Variable ou équipement introuvable")
    s = next((s for s in catalogue.signaux_du_type(eq.type)
              if f"{s['famille']}_{s['code']}" == cle), None)
    if not s:
        raise ValueError("Signal absent du catalogue")
    if not types_compatibles(v.type_logique, s.get("type_logique")):
        raise ValueError("Types incompatibles : correspondance refusée")
    if any(x is not v and x.retenue and x.ident_eq == ident_eq and x.cle == cle
           for x in ouvrage.existantes):
        raise ValueError("Ce signal possède déjà une variable associée")
    v.ident_eq, v.cle, v.retenue = ident_eq, cle, True
    v.identification = "Confirmée"
    v.remarque = "Correspondance acceptée manuellement depuis l'assistant de rapprochement."
    if ouvrage.statut == "Validé":
        ouvrage.statut = "À contrôler"
    return v
