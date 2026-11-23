"""Indices de livraison et liste des modifications (feuille de route du 22/11/2026, objectif 2).

Comme le marquage des révisions des outils d'ingénierie, OGIAS garde une PHOTO de l'ouvrage à chaque indice livré
(A, B, C…) et produit la liste exacte des modifications entre deux indices, ou entre le dernier indice livré et
l'état en cours : équipements, E/S, variables (adresses et registres compris), cartes d'E/S et identification de
l'ouvrage, chacun ajouté, supprimé ou modifié champ par champ.

Règles
- Un indice livré ne change plus : livrer de nouveau demande de passer à l'indice suivant.
- Les éléments sont rapprochés par leur identité stable (équipement, signal de l'équipement, emplacement de carte),
  pas par leur nom : un renommage apparaît comme une modification du nom, jamais comme une suppression suivie d'un
  ajout.
- Rien n'est recalculé dans l'ouvrage : la photo est une lecture.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

CATEGORIES = {"ouvrage": "Ouvrage", "equipements": "Équipements", "es": "E/S physiques", "variables": "Variables",
              "cartes": "Cartes d'E/S"}
CHAMPS = {
    "lieu": "Lieu", "code_ouvrage": "Type d'ouvrage", "numero_ouvrage": "Numéro", "libelle": "Libellé",
    "automate": "Automate", "supervision": "Supervision", "ihm": "IHM", "decalage_modbus": "Décalage Modbus",
    "repere": "Repère", "type": "Type", "modele": "Modèle", "options": "Options", "nom": "Nom", "point": "Nature",
    "type_logique": "Type logique", "adresse": "Adresse", "module": "Carte", "voie": "Voie",
    "designation": "Désignation", "raccordement": "Raccordement", "famille": "Famille", "registre": "Registre",
    "libelle_supervision": "Libellé de supervision", "alarme": "Alarme", "unite": "Unité", "reference": "Référence",
    "nature": "Nature", "voies": "Voies",
}
RE_INDICE = re.compile(r"[A-Z0-9]{1,4}")


class IndiceRefuse(ValueError):
    """Livraison d'indice impossible : le message s'affiche tel quel."""


def photo(session) -> dict:
    """État livrable de l'ouvrage, en clés stables (lecture seule)."""
    o = session.ouvrage
    p = {"ouvrage": {"ouvrage": {k: "" if getattr(o, k, None) is None else str(getattr(o, k)) for k in
                                 ("lieu", "code_ouvrage", "numero_ouvrage", "libelle", "automate", "supervision", "ihm",
                                  "decalage_modbus")}},
         "equipements": {}, "es": {}, "variables": {}, "cartes": {}}
    for e in o.equipements:
        p["equipements"][e.ident] = {"repere": o.repere(e), "type": e.type, "libelle": e.libelle or "",
                                     "modele": e.modele or "", "options": ", ".join(sorted(e.options or []))}
    for pt in session.points():
        p["es"][f"{pt.ident_eq}|{pt.cle}"] = {
            "nom": pt.nom, "repere": pt.repere, "point": pt.point, "type_logique": pt.type_logique,
            "adresse": pt.adresse or "", "module": pt.module or "", "voie": str(pt.voie or ""),
            "designation": pt.designation or pt.commentaire or "", "raccordement": pt.raccordement}
    for v in session.variables():
        p["variables"][f"{v.ident_eq}|{v.cle}"] = {
            "nom": v.nom, "repere": v.repere, "famille": v.famille, "type_logique": v.type_logique,
            "adresse": v.adresse or "", "registre": session.registre_modbus(v.adresse) if v.adresse else "",
            "libelle_supervision": v.libelle_topkapi or "", "alarme": "Oui" if v.alarme else "Non",
            "unite": v.unite or ""}
    for m in o.modules:
        p["cartes"][m.cle] = {"reference": m.reference or "", "nature": m.nature, "voies": str(m.voies)}
    return p


