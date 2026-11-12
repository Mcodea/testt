"""Guidage de l'utilisateur : « que dois-je faire maintenant, et pourquoi ? ».

Module sans Qt (testable seul). Il ne décide rien : il traduit l'état calculé par le moteur
(identification, équipements, propositions, adresses, contrôles) en actions concrètes, chacune
avec un bouton qui mène au bon endroit. Il explique aussi les noms et les adresses.
"""
import re
from dataclasses import dataclass, field

from genvar.catalogue import SIGNIFICATION_FAMILLES
from genvar.modele import _mot, zone, TAILLE_MOTS


@dataclass
class Action:
    titre: str
    detail: str
    bouton: str
    commande: str              # fiche, ajouter_uf, ajouter_se, ajouter_eq, propositions, attribuer, valider, es, controles, exports
    niveau: str = "faire"      # faire, erreur, alerte, ok
    nombre: int = 0
    ecrans: tuple = ()         # écrans où l'action est particulièrement utile


@dataclass
class Groupe:
    cle: str
    titre: str
    explication: str
    commande: str
    bouton: str
    niveau: str = "Alerte"
    anomalies: list = field(default_factory=list)


# (clé, motif du message, titre, explication, commande, bouton)
CATEGORIES = [
    ("identification", r"^(Le lieu|Le code de l'ouvrage|Sous-ensemble « |Sous-ensemble \w+ déclaré)",
     "Identification de l'ouvrage", "Le lieu (4 caractères) et le code de l'ouvrage (2 lettres) forment le début "
     "de tous les repères et noms de variables.", "fiche", "Ouvrir la fiche ouvrage"),
    ("sans_adresse", r"pas d'adresse dans la table d'échange",
     "Variables sans adresse d'échange", "Étape normale d'un projet neuf : l'outil calcule les adresses %MW selon le "
     "plan mémoire, vous vérifiez l'aperçu puis vous confirmez.", "attribuer", "Attribuer les adresses"),
    ("non_validees", r"pas encore validée",
     "Adresses proposées à valider", "Les adresses calculées restent « proposées » tant que vous ne les avez pas "
     "validées ; une adresse validée n'est plus jamais recalculée.", "valider", "Valider les adresses"),
    ("adresse_physique", r"adresse physique à renseigner",
     "E/S sans adresse physique", "Adresse réelle du câblage (%I0.3.5, %Q0.4.2, %IW0.5.0…), à reprendre du schéma "
     "électrique. Facultatif tant que le câblage n'est pas connu ; obligatoire pour exporter ces E/S dans le XSY.",
     "es", "Saisir les adresses physiques"),
    ("adresse_incorrecte", r"(chevauche|hors de la plage|adresse impaire|non reconnue|miroir|BOOL doit|déjà utilisée|"
                           r"s'adresse en|adresse de départ)",
     "Adresses incorrectes", "Adresse saisie à la main en conflit avec une autre, hors de sa plage ou d'un format "
     "inadapté au type.", "variables", "Voir les variables"),
    ("noms", r"(caractères|nom en double|Repère utilisé|numéro doit)",
     "Noms ou repères incorrects", "Un nom de variable fait au plus 32 caractères ; un repère est unique.",
     "fiche", "Ouvrir la fiche ouvrage"),
    ("regles", r"(n'est plus satisfaite|conservée pour|obligatoire retiré|Option « )",
     "Équipements à revoir", "Signaux retirés, options inconnues ou propositions dont la condition a disparu.",
     "fiche", "Ouvrir la fiche ouvrage"),
    ("libelles", r"Libellé Topkapi", "Libellés de supervision trop longs",
     "40 caractères au plus : raccourcir dans la fiche de la variable (double-clic).", "variables", "Voir les variables"),
]


def categoriser(anomalie):
    for cle, motif, *_ in CATEGORIES:
        if re.search(motif, anomalie.message):
            return cle
    return "autres"


