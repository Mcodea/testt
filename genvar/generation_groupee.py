"""Génération groupée des livrables d'un ouvrage (lot 6 de la feuille de route du 19/11/2026).

Un seul geste produit, dans une archive zip rangée par destination, tous les livrables qu'OGIAS sait déjà
produire pour l'ouvrage ouvert, avec un journal de ce qui a été produit et de ce qui ne l'a pas été :

- `01_Automate/`         : E/S au format automate (XSY, TXT), table de télétransmission (XSY) ;
- `02_Telegestion_SOFREL/` : rien tant que le format d'import SOFREL n'est pas décrit (signalé au journal) ;
- `03_Supervision/`      : table TOPKAPI (zip, compte rendu des points exclus) ;
- `04_Documents/`        : formats d'études (E/S par carte, liste de travail, télétransmission, variables, cartes,
                           nomenclature) et la liste des équipements en aller-retour Excel ;
- `05_Essais/`           : cahiers FAT et SAT ;
- `06_Modeles_client/`   : chaque modèle de la bibliothèque de l'atelier, rempli pour l'ouvrage ;
- `00_journal.html` (imprimable en PDF) et `00_journal.csv` : pièce par pièce, produite (empreinte SHA-256,
  taille) ou non produite **avec son motif**.

Principes
- Aucun format nouveau : chaque pièce est produite par l'export unitaire existant (`produire(quoi)` fourni par
  l'application), donc avec exactement les mêmes contrôles et les mêmes refus que le bouton de l'écran Recette.
  Rien n'est assoupli parce que l'export est groupé.
- Une pièce refusée ne bloque pas les autres ; elle figure au journal avec la raison du refus, jamais remplacée.
- Un modèle client en erreur n'est pas rempli : il est listé avec ses erreurs d'analyse.
- Lot 8 : un modèle déclaré pour un autre logiciel que ceux de l'ouvrage est « non retenu » (motif au journal) ; un
  type d'équipement sans brique pour le logiciel de l'ouvrage est « manquant », jamais comblé par un autre logiciel.
- Les formats qu'OGIAS ne sait pas produire (SOFREL, Vijeo) sont nommés au journal comme non disponibles.
- Les exports Control Expert, TOPKAPI et les modèles client ne sont pas qualifiés : le journal le dit.
"""
from __future__ import annotations

import csv
import hashlib
import html
import io
import os
import zipfile
from datetime import datetime

FAMILLES = {
    "automate": ("01_Automate", "Automate (Control Expert)"),
    "sofrel": ("02_Telegestion_SOFREL", "Télégestion SOFREL"),
    "supervision": ("03_Supervision", "Supervision / IHM"),
    "documents": ("04_Documents", "Documents d'études"),
    "essais": ("05_Essais", "Cahiers d'essais FAT / SAT"),
    "modeles": ("06_Modeles_client", "Modèles de l'atelier"),
}

# (famille, clé d'export unitaire, libellé) : l'ordre est celui de l'écran Recette et livrables.
PIECES = [
    ("automate", "es_xsy", "Liste des E/S au format automate (XSY)"),
    ("automate", "es_txt", "Liste des E/S au format automate (TXT)"),
    ("automate", "xsy", "Table de télétransmission au format automate (XSY)"),
    ("supervision", "topkapi", "Table de télétransmission TOPKAPI"),
    ("documents", "es_cartes", "Liste des E/S par carte"),
    ("documents", "liste_es", "Tableau de travail des E/S"),
    ("documents", "tele_etudes", "Table de télétransmission (format d'études)"),
    ("documents", "variables", "Table des variables"),
    ("documents", "cartes", "Cartes d'E/S"),
    ("documents", "nomenclature", "Nomenclature matériel"),
    ("documents", "equipements", "Liste des équipements (aller-retour Excel)"),
    ("essais", "essais_fat", "Cahier d'essais FAT"),
    ("essais", "essais_sat", "Cahier d'essais SAT"),
]

# Formats nommés à l'écran Recette mais qu'OGIAS ne produit pas : jamais simulés, signalés au journal.
NON_DISPONIBLES = [
    ("sofrel", "Liste des E/S SOFREL", "Format d'import SOFREL pas encore décrit dans OGIAS."),
    ("supervision", "Table de télétransmission IHM Vijeo",
     "Format d'import Vijeo Designer pas encore décrit dans OGIAS."),
]

NON_QUALIFIES = {"es_xsy", "es_txt", "xsy", "topkapi"}


class GenerationRefusee(ValueError):
    """Demande impossible (aucune famille, ouvrage absent) : message affiché tel quel."""


