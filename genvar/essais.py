"""Cahiers d'essais FAT / SAT (lot 3 de la feuille de route du 19/11/2026).

Idée reprise des outils d'ingénierie de données (fiches d'essai point par point générées depuis la base), adaptée
à OGIAS :
- FAT (essais en atelier) : une ligne par entrée / sortie physique, avec sa voie ;
- SAT (essais sur site) : une ligne par variable de télétransmission, avec son registre Modbus et son libellé de
  supervision.
Le cahier est un classeur : une feuille « Sommaire », puis une feuille par équipement. On le remplit (Conforme,
Non conforme, Sans objet, remarque, date, visa), puis on le reporte dans OGIAS : les résultats sont lus, montrés,
et enregistrés seulement sur confirmation. Une cellule vide ne change rien. OGIAS ne déduit jamais un résultat.

Un résultat garde l'adresse essayée : si l'adresse change ensuite, le point redevient « à refaire ».
"""
from __future__ import annotations

import time

from .export_xlsx import ecrire_xlsx

NATURES = {"FAT": "Essais en atelier (FAT) : entrées / sorties physiques",
           "SAT": "Essais sur site (SAT) : variables de télétransmission"}
RESULTATS = ("Conforme", "Non conforme", "Sans objet")
SYNONYMES = {"CONFORME": "Conforme", "OK": "Conforme", "C": "Conforme",
             "NON CONFORME": "Non conforme", "NOK": "Non conforme", "NC": "Non conforme",
             "SANS OBJET": "Sans objet", "SO": "Sans objet", "NA": "Sans objet", "N/A": "Sans objet"}
CLE_COLONNE = "Clé OGIAS (ne pas modifier)"
VERIFIER = {"ET": "État lu sur la voie et dans la variable", "EA": "Valeur lue sur la voie et dans la variable",
            "ST": "Commande de la voie : action constatée", "SA": "Consigne de la voie : valeur constatée"}


class EssaiRefuse(ValueError):
    """Cahier illisible ou contraire aux règles : message affiché tel quel."""


def points(session, nature: str) -> list[dict]:
    """Points à essayer, dans l'ordre des repères : {cle, eq, repere, libelle_eq, nom, designation, nature, adresse,
    complement1, complement2, verifier}."""
    o = session.ouvrage
    eqs = {e.ident: e for e in o.equipements}
    sortie = []
    if nature == "FAT":
        for p in session.points():
            e = eqs.get(p.ident_eq)
            if e is None or p.raccordement == "Communication":
                continue
            sortie.append({"cle": f"{p.ident_eq}|{p.cle}", "eq": p.ident_eq, "repere": o.repere(e), "libelle_eq": e.libelle,
                           "nom": p.nom, "designation": p.designation or p.commentaire, "nature": p.point,
                           "adresse": p.adresse, "complement1": p.module, "complement2": p.voie,
                           "verifier": VERIFIER.get(p.point, "")})
    elif nature == "SAT":
        for v in session.variables():
            e = eqs.get(v.ident_eq)
            if e is None:
                continue
            sortie.append({"cle": f"{v.ident_eq}|{v.cle}", "eq": v.ident_eq, "repere": o.repere(e), "libelle_eq": e.libelle,
                           "nom": v.nom, "designation": v.information, "nature": v.famille,
                           "adresse": v.adresse, "complement1": session.registre_modbus(v.adresse) if v.adresse else "",
                           "complement2": v.libelle_topkapi, "verifier": "Valeur et état vus en supervision"})
    else:
        raise EssaiRefuse("Nature d'essai inconnue (FAT ou SAT).")
    return sorted(sortie, key=lambda x: (x["repere"], x["nom"]))


def _etat_point(p: dict, r: dict | None) -> str:
    if not r or not r.get("resultat"):
        return "à faire"
    if (r.get("adresse") or "") != (p["adresse"] or ""):
        return "à refaire"
    return r["resultat"]


def etat(session, nature: str) -> dict:
    """Avancement : nombres par état, non-conformités et points à refaire (adresse changée depuis l'essai)."""
    ps = points(session, nature)
    res = (session.ouvrage.essais or {}).get(nature, {})
    compte = {"Conforme": 0, "Non conforme": 0, "Sans objet": 0, "à faire": 0, "à refaire": 0}
    a_voir = []
    for p in ps:
        e = _etat_point(p, res.get(p["cle"]))
        compte[e] += 1
        if e in ("Non conforme", "à refaire"):
            r = res.get(p["cle"], {})
            a_voir.append({"nom": p["nom"], "repere": p["repere"], "etat": e, "remarque": r.get("remarque", ""),
                           "date": r.get("date", ""), "visa": r.get("visa", "")})
    orphelins = len(set(res) - {p["cle"] for p in ps})
    return {"nature": nature, "titre": NATURES[nature], "total": len(ps), "compte": compte, "a_voir": a_voir,
            "orphelins": orphelins}


def _entetes(nature: str) -> list[str]:
    c1, c2 = ("Module", "Voie") if nature == "FAT" else ("Registre Modbus", "Libellé supervision")
    return ["N°", "Nom", "Désignation", "Nature", "Adresse", c1, c2, "À vérifier", "Résultat", "Remarque", "Date",
            "Visa", CLE_COLONNE]