def empreinte(p: dict) -> str:
    return hashlib.sha256(json.dumps(p, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _libelle(categorie: str, cle: str, x: dict) -> str:
    if categorie == "ouvrage":
        return "Identification de l'ouvrage"
    if categorie == "equipements":
        return x.get("repere", cle)
    if categorie == "cartes":
        return f"Carte {cle}"
    return x.get("nom", cle)


def differences(avant: dict, apres: dict) -> list[dict]:
    """[{categorie, categorie_libelle, cle, element, etat, champs: [{champ, libelle, avant, apres}]}], dans l'ordre
    des catégories puis des éléments."""
    sortie = []
    for cat, libelle_cat in CATEGORIES.items():
        a, b = avant.get(cat, {}), apres.get(cat, {})
        lignes = []
        for cle in sorted(set(a) | set(b)):
            if cle not in a:
                lignes.append({"cle": cle, "element": _libelle(cat, cle, b[cle]), "etat": "ajouté",
                               "champs": [{"champ": k, "libelle": CHAMPS.get(k, k), "avant": "", "apres": v}
                                          for k, v in b[cle].items() if v not in ("", None)]})
            elif cle not in b:
                lignes.append({"cle": cle, "element": _libelle(cat, cle, a[cle]), "etat": "supprimé",
                               "champs": [{"champ": k, "libelle": CHAMPS.get(k, k), "avant": v, "apres": ""}
                                          for k, v in a[cle].items() if v not in ("", None)]})
            else:
                champs = [{"champ": k, "libelle": CHAMPS.get(k, k), "avant": a[cle].get(k, ""), "apres": b[cle].get(k, "")}
                          for k in dict.fromkeys([*a[cle], *b[cle]]) if a[cle].get(k, "") != b[cle].get(k, "")]
                if champs:
                    lignes.append({"cle": cle, "element": _libelle(cat, cle, b[cle]), "etat": "modifié",
                                   "champs": champs})
        ordre = {"supprimé": 0, "modifié": 1, "ajouté": 2}
        for x in sorted(lignes, key=lambda x: (x["element"], ordre[x["etat"]])):
            sortie.append({"categorie": cat, "categorie_libelle": libelle_cat, **x})
    return sortie


def bilan(diff: list[dict]) -> dict:
    b = {cat: {"ajouté": 0, "supprimé": 0, "modifié": 0} for cat in CATEGORIES}
    for x in diff:
        b[x["categorie"]][x["etat"]] += 1
    return b


# --------------------------------------------------------------------------------------------- indices
def indices(ouvrage) -> list[dict]:
    return list(getattr(ouvrage, "indices", None) or [])


def livrer(session, motif: str, auteur: str = "") -> dict:
    """Fige l'indice courant de l'ouvrage (sa révision) avec la photo de son état. Refusé si déjà livré."""
    o = session.ouvrage
    indice = (o.revision or "").strip().upper()
    if not RE_INDICE.fullmatch(indice):
        raise IndiceRefuse("Indice de révision invalide dans la fiche de l'ouvrage.")
    if any(x["indice"] == indice for x in indices(o)):
        raise IndiceRefuse(f"L'indice {indice} est déjà livré et ne change plus : passez à l'indice suivant pour "
                           "livrer les modifications.")
    if not o.equipements:
        raise IndiceRefuse("Ouvrage sans équipement : rien à livrer.")
    motif = " ".join(str(motif or "").split())[:300]
    if len(motif) < 3:
        raise IndiceRefuse("Indiquez l'objet de la livraison (ex. « Première diffusion », « Ajout du poste 2 »).")
    p = photo(session)
    x = {"indice": indice, "le": datetime.now(timezone.utc).isoformat(timespec="seconds"), "motif": motif,
         "auteur": " ".join(str(auteur or "").split())[:60], "empreinte": empreinte(p), "photo": p}
    o.indices = [*indices(o), x]
    return x


def indice_suivant(indice: str) -> str:
    """A → B, 1 → 2, A1 → A2 ; refusé quand la suite n'est pas évidente (Z, 9999…)."""
    i = (indice or "").strip().upper()
    if re.fullmatch(r"[A-Y]", i):
        return chr(ord(i) + 1)
    m = re.fullmatch(r"([A-Z]*)(\d+)", i)
    if m and len(m.group(1) + str(int(m.group(2)) + 1)) <= 4:
        return m.group(1) + str(int(m.group(2)) + 1)
    raise IndiceRefuse(f"Indice suivant de « {i} » à saisir dans la fiche de l'ouvrage.")


def comparer(session, depuis: str = "", vers: str = "") -> dict:
    """Modifications entre deux indices livrés, ou du dernier indice livré (`depuis` vide) à l'état en cours
    (`vers` vide)."""
    liste = indices(session.ouvrage)
    if not liste:
        raise IndiceRefuse("Aucun indice livré : la liste des modifications commence après la première livraison.")
    par = {x["indice"]: x for x in liste}
    a = par.get(depuis) if depuis else liste[-1]
    if a is None:
        raise IndiceRefuse(f"Indice {depuis} non livré.")
    if vers:
        if vers not in par:
            raise IndiceRefuse(f"Indice {vers} non livré.")
        b, nom_b = par[vers]["photo"], vers
    else:
        b, nom_b = photo(session), f"{session.ouvrage.revision} (en cours)"
    diff = differences(a["photo"], b)
    return {"depuis": a["indice"], "vers": nom_b, "modifications": diff, "bilan": bilan(diff)}


def resume_indices(ouvrage) -> list[dict]:
    return [{k: x[k] for k in ("indice", "le", "motif", "auteur", "empreinte")} for x in indices(ouvrage)]


def feuilles_xlsx(ouvrage, c: dict) -> list:
    """Feuilles du classeur « Liste des modifications » (export_xlsx.ecrire_xlsx)."""
    lignes = []
    for x in c["modifications"]:
        for ch in x["champs"] or [{"libelle": "", "avant": "", "apres": ""}]:
            lignes.append([x["categorie_libelle"], x["element"], x["etat"], ch["libelle"], ch["avant"], ch["apres"]])
    b = c["bilan"]
    synthese = [[CATEGORIES[cat], b[cat]["ajouté"], b[cat]["supprimé"], b[cat]["modifié"]] for cat in CATEGORIES]
    return [("Modifications", ["Catégorie", "Élément", "État", "Champ", f"Indice {c['depuis']}", f"Indice {c['vers']}"],
             lignes, [16, 30, 11, 24, 36, 36]),
            ("Synthèse", ["Catégorie", "Ajoutés", "Supprimés", "Modifiés"], synthese, [20, 10, 10, 10]),
            ("Indices", ["Indice", "Livré le (UTC)", "Objet", "Par", "Empreinte"],
             [[x["indice"], x["le"], x["motif"], x["auteur"], x["empreinte"][:16]] for x in resume_indices(ouvrage)],
             [8, 22, 50, 20, 20])]
