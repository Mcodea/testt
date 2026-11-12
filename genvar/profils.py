"""Version calculée des profils et état de synchronisation des équipements (décisions R2 / R3).

Un **profil** est un type d'équipement du référentiel avec ses signaux, ses règles et ses modèles. Sa version
n'est stockée nulle part (aucune seconde source de vérité) : elle se déduit de l'historique des révisions
publiées, en comparant l'empreinte SHA-256 du profil d'une révision à l'autre. La version 1 est celle de la
première révision où le profil apparaît ; elle s'incrémente à chaque révision publiée où l'empreinte change.

L'**état de synchronisation** compare le profil figé dans un ouvrage au profil publié, sans rien modifier :

- « À jour » : aucun écart ;
- « Mise à jour disponible » : écarts adoptables sans renommage ni conflit (adoption contrôlée, L2) ;
- « Mise à jour à examiner » : renommage à confirmer, surcharge locale en conflit (R4), blocage de l'adoption (donnée portée par une clé qui
  disparaît, type retiré…) ou modèle figé différent du modèle publié, que l'adoption ne migre pas.
"""
from __future__ import annotations

import copy

from .catalogue import Catalogue
from .referentiel_depot import DepotRefuse, empreinte

A_JOUR = "À jour"
DISPONIBLE = "Mise à jour disponible"
A_EXAMINER = "Mise à jour à examiner"
_GRAVITE = {A_JOUR: 0, DISPONIBLE: 1, A_EXAMINER: 2}


def _pire(*etats):
    return max(etats, key=lambda e: _GRAVITE[e])


def _parties(donnees, code):
    c = donnees.get("catalogue", {})
    t = next((x for x in c.get("types", []) if x.get("code") == code), None)
    if t is None:
        return None
    catalogue = {"type": t, "signaux": [s for s in c.get("signaux", []) if s.get("type") == code],
                 "regles": [r for r in c.get("regles", []) if r.get("type") == code]}
    modeles = {n: m for n, m in sorted((donnees.get("modeles", {}).get("modeles", {}) or {}).items())
               if isinstance(m, dict) and m.get("type") == code}
    return catalogue, modeles


def empreinte_profil(donnees, code):
    """Empreinte SHA-256 du profil `code` dans des données de révision ({"catalogue", "modeles"}), ou None."""
    p = _parties(donnees, code)
    return None if p is None else empreinte({**p[0], "modeles": p[1]})


def empreinte_catalogue_profil(donnees, code):
    """Partie « catalogue » du profil (type, signaux, règles) : c'est elle que fige un ouvrage enregistré."""
    p = _parties(donnees, code)
    return None if p is None else empreinte(p[0])


def versions(depot):
    """{code: [{revision, version, empreinte, empreinte_catalogue}]} : une entrée par révision où le profil change.

    Sans historique, le référentiel en service compte comme révision 0. Lecture seule : les révisions altérées
    ou illisibles sont ignorées (le dépôt les signale par ailleurs)."""
    numeros = sorted(r["numero"] for r in depot.revisions())
    sources = []
    for n in numeros:
        try:
            sources.append((n, depot.revision(n)["donnees"]))
        except DepotRefuse:
            continue
    if not sources:
        sources = [(0, depot.publie())]
    sortie: dict[str, list[dict]] = {}
    for n, donnees in sources:
        for t in donnees.get("catalogue", {}).get("types", []):
            code = t.get("code")
            e = empreinte_profil(donnees, code)
            hist = sortie.setdefault(code, [])
            if not hist or hist[-1]["empreinte"] != e:
                hist.append({"revision": n, "version": len(hist) + 1, "empreinte": e,
                             "empreinte_catalogue": empreinte_catalogue_profil(donnees, code)})
    return sortie


def version_publiee(depot, code, historique=None):
    hist = (historique if historique is not None else versions(depot)).get(code) or []
    return dict(hist[-1]) if hist else None


def version_figee(catalogue_ouvrage, code, historique):
    """Dernière version publiée dont la partie catalogue est identique à celle figée dans l'ouvrage, ou None
    (profil figé avant le cycle des révisions, ou adapté localement)."""
    donnees = {"catalogue": {"types": catalogue_ouvrage.types, "signaux": catalogue_ouvrage.signaux,
                             "regles": catalogue_ouvrage.regles}}
    e = empreinte_catalogue_profil(donnees, code)
    trouvees = [x for x in historique.get(code, []) if x["empreinte_catalogue"] == e]
    return dict(trouvees[-1]) if trouvees else None