def exporter(chemin, session, nature: str) -> None:
    """Classeur du cahier : sommaire + une feuille par équipement ; résultats déjà reportés pré-remplis."""
    o = session.ouvrage
    ps = points(session, nature)
    if not ps:
        raise EssaiRefuse("Aucun point à essayer : " + ("aucune E/S câblée." if nature == "FAT" else "aucune variable de télétransmission."))
    res = (o.essais or {}).get(nature, {})
    par_eq: dict[str, list[dict]] = {}
    for p in ps:
        par_eq.setdefault(p["repere"], []).append(p)
    e = etat(session, nature)
    sommaire = [["Ouvrage", f"{o.prefixe()} - {o.libelle}"], ["Cahier", NATURES[nature]],
                ["Édité le", time.strftime("%d/%m/%Y")], ["Points", str(len(ps))],
                ["Déjà reportés", f"{e['compte']['Conforme']} conformes, {e['compte']['Non conforme']} non conformes, "
                                  f"{e['compte']['Sans objet']} sans objet, {e['compte']['à refaire']} à refaire"],
                ["", ""], ["Mode d'emploi", "Remplir la colonne Résultat : Conforme, Non conforme ou Sans objet (OK, NOK, SO acceptés)."],
                ["", "Remarque, date et visa sont facultatifs. Une cellule vide ne change rien dans OGIAS."],
                ["", "Ne pas modifier la colonne « Clé OGIAS ». Reporter ensuite le cahier : Recette et livrables > Essais."],
                ["", ""], ["Équipement", "Points"]]
    sommaire += [[rep, str(len(lst))] for rep, lst in par_eq.items()]
    feuilles = [("Sommaire", [f"Cahier d'essais {nature}", ""], sommaire, [22, 90])]
    noms_pris = {"Sommaire"}
    for rep, lst in par_eq.items():
        nom = rep[:31]
        k = 2
        while nom in noms_pris:
            nom = f"{rep[:28]}~{k}"
            k += 1
        noms_pris.add(nom)
        lignes = []
        for i, p in enumerate(lst, 1):
            r = res.get(p["cle"], {})
            refaire = _etat_point(p, r) == "à refaire"
            lignes.append([str(i), p["nom"], p["designation"], p["nature"], p["adresse"], p["complement1"], p["complement2"],
                           p["verifier"], "" if refaire else r.get("resultat", ""),
                           ("Adresse changée depuis l'essai : à refaire. " if refaire else "") + r.get("remarque", ""),
                           r.get("date", ""), r.get("visa", ""), p["cle"]])
        feuilles.append((nom, _entetes(nature), lignes, [5, 30, 34, 8, 13, 14, 22, 30, 14, 34, 11, 10, 26]))
    ecrire_xlsx(chemin, feuilles)


def _date(brut: str) -> str:
    """Une date saisie dans Excel arrive en numéro de série (ex. 46345) : relue en JJ/MM/AAAA ; sinon texte tel quel."""
    import datetime
    try:
        n = float(brut)
    except ValueError:
        return brut[:20]
    if 20000 <= n <= 80000:
        return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(n))).strftime("%d/%m/%Y")
    return brut[:20]


def lire(feuilles: dict, session, nature: str) -> dict:
    """Résultats lus dans un cahier rempli (aucune écriture) : {resultats, modifies, inchanges, erreurs, ignores}."""
    connus = {p["cle"]: p for p in points(session, nature)}
    deja = (session.ouvrage.essais or {}).get(nature, {})
    resultats, erreurs, inchanges, vides = {}, [], 0, 0
    lues = 0
    for nom_feuille, lignes in feuilles.items():
        if not lignes or CLE_COLONNE not in [str(c).strip() for c in lignes[0]]:
            continue
        lues += 1
        entete = [str(c).strip() for c in lignes[0]]
        col = {h: i for i, h in enumerate(entete)}
        if "Résultat" not in col:
            erreurs.append(f"Feuille « {nom_feuille} » : colonne Résultat absente.")
            continue
        g = lambda ligne, h: str(ligne[col[h]]).strip() if h in col and col[h] < len(ligne) else ""
        for n, ligne in enumerate(lignes[1:], 2):
            cle = g(ligne, CLE_COLONNE)
            brut = g(ligne, "Résultat")
            if not cle:
                continue
            if not brut:
                vides += 1
                continue
            resultat = SYNONYMES.get(brut.upper().replace("É", "E").replace("È", "E")) or SYNONYMES.get(brut.upper())
            if resultat is None:
                erreurs.append(f"Feuille « {nom_feuille} », ligne {n} : résultat « {brut} » inconnu (Conforme, Non conforme, Sans objet).")
                continue
            if cle not in connus:
                erreurs.append(f"Feuille « {nom_feuille} », ligne {n} : point inconnu de l'ouvrage (supprimé, ou clé modifiée).")
                continue
            r = {"resultat": resultat, "remarque": g(ligne, "Remarque")[:300], "date": _date(g(ligne, "Date")),
                 "visa": g(ligne, "Visa")[:40], "adresse": connus[cle]["adresse"]}
            if r["remarque"].startswith("Adresse changée depuis l'essai : à refaire. "):
                r["remarque"] = r["remarque"][len("Adresse changée depuis l'essai : à refaire. "):]
            if deja.get(cle) == r:
                inchanges += 1
            else:
                resultats[cle] = {**r, "nom": connus[cle]["nom"], "avant": (deja.get(cle) or {}).get("resultat", "")}
    if not lues:
        raise EssaiRefuse(f"Aucune feuille de cahier {nature} reconnue (colonne « {CLE_COLONNE} » absente).")
    return {"resultats": resultats, "inchanges": inchanges, "vides": vides, "erreurs": erreurs}


def reporter(session, nature: str, resultats: dict) -> int:
    """Enregistre des résultats lus par `lire` (après confirmation). Rien n'est effacé ; renvoie le nombre reporté."""
    connus = {p["cle"] for p in points(session, nature)}
    cible = session.ouvrage.essais.setdefault(nature, {})
    n = 0
    for cle, r in resultats.items():
        if cle in connus:
            cible[cle] = {k: r[k] for k in ("resultat", "remarque", "date", "visa", "adresse")}
            n += 1
    if n:
        session.modifie = True
    return n
