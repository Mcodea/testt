"""Parcours guidé : points bloquants et points à vérifier de chaque étape (retours d'essai 4, 5 et 7 du 12/11/2026).

Pour chaque étape du parcours d'un ouvrage neuf (1 Équipements → 2 Liste des E/S → 3 Matériel → 4 Variables →
5 Recette), `etat_parcours` liste **tous** les points qui empêchent de passer à l'étape suivante (bloquants) et
ceux qui méritent un contrôle sans bloquer (à vérifier). Chaque point porte un message en clair et une cible
(vue et, le cas échéant, équipement) pour que l'interface mène l'utilisateur à l'endroit à corriger.

Lecture seule : rien n'est modifié, rien n'est deviné. Les règles reprennent exactement les contrôles déjà
appliqués par le moteur et l'interface (aucune nouvelle exigence cachée).
"""
from __future__ import annotations

ETAPES = (("ouvrage", "Équipements"), ("es", "Liste des E/S"), ("materiel", "Matériel"),
          ("variables", "Variables"), ("recette", "Recette"))
MAX_DETAILS = 20          # points détaillés par catégorie ; le reste est résumé


def _point(code, message, vue, ident_eq="", gravite="bloquant"):
    return {"code": code, "message": message, "vue": vue, "ident_eq": ident_eq, "gravite": gravite}


def _liste(code, items, gabarit, vue, gravite="bloquant"):
    """Un point par élément (au plus MAX_DETAILS), puis un point de synthèse pour le reste."""
    sortie = [_point(code, gabarit.format(nom=nom), vue, ident, gravite) for ident, nom in items[:MAX_DETAILS]]
    if len(items) > MAX_DETAILS:
        sortie.append(_point(code, f"… et {len(items) - MAX_DETAILS} autre(s) du même type.", vue, "", gravite))
    return sortie


def _etape_equipements(s):
    o, pts = s.ouvrage, []
    if o.statut == "Brouillon":
        pts.append(_point("creation", "Confirmez la création de l'ouvrage (fiche d'identification).", "ouvrage"))
    for champ, libelle in (("lieu", "le lieu"), ("code_ouvrage", "le type d'ouvrage"),
                           ("numero_ouvrage", "le numéro d'ouvrage"), ("libelle", "le libellé de l'ouvrage"),
                           ("automate", "l'automate")):
        if not str(getattr(o, champ, "") or "").strip():
            pts.append(_point(f"identification:{champ}", f"Renseignez {libelle} dans la fiche de l'ouvrage.", "ouvrage"))
    if not o.equipements:
        pts.append(_point("aucun_equipement", "Ajoutez au moins un équipement (bouton « Structure / ajouter »).",
                          "ouvrage"))
    a_valider = [(e.ident, o.repere(e)) for e in s.equipements_tries() if not e.valide]
    pts += _liste("equipement_a_valider", a_valider, "Validez le paramétrage de l'équipement {nom}.", "ouvrage")
    return pts


def _etape_es(s):
    o, pts = s.ouvrage, []
    points = s.points()
    par_eq: dict[str, list] = {}
    for p in points:
        if not p.contenu_valide:
            par_eq.setdefault(p.ident_eq, []).append(p.nom)
    items = [(i, f"{o.repere(o.equipement(i))} ({len(n)} E/S, ex. {n[0]})") for i, n in par_eq.items()]
    pts += _liste("es_a_valider", items, "Validez le contenu des E/S de {nom}.", "es")
    avec_es = {p.ident_eq for p in points}
    sans = [(e.ident, o.repere(e)) for e in s.equipements_tries() if e.ident not in avec_es]
    pts += _liste("equipement_sans_es", sans, "L'équipement {nom} n'a aucune E/S physique : vérifiez ses options.",
                  "es", "à vérifier")
    return pts