def grouper(anomalies):
    """Anomalies regroupées par nature, dans l'ordre où il faut les traiter."""
    groupes = {}
    for a in anomalies:
        cle = categoriser(a)
        if cle not in groupes:
            spec = next((c for c in CATEGORIES if c[0] == cle), None)
            if spec:
                groupes[cle] = Groupe(cle, spec[2], spec[3], spec[4], spec[5])
            else:
                groupes[cle] = Groupe(cle, "Autres contrôles", "Voir le détail dans la liste.", "controles", "Voir")
        g = groupes[cle]
        g.anomalies.append(a)
        if a.niveau == "Erreur":
            g.niveau = "Erreur"
    ordre = [c[0] for c in CATEGORIES] + ["autres"]
    return sorted(groupes.values(), key=lambda g: ordre.index(g.cle))


def _identification(o):
    manques = []
    if not re.match(r"^[A-Z0-9]{4}$", o.lieu or ""):
        manques.append(f"lieu « {o.lieu or '—'} » : 4 caractères (ex. ATMS)")
    if not re.match(r"^[A-Z]{2}$", o.code_ouvrage or ""):
        manques.append(f"code ouvrage « {o.code_ouvrage or '—'} » : 2 lettres (ex. RV)")
    if not o.libelle:
        manques.append("libellé")
    return manques


def a_faire(session, ecran=""):
    """Actions à réaliser, dans l'ordre du parcours (projet neuf). Liste vide : tout est fait."""
    o = session.ouvrage
    if o.mode == "Existant":
        return []
    actions = []
    manques = _identification(o)
    if manques:
        actions.append(Action("Compléter l'identification de l'ouvrage", " ; ".join(manques).capitalize() + ".",
                              "Ouvrir la fiche ouvrage", "fiche", "erreur", len(manques), ("Ouvrage", "Variables")))
    if not o.equipements:
        if not o.unites:
            actions.append(Action("Créer les unités fonctionnelles (facultatif)",
                                  "Ex. UF01 Stockage, sous-ensemble 11. Un ouvrage simple peut s'en passer.",
                                  "Créer une UF", "ajouter_uf", "faire", 0, ("Ouvrage",)))
        actions.append(Action("Ajouter les équipements",
                              "Choisir le type dans le référentiel, puis cocher les options réellement présentes.",
                              "Ajouter un équipement", "ajouter_eq", "faire", 0, ("Ouvrage",)))
        return actions
    points = session.points()
    a_valider_es = sum(1 for p in points if not p.validee)
    if a_valider_es:
        actions.append(Action(f"Vérifier et valider la liste des E/S ({a_valider_es} à valider)",
                              "Premier livrable du projet neuf : retirer les E/S absentes, compléter les désignations, "
                              "puis valider. Les adresses physiques peuvent attendre.",
                              "Ouvrir la liste des E/S", "es", "faire", a_valider_es, ("E/S automate", "Ouvrage")))
    en_attente = []
    for eq in o.equipements:
        n = sum(1 for p in session.propositions(eq).values() if p.etat == "proposé")
        if n:
            en_attente.append((o.repere(eq), n))
    if en_attente:
        total = sum(n for _, n in en_attente)
        exemples = ", ".join(f"{r} ({n})" for r, n in en_attente[:3])
        actions.append(Action(f"Examiner {total} signal(aux) proposé(s) par les règles",
                              f"Accepter ce qui doit être programmé, refuser le reste : {exemples}"
                              + ("…" if len(en_attente) > 3 else "") + ". Rien n'est généré sans accord.",
                              "Ouvrir le premier équipement", "propositions", "alerte", total, ("Ouvrage", "Variables")))
    variables = session.variables()
    anomalies = session.anomalies(variables)
    sans = sum(1 for v in variables if not v.adresse)
    if sans:
        actions.append(Action(f"Attribuer les adresses ({sans} variable(s))",
                              "L'outil calcule les adresses %MW selon le plan mémoire et vous montre l'aperçu ; "
                              "les adresses existantes ne bougent pas.",
                              "Attribuer les adresses", "attribuer", "faire", sans, ("Variables", "Plan mémoire")))
    a_valider = sum(1 for v in variables if v.adresse and not v.adresse_validee)
    if a_valider and not sans:
        actions.append(Action(f"Valider les adresses ({a_valider})",
                              "Vérifier les adresses proposées puis les valider : elles seront figées.",
                              "Valider les adresses", "valider", "faire", a_valider, ("Variables",)))
    sans_es = sum(1 for p in points if not p.adresse and p.raccordement != "Communication")
    if sans_es:
        actions.append(Action(f"Saisir les adresses physiques ({sans_es} E/S)",
                              "Reprendre les adresses du schéma électrique (%I…, %Q…, %IW…, %QW…). "
                              "Facultatif tant que le câblage n'est pas défini.",
                              "Saisir les adresses physiques", "es", "alerte", sans_es, ("E/S automate",)))
    autres = [a for a in anomalies if a.niveau == "Erreur" and categoriser(a) not in ("sans_adresse", "identification")]
    if autres:
        actions.append(Action(f"Corriger {len(autres)} erreur(s)", autres[0].message,
                              "Voir les contrôles", "controles", "erreur", len(autres), ("Contrôles",)))
    if not actions:
        actions.append(Action("Prêt pour l'export", "Aucune erreur bloquante : produire le XSY et la table Excel, "
                              "puis les vérifier dans Control Expert et TOPKAPI.", "Aller aux exports", "exports", "ok"))
    return actions


