"""Dossier de recette d'un ouvrage (retour d'essai n° 11 du 12/11/2026).

Rassemble, dans un dossier puis une archive zip, les livrables de recette **à partir des exports existants**
(aucun nouveau format inventé) :

- `01_equipements.xlsx` : équipements de la configuration (repère, type, modèle, options, état) ;
- `02_liste_es.xlsx` : liste des E/S avec matériel et affectation (export « liste des E/S ») ;
- `03_cartes_es.xlsx` : cartes et voies, si le matériel est retenu ;
- `04_variables.xlsx` : variables et table de télétransmission (export « variables ») ;
- formats cibles pris en charge : `05_variables_control_expert.xsy`, `06_topkapi.zip` (fichier .$$t) ;
- `00_sommaire.html` : identification, liste des pièces avec empreinte SHA-256, pièces non produites et leur
  motif, points du parcours restant à traiter, mention « exports non qualifiés » ; imprimable en PDF.

Échanges inter-automates (11 d) : aucun mécanisme RX / TX n'est encore déclaré (décision P2) ; le sommaire le
dit. Une pièce impossible à produire est **signalée avec son motif**, jamais remplacée ni inventée.
"""
from __future__ import annotations

import hashlib
import html
import os
import zipfile
from datetime import datetime

from .export_xlsx import ecrire_xlsx


def _equipements(chemin, session):
    o = session.ouvrage
    lignes = [[o.repere(e), e.type, session.catalogue.designation(e.type), e.modele or "",
               ", ".join(e.options), "validé" if e.valide else "à valider"] for e in session.equipements_tries()]
    ecrire_xlsx(chemin, [("Équipements", ["Repère", "Type", "Désignation", "Modèle", "Options", "État"], lignes,
                          [16, 8, 36, 30, 40, 12])])


def _non_applicable(motif):
    """Écriture d'une pièce sans objet pour cet ouvrage : elle est listée avec son motif, jamais remplacée."""
    def ecrire(_chemin):
        raise ValueError(motif)
    return ecrire


def _pieces(session):
    """[(nom, libellé, fonction d'écriture(chemin))] dans l'ordre du dossier. Une pièce sans objet garde sa place
    et lève son motif : elle figure parmi les pièces non produites du sommaire."""
    s, o = session, session.ouvrage
    pieces = [("01_equipements.xlsx", "Liste des équipements", lambda c: _equipements(c, s)),
              ("02_liste_es.xlsx", "Liste des E/S (matériel et affectation)", s.exporter_liste_es),
              ("03_cartes_es.xlsx", "Cartes et voies",
               s.exporter_cartes_es if o.modules else
               _non_applicable("Aucune carte d'E/S déclarée : matériel non encore retenu pour cet ouvrage."))]
    pieces.append(("04_variables.xlsx", "Variables et table de télétransmission", s.exporter_excel))
    pieces.append(("05_variables_control_expert.xsy", "Variables Control Expert (XSY)",
                   s.exporter_xsy if o.mode == "Neuf" else
                   _non_applicable("Projet existant : le programme automate existe déjà ; aucun XSY n'est produit "
                                   "(table de correspondances Excel en pièce 04).")))
    pieces.append(("06_topkapi.zip", "Table de télétransmission TOPKAPI (.$$t et compte rendu)", s.exporter_topkapi))
    return pieces


