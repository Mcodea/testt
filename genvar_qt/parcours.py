"""Avancement du parcours de travail, calculé à partir de la Session.

Module sans dépendance Qt (testable seul). Il ne décide rien : il résume l'état que le
moteur calcule déjà (variables, adresses, anomalies, qualifications) pour guider
l'utilisateur vers l'étape suivante. Une étape « faite » n'est jamais une validation
industrielle : elle indique seulement que l'outil n'a plus rien à signaler sur ce point.
"""
from dataclasses import dataclass

from genvar import teletransmission

PARCOURS_NEUF = ("Ouvrage", "E/S automate", "Variables", "Plan mémoire", "Contrôles", "Exports")
PARCOURS_EXISTANT = ("Ouvrage", "Projet existant", "Contrôles", "Exports")

TITRES = {
    "Ouvrage": "Ouvrage & équipements",
    "Variables": "Variables fonctionnelles",
    "E/S automate": "Liste des E/S",
    "Plan mémoire": "Plan mémoire",
    "Projet existant": "Analyse & télétransmission",
    "Contrôles": "Contrôles",
    "Exports": "Exports",
}

DESCRIPTIONS = {
    "Ouvrage": "Identifier l'ouvrage, déclarer les sous-ensembles et les équipements.",
    "Variables": "Examiner les signaux proposés, générer la table d'échange, attribuer et valider les adresses.",
    "E/S automate": "Vérifier, compléter et valider la liste des entrées / sorties ; l'exporter (Excel, PDF).",
    "Plan mémoire": "Ajuster les plages d'adresses réservées par famille.",
    "Projet existant": "Importer le programme, construire la table de télétransmission, valider chaque ligne.",
    "Contrôles": "Corriger les erreurs bloquantes, examiner les alertes.",
    "Exports": "Produire les livrables XSY et Excel.",
}


@dataclass
class Etape:
    nom: str
    numero: int
    titre: str
    description: str
    etat: str = "a_faire"          # a_faire, fait, erreur
    detail: str = ""
    badge: str = ""
    gravite: str = "Info"          # gravité du badge
    recommande: bool = False


@dataclass
class Avancement:
    etapes: list
    variables: int = 0
    points: int = 0
    erreurs: int = 0
    alertes: int = 0

    def etape(self, nom):
        return next((e for e in self.etapes if e.nom == nom), None)

    def prochaine(self):
        return next((e for e in self.etapes if e.recommande), None)

    @property
    def faites(self):
        return sum(e.etat == "fait" for e in self.etapes)


def _ouvrage(s, neuf):
    o = s.ouvrage
    if not o.lieu or not o.code_ouvrage:
        return "a_faire", "Renseigner le lieu et le code de l'ouvrage."
    if not o.libelle:
        return "a_faire", "Renseigner le libellé de l'ouvrage."
    if neuf and not o.equipements:
        return "a_faire", "Ajouter au moins un équipement."
    n, k = len(o.equipements), len(o.sous_ensembles)
    return "fait", f"{n} équipement(s) · {k} sous-ensemble(s)"


