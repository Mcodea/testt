"""Export Excel des cartes d'E/S, au format de carte d'E/S retenu (R1 à R11) : un onglet par module, une ligne par voie.

Colonnes (règles R1 à R7) : entrée/sortie (%I0.2.2), voie (02), sens contact, organe (type), domaine, désignation (majuscules sans accents), PCF, validation
(vide, à remplir à la recette), mnémonique API, extension. Les voies libres sont écrites « RESERVE ».
Document de travail : à vérifier avant diffusion. Aucun module n'est inventé.
"""
from .cartes_es import adresse, bilan_modules, occupation, place, texte_carte
from .export_xlsx import ecrire_xlsx

ENTETES = ["Entrée / sortie", "Voie", "Sens contact", "Organe", "Domaine", "Désignation",
           "PCF", "Validation", "Mnémonique API", "Extension"]
LARGEURS = [14, 6, 18, 26, 24, 36, 16, 12, 30, 16]


def _ligne(m, v, p):
    adr = adresse(m.nature, m.cle, v)
    if p is None:
        return [adr, f"{v:02d}", "", "RESERVE", "", "", "", "", "", ""]
    texte = texte_carte(p.designation or p.information)
    return [adr, f"{v:02d}", p.sens, texte_carte(p.organe1), p.organe2, texte, p.repere, "", p.nom,
            p.extension.lower()]


def exporter(chemin, ouvrage, points):
    modules = sorted(ouvrage.modules, key=lambda m: (m.rack, m.position))
    occ = occupation(points, modules)
    feuilles = []
    synthese = []
    for b in bilan_modules(points, modules, ouvrage.reserve_min):
        synthese.append([b["module"], b["nature"], b["reference"], b["voies"], b["occupees"], b["reserve"],
                         f"{b['taux']:.2%}".replace(".", ","), "SOUS LE SEUIL" if b["sous_seuil"] else ""])
    feuilles.append(("Modules", ["Rack.position", "Nature", "Référence", "Nb d'infos", "Occupées", "Réserve",
                                 "Réserve %", "Alerte"], synthese, [14, 8, 18, 10, 10, 10, 10, 16]))
    for m in modules:
        lignes = [_ligne(m, v, occ.get(m.cle, {}).get(v)) for v in range(m.voies)]
        feuilles.append((f"R{m.rack} P{m.position} {m.nature}", ENTETES, lignes, LARGEURS))
    restantes = [[p.repere, p.point, p.nom, texte_carte(p.designation or p.information)] for p in points
                 if p.raccordement != "Communication" and place(p)[1] is None]
    feuilles.append(("À implanter", ["PCF", "Nature", "Mnémonique API", "Désignation"], restantes, [16, 8, 30, 36]))
    feuilles.append(("Ouvrage", ["Rubrique", "Valeur"], [
        ["Ouvrage", f"{ouvrage.prefixe()} {ouvrage.libelle}"], ["Automate", ouvrage.automate],
        ["Révision", ouvrage.revision], ["Réserve minimale", f"{ouvrage.reserve_min:.0%}"],
        ["Statut", "Document de travail — vérifier avant diffusion"]], [20, 50]))
    ecrire_xlsx(chemin, feuilles)
    return sum(len(occ.get(m.cle, {})) for m in modules)