def familles_demandees(brut) -> list[str]:
    """« automate,documents » ou liste → familles connues, dans l'ordre du dossier. Vide → toutes."""
    if brut is None or brut == "" or brut == []:
        return list(FAMILLES)
    valeurs = brut.split(",") if isinstance(brut, str) else list(brut)
    demandees = {str(v).strip() for v in valeurs if str(v).strip()}
    inconnues = demandees - set(FAMILLES)
    if inconnues:
        raise GenerationRefusee(f"Famille de livrables inconnue : {', '.join(sorted(inconnues))}.")
    if not demandees:
        raise GenerationRefusee("Choisissez au moins une famille de livrables.")
    return [f for f in FAMILLES if f in demandees]


def _nom_libre(nom: str, pris: set[str]) -> str:
    racine, ext = os.path.splitext(nom)
    k, candidat = 2, nom
    while candidat in pris:
        candidat = f"{racine}_{k}{ext}"
        k += 1
    pris.add(candidat)
    return candidat


def constituer(session, produire, familles=None, erreurs_attendues=(ValueError, OSError)) -> dict:
    """Produit les pièces des familles demandées. `produire(quoi) -> (nom, octets)` est l'export unitaire de
    l'application ; toute exception de `erreurs_attendues` vaut refus motivé.
    Renvoie {"fichiers": {chemin_dans_zip: octets}, "journal": [...], "familles": [...]}."""
    from . import modeles_livrables as ml
    familles = familles_demandees(familles)
    fichiers: dict[str, bytes] = {}
    journal: list[dict] = []
    pris: set[str] = set()

    def ajouter(famille, libelle, nom, octets, remarque=""):
        chemin = _nom_libre(f"{FAMILLES[famille][0]}/{nom}", pris)
        fichiers[chemin] = octets
        journal.append({"famille": famille, "piece": libelle, "etat": "produit", "fichier": chemin,
                        "taille": len(octets), "sha256": hashlib.sha256(octets).hexdigest(), "motif": remarque})

    def refuser(famille, libelle, motif, etat="non produit"):
        journal.append({"famille": famille, "piece": libelle, "etat": etat, "fichier": "", "taille": 0,
                        "sha256": "", "motif": motif})

    for famille, quoi, libelle in PIECES:
        if famille not in familles:
            continue
        try:
            nom, octets = produire(quoi)
        except erreurs_attendues as exc:
            refuser(famille, libelle, str(exc) or exc.__class__.__name__)
            continue
        ajouter(famille, libelle, nom, octets,
                "Export non qualifié : à importer et vérifier dans le logiciel cible." if quoi in NON_QUALIFIES else "")
    if "automate" in familles:                 # formats appris (22/11) : liste des E/S au format d'un constructeur
        from . import formats_appris as fa
        for f in fa.lister():
            libelle = f"Format appris « {f['nom']} »"
            ok, motif = fa.retenu(f, session.ouvrage)
            if not ok:
                refuser("automate", libelle, motif, etat="non retenu")
                continue
            try:
                nom, octets = produire("format_appris:" + f["ident"])
            except erreurs_attendues as exc:
                refuser("automate", libelle, str(exc) or exc.__class__.__name__)
                continue
            ajouter("automate", libelle, nom, octets,
                    f"Conforme au format qualifié ({f['logiciel']}) : contrôle automatique réussi." if fa.qualifie(f)
                    else f"Format appris non qualifié : à importer une fois dans {f['logiciel']} puis confirmer.")
    for famille, libelle, motif in NON_DISPONIBLES:
        if famille in familles:
            refuser(famille, libelle, motif, etat="non disponible")
    if "modeles" in familles:
        resumes = [ml.resume(m) for m in ml.lister()]
        if not resumes:
            refuser("modeles", "Modèles de l'atelier", "Aucun modèle dans la bibliothèque (Standards > Modèles de livrables).")
        selection = ml.pour_ouvrage(session, resumes)
        ecartes = {c["ident"]: c["motif"] for c in selection["choix"] if not c["retenu"]}
        for r in resumes:
            m = r
            libelle = f"Modèle « {m['nom']} »"
            if m["ident"] in ecartes:                # lot 8 : brique d'un autre logiciel que ceux de l'ouvrage
                refuser("modeles", libelle, ecartes[m["ident"]], etat="non retenu")
                continue
            if r["erreurs"]:
                refuser("modeles", libelle, "Modèle à corriger : " + " ; ".join(r["erreurs"][:3]))
                continue
            try:
                nom, octets = ml.generer(m["ident"], session)
            except (ml.ModeleRefuse, OSError, UnicodeDecodeError) as exc:
                refuser("modeles", libelle, str(exc))
                continue
            ajouter("modeles", libelle, nom, octets, "Format défini par l'atelier : non qualifié par OGIAS.")
        for manque in selection["manques"]:
            refuser("modeles", f"Brique {manque['logiciel']} du type {manque['type']}", manque["message"]
                    + " Rien n'est produit à sa place.", etat="manquant")
    ordre = list(FAMILLES)
    journal.sort(key=lambda j: ordre.index(j["famille"]))     # tri stable : l'ordre des pièces est conservé
    return {"fichiers": fichiers, "journal": journal, "familles": familles}


