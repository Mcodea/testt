"""Assistant de création d'un modèle de livrable à partir d'un export (lot 7, 19/11/2026).

Problème : chez un client qui a son propre standard (symbole de pompe, table de variables, format d'import de sa
supervision ou de son automate), écrire un modèle `<#…#>` à la main est long. L'assistant part d'un FICHIER EXPORTÉ
de l'outil du client pour UN équipement de référence (ex. la pompe PM01, déjà décrite dans l'ouvrage ouvert) et
reconnaît dans ce fichier les valeurs qu'OGIAS connaît pour cet équipement : repère, noms de variables, adresses,
libellés, noms d'E/S… Il propose de les remplacer par les variables du moteur de modèles, puis il range les lignes :

- les lignes qui ne citent aucune valeur de l'équipement (en-tête, pied) restent hors bloc, recopiées telles quelles ;
- le corps devient un bloc `EQUIPEMENTS_<TYPE>` : il se répète pour chaque équipement du même type ;
- dans le corps, une suite de lignes « une par variable » (ou « une par E/S ») de même gabarit devient un bloc
  VARIABLES (ou ES), éventuellement filtré par famille (ou nature) quand chaque famille a son propre gabarit ;
- une ligne qu'on ne sait pas généraliser est recopiée telle quelle et SIGNALÉE (elle citerait l'équipement de
  référence pour tous les autres).

Contrôle final, sans lequel rien n'est proposé à l'enregistrement : le modèle obtenu est rempli pour l'équipement
de référence et comparé au fichier d'origine. « Identique » veut dire qu'il reproduit exactement l'export ; sinon
les lignes différentes sont montrées. Les valeurs utilisées sont celles que le moteur de remplissage écrit
(`modeles_livrables.valeurs_*`) : la reconnaissance et la génération ne peuvent pas diverger.

Rien n'est inventé : le format est celui du fichier du client ; OGIAS ne fait que repérer ses propres valeurs.
"""
from __future__ import annotations

import re
from collections import Counter
from xml.sax.saxutils import escape as _xml

from . import modeles_livrables as ml

LONGUEUR_MIN = 2
# Variables qu'on ne propose pas : trop courtes ou trop génériques pour être reconnues sans ambiguïté.
EXCLUES = {"N", "DATE", "ALARME", "ADRESSE_VALIDEE", "EQ_NUMERO", "ES_VOIE", "ES_RACCORDEMENT"}


RE_ADRESSE = re.compile(r"%[A-Z]{1,3}\d")      # forme d'adresse automate restée en clair dans une ligne


class AssistantRefuse(ValueError):
    """Analyse impossible : message affiché tel quel."""


def _echappeur(echappement):
    if echappement == "xml":
        return lambda s: _xml(s, {'"': "&quot;", "'": "&apos;"})
    return lambda s: s


def echappement_probable(texte: str) -> str:
    debut = texte.lstrip("﻿ \t\r\n")
    return "xml" if debut.startswith("<") and not debut.startswith("<#") else "aucun"


