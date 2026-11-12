"""Moteur de règles fonctionnelles du référentiel.

Une règle relie des signaux d'un type d'équipement :

    {"id": "MV-02", "type": "MV", "libelle": "Deux fins de course",
     "si": ["ES_FDC_OUV", "ES_FDC_FER"],          # TOUS ces signaux doivent être retenus
     "propose": ["TS_DISC", "TS_INT"],            # signaux proposés
     "mode": "proposition",                       # « auto » ou « proposition »
     "logique": "Discordance : les deux fins de course actifs ensemble pendant T_DISC…"}

- mode « auto » : le signal proposé est retenu d'office (son origine reste affichée : « issu de la
  règle MV-01 ») ; l'utilisateur peut le retirer. Réservé aux liaisons directes (une fin de course
  donne la TS de position).
- mode « proposition » : le signal est seulement PROPOSÉ ; il faut l'accepter explicitement.
  Réservé aux informations qui exigent un traitement automate (discordance, temps de manœuvre…).

Un type « * » s'applique à tous les types ; le joker `*` dans un code relie des signaux de même
code (ex. si ["TR_*"] propose ["RTR_*"] : chaque téléréglage propose son retour).

Gouvernance (référentiel V2, décision D1/D5) : « relation documentaire » (l'information fonctionnelle associée
à une E/S, retenue d'office en mode auto), « suggestion optionnelle » (signal à sélectionner ; les règles
« auto » de cette catégorie restent retenues d'office jusqu'à la décision D5-b), « contrôle de cohérence ». OGIAS n'impose aucun algorithme : calcul,
conditions et temporisations relèvent de l'analyse fonctionnelle. Une règle sans gouvernance (référentiel figé
d'un ancien ouvrage) garde son comportement d'origine.

Le moteur est déterministe : mêmes signaux retenus → mêmes propositions, dans le même ordre.
Une proposition n'est JAMAIS une variable existante ni une fonction programmée dans l'automate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .catalogue import est_interne

MODES = ("auto", "proposition")
GOUVERNANCES = ("relation documentaire", "suggestion optionnelle", "contrôle de cohérence")
NOTES_GOUVERNANCE = {
    "relation documentaire": "Relation documentaire : information fonctionnelle associée à l'E/S.",
    "suggestion optionnelle": "Suggestion optionnelle : à retenir ou écarter par l'utilisateur ; calcul, conditions "
                              "et temporisations définis par l'analyse fonctionnelle et réalisés par le programme "
                              "automate.",
    "contrôle de cohérence": "Contrôle de cohérence documentaire ; aucun traitement automate imposé.",
}


def retenue_d_office(regle):
    """Mode auto historique. Les 10 règles « auto » classées « suggestion optionnelle » (FT-02, FT-03, GEN-01…)
    restent retenues d'office tant que la décision D5-b n'est pas validée (docs/INSTRUCTIONS_EN_COURS.md) :
    les rendre manuelles modifie le contenu de tous les projets neufs."""
    return regle.get("mode") == "auto"


def texte(regle):
    """Texte affiché pour une règle : sa logique éventuelle, sinon la note de sa gouvernance."""
    return regle.get("logique", "") or NOTES_GOUVERNANCE.get(regle.get("gouvernance", ""), "")


@dataclass
class Proposition:
    cle: str                       # FAMILLE_CODE proposé
    signal: dict                   # signal du catalogue
    regles: list = field(default_factory=list)   # règles qui le proposent (dict)
    etat: str = "proposé"          # « retenu » (auto ou accepté), « proposé », « refusé »
    auto: bool = False

    @property
    def raison(self):
        parties = []
        for r in self.regles:
            si = " + ".join(r.get("si", []))
            parties.append(f"règle {r.get('id', '?')} « {r.get('libelle', '')} » : {si} présent(s)")
        return " ; ".join(parties)

    @property
    def logique(self):
        textes = [texte(r) for r in self.regles if texte(r)]
        if self.signal.get("logique"):
            textes.append(self.signal["logique"])
        vus = []
        for t in textes:
            if t not in vus:
                vus.append(t)
        return " ".join(vus)


def regles_du_type(catalogue, code_type):
    return [r for r in getattr(catalogue, "regles", []) if r.get("type") in (code_type, "*")]


def _instancier(regle, cles_type):
    """Développe les jokers : [(si, propose)] concrets pour les codes existants du type."""
    si, propose = list(regle.get("si", [])), list(regle.get("propose", []))
    if not any("*" in c for c in si + propose):
        return [(si, propose)]
    resultat = []
    jokers = [c for c in si if c.endswith("_*")]
    if not jokers:
        return []
    famille = jokers[0][:-2]
    for cle in sorted(cles_type):
        f, code = cle.split("_", 1)
        if f != famille:
            continue
        resultat.append(([c.replace("*", code) for c in si], [c.replace("*", code) for c in propose]))
    return resultat


def evaluer(catalogue, eq, base):
    """Propositions des règles pour l'équipement `eq`.

    `base` : clés retenues hors règles (catalogue par défaut + options + signaux propres − retirés).
    Les règles sont appliquées jusqu'à stabilité (une proposition retenue peut en déclencher
    d'autres) ; un signal retiré (`eq.exclus`) ne déclenche rien.
    Renvoie {cle: Proposition}.
    """
    signaux = {f"{s['famille']}_{s['code']}": s for s in catalogue.signaux_du_type(eq.type)}
    regles = []
    for r in regles_du_type(catalogue, eq.type):
        for si, propose in _instancier(r, signaux):
            regles.append((r, si, propose))
    acceptes = set(getattr(eq, "acceptes", []) or [])
    retenues = set(base)
    propositions: dict[str, Proposition] = {}
    for _ in range(10):                      # borne : le catalogue ne peut pas boucler indéfiniment
        change = False
        for r, si, propose in regles:
            if not all(c in retenues for c in si):
                continue
            for cle in propose:
                s = signaux.get(cle)
                if s is None or cle in base:
                    continue                 # déjà retenu par ailleurs : rien à proposer
                p = propositions.get(cle)
                if p is None:
                    p = propositions[cle] = Proposition(cle, s)
                if r not in p.regles:
                    p.regles.append(r)
                    change = True
                # une variable interne déclarée (P1) n'est jamais retenue sans sélection de l'utilisateur
                p.auto = p.auto or (retenue_d_office(r) and not est_interne(s.get("famille")))
                if cle in eq.exclus:
                    p.etat = "refusé"
                elif p.auto or cle in acceptes:
                    p.etat = "retenu"
                else:
                    p.etat = "proposé"
                if p.etat == "retenu" and cle not in retenues:
                    retenues.add(cle)
                    change = True
        if not change:
            break
    return propositions


def anomalies_regles(catalogue):
    """Contrôle du référentiel : règles mal formées ou signaux « Règle » jamais proposés."""
    msg = []
    ids = [r.get("id") for r in getattr(catalogue, "regles", [])]
    for i in sorted({x for x in ids if ids.count(x) > 1}):
        msg.append(f"Règle {i} : identifiant utilisé plusieurs fois.")
    types = {t["code"] for t in catalogue.types}
    proposes: dict[str, set[str]] = {}
    for r in getattr(catalogue, "regles", []):
        rid = r.get("id", "?")
        if r.get("type") != "*" and r.get("type") not in types:
            msg.append(f"Règle {rid} : type {r.get('type')} inconnu.")
            continue
        if r.get("mode") not in MODES:
            msg.append(f"Règle {rid} : mode « {r.get('mode')} » inconnu (auto ou proposition).")
        if r.get("gouvernance") and r["gouvernance"] not in GOUVERNANCES:
            msg.append(f"Règle {rid} : gouvernance « {r['gouvernance']} » inconnue ({', '.join(GOUVERNANCES)}).")
        if not r.get("si") or not r.get("propose"):
            msg.append(f"Règle {rid} : conditions et signaux proposés obligatoires.")
        for c in r.get("propose", []):
            if retenue_d_office(r) and est_interne(c.split("_", 1)[0]):
                msg.append(f"Règle {rid} : la variable interne {c} ne peut pas être retenue d'office "
                           "(sélection de l'utilisateur obligatoire, mode « proposition »).")
        if r.get("type") == "*":
            continue
        cles = {f"{s['famille']}_{s['code']}" for s in catalogue.signaux_du_type(r["type"])}
        for c in r.get("si", []) + r.get("propose", []):
            if c not in cles:
                msg.append(f"Règle {rid} : signal {c} absent du type {r['type']}.")
        for c in r.get("propose", []):
            proposes.setdefault(r["type"], set()).add(c)
    for s in catalogue.signaux:
        if s.get("presence") == "Règle" and s.get("statut") != "Écarté":
            cle = f"{s['famille']}_{s['code']}"
            generiques = any(r.get("type") == "*" and any(p.split("_", 1)[0] == s["famille"] for p in r.get("propose", []))
                             for r in getattr(catalogue, "regles", []))
            if cle not in proposes.get(s["type"], set()) and not generiques:
                msg.append(f"Type {s['type']}, signal {cle} : présence « Règle » mais aucune règle ne le propose.")
    return msg