def _etape_materiel(s):
    from . import materiel
    o, pts = s.ouvrage, []
    plat = ""
    try:
        plat = materiel.plateforme_materiel(o.automate)[0]
    except materiel.CatalogueMaterielErreur as exc:
        pts.append(_point("gamme_non_decrite", str(exc), "materiel"))
    if not o.modules and plat in ("STB", "S4W"):
        nom = "un îlot Advantys STB" if plat == "STB" else "un poste SOFREL S4W"
        pts.append(_point("materiel_indicatif", f"Matériel proposé à titre indicatif pour {nom} : l'implantation "
                                                "des voies n'est pas encore prise en charge (correspondance des "
                                                "voies à établir).", "materiel"))
    elif not o.modules:
        pts.append(_point("materiel_non_calcule", "Calculez puis retenez le matériel (racks et cartes).", "materiel"))
    elif not o.materiel_valide:
        pts.append(_point("materiel_non_valide", "Validez le matériel retenu.", "materiel"))
    b = s.bilan_es()
    if o.modules and b["sans_adresse"]:
        pts.append(_point("es_sans_voie", f"{b['sans_adresse']} E/S câblée(s) sans voie : implantez-les sur les cartes.",
                          "materiel"))
    if o.modules and b["voies_non_validees"]:
        pts.append(_point("voies_a_valider", f"{b['voies_non_validees']} affectation(s) de voie à valider.", "materiel"))
    if o.separation_secours:                              # B4 : propositions à confirmer, cartes partagées
        for g in s.groupes_secours_proposes()[:MAX_DETAILS]:
            reps = ", ".join(m["repere"] for m in g["membres"])
            pts.append(_point("groupe_secours_a_confirmer", f"Groupe de secours probable à confirmer ou refuser : "
                                                            f"{reps}.", "materiel", "", "à vérifier"))
        from .cartes_es import secours_partageant_une_carte
        for k, reps in secours_partageant_une_carte(s.points(), o.modules, s.groupes_secours_actifs()):
            pts.append(_point("secours_meme_carte", f"La carte {k} porte des E/S de {', '.join(reps)}, "
                                                    "du même groupe de secours.", "materiel", "", "à vérifier"))
    for rack, libres in sorted(materiel.emplacements_libres(o.racks, o.modules).items()):   # B3
        if o.racks and libres < o.emplacements_libres_rack:
            pts.append(_point("emplacements_libres", f"Rack {rack} : {max(libres, 0)} emplacement(s) libre(s) "
                                                     f"pour {o.emplacements_libres_rack} souhaité(s).", "materiel",
                              "", "à vérifier"))
    return pts


def _etape_variables(s):
    pts = []
    try:
        plan = s.plan_adressage()
    except Exception as exc:                               # noqa: BLE001 — affiché, jamais avalé en silence
        return [_point("adressage_impossible", f"Plan d'adressage impossible : {exc}", "variables")]
    for niveau, message in plan.conflits[:MAX_DETAILS]:
        pts.append(_point("conflit_adressage", f"Conflit d'adressage ({niveau}) : {message}", "variables"))
    auto = [a for a in plan.affectations if a.niveau == "automate"]
    non_resolues = [a for a in auto if a.etat in ("non résolue", "en conflit")]
    a_valider = [a for a in auto if a.etat in ("à valider", "proposée")]
    pts += _liste("variable_sans_adresse", [(a.ident_eq, a.nom) for a in non_resolues],
                  "Attribuez une adresse à la variable {nom}.", "variables")
    if a_valider:
        pts.append(_point("variables_a_valider", f"{len(a_valider)} adresse(s) de variable à valider "
                                                 f"(ex. {a_valider[0].nom}).", "variables"))
    for m in s.anomalies_homonymes()[:MAX_DETAILS]:
        pts.append(_point("homonyme", str(m), "variables"))
    if not str(s.ouvrage.nom_projet or "").strip():
        pts.append(_point("programme_non_renseigne", "Nom du programme automate non renseigné : les homonymes avec "
                                                     "les autres ouvrages du même programme ne sont pas contrôlés.",
                          "ouvrage", "", "à vérifier"))
    return pts


def _etape_recette(s):
    return [_point("exports_non_qualifies", "Exports Control Expert, SOFREL S4W et TOPKAPI non qualifiés : "
                                            "à importer et vérifier dans les logiciels cibles.", "recette", "",
                   "à vérifier")]


CONTROLES = {"ouvrage": _etape_equipements, "es": _etape_es, "materiel": _etape_materiel,
             "variables": _etape_variables, "recette": _etape_recette}


def etat_parcours(session):
    """[{etape, vue, libelle, pret, bloquants, a_verifier}] pour un ouvrage neuf ; [] pour un projet existant
    (le parcours d'un existant suit l'inventaire, non ces étapes). Une étape n'est prête que si toutes les
    précédentes le sont : les points d'une étape suivante sont listés, mais elle reste « non prête »."""
    if session.ouvrage.mode != "Neuf":
        return []
    sortie, precedentes_pretes = [], True
    for n, (vue, libelle) in enumerate(ETAPES, 1):
        points = CONTROLES[vue](session)
        bloquants = [p for p in points if p["gravite"] == "bloquant"]
        pret = precedentes_pretes and not bloquants
        sortie.append({"etape": n, "vue": vue, "libelle": libelle, "pret": pret, "bloquants": bloquants,
                       "a_verifier": [p for p in points if p["gravite"] != "bloquant"]})
        precedentes_pretes = pret
    return sortie
