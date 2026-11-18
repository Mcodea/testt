"""Règles de cohérence d'OGIAS : catalogue nommé et contrôles transversaux de la chaîne de l'information.

Orientation du 18/11/2026 : la cohérence est la première capacité d'OGIAS. Chaque contrôle porte un code stable,
un titre, une gravité, l'étape où il se corrige, la raison qui le justifie et la façon de corriger. Le code
apparaît dans la recette et dans les rapports ; il permet de parler d'un écart sans ambiguïté (« R-VAR-05 »).

Rien n'est inventé ici : les contrôles transversaux n'utilisent que des liens déjà présents dans l'ouvrage
(variable d'échange liée à une E/S, nom de l'E/S source d'une variable, paires TR / RTR, décalage de
télétransmission saisi par l'utilisateur). OGIAS signale ; il ne corrige jamais à la place de l'automaticien.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Regle:
    code: str
    titre: str
    gravite: str          # gravité habituelle : « Erreur » (bloque la livraison) ou « Alerte » (à examiner)
    etape: str            # étape du parcours où l'écart se corrige
    pourquoi: str         # ce qui se passe sur site si l'écart n'est pas corrigé
    corriger: str         # où et comment corriger


_E, _A = "Erreur", "Alerte"
_OUV, _EQ, _ES, _VAR, _TEL = "Ouvrage", "Équipements", "Liste des E/S et matériel", "Variables", "Télétransmission"

REGLES: dict[str, Regle] = {r.code: r for r in [
    # --- Ouvrage
    Regle("R-OUV-01", "Identification de l'ouvrage incomplète", _E, _OUV,
          "Sans lieu, code et libellé, les noms de variables et les fichiers livrés ne sont pas identifiables.",
          "Compléter la fiche de l'ouvrage."),
    Regle("R-OUV-02", "Lieu mal formé", _E, _OUV,
          "Le lieu entre dans chaque repère et chaque nom de variable : un format différent casse la charte.",
          "Saisir 4 caractères (lettres majuscules ou chiffres) dans la fiche de l'ouvrage."),
    Regle("R-OUV-03", "Code d'ouvrage mal formé", _E, _OUV,
          "Le code d'ouvrage entre dans les repères : un format différent casse la charte.",
          "Saisir 2 lettres majuscules dans la fiche de l'ouvrage."),
    Regle("R-OUV-04", "Numéro d'ouvrage invalide", _E, _OUV,
          "Le numéro distingue deux ouvrages du même lieu : invalide, il crée des repères ambigus.",
          "Saisir un numéro de 01 à 99, ou le laisser vide pour un ouvrage historique."),
    Regle("R-OUV-05", "Sous-ensemble mal formé", _E, _OUV,
          "Le code du sous-ensemble entre dans le repère des équipements.",
          "Saisir 2 caractères (lettres majuscules ou chiffres)."),
    Regle("R-OUV-06", "Sous-ensemble déclaré deux fois", _E, _OUV,
          "Deux sous-ensembles de même code produisent des repères en double.",
          "Supprimer ou renommer le doublon dans la fiche de l'ouvrage."),
    # --- Équipements
    Regle("R-EQ-01", "Équipement non validé", _E, _EQ,
          "Un paramétrage non validé peut encore changer : les E/S et variables qui en découlent ne sont pas sûres.",
          "Ouvrir la fiche de l'équipement, vérifier puis valider."),
    Regle("R-EQ-02", "Inventaire vide", _A, _EQ,
          "Un ouvrage sans équipement ne produit aucune E/S ni variable.",
          "Ajouter les équipements dans l'inventaire."),
    Regle("R-EQ-03", "Modèle d'équipement incohérent", _E, _EQ,
          "Le modèle utilisé contient des signaux contradictoires : les variables générées seraient fausses.",
          "Corriger le modèle dans le référentiel métier, ou changer de modèle."),
    Regle("R-EQ-04", "Type absent du catalogue", _E, _EQ,
          "Sans type connu, OGIAS ne sait pas quels signaux produire.",
          "Choisir un type existant ou l'ajouter au référentiel métier."),
    Regle("R-EQ-05", "Sous-ensemble non déclaré", _E, _EQ,
          "L'équipement référence un sous-ensemble absent de l'ouvrage : son repère est invalide.",
          "Déclarer le sous-ensemble dans la fiche de l'ouvrage ou corriger l'équipement."),
    Regle("R-EQ-06", "Numéro d'équipement mal formé", _E, _EQ,
          "Le numéro entre dans le repère : un format différent casse la charte.",
          "Saisir 2 chiffres (01 à 99)."),
    Regle("R-EQ-07", "Repère en double", _E, _EQ,
          "Deux équipements de même repère produisent des noms de variables identiques.",
          "Renuméroter l'un des deux équipements."),
    Regle("R-EQ-08", "Option inconnue", _A, _EQ,
          "Une option inconnue du type n'a aucun effet : l'information attendue ne sera pas produite.",
          "Retirer l'option ou compléter le type dans le référentiel métier."),
    Regle("R-EQ-09", "Signal obligatoire retiré", _A, _EQ,
          "Une information obligatoire du type manquera en supervision.",
          "Rétablir le signal, ou le remplacer par un signal propre équivalent."),
    Regle("R-EQ-10", "Information attendue non décidée", _E, _EQ,
          "Une règle du référentiel propose une information : sans décision, la liste des variables n'est pas figée.",
          "Dans la fiche de l'équipement, retenir l'information ou l'écarter avec un motif."),
    Regle("R-EQ-11", "Information écartée sans motif", _A, _EQ,
          "Un écart non motivé ne se justifie pas à la recette.",
          "Écrire le motif dans la fiche de l'équipement."),
    Regle("R-EQ-12", "Signal accepté dont la règle n'est plus satisfaite", _A, _EQ,
          "Le signal n'est plus généré alors qu'il avait été accepté : une information disparaît sans décision.",
          "Vérifier les E/S de l'équipement, puis confirmer ou retirer le signal."),
    Regle("R-EQ-13", "Adresse conservée pour un signal non retenu", _A, _EQ,
          "Une adresse reste réservée sans variable : elle sera réutilisée si le signal revient.",
          "Libérer l'adresse si le signal ne doit pas revenir."),
    Regle("R-EQ-14", "Signal propre incohérent", _E, _EQ,
          "Le sens ou la nature du signal propre contredit sa famille : l'E/S ou la variable serait fausse.",
          "Corriger le signal propre dans la fiche de l'équipement."),
    Regle("R-EQ-15", "Information calculée sans source", _A, _EQ,
          "Une information calculée (position, marche…) n'a ni E/S de retour ni ordre pour la calculer.",
          "Ajouter les E/S nécessaires ou retirer l'information."),
    Regle("R-EQ-16", "Informations transmises sans E/S physique", _A, _EQ,
          "L'équipement transmet des informations sans aucune E/S câblée ni liaison déclarée.",
          "Ajouter les E/S câblées ou confirmer une liaison par communication."),
    # --- Noms
    Regle("R-NOM-01", "Nom trop long", _E, _VAR,
          "Control Expert et TOPKAPI refusent ou tronquent les noms trop longs.",
          "Raccourcir le code du signal ou du repère."),
    Regle("R-NOM-02", "Caractères non autorisés dans un nom", _E, _VAR,
          "Les logiciels cibles refusent ces caractères à l'import.",
          "N'utiliser que lettres, chiffres et _ simple."),
    Regle("R-NOM-03", "Nom en double", _E, _VAR,
          "Deux variables de même nom : l'import automate ou supervision échoue ou en écrase une.",
          "Renommer l'un des signaux ou renuméroter l'équipement."),
    Regle("R-NOM-04", "Ouvrages du même programme en collision de noms", _E, _VAR,
          "Deux ouvrages du même programme automate emploient les mêmes noms.",
          "Mettre le lieu dans les noms ou renuméroter l'un des ouvrages (aucun renommage automatique)."),
    # --- E/S physiques et matériel
    Regle("R-ES-01", "E/S non validées", _A, _ES,
          "Des E/S restent à valider : leur contenu peut encore changer avant le câblage.",
          "Valider les E/S dans la Liste des E/S."),
    Regle("R-ES-02", "Adresse physique manquante", _A, _ES,
          "Une E/S câblée sans adresse %I / %Q n'est reliée à aucune voie.",
          "Implanter l'E/S sur une voie dans l'écran Matériel."),
    Regle("R-ES-03", "Adresse physique en double", _E, _ES,
          "Deux E/S sur la même adresse : un signal de terrain en écrase un autre.",
          "Déplacer l'une des E/S sur une voie libre."),
    Regle("R-ES-04", "Préfixe d'adresse incohérent", _A, _ES,
          "Le préfixe ne correspond pas à la nature (ET %I, ST %Q, EA %IW, SA %QW).",
          "Corriger l'adresse ou la nature de l'E/S."),
    Regle("R-ES-05", "Voie déjà affectée", _E, _ES,
          "Deux E/S sur la même voie d'un module.",
          "Déplacer l'une des E/S dans l'écran Matériel."),
    Regle("R-ES-06", "Module non déclaré", _E, _ES,
          "L'E/S est placée sur un module absent de la configuration.",
          "Déclarer le module ou déplacer l'E/S."),
    Regle("R-ES-07", "E/S sur un module de mauvaise nature", _E, _ES,
          "Une entrée sur un module de sorties (ou l'inverse) ne fonctionnera pas.",
          "Déplacer l'E/S sur un module de sa nature."),
    Regle("R-ES-08", "Voie hors du module", _E, _ES,
          "Le numéro de voie dépasse la capacité du module.",
          "Choisir une voie existante du module."),
    Regle("R-ES-09", "Réserve d'un module sous le seuil", _A, _ES,
          "Trop peu de voies libres pour les évolutions futures.",
          "Ajouter une carte ou répartir les E/S."),
    Regle("R-ES-10", "Voie d'E/S non renseignée", _E, _ES,
          "Une E/S de l'inventaire validé n'a pas de voie : elle ne sera pas câblée.",
          "Implanter l'E/S dans l'écran Matériel."),
    # --- Variables
    Regle("R-VAR-01", "Type logique inconnu", _E, _VAR,
          "Sans type connu, l'occupation mémoire ne peut pas être calculée.",
          "Corriger le type dans le référentiel métier."),
    Regle("R-VAR-02", "Variable sans adresse", _E, _VAR,
          "La variable n'a pas d'adresse dans la table d'échange : elle n'arrive pas en supervision.",
          "Calculer puis valider les adresses dans l'écran Variables."),
    Regle("R-VAR-03", "Adresse non reconnue", _E, _VAR,
          "L'adresse n'est pas au format %MW (bit de 0 à 15).",
          "Corriger l'adresse dans l'écran Variables."),
    Regle("R-VAR-04", "Format d'adresse incohérent avec le type", _E, _VAR,
          "Un BOOL doit être un bit (%MWn.b), une valeur numérique un mot (%MWn).",
          "Corriger l'adresse ou le type."),
    Regle("R-VAR-05", "Chevauchement d'adresses", _E, _VAR,
          "Deux variables partagent la même mémoire : l'une écrase l'autre dans l'automate.",
          "Déplacer l'une des variables (recalcul de l'adressage)."),
    Regle("R-VAR-06", "Adresse hors de la plage de la famille", _E, _VAR,
          "La variable sort de la plage réservée à sa famille : la supervision ne la lira pas où elle l'attend.",
          "Recalculer l'adressage ou corriger la plage de l'ouvrage."),
    Regle("R-VAR-07", "Variable 32 bits sur adresse impaire", _E, _VAR,
          "M340 et M580 refusent une variable 32 bits sur une adresse impaire.",
          "Placer la variable sur une adresse paire."),
    Regle("R-VAR-08", "RTR pas en miroir de son TR", _E, _VAR,
          "Le retour de téléréglage n'est pas à l'adresse attendue en face de sa consigne.",
          "Recalculer l'adressage TR / RTR."),
    Regle("R-VAR-09", "Types TR / RTR différents", _E, _VAR,
          "La consigne et son retour n'ont pas le même type : la supervision comparera des valeurs incompatibles.",
          "Aligner les types dans le référentiel ou déclarer la conversion."),
    Regle("R-VAR-10", "Libellé TOPKAPI trop long", _A, _VAR,
          "TOPKAPI tronque les libellés au-delà de 40 caractères.",
          "Raccourcir le libellé."),
    Regle("R-VAR-11", "Adresses proposées non validées", _A, _VAR,
          "Des adresses sont proposées mais pas validées par l'automaticien : elles peuvent encore bouger.",
          "Valider les adresses dans l'écran Variables."),
    # --- Chaîne de l'information (contrôles transversaux, 18/11)
    Regle("R-CHA-01", "Variable liée à une E/S introuvable", _E, _VAR,
          "L'E/S indiquée comme source de la variable n'existe pas dans la liste des E/S : le fil est rompu, la "
          "variable ne reflète aucun signal de terrain.",
          "Rétablir l'E/S dans la fiche de l'équipement ou corriger la source de la variable."),
    Regle("R-CHA-02", "E/S liée à une variable introuvable", _E, _ES,
          "L'E/S désigne une variable d'échange qui n'existe pas : son information n'arrive pas en supervision.",
          "Vérifier les signaux retenus de l'équipement, puis régénérer les variables."),
    # --- Télétransmission
    Regle("R-TEL-01", "Téléréglage sans retour", _A, _TEL,
          "Une consigne (TR) sans retour (RTR) : la supervision ne peut pas vérifier que la consigne est appliquée.",
          "Ajouter le retour de téléréglage dans le référentiel ou justifier son absence."),
    Regle("R-TEL-02", "Adresse de télétransmission négative", _E, _TEL,
          "Le décalage Modbus réglé fait passer des adresses sous zéro : elles sont impossibles à lire.",
          "Corriger le décalage dans les paramètres d'adressage."),
    Regle("R-TEL-03", "Libellés TOPKAPI identiques sur un équipement", _A, _TEL,
          "Deux informations du même équipement portent le même libellé : l'opérateur ne peut pas les distinguer.",
          "Différencier les libellés dans la fiche de l'équipement ou le référentiel."),
    Regle("R-TEL-04", "Ligne de télétransmission incohérente", _E, _TEL,
          "La ligne de la table de télétransmission existante contredit sa source.",
          "Corriger la ligne dans la table de télétransmission."),
    Regle("R-TEL-05", "Informations sans source", _A, _TEL,
          "Des informations de la table n'ont pas de variable source.",
          "Associer une variable ou déclarer l'information non accessible."),
    Regle("R-TEL-06", "Lignes à compléter", _A, _TEL,
          "Fonction ou accès TOPKAPI restent à valider.",
          "Compléter les lignes dans la table de télétransmission."),
    # --- Projet existant
    Regle("R-EXI-01", "Doublon d'identification", _E, _VAR,
          "Deux variables existantes sont rattachées au même signal du même équipement.",
          "Corriger l'identification de l'une des deux."),
    Regle("R-EXI-02", "BOOL sur un mot entier", _A, _VAR,
          "Un booléen placé sur un mot entier : un bit manque probablement dans l'adresse.",
          "Vérifier l'adresse dans le programme existant."),
    Regle("R-EXI-03", "Variable 32 bits sur adresse impaire (existant)", _E, _VAR,
          "L'automate refuse une variable 32 bits sur une adresse impaire.",
          "Vérifier le programme existant (aucune correction automatique)."),
    Regle("R-EXI-04", "Chevauchement mémoire (existant)", _E, _VAR,
          "Deux variables existantes partagent la même mémoire.",
          "Vérifier le programme existant (aucune correction automatique)."),
    Regle("R-EXI-05", "Identification à confirmer", _A, _VAR,
          "Le rattachement de la variable existante est probable mais pas certain.",
          "Confirmer ou corriger l'identification."),
    Regle("R-EXI-06", "Identification incohérente", _E, _VAR,
          "Le rattachement de la variable existante contredit ses caractéristiques.",
          "Corriger l'identification."),
]}


def regle(code: str) -> Regle | None:
    return REGLES.get(code)


def decrire(code: str) -> dict:
    """Description d'une règle pour l'interface et les rapports ({} si le code est inconnu)."""
    r = REGLES.get(code)
    return {} if r is None else {"code": r.code, "titre": r.titre, "gravite": r.gravite, "etape": r.etape,
                                 "pourquoi": r.pourquoi, "corriger": r.corriger}


def controler_chaine(ouvrage, variables, points):
    """Contrôles transversaux : fil E/S ↔ variable, paires TR / RTR, libellés TOPKAPI. [Anomalie]."""
    from .modele import Anomalie
    sortie = []
    noms_points = {p.nom for p in points}
    noms_variables = {v.nom for v in variables}
    for v in variables:
        if v.nom_es and v.nom_es not in noms_points:
            sortie.append(Anomalie("Erreur", v.repere, f"{v.nom} : E/S source {v.nom_es} introuvable dans la liste des "
                                   "E/S.", v.ident_eq, "Variables", "R-CHA-01"))
    for p in points:
        if p.variable and p.variable not in noms_variables:
            sortie.append(Anomalie("Erreur", p.repere, f"{p.nom} : variable d'échange {p.variable} introuvable.",
                                   p.ident_eq, "Liste des E/S et matériel", "R-CHA-02"))
    rtr = {(v.ident_eq, v.code) for v in variables if v.famille == "RTR"}
    for v in variables:
        if v.famille == "TR" and (v.ident_eq, v.code) not in rtr:
            sortie.append(Anomalie("Alerte", v.repere, f"{v.nom} : téléréglage sans retour (RTR) correspondant.",
                                   v.ident_eq, "Variables", "R-TEL-01"))
    par_libelle: dict[tuple[str, str], list[str]] = {}
    for v in variables:
        if v.libelle_topkapi:
            par_libelle.setdefault((v.ident_eq, v.libelle_topkapi.strip().lower()), []).append(v.nom)
    reperes = {v.ident_eq: v.repere for v in variables}
    for (ident, _libelle), noms in sorted(par_libelle.items()):
        if len(noms) > 1:
            sortie.append(Anomalie("Alerte", reperes.get(ident, ""), f"Libellé TOPKAPI identique pour {', '.join(noms)}.",
                                   ident, "Variables", "R-TEL-03"))
    if ouvrage.decalage_modbus and ouvrage.mode == "Neuf":
        from .modele import _mot
        negatives = [v.nom for v in variables if v.adresse and _mot(v.adresse) and _mot(v.adresse)[0] + ouvrage.decalage_modbus < 0]
        if negatives:
            sortie.append(Anomalie("Erreur", "Télétransmission", f"Décalage {ouvrage.decalage_modbus} : {len(negatives)} "
                                   f"adresse(s) de télétransmission négative(s) (ex. {negatives[0]}).", "", "Variables",
                                   "R-TEL-02"))
    return sortie