def bilan(journal: list[dict]) -> dict:
    produits = sum(1 for j in journal if j["etat"] == "produit")
    return {"produits": produits, "non_produits": len(journal) - produits}


def journal_csv(journal: list[dict]) -> bytes:
    sortie = io.StringIO()
    w = csv.writer(sortie, delimiter=";", lineterminator="\r\n")
    w.writerow(["Destination", "Pièce", "État", "Fichier", "Taille (octets)", "SHA-256", "Motif ou remarque"])
    for j in journal:
        w.writerow([FAMILLES[j["famille"]][1], j["piece"], j["etat"], j["fichier"], j["taille"] or "", j["sha256"],
                    j["motif"]])
    return sortie.getvalue().encode("utf-8-sig")       # BOM : Excel ouvre l'UTF-8 sans casser les accents


def journal_html(session, journal: list[dict], familles: list[str]) -> bytes:
    from . import VERSION
    o, e = session.ouvrage, html.escape
    b = bilan(journal)
    sections = []
    for f in familles:
        lignes = [j for j in journal if j["famille"] == f]
        if not lignes:
            continue
        corps = "".join(
            f"<tr class=\"{'ok' if j['etat'] == 'produit' else 'non'}\"><td>{e(j['piece'])}</td><td>{e(j['etat'])}</td>"
            f"<td>{e(j['fichier'])}</td><td>{e(j['motif'])}</td>"
            f"<td><code>{e(j['sha256'][:16])}{'…' if j['sha256'] else ''}</code></td></tr>" for j in lignes)
        sections.append(f"<h2>{e(FAMILLES[f][1])}</h2><table><tr><th>Pièce</th><th>État</th><th>Fichier</th>"
                        f"<th>Motif ou remarque</th><th>SHA-256 (début)</th></tr>{corps}</table>")
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Livrables {e(o.prefixe())}</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#14243b}}table{{border-collapse:collapse;width:100%;margin-bottom:16px}}
td,th{{border:1px solid #c8cfe0;padding:6px;text-align:left;font-size:13px;vertical-align:top}}th{{background:#eef1fb}}
tr.non td:nth-child(2){{color:#8a5a00;font-weight:600}}.alerte{{background:#fff4d6;padding:10px;border-radius:6px}}
@media print{{body{{margin:0}}}}</style></head><body>
<h1>Génération groupée des livrables — {e(o.libelle or o.prefixe())}</h1>
<p>Ouvrage <b>{e(o.prefixe())}</b> · révision {e(o.revision or "—")} · produit par OGIAS {VERSION} le {datetime.now():%d/%m/%Y %H:%M}</p>
<p><b>{b['produits']}</b> pièce(s) produite(s), <b>{b['non_produits']}</b> non produite(s) ou non disponible(s).
Chaque pièce est issue de l'export unitaire d'OGIAS, avec les mêmes contrôles ; une pièce non produite est listée avec
son motif, jamais remplacée.</p>
<p class="alerte">Exports Control Expert, TOPKAPI et modèles de l'atelier <b>non qualifiés</b> : ils doivent être
importés et vérifiés dans les logiciels cibles avant toute mise en service.</p>
{''.join(sections)}
<p>Empreintes complètes : <code>00_journal.csv</code>.</p></body></html>""".encode("utf-8")


def archive(session, chemin_zip, produire, familles=None, erreurs_attendues=(ValueError, OSError)) -> dict:
    """Constitue les pièces puis écrit l'archive ; renvoie {journal, familles, bilan}."""
    r = constituer(session, produire, familles, erreurs_attendues)
    with zipfile.ZipFile(chemin_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("00_journal.html", journal_html(session, r["journal"], r["familles"]))
        z.writestr("00_journal.csv", journal_csv(r["journal"]))
        for chemin in sorted(r["fichiers"]):
            z.writestr(chemin, r["fichiers"][chemin])
    return {"journal": r["journal"], "familles": r["familles"], "bilan": bilan(r["journal"])}