def _motif(valeurs: dict[str, str]):
    """Regex : chaque valeur (la plus longue d'abord) entourée de non-alphanumériques ; groupe nommé → variable."""
    vus, morceaux = {}, []
    for var, val in sorted(valeurs.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if val in vus:                       # même valeur portée par deux variables : la première (plus spécifique) gagne
            continue
        vus[val] = var
        morceaux.append(re.escape(val))
    if not morceaux:
        return None, {}
    return re.compile(r"(?<![A-Za-z0-9])(" + "|".join(morceaux) + r")(?![A-Za-z0-9])"), vus


def _substituer(ligne: str, valeurs: dict[str, str], compte: Counter) -> str:
    rx, par_valeur = _motif(valeurs)
    if rx is None:
        return ligne

    def remplacer(m):
        var = par_valeur[m.group(1)]
        compte[(var, m.group(1))] += 1
        return f"<#{var}#>"
    return rx.sub(remplacer, ligne)


def _candidates(d: dict, esc, refus: set[str]) -> dict[str, str]:
    return {k: esc(str(v)) for k, v in d.items()
            if k not in EXCLUES and k not in refus and v is not None and len(str(v).strip()) >= LONGUEUR_MIN
            and str(v) == str(v).strip()}


def construire(texte: str, session, ident_eq: str, refus=(), echappement: str | None = None) -> dict:
    """Propose un modèle à partir de l'export `texte` de l'équipement `ident_eq`. Rien n'est enregistré.
    `refus` : variables à NE PAS substituer (choix de l'utilisateur)."""
    o = session.ouvrage
    eq = next((e for e in o.equipements if e.ident == ident_eq), None)
    if eq is None:
        raise AssistantRefuse("Choisissez l'équipement de référence dans l'ouvrage ouvert.")
    if "<#" in texte:
        raise AssistantRefuse("Ce fichier contient déjà des variables <#…#> : importez-le directement comme modèle.")
    echappement = echappement or echappement_probable(texte)
    esc, refus = _echappeur(echappement), set(refus or ())
    v_ouvrage = _candidates(ml.valeurs_ouvrage(session), esc, refus)
    v_eq = _candidates(ml.valeurs_equipement(session, eq), esc, refus)
    variables = [v for v in session.variables() if v.ident_eq == eq.ident]
    points = [p for p in session.points() if p.ident_eq == eq.ident]
    noms_var = {esc(v.nom): v for v in variables if v.nom}
    noms_es = {esc(p.nom): p for p in points if p.nom}
    rx_var, _ = _motif({v: v for v in noms_var})
    rx_es, _ = _motif({p: p for p in noms_es})

    fin = "\r\n" if "\r\n" in texte else "\n"
    lignes = texte.splitlines(keepends=True)
    compte: Counter = Counter()
    analyse = []                 # [{texte, sorte: entete|variable|es|equipement, gabarit, famille, cle}]
    for brut in lignes:
        trouves_var = {m.group(1) for m in rx_var.finditer(brut)} if rx_var else set()
        trouves_es = {m.group(1) for m in rx_es.finditer(brut)} if rx_es else set()
        local: Counter = Counter()
        if len(trouves_var) == 1:
            v = noms_var[next(iter(trouves_var))]
            vals = {**v_ouvrage, **v_eq, **_candidates(ml.valeurs_variable(session, v), esc, refus)}
            analyse.append({"sorte": "variable", "famille": v.famille, "cle": v.nom,
                            "gabarit": _substituer(brut, vals, local), "texte": brut})
        elif not trouves_var and len(trouves_es) == 1:
            p = noms_es[next(iter(trouves_es))]
            vals = {**v_ouvrage, **v_eq, **_candidates(ml.valeurs_es(p), esc, refus)}
            analyse.append({"sorte": "es", "famille": p.point, "cle": p.nom,
                            "gabarit": _substituer(brut, vals, local), "texte": brut})
        else:
            g_eq = _substituer(brut, {**v_ouvrage, **v_eq}, local)
            ambigu = len(trouves_var) > 1 or len(trouves_es) > 1
            sorte = "ambigu" if ambigu else ("equipement" if any(k[0] in v_eq for k in local) else "entete")
            analyse.append({"sorte": sorte, "famille": "", "cle": "", "gabarit": g_eq, "texte": brut})
        a = analyse[-1]
        a["compte"] = local
        if a["sorte"] not in ("ambigu",):
            compte.update(local)

    corps = [i for i, a in enumerate(analyse) if a["sorte"] in ("variable", "es", "equipement", "ambigu")]
    alertes: list[str] = []
    if not corps:
        raise AssistantRefuse(f"Aucune valeur de {o.repere(eq)} reconnue dans ce fichier : vérifiez l'équipement de "
                              "référence (le fichier doit être l'export de CET équipement).")
    debut, dernier = corps[0], corps[-1]
    sortie: list[str] = [a["gabarit"] for a in analyse[:debut]]
    type_ok = ml.RE_TYPE_FILTRE.fullmatch(eq.type or "")
    bloc_eq = f"EQUIPEMENTS_{eq.type}" if type_ok else "EQUIPEMENTS"
    if not type_ok:
        alertes.append(f"Type {eq.type} non utilisable comme filtre de bloc : le modèle se répétera pour TOUS les "
                       "équipements de l'ouvrage.")
    sortie.append(f"<#DEBUT_{bloc_eq}#>{fin}")
    blocs: list[str] = []
    non_generalisees = 0
    i = debut
    while i <= dernier:
        a = analyse[i]
        if a["sorte"] in ("variable", "es"):
            j = i
            while j + 1 <= dernier and analyse[j + 1]["sorte"] == a["sorte"]:
                j += 1
            serie = analyse[i:j + 1]
            nom_bloc = "VARIABLES" if a["sorte"] == "variable" else "ES"
            gabarits = {x["gabarit"] for x in serie}
            if len(gabarits) == 1:
                sortie += [f"<#DEBUT_{nom_bloc}#>{fin}", serie[0]["gabarit"], f"<#FIN_{nom_bloc}#>{fin}"]
                blocs.append(f"{nom_bloc} ({len(serie)} ligne(s) d'exemple)")
            else:
                par_famille: dict[str, set] = {}
                for x in serie:
                    par_famille.setdefault(x["famille"], set()).add(x["gabarit"])
                ordre = list(dict.fromkeys(x["famille"] for x in serie))
                filtres = ml.FAMILLES_FILTRE if nom_bloc == "VARIABLES" else ml.POINTS_FILTRE
                groupes_contigus = [x["famille"] for k, x in enumerate(serie)
                                    if k == 0 or serie[k - 1]["famille"] != x["famille"]] == ordre
                if all(len(g) == 1 for g in par_famille.values()) and groupes_contigus \
                        and all(f in filtres for f in ordre):
                    for f in ordre:
                        sortie += [f"<#DEBUT_{nom_bloc}_{f}#>{fin}", next(iter(par_famille[f])),
                                   f"<#FIN_{nom_bloc}_{f}#>{fin}"]
                        blocs.append(f"{nom_bloc}_{f}")
                else:
                    for x in serie:
                        sortie.append(x["texte"])
                    non_generalisees += len(serie)
                    alertes.append(f"{len(serie)} ligne(s) {('de variables' if nom_bloc == 'VARIABLES' else 'd’E/S')} "
                                   "de formes différentes (ex. « " + serie[0]["texte"].strip()[:60] + " ») : "
                                   "recopiées telles quelles, à reprendre à la main.")
            i = j + 1
            continue
        if a["sorte"] == "ambigu":
            sortie.append(a["texte"])
            non_generalisees += 1
            alertes.append("Ligne citant plusieurs variables ou E/S (« " + a["texte"].strip()[:60] + " ») : recopiée "
                           "telle quelle, à reprendre à la main.")
        else:
            sortie.append(a["gabarit"])
        i += 1
    if not sortie[-1].endswith(("\n", "\r")):
        sortie[-1] += fin
    sortie.append(f"<#FIN_{bloc_eq}#>{fin}")
    sortie += [a["gabarit"] for a in analyse[dernier + 1:]]
    gabarit = "".join(sortie)
    sans_adresse = [x["cle"] for x in analyse if x["sorte"] == "variable" and not noms_var[esc(x["cle"])].adresse
                    and RE_ADRESSE.search(x["gabarit"])]
    if variables and not any(v.adresse for v in variables) and not sans_adresse:
        alertes.append(f"Aucune adresse n'est encore attribuée aux variables de {o.repere(eq)} : si l'export a une "
                       "colonne d'adresses, elle ne peut pas être reconnue et resterait vide pour tous les équipements. "
                       "Attribuez d'abord les adresses de l'équipement de référence (étape Variables).")
    if sans_adresse:
        alertes.append(f"{len(sans_adresse)} variable(s) de l'export sans adresse attribuée dans OGIAS (ex. "
                       f"{sans_adresse[0]}) : une adresse écrite dans le fichier ne peut pas être reconnue ; attribuez "
                       "les adresses de l'équipement de référence avant de construire le modèle.")

    propositions: dict[str, dict] = {}
    for (var, val), n in compte.items():
        p = propositions.setdefault(var, {"variable": var, "description": ml.DESCRIPTIONS.get(var, "")
                                          or ml._description_attribut(var), "occurrences": 0, "exemples": []})
        p["occurrences"] += n
        if len(p["exemples"]) < 3 and val not in p["exemples"]:
            p["exemples"].append(val)
    refusees = [{"variable": r, "description": ml.DESCRIPTIONS.get(r, ""), "occurrences": 0, "exemples": [],
                 "refusee": True} for r in sorted(refus)]
    return {"gabarit": gabarit, "echappement": echappement, "equipement": o.repere(eq), "type": eq.type,
            "propositions": sorted(propositions.values(), key=lambda p: (-p["occurrences"], p["variable"])) + refusees,
            "blocs": blocs, "alertes": alertes, "non_generalisees": non_generalisees,
            "lignes": {"entete": debut, "corps": dernier - debut + 1, "pied": len(analyse) - dernier - 1},
            "verification": verifier(gabarit, texte, session, eq, echappement)}


def verifier(gabarit: str, texte: str, session, eq, echappement: str) -> dict:
    """Le modèle rempli pour le seul équipement de référence reproduit-il l'export d'origine ?"""
    _, erreurs, _ = ml.analyser(gabarit)
    if erreurs:
        return {"etat": "erreur", "message": "Modèle incorrect : " + " ".join(erreurs[:3]), "manquantes": [], "en_plus": []}
    rempli = ml.remplir(gabarit, session, echappement, seulement={eq.ident})
    if rempli == texte or rempli.rstrip("\r\n") == texte.rstrip("\r\n"):
        return {"etat": "identique", "message": "Rempli pour " + session.ouvrage.repere(eq)
                + ", le modèle reproduit exactement le fichier d'origine.", "manquantes": [], "en_plus": []}
    a = Counter(texte.splitlines())
    b = Counter(rempli.splitlines())
    manquantes = list((a - b).elements())
    en_plus = list((b - a).elements())
    if not manquantes and not en_plus:
        return {"etat": "ordre", "message": "Mêmes lignes que le fichier d'origine, dans un autre ordre (OGIAS range "
                "les variables par nom) : vérifiez que l'outil cible accepte cet ordre.", "manquantes": [], "en_plus": []}
    if not manquantes:
        return {"etat": "complete", "message": f"Toutes les lignes d'origine sont reproduites ; {len(en_plus)} ligne(s) "
                "en plus : variables ou E/S de l'équipement absentes de l'export (elles seront aussi générées).",
                "manquantes": [], "en_plus": en_plus[:10]}
    return {"etat": "different", "message": f"{len(manquantes)} ligne(s) d'origine non reproduite(s), "
            f"{len(en_plus)} ligne(s) différente(s) : à examiner avant d'enregistrer.",
            "manquantes": manquantes[:10], "en_plus": en_plus[:10]}
