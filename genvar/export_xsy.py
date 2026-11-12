"""Export des variables au format .XSY (Unity Pro / Control Expert).

Le fichier suit le modèle utilisé par l'outil Schneider « Excel Import Export
Tool » (Unity Variables Management) :

<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<VariablesExchangeFile>
 <fileHeader company="Schneider Automation" product="…" dateTime="date_and_time#…"
             content="Variable source file" DTDVersion="41"></fileHeader>
 <contentHeader name="Project" version="0.0.000"></contentHeader>
 <dataBlock>
  <variables name="…" typeName="…" topologicalAddress="…"><comment>…</comment></variables>
 </dataBlock>
</VariablesExchangeFile>

Le fichier est préparé pour les essais d'import Control Expert et TOPKAPI via
SOFTLINK ; aucune compatibilité industrielle n'est déclarée sans leurs preuves.
"""


def variables_ce(ouvrage, variables, points=(), avec_echange=True, avec_es=True, avec_reserves=True, internes=()):
    """Liste ordonnée des variables Control Expert : E/S localisées (et voies de réserve des cartes
    déclarées, comme dans l'export Control Expert), triées par carte et voie, puis variables d'échange,
    puis variables internes déclarées et sélectionnées (P1), non localisées : sans ``topologicalAddress``."""
    from .cartes_es import place
    from .formats_control_expert import VariableCE, reserve
    from .modele import type_point_es
    sortie = []
    if avec_es:
        prefixe = {"ET": "%I", "ST": "%Q", "EA": "%IW", "SA": "%QW"}
        es = [p for p in points if p.adresse]
        occupees = {(place(p)[0], place(p)[1]) for p in es}
        lignes = [((*map(int, place(p)[0].split(".")), place(p)[1]) if place(p)[1] is not None else (99, 99, 999),
                   VariableCE(p.nom, p.adresse.upper(), p.type_logique, p.commentaire)) for p in es]
        if avec_reserves:
            for m in getattr(ouvrage, "modules", []):
                for v in range(m.voies):
                    if (m.cle, v) not in occupees:
                        lignes.append(((m.rack, m.position, v),
                                       reserve(f"{prefixe[m.nature]}{m.rack}.{m.position}.{v}", type_point_es(m.nature))))
        sortie += [v for _, v in sorted(lignes, key=lambda x: x[0])]
    if avec_echange:
        sortie += [VariableCE(v.nom, v.adresse, v.type_logique, v.commentaire) for v in variables]
    sortie += [VariableCE(x.nom, "", x.type_logique, x.commentaire) for x in internes]
    return sortie


def contenu_xsy(ouvrage, variables, points=(), avec_echange=True, avec_es=True, maintenant=None, avec_reserves=True,
                internes=()):
    """Texte XSY au format de l'export Control Expert V14.1 (échantillon du 9 novembre 2026)."""
    from . import VERSION
    from .formats_control_expert import xsy
    liste = variables_ce(ouvrage, variables, points, avec_echange, avec_es, avec_reserves, internes)
    nom_projet = ouvrage.nom_projet or ouvrage.prefixe()
    texte = xsy(liste, nom_projet, commentaire=ouvrage.libelle or "", produit=f"OGIAS V{VERSION}", maintenant=maintenant)
    return texte, sum(1 for v in liste if v.nom)


def exporter_xsy(chemin, ouvrage, variables, points=(), avec_echange=True, avec_es=True, avec_reserves=True,
                 internes=()):
    texte, nb = contenu_xsy(ouvrage, variables, points, avec_echange, avec_es, avec_reserves=avec_reserves,
                            internes=internes)
    with open(chemin, "w", encoding="utf-8", newline="") as f:      # le texte porte déjà ses fins de ligne CRLF
        f.write(texte)
    return nb


def exporter_txt(chemin, ouvrage, variables, points=(), avec_echange=True, avec_es=True, avec_reserves=True):
    """TXT tabulé identique à l'export texte des variables de Control Expert."""
    from .formats_control_expert import txt
    liste = variables_ce(ouvrage, variables, points, avec_echange, avec_es, avec_reserves)
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        f.write(txt(liste))
    return sum(1 for v in liste if v.nom)
