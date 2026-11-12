"""Adoption contrôlée d'une nouvelle révision du référentiel par un ouvrage (décisions du 10/11/2026).

Principes :
- rien n'est appliqué sans acte explicite ; l'adoption se décide **type par type**, après un aperçu qui montre
  chaque ajout, retrait, renommage physique et renommage fonctionnel ;
- un type dont l'adoption renomme une variable n'est adopté que si l'utilisateur confirme les renommages ;
- les adresses (%MW, voies physiques), commentaires, décisions et correspondances TOPKAPI suivent les
  **correspondances** déclarées dans le référentiel (`correspondances` de referentiel_modeles.json) : elles ne
  sont jamais recalculées ni réaffectées ;
- un type est bloqué si l'adoption ferait disparaître un signal qui porte des données sans correspondance, si une
  correspondance écraserait une donnée existante, ou si elle change le type de l'équipement (le repère contient le
  code du type : décision R1 à valider) ;
- une sauvegarde horodatée du fichier précède l'application ; `annuler` rétablit l'état antérieur.
"""
from __future__ import annotations

import copy
import os
import shutil
import tempfile
from datetime import datetime

from .catalogue import Catalogue
from .modele import suffixe_physique

CHAMPS_DICT = ("adresses", "adresses_es", "commentaires", "libelles", "motifs", "es_meta")
CHAMPS_LISTE = ("exclus", "validees", "acceptes")
NATURES = ("ET", "ST", "EA", "SA")


class AdoptionRefusee(ValueError):
    """Adoption impossible ; l'ouvrage n'a pas été modifié."""


def _cle(s):
    return f"{s['famille']}_{s['code']}"


def noms(s):
    """(nom physique, nom fonctionnel) génériques d'un signal, avec « <repère> »."""
    physique = f"{s['es']}_<repère>_{suffixe_physique(s)}" if s.get("es") in NATURES else ""
    fonctionnel = f"{s['famille']}_<repère>_{s['code']}" if s.get("famille") != "ES" else ""
    return physique, fonctionnel


def controler_correspondances(correspondances, catalogue) -> list[str]:
    """Erreurs : forme, ancienne clé encore en service, nouvelle clé absente, ambiguïtés."""
    erreurs: list[str] = []
    if not isinstance(correspondances, list):
        return ["Correspondances : liste attendue."]
    vues_a: dict = {}
    vues_n: dict = {}
    actives = {(s["type"], _cle(s)) for s in catalogue.signaux}
    for n, c in enumerate(correspondances, 1):
        if not isinstance(c, dict) or not all(c.get(k) for k in ("type", "ancienne", "nouvelle")):
            erreurs.append(f"Correspondance {n} : type, ancienne et nouvelle clé obligatoires.")
            continue
        a = (c["type"], c["ancienne"])
        b = (c.get("type_nouveau") or c["type"], c["nouvelle"])
        if a in actives:
            erreurs.append(f"Correspondance {a[0]}.{a[1]} : l'ancienne clé est toujours en service.")
        if b not in actives:
            erreurs.append(f"Correspondance {a[0]}.{a[1]} → {b[0]}.{b[1]} : nouvelle clé absente du référentiel.")
        if a in vues_a:
            erreurs.append(f"Correspondance {a[0]}.{a[1]} : citée deux fois (ambiguë).")
        if b in vues_n:
            erreurs.append(f"Correspondance → {b[0]}.{b[1]} : visée par deux anciennes clés (ambiguë).")
        vues_a[a], vues_n[b] = n, n
    return erreurs


def _porte_donnees(ouvrage, eq, cle):
    if any(cle in getattr(eq, c) for c in CHAMPS_DICT + CHAMPS_LISTE):
        return True
    if any(k.split(":", 1)[-1] == cle for k in eq.traces):
        return True
    return any(x.ident_eq == eq.ident and x.cle == cle for x in list(ouvrage.existantes) + list(ouvrage.table_tt))


# Surcharges locales d'un équipement et propriété maître dont elles dépendent (décision R4).
# (propriété affichée, champ de l'équipement, sous-clé d'es_meta ou None, champs maîtres concernés)
SURCHARGES = (
    ("libelle", "libelles", None, ("information",)),
    ("commentaire", "commentaires", None, ("information",)),
    ("designation", "es_meta", "designation", ("information",)),
    ("type", "es_meta", "type", ("type_logique",)),
    ("sens", "es_meta", "sens", ("sens",)),
)
PROPRIETES_STANDARD = tuple(x[0] for x in SURCHARGES) + ("exclusion",)