def calculer(s):
    """Retourne l'Avancement de l'ouvrage ouvert dans la Session `s`."""
    o = s.ouvrage
    neuf = o.mode != "Existant"
    ordre = PARCOURS_NEUF if neuf else PARCOURS_EXISTANT
    etapes = {nom: Etape(nom, i, TITRES[nom], DESCRIPTIONS[nom]) for i, nom in enumerate(ordre, start=1)}

    e = etapes["Ouvrage"]
    e.etat, e.detail = _ouvrage(s, neuf)

    if neuf:
        variables = s.variables()
        anomalies = s.anomalies(variables)
        points = s.points()
        sans = sum(1 for v in variables if not v.adresse)
        e = etapes["Variables"]
        if not variables:
            e.detail = "Aucune variable : les équipements génèrent la table."
        elif sans:
            e.detail = f"{sans} variable(s) sans adresse sur {len(variables)}."
            e.badge, e.gravite = str(sans), "Alerte"
        else:
            e.etat, e.detail = "fait", f"{len(variables)} variables adressées."
        e = etapes["E/S automate"]
        a_valider = sum(1 for p in points if not p.validee)
        sans_adr = sum(1 for p in points if not p.adresse and p.raccordement != "Communication")
        if not points:
            e.detail = "Aucune E/S : les équipements déclarés n'ont pas d'E/S physique."
        elif a_valider:
            e.detail = f"{a_valider} E/S à valider sur {len(points)}" + (f" · {sans_adr} sans adresse." if sans_adr else ".")
            e.badge, e.gravite = str(a_valider), "Alerte"
        else:
            e.etat = "fait"
            e.detail = f"{len(points)} E/S validées" + (f" · {sans_adr} adresse(s) physique(s) à saisir." if sans_adr else ".")
        e = etapes["Plan mémoire"]
        if variables and not sans:
            e.etat, e.detail = "fait", "Plages appliquées aux adresses attribuées."
        else:
            e.detail = "Vérifier les plages avant d'attribuer les adresses."
        total = len(variables)
    else:
        anomalies = s.anomalies_existant()
        points = []
        total = len(o.existantes)
        e = etapes["Projet existant"]
        if not o.existantes:
            e.detail = "Importer le XSY, le SCY, un fichier Excel ou CSV."
        elif not o.equipements:
            e.detail = "Déclarer les équipements ou accepter ceux détectés dans le programme."
        elif not o.table_tt:
            e.detail = "Construire la table de télétransmission."
        else:
            b = teletransmission.bilan(o, s.catalogue)
            cloture = teletransmission.verifier_cloture(o, s.catalogue)
            a_traiter = b["À compléter"] + b["Sans source"]
            if b["Incohérence"]:
                e.etat = "erreur"
                e.badge, e.gravite = str(b["Incohérence"]), "Erreur"
                e.detail = f"{b['Incohérence']} incohérence(s) · {a_traiter} ligne(s) à traiter · {b['Validée']} validée(s)."
            elif a_traiter:
                e.badge, e.gravite = str(a_traiter), "Alerte"
                e.detail = f"{a_traiter} ligne(s) à traiter · {b['Validée']} validée(s)."
            if cloture and not b["Incohérence"] and not a_traiter:
                e.etat = "a_faire"
                e.badge, e.gravite = "!", "Alerte"
                e.detail = cloture[0]
            elif not cloture:
                e.etat = "fait"
                e.detail = f"{b['Validée']} validée(s) · {b['Non accessible']} non accessible(s)."

    erreurs = sum(1 for a in anomalies if a.niveau == "Erreur")
    alertes = sum(1 for a in anomalies if a.niveau == "Alerte")
    e = etapes["Contrôles"]
    if not total:
        e.detail = "Rien à contrôler pour l'instant."
    elif erreurs:
        e.etat = "erreur"
        e.badge, e.gravite = str(erreurs), "Erreur"
        e.detail = f"{erreurs} erreur(s) bloquante(s) · {alertes} alerte(s)."
    elif alertes:
        e.etat = "fait"
        e.badge, e.gravite = str(alertes), "Alerte"
        e.detail = f"Aucune erreur bloquante · {alertes} alerte(s) à examiner."
    else:
        e.etat, e.detail = "fait", "Aucune anomalie détectée."

    e = etapes["Exports"]
    if not total:
        e.detail = "Disponible lorsque l'ouvrage contient des variables."
    elif erreurs:
        e.detail = "Export contrôlé bloqué : corriger les erreurs (brouillon possible)."
    else:
        e.detail = "Prêt pour un export contrôlé."

    liste = [etapes[n] for n in ordre]
    suivante = next((x for x in liste if x.etat != "fait"), None)
    if suivante is not None:
        suivante.recommande = True
    return Avancement(liste, variables=total, points=len(points), erreurs=erreurs, alertes=alertes)