def _empreinte(chemin):
    with open(chemin, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def constituer(session, dossier):
    """Écrit les pièces dans `dossier` et renvoie le manifeste {pieces, non_produites, sommaire}."""
    from .session import RegleMetier
    os.makedirs(dossier, exist_ok=True)
    produites, non_produites = [], []
    for nom, libelle, ecrire in _pieces(session):
        chemin = os.path.join(dossier, nom)
        try:
            ecrire(chemin)
        except (RegleMetier, ValueError, OSError) as exc:
            if os.path.exists(chemin):
                os.unlink(chemin)
            non_produites.append({"fichier": nom, "libelle": libelle, "motif": str(exc)})
            continue
        produites.append({"fichier": nom, "libelle": libelle, "sha256": _empreinte(chemin)})
    sommaire = os.path.join(dossier, "00_sommaire.html")
    with open(sommaire, "w", encoding="utf-8") as f:
        f.write(_sommaire_html(session, produites, non_produites))
    return {"pieces": produites, "non_produites": non_produites, "sommaire": "00_sommaire.html"}


def archive(session, dossier, chemin_zip):
    """Constitue le dossier puis l'archive zip ; renvoie le manifeste."""
    manifeste = constituer(session, dossier)
    with zipfile.ZipFile(chemin_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for nom in sorted(os.listdir(dossier)):
            z.write(os.path.join(dossier, nom), nom)
    return manifeste


def _repartition(session):
    """Règles appliquées à la répartition (B8 : la logique de répartition est documentée)."""
    o, e = session.ouvrage, html.escape
    lignes = [f"Réserve minimale de voies par carte : {o.reserve_min:.0%}.",
              f"Emplacements laissés libres par rack : {o.emplacements_libres_rack}.",
              "E/S d'un même équipement groupées sur une carte, voies contiguës ; une E/S validée ne bouge pas."]
    if not o.separation_secours:
        lignes.append("Séparation des groupes de secours : désactivée pour cet ouvrage.")
    else:
        groupes = session.groupes_secours_actifs()
        lignes.append("Groupes de secours sur cartes distinctes : "
                      + ("; ".join(", ".join(o.repere(o.equipement(i)) for i in g) for g in groupes)
                         if groupes else "aucun groupe confirmé") + ".")
    return "".join(f"<li>{e(x)}</li>" for x in lignes)


def _sommaire_html(session, produites, non_produites):
    from . import VERSION
    o, e = session.ouvrage, html.escape
    parcours = [p for etape in session.parcours() for p in etape["bloquants"] + etape["a_verifier"]]
    lignes = "".join(f"<tr><td>{e(p['fichier'])}</td><td>{e(p['libelle'])}</td><td><code>{p['sha256']}</code></td></tr>"
                     for p in produites)
    absentes = "".join(f"<li><b>{e(p['libelle'])}</b> ({e(p['fichier'])}) : {e(p['motif'])}</li>"
                       for p in non_produites) or "<li>Aucune.</li>"
    points = "".join(f"<li>{e(p['message'])}</li>" for p in parcours) or "<li>Aucun.</li>"
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Dossier de recette {e(o.prefixe())}</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#14243b}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #c8cfe0;padding:6px;text-align:left;font-size:13px}}th{{background:#eef1fb}}
.alerte{{background:#fff4d6;padding:10px;border-radius:8px}}@media print{{body{{margin:0}}}}</style></head><body>
<h1>Dossier de recette — {e(o.libelle or o.prefixe())}</h1>
<p>Ouvrage <b>{e(o.prefixe())}</b> · automate {e(o.automate or "non renseigné")} · révision {e(o.revision or "—")}
 · produit par OGIAS {VERSION} le {datetime.now():%d/%m/%Y %H:%M}</p>
<p class="alerte">Exports Control Expert, SOFREL S4W et TOPKAPI <b>non qualifiés</b> : ils doivent être importés et
vérifiés dans les logiciels cibles avant toute mise en service.</p>
<h2>Pièces du dossier</h2><table><tr><th>Fichier</th><th>Contenu</th><th>SHA-256</th></tr>{lignes}</table>
<h2>Pièces non produites</h2><ul>{absentes}</ul>
<h2>Règles de répartition des E/S</h2><ul>{_repartition(session)}</ul>
<h2>Échanges inter-automates</h2><p>Aucun échange inter-automates déclaré (fonction prévue, décision P2).</p>
<h2>Points restant à traiter</h2><ul>{points}</ul>
</body></html>"""