def conflits_surcharges(eq, a, b):
    """Propriétés maîtres modifiées entre `a` et `b` ({clé: signal}) alors que l'équipement les surcharge
    ou exclut le signal. La surcharge est conservée : la liste sert seulement à l'afficher (R4)."""
    sortie = []
    for k in sorted(set(a) & set(b)):
        if a[k] == b[k]:
            continue
        for prop, champ, sous_cle, maitres in SURCHARGES:
            valeur = getattr(eq, champ, {}).get(k)
            if sous_cle is not None:
                valeur = valeur.get(sous_cle) if isinstance(valeur, dict) else None
            if valeur in (None, ""):
                continue
            changes = [m for m in maitres if a[k].get(m, "") != b[k].get(m, "")]
            if changes:
                sortie.append({"ident": eq.ident, "equipement": eq.code_court(), "cle": k, "propriete": prop,
                               "local": valeur, "ancien": a[k].get(changes[0], ""), "nouveau": b[k].get(changes[0], "")})
        if k in eq.exclus:
            sortie.append({"ident": eq.ident, "equipement": eq.code_court(), "cle": k, "propriete": "exclusion",
                           "local": "exclu", "ancien": a[k].get("information", ""), "nouveau": b[k].get("information", "")})
    return sortie


def apercu(ouvrage, ancien, nouveau, correspondances):
    """Aperçu par type utilisé : ajouts, retraits, renommages et motifs de blocage. Rien n'est modifié."""
    corr = {(c["type"], c["ancienne"]): c for c in correspondances or [] if isinstance(c, dict)}
    types_nouveaux = {t["code"] for t in nouveau.types}
    sortie: list[dict] = []
    for t in sorted({e.type for e in ouvrage.equipements}):
        eqs = [e for e in ouvrage.equipements if e.type == t]
        a = {_cle(s): s for s in ancien.signaux_du_type(t)}
        b = {_cle(s): s for s in nouveau.signaux_du_type(t)} if t in types_nouveaux else {}
        ra = {r.get("id"): r for r in ancien.regles if r.get("type") == t}
        rb = {r.get("id"): r for r in nouveau.regles if r.get("type") == t}
        renommages: list[dict] = []
        bloquants: list[str] = []
        cibles: set[str] = set()
        for k, s in a.items():
            c = corr.get((t, k))
            if k not in b and c:
                tn = c.get("type_nouveau") or t
                cible = next((x for x in nouveau.signaux_du_type(tn) if _cle(x) == c["nouvelle"]), None)
                if tn != t:
                    bloquants.append(f"{t}.{k} → {tn}.{c['nouvelle']} : changement de type, le repère changerait "
                                     "(décision R1 à valider).")
                if cible is None:
                    bloquants.append(f"{t}.{k} : correspondance vers une clé absente.")
                    continue
                cibles.add(c["nouvelle"])
                for e in eqs:
                    if c["nouvelle"] in a or _porte_donnees(ouvrage, e, c["nouvelle"]):
                        bloquants.append(f"{t}.{k} → {c['nouvelle']} : la nouvelle clé porte déjà des données dans "
                                         "l'équipement ; aucune donnée n'est écrasée.")
                        break
                renommages.append({"ancienne": k, "nouvelle": c["nouvelle"], "type_nouveau": tn,
                                   "physique": [noms(s)[0], noms(cible)[0]],
                                   "fonctionnel": [noms(s)[1], noms(cible)[1]]})
            elif k in b and noms(s) != noms(b[k]):
                renommages.append({"ancienne": k, "nouvelle": k, "type_nouveau": t,
                                   "physique": [noms(s)[0], noms(b[k])[0]], "fonctionnel": [noms(s)[1], noms(b[k])[1]]})
        retirees = sorted(k for k in a if k not in b and (t, k) not in corr)
        for k in retirees:
            porteurs = [e.code_court() for e in eqs if _porte_donnees(ouvrage, e, k)]
            if porteurs:
                bloquants.append(f"{t}.{k} disparaît et porte des données ({', '.join(porteurs)}) : déclarer une "
                                 "correspondance avant d'adopter.")
        if t not in types_nouveaux:
            bloquants.append(f"Type {t} absent du référentiel actuel : conversion à valider (décision R1).")
        ecart = {"type": t, "equipements": [e.code_court() for e in eqs],
                 "ajoutees": sorted(k for k in b if k not in a and k not in cibles),
                 "retirees": retirees,
                 "modifiees": sorted(k for k in set(a) & set(b) if a[k] != b[k]),
                 "regles": sorted(k for k in set(ra) | set(rb) if ra.get(k) != rb.get(k)),
                 "renommages": renommages, "bloquants": sorted(set(bloquants)),
                 "conflits": [c for e in eqs for c in conflits_surcharges(e, a, b)]}
        if any(ecart[k] for k in ("ajoutees", "retirees", "modifiees", "regles", "renommages", "bloquants")):
            ecart["adoptable"] = not ecart["bloquants"]
            sortie.append(ecart)
    return sortie