def etat_synchronisation(ouvrage, catalogue_ouvrage, publie, correspondances=None):
    """{"types": {code: {etat, motifs}}, "equipements": {ident: {repere, type, etat, motifs}}}. Lecture seule."""
    from . import adoption
    c = publie["catalogue"]
    nouveau = Catalogue(copy.deepcopy(c["types"]), copy.deepcopy(c["signaux"]), c.get("version", ""),
                        copy.deepcopy(c.get("regles", [])))
    if correspondances is None:
        correspondances = publie.get("modeles", {}).get("correspondances", [])
    ecarts = {x["type"]: x for x in adoption.apercu(ouvrage, catalogue_ouvrage, nouveau, correspondances)}
    types: dict[str, dict] = {}
    communs: dict[str, tuple[str, list[str]]] = {}        # état et motifs partagés par tous les équipements du type
    for code in sorted({e.type for e in ouvrage.equipements}):
        x = ecarts.get(code)
        if x is None:
            types[code] = {"etat": A_JOUR, "motifs": []}
            communs[code] = (A_JOUR, [])
            continue
        motifs = list(x["bloquants"])
        if x["renommages"]:
            motifs.append(f"{len(x['renommages'])} renommage(s) à confirmer ligne à ligne.")
        resume = [f"{len(x[k])} {lib}" for k, lib in (("ajoutees", "information(s) ajoutée(s)"),
                                                       ("retirees", "retirée(s)"), ("modifiees", "modifiée(s)"),
                                                       ("regles", "règle(s) modifiée(s)")) if x[k]]
        resume_txt = [", ".join(resume) + "."] if resume else []
        communs[code] = (A_EXAMINER if motifs else DISPONIBLE, motifs + resume_txt)
        conflits = x.get("conflits") or []
        texte = ([f"{len(conflits)} surcharge(s) locale(s) en conflit avec le référentiel publié "
                  "(conservées, à examiner)."] if conflits else [])
        types[code] = {"etat": A_EXAMINER if motifs or conflits else DISPONIBLE,
                       "motifs": motifs + texte + resume_txt, "conflits": conflits}
    modeles_publies = publie.get("modeles", {}).get("modeles", {}) or {}
    equipements: dict[str, dict] = {}
    for eq in ouvrage.equipements:
        etat, motifs = communs[eq.type][0], list(communs[eq.type][1])
        propres = [c for c in types[eq.type].get("conflits", []) if c["ident"] == eq.ident]
        if propres:
            etat = _pire(etat, A_EXAMINER)
            motifs.append(f"{len(propres)} surcharge(s) locale(s) en conflit : "
                          + ", ".join(f"{c['cle']} ({c['propriete']})" for c in propres) + ".")
        if eq.modele and eq.modele in ouvrage.modeles_snapshot:
            m = adoption.apercu_modele(ouvrage, eq.modele, modeles_publies.get(eq.modele), catalogue_ouvrage,
                                       correspondances)
            if not m["identique"]:
                propres_m = [c for c in m["conflits"] if c["ident"] == eq.ident]
                if m["bloquants"] or m["renommages"] or propres_m:
                    etat = _pire(etat, A_EXAMINER)
                    motifs += m["bloquants"] + ([f"Modèle « {eq.modele} » : {len(m['renommages'])} renommage(s) à "
                                                 "confirmer."] if m["renommages"] else []) + (
                        [f"Modèle « {eq.modele} » : {len(propres_m)} surcharge(s) locale(s) en conflit."]
                        if propres_m else [])
                else:
                    etat = _pire(etat, DISPONIBLE)
                    motifs.append(f"Modèle « {eq.modele} » modifié dans le référentiel publié : reprise contrôlée "
                                  "du modèle disponible.")
        elif eq.modele and eq.modele not in modeles_publies:
            etat = _pire(etat, A_EXAMINER)
            motifs.append(f"Modèle « {eq.modele} » absent du référentiel publié (retiré ou renommé).")
        equipements[eq.ident] = {"repere": ouvrage.repere(eq), "type": eq.type, "etat": etat, "motifs": motifs}
    return {"types": types, "equipements": equipements}


def profils_modifies(avant, apres):
    """Codes des profils dont l'empreinte diffère entre deux états du référentiel (ajout et retrait compris)."""
    codes = {t.get("code") for d in (avant, apres) for t in d.get("catalogue", {}).get("types", [])}
    return sorted(c for c in codes if empreinte_profil(avant, c) != empreinte_profil(apres, c))


def rapport_impact(avant, apres, ouvrages, historique=None):
    """Rapport d'impact d'une révision (R5) : pour chaque profil modifié, les ouvrages enregistrés et leurs
    équipements concernés avec leur état de synchronisation vis-à-vis de `apres`. Lecture seule.

    `ouvrages` : [(repère, nom de fichier, ouvrage, catalogue figé, archivé)]."""
    from . import modeles as _modeles
    cible = copy.deepcopy(apres)
    c = cible["catalogue"]
    _modeles.completer_signaux(cible.setdefault("modeles", {}),
                               Catalogue(c["types"], c["signaux"], c.get("version", ""), c.get("regles", [])))
    modifies = profils_modifies(avant, apres)
    historique = historique or {}
    sortie = []
    for code in modifies:
        actuelle = version_publiee(None, code, historique)
        n = actuelle["version"] if actuelle else 0
        entree = {"profil": code, "version_actuelle": n or None,
                  "version_suivante": n + 1 if empreinte_profil(apres, code) else None,
                  "retire": empreinte_profil(apres, code) is None, "ouvrages": []}
        for repere, fichier, ouvrage, catalogue, archive in ouvrages:
            if not any(e.type == code for e in ouvrage.equipements):
                continue
            etat = etat_synchronisation(ouvrage, catalogue, cible)
            entree["ouvrages"].append({
                "repere": repere, "fichier": fichier, "archive": bool(archive),
                "etat": etat["types"][code]["etat"], "motifs": etat["types"][code]["motifs"],
                "equipements": [{"repere": x["repere"], "etat": x["etat"], "motifs": x["motifs"]}
                                for x in etat["equipements"].values() if x["type"] == code]})
        sortie.append(entree)
    return {"profils": sortie}