def pour_ecran(actions, ecran, maximum=3):
    """Actions à montrer sur un écran : d'abord celles qui le concernent, puis la prochaine du parcours."""
    propres = [a for a in actions if ecran in a.ecrans]
    choix = propres[:maximum]
    if actions and actions[0] not in choix:
        choix = [actions[0]] + choix[:maximum - 1]
    return choix


# ====================================================================== explications
def expliquer_repere(ouvrage, eq):
    """Liste (valeur, rôle, règle, correct) des morceaux d'un repère."""
    return [
        (ouvrage.lieu, "lieu", "4 caractères", bool(re.match(r"^[A-Z0-9]{4}$", ouvrage.lieu or ""))),
        (ouvrage.code_ouvrage, "ouvrage", "2 lettres", bool(re.match(r"^[A-Z]{2}$", ouvrage.code_ouvrage or ""))),
        (eq.sous_ensemble if eq else "", "sous-ensemble", "2 caractères",
         bool(eq and re.match(r"^[A-Z0-9]{2}$", eq.sous_ensemble or ""))),
        (eq.type if eq else "", "type", "2 lettres du référentiel", bool(eq and len(eq.type or "") == 2)),
        (eq.numero if eq else "", "numéro", "2 chiffres", bool(eq and re.match(r"^\d{2}$", eq.numero or ""))),
    ]


def expliquer_nom(ouvrage, v):
    """« TS_ATMSRV11MV03_FER » décomposé en mots."""
    eq = ouvrage.equipement(v.ident_eq)
    morceaux = expliquer_repere(ouvrage, eq)
    if not ouvrage.lieu_dans_le_nom:
        morceaux = morceaux[1:]
    repere = " + ".join(f"{val or '?'} ({role})" for val, role, _, _ in morceaux)
    famille = SIGNIFICATION_FAMILLES.get(v.famille, v.famille)
    return (f"{v.famille} ({famille}) + {repere} + {v.code} ({v.information})")


def expliquer_adresse(ouvrage, v, decalage=0):
    if not v.adresse:
        debut, fin = zone(ouvrage, v.famille)
        return (f"Pas encore d'adresse. « Attribuer les adresses » la placera dans la plage {v.famille} "
                f"(%MW{debut} à %MW{fin}).")
    p = _mot(v.adresse)
    if p is None:
        return f"Adresse « {v.adresse} » non reconnue."
    debut, fin = zone(ouvrage, v.famille)
    if p[1] is not None:
        quoi = f"bit {p[1]} du mot {p[0]}"
    else:
        taille = max(1, TAILLE_MOTS.get(v.type_logique, 1))
        quoi = f"mot {p[0]}" if taille == 1 else f"mots {p[0]} et {p[0] + 1} ({v.type_logique} sur 32 bits)"
    modbus = f"{p[0] + int(decalage)}" + (f".{p[1]}" if p[1] is not None else "")
    etat = "validée (figée)" if v.adresse_validee else "proposée — à valider"
    return (f"{v.adresse} = {quoi}, plage {v.famille} %MW{debut}–%MW{fin}, registre Modbus {modbus} · {etat}.")