def apercu_modele(ouvrage, nom, publie, catalogue_ouvrage, correspondances):
    """Aperçu de la reprise du modèle figé `nom` par sa version publiée `publie` (None : absent).

    Les signaux actuels sont ceux de la copie figée, ou ceux du catalogue figé du type pour une ancienne copie
    sans signaux. Mêmes règles que `apercu` : clé qui disparaît en portant des données → blocage, correspondance
    du type → renommage avec report des données, nom changé → renommage à confirmer. Rien n'est modifié."""
    fige = ouvrage.modeles_snapshot.get(nom) or {}
    eqs = [e for e in ouvrage.equipements if e.modele == nom]
    t = fige.get("type") or (eqs[0].type if eqs else "")
    sortie = {"modele": nom, "type": t, "equipements": [e.code_court() for e in eqs], "ajoutees": [],
              "retirees": [], "modifiees": [], "lignes": False, "renommages": [], "bloquants": [], "conflits": []}
    if publie is None:
        sortie["bloquants"] = [f"Modèle « {nom} » absent du référentiel publié : rien à reprendre."]
        sortie.update(adoptable=False, identique=False)
        return sortie
    if publie.get("type") != t:
        sortie["bloquants"].append(f"Modèle « {nom} » : type {t} → {publie.get('type')}, le repère changerait "
                                   "(décision R1 à valider).")
    actuels = fige["signaux"] if "signaux" in fige else catalogue_ouvrage.signaux_du_type(t, avec_ecartes=True)
    a = {_cle(x): x for x in actuels}
    b = {_cle(x): x for x in publie.get("signaux", [])}
    corr = {c["ancienne"]: c for c in correspondances or [] if isinstance(c, dict) and c.get("type") == t}
    cibles: set[str] = set()
    for k, x in a.items():
        c = corr.get(k)
        if k not in b and c:
            if (c.get("type_nouveau") or t) != t:
                sortie["bloquants"].append(f"{nom}.{k} → {c.get('type_nouveau')}.{c['nouvelle']} : changement de "
                                           "type, le repère changerait (décision R1 à valider).")
                continue
            cible = b.get(c["nouvelle"])
            if cible is None:
                sortie["bloquants"].append(f"{nom}.{k} : correspondance vers une clé absente du modèle publié.")
                continue
            if c["nouvelle"] in a or any(_porte_donnees(ouvrage, e, c["nouvelle"]) for e in eqs):
                sortie["bloquants"].append(f"{nom}.{k} → {c['nouvelle']} : la nouvelle clé porte déjà des données ; "
                                           "aucune donnée n'est écrasée.")
                continue
            cibles.add(c["nouvelle"])
            sortie["renommages"].append({"ancienne": k, "nouvelle": c["nouvelle"], "physique": [noms(x)[0], noms(cible)[0]],
                                         "fonctionnel": [noms(x)[1], noms(cible)[1]]})
        elif k in b and noms(x) != noms(b[k]):
            sortie["renommages"].append({"ancienne": k, "nouvelle": k, "physique": [noms(x)[0], noms(b[k])[0]],
                                         "fonctionnel": [noms(x)[1], noms(b[k])[1]]})
    sortie["retirees"] = sorted(k for k in a if k not in b and k not in corr)
    for k in sortie["retirees"]:
        porteurs = [e.code_court() for e in eqs if _porte_donnees(ouvrage, e, k)]
        if porteurs:
            sortie["bloquants"].append(f"{nom}.{k} disparaît du modèle et porte des données ({', '.join(porteurs)}) : "
                                       "déclarer une correspondance avant la reprise.")
    sortie["ajoutees"] = sorted(k for k in b if k not in a and k not in cibles)
    sortie["modifiees"] = sorted(k for k in set(a) & set(b) if a[k] != b[k])
    sortie["lignes"] = fige.get("lignes") != publie.get("lignes")
    sortie["conflits"] = [c for e in eqs for c in conflits_surcharges(e, a, b)]
    sortie["bloquants"] = sorted(set(sortie["bloquants"]))
    sortie["adoptable"] = not sortie["bloquants"]
    if "signaux" in fige:
        sortie["identique"] = fige == publie
    else:                       # ancienne copie sans signaux : comparer les signaux effectifs et le reste du modèle
        hors = ("signaux", "origine_signaux")
        sortie["identique"] = a == b and ({k: v for k, v in fige.items() if k not in hors}
                                          == {k: v for k, v in publie.items() if k not in hors})
    return sortie


def _renommer(ouvrage, eq, ancienne, nouvelle):
    for champ in CHAMPS_DICT:
        d = getattr(eq, champ)
        if ancienne in d:
            d[nouvelle] = d.pop(ancienne)
    for champ in CHAMPS_LISTE:
        setattr(eq, champ, [nouvelle if x == ancienne else x for x in getattr(eq, champ)])
    eq.traces = {(k.rsplit(":", 1)[0] + ":" + nouvelle if k.split(":", 1)[-1] == ancienne else k): v
                 for k, v in eq.traces.items()}
    for x in list(ouvrage.existantes) + list(ouvrage.table_tt):
        if x.ident_eq == eq.ident and x.cle == ancienne:
            x.cle = nouvelle


def catalogue_fusionne(ancien, nouveau, adoptes, utilises):
    """Référentiel actuel pour les types adoptés et les types non utilisés ; référentiel figé pour les autres."""
    gardes = set(utilises) - set(adoptes)
    types = [t for t in nouveau.types if t["code"] not in gardes]
    types += [t for t in ancien.types if t["code"] in gardes]
    signaux = [s for s in nouveau.signaux if s["type"] not in gardes]
    signaux += [s for s in ancien.signaux if s["type"] in gardes]
    tout = not gardes & {t["code"] for t in ancien.types}
    regles = [r for r in nouveau.regles if r.get("type") not in gardes and (r.get("type") != "*" or tout)]
    regles += [r for r in ancien.regles if r.get("type") in gardes or (r.get("type") == "*" and not tout)]
    version = nouveau.version if tout else f"{nouveau.version} (adoption partielle : {', '.join(sorted(adoptes))})"
    return Catalogue(copy.deepcopy(types), copy.deepcopy(signaux), version, copy.deepcopy(regles))


def sauvegarder(chemin, operation="adoption"):
    """Copie horodatée du fichier de projet avant adoption ; renvoie son chemin (ou "")."""
    if not chemin or not os.path.isfile(chemin):
        return ""
    prefixe = f"{os.path.basename(chemin)}.avant-{operation}-{datetime.now().strftime('%Y%m%d-%H%M%S')}-"
    fd, copie = tempfile.mkstemp(prefix=prefixe, dir=os.path.dirname(os.path.abspath(chemin)))
    os.close(fd)
    try:
        shutil.copy2(chemin, copie)
    except OSError:
        os.unlink(copie)
        raise
    return copie


def restaurer(sauvegarde, chemin):
    """Restaure les octets par remplacement atomique, après conservation de l'état courant."""
    if not sauvegarde or not os.path.isfile(sauvegarde):
        raise AdoptionRefusee("Sauvegarde avant adoption introuvable : annulation refusée.")
    copie_courante = sauvegarder(chemin, "annulation-adoption")
    fd, temporaire = tempfile.mkstemp(prefix=".ogias-restauration-", dir=os.path.dirname(os.path.abspath(chemin)))
    os.close(fd)
    try:
        shutil.copy2(sauvegarde, temporaire)
        os.replace(temporaire, chemin)
    finally:
        if os.path.exists(temporaire):
            os.unlink(temporaire)
    return copie_courante
