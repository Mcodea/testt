"""Cartes d'E/S par module : règles R4 à R11 du document « Règles de construction des E/S ».

Module sans Qt, déterministe : le même ouvrage et les mêmes modules donnent toujours la même implantation.
L'outil n'invente aucun module : il place les E/S sur les cartes déclarées par l'automaticien, propose
les voies (adresses « proposées »), et ne déplace jamais une E/S déjà placée ou validée.
"""
import math
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .modele import PointES

NATURES = ("ET", "ST", "EA", "SA")
PREFIXES = {"ET": "%I", "ST": "%Q", "EA": "%IW", "SA": "%QW"}
RESERVE_MIN = 0.20          # décision du 5 novembre : 20 % de réserve par module

# Catalogue de départ (à confirmer par l'automaticien) : référence, nature, nombre de voies.
CARTES = [
    ("BMX DDI 1602", "ET", 16), ("BMX DDI 3202K", "ET", 32), ("BMX DDI 6402K", "ET", 64),
    ("BMX DDO 1602", "ST", 16), ("BMX DDO 3202K", "ST", 32), ("BMX DDO 6402K", "ST", 64),
    ("BMX AMI 0410", "EA", 4), ("BMX AMI 0810", "EA", 8),
    ("BMX AMO 0210", "SA", 2), ("BMX AMO 0410", "SA", 4),
]


@dataclass
class Module:
    """Carte d'E/S déclarée : rack, position dans le rack, nature, nombre de voies."""
    rack: int
    position: int
    nature: str
    voies: int
    reference: str = ""
    libelle: str = ""

    @property
    def cle(self):
        return f"{self.rack}.{self.position}"


def cle_module(texte):
    """« 3 » ou « 0.3 » → « 0.3 » ; vide si illisible."""
    t = (texte or "").strip()
    if re.fullmatch(r"\d{1,2}", t):
        return f"0.{int(t)}"
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})", t)
    return f"{int(m.group(1))}.{int(m.group(2))}" if m else ""


# ====================================================================== R7 — sens contact
def sens_par_defaut(point, code, information):
    """État de la voie à 1, déduit du code quand le référentiel ne le donne pas (à confirmer)."""
    if point not in ("ET", "ST"):
        return ""
    c = (code or "").upper()
    info = (information or "").strip()
    if point == "ST":
        return f"1 = {info}" if info else ""
    regles = [(r"(^|_)DEF($|_)|^DEF", "Défaut"), (r"^AL($|_)", "Alarme"), (r"^MA($|_)", "En marche"),
              (r"^DISPO$", "Disponible"), (r"^PRES($|_)", "Présence"), (r"BYP", "Sur by-pass"),
              (r"BATT_DECH|BATT_BAS", "Batterie basse")]
    for motif, texte in regles:
        if re.search(motif, c):
            return f"1 = {texte}"
    if re.search(r"d[ée]faut", info, re.I):
        return "1 = Défaut"
    return f"1 = {info[:1].upper() + info[1:]}" if info else ""


# ====================================================================== occupation
def _voie(p):
    try:
        return int(str(p.voie).strip())
    except (TypeError, ValueError):
        return None


def occupation(points, modules):
    """{clé module: {voie: point}} pour les E/S déjà placées (module + voie renseignés)."""
    occ: dict[str, dict[int, object]] = {m.cle: {} for m in modules}
    for p in points:
        k, v = place(p)
        if k and v is not None:
            occ.setdefault(k, {})[v] = p
    return occ


RE_ADRESSE = re.compile(r"^%(?:I|Q|IW|QW)(\d{1,2})\.(\d{1,2})\.(\d{1,3})$")


def place(p):
    """(clé module, voie) d'une E/S : depuis module + voie, sinon depuis une adresse saisie %I0.3.5."""
    k, v = cle_module(p.module), _voie(p)
    if k and v is not None:
        return k, v
    m = RE_ADRESSE.match((p.adresse or "").upper())
    if m:
        return f"{int(m.group(1))}.{int(m.group(2))}", int(m.group(3))
    return "", None


# ====================================================================== R9 — implantation
def implanter(points, modules, ordre_uf=(), rang_eq=None, seuil=RESERVE_MIN, reservees=(), groupes=(),
              rapport=None):
    """Propose module + voie pour chaque E/S câblée encore sans place.

    Retourne (affectations, manquantes, depassements) :
      affectations = [(point, clé module, voie)] dans l'ordre d'implantation ;
      manquantes = {nature: nombre d'E/S restées sans voie} ;
      depassements = clés des modules dont la réserve passe sous le seuil.
    Ordre : UF, puis équipement, puis ordre des signaux ; les E/S d'un équipement restent groupées (B5).

    `groupes` : groupes de secours CONFIRMÉS (listes d'ident d'équipements, B4). Les équipements d'un même
    groupe sont placés sur des cartes distinctes ; la séparation passe avant la réserve de voies (B4 > B2).
    Si elle est impossible faute de place, l'E/S est placée quand même et le conflit est signalé, jamais tu.
    `rapport` (dict, facultatif) reçoit `motifs` {(ident_eq, clé E/S): règle appliquée} (B8) et
    `secours_non_separes` [(ident_eq, clé module, [idents du groupe déjà sur la carte])].
    """
    rang_eq = rang_eq or {}
    uf_rang = {u: i for i, u in enumerate(ordre_uf)}
    occ = occupation(points, modules)
    for k, v in reservees:                      # voies réservées : jamais prises sans décision explicite
        occ.setdefault(k, {}).setdefault(v, "RÉSERVÉE")
    groupes = [list(g) for g in groupes]
    groupe_de = {i: n for n, g in enumerate(groupes) for i in g}
    sur_carte: dict[int, dict[str, set]] = {}   # groupe -> clé module -> idents du groupe déjà présents
    for k, voies in occ.items():
        for p in voies.values():
            n = groupe_de.get(getattr(p, "ident_eq", None))
            if n is not None:
                sur_carte.setdefault(n, {}).setdefault(k, set()).add(p.ident_eq)
    repere = {p.ident_eq: p.repere for p in points}
    a_placer = [p for p in points if p.raccordement != "Communication" and not p.adresse
                and place(p)[1] is None]
    index = {id(p): i for i, p in enumerate(points)}
    a_placer.sort(key=lambda p: (uf_rang.get(p.uf, len(uf_rang)) if p.uf else len(uf_rang) + 1,
                                 rang_eq.get(p.ident_eq, 0), index[id(p)]))
    blocs: list[tuple[str, list["PointES"]]] = []  # (nature, [points d'un même équipement])
    for p in a_placer:
        if blocs and blocs[-1][0] == p.point and blocs[-1][1][0].ident_eq == p.ident_eq:
            blocs[-1][1].append(p)
        else:
            blocs.append((p.point, [p]))
    par_nature = {n: sorted([m for m in modules if m.nature == n], key=lambda m: (m.rack, m.position))
                  for n in NATURES}
    affectations: list[tuple["PointES", str, int]] = []
    manquantes: dict[str, int] = {}
    motifs: dict[tuple, str] = {}
    non_separes: list[tuple] = []

    def libres(m):
        return [v for v in range(m.voies) if v not in occ.setdefault(m.cle, {})]

    for nature, bloc in blocs:
        ident = bloc[0].ident_eq
        n_grp = groupe_de.get(ident)

        def voisins(m):
            if n_grp is None:
                return set()
            return sur_carte.get(n_grp, {}).get(m.cle, set()) - {ident}

        def avec_reserve(m):
            return len(occ.setdefault(m.cle, {})) + len(bloc) <= math.floor(m.voies * (1 - seuil))

        candidats = [m for m in par_nature.get(nature, []) if len(libres(m)) >= len(bloc)]
        cible, reserve_ok, separe = None, True, True
        for reserve, separation in ((True, True), (False, True), (True, False), (False, False)):
            cible = next((m for m in candidats if (not reserve or avec_reserve(m))
                          and (not separation or not voisins(m))), None)
            if cible is not None:
                reserve_ok, separe = reserve, separation or not voisins(cible)
                break
        if cible is None:
            manquantes[nature] = manquantes.get(nature, 0) + len(bloc)
            continue
        regle = (f"Première voie {nature} libre de la carte {cible.cle} (cartes par rack et position ; "
                 f"E/S de {bloc[0].repere} groupées ; ")
        regle += "réserve de voies respectée" if reserve_ok else "réserve de voies entamée faute de place"
        if n_grp is not None:
            autres = sorted(repere.get(i, i) for i in groupes[n_grp] if i != ident)
            if separe:
                regle += f" ; carte distincte de son groupe de secours ({', '.join(autres)})"
            else:
                deja = sorted(voisins(cible))
                non_separes.append((ident, cible.cle, deja))
                regle += (" ; ATTENTION : même carte que " + ", ".join(repere.get(i, i) for i in deja)
                          + " du même groupe de secours, faute de carte libre")
        regle += ")."
        voies = libres(cible)
        for p, v in zip(bloc, voies):
            occ[cible.cle][v] = p
            affectations.append((p, cible.cle, v))
            motifs[(p.ident_eq, p.cle)] = regle
        if n_grp is not None:
            sur_carte.setdefault(n_grp, {}).setdefault(cible.cle, set()).add(ident)
    depassements = [m.cle for m in modules if m.voies and
                    (m.voies - len(occ.get(m.cle, {}))) / m.voies < seuil and occ.get(m.cle)]
    if rapport is not None:
        rapport["motifs"], rapport["secours_non_separes"] = motifs, non_separes
    return affectations, manquantes, depassements


def secours_partageant_une_carte(points, modules, groupes):
    """[(clé module, [repères])] : cartes portant déjà des E/S PLACÉES de plusieurs équipements d'un même
    groupe de secours (B4). Contrôle des placements existants ou saisis ; rien n'est déplacé (B7)."""
    groupe_de = {i: n for n, g in enumerate(groupes) for i in g}
    vus: dict[tuple, set] = {}
    for k, voies in occupation(points, modules).items():
        for p in voies.values():
            n = groupe_de.get(p.ident_eq)
            if n is not None:
                vus.setdefault((k, n), set()).add(p.repere)
    return [(k, sorted(r)) for (k, _n), r in sorted(vus.items()) if len(r) > 1]


# ====================================================================== R10 — bilan
def bilan_modules(points, modules, seuil=RESERVE_MIN):
    occ = occupation(points, modules)
    lignes = []
    for m in sorted(modules, key=lambda m: (m.rack, m.position)):
        n = len([v for v in occ.get(m.cle, {}) if v < m.voies])
        reserve = m.voies - n
        taux = reserve / m.voies if m.voies else 0
        lignes.append({"module": m.cle, "nature": m.nature, "reference": m.reference, "voies": m.voies,
                       "occupees": n, "reserve": reserve, "taux": taux, "sous_seuil": taux < seuil})
    return lignes


# ====================================================================== R11 — contrôles
def controler(points, modules, seuil=RESERVE_MIN):
    """[(niveau, repère, message, ident_eq)] : cohérence des E/S placées avec les modules déclarés."""
    if not modules:
        return []
    par_cle = {m.cle: m for m in modules}
    sortie = []
    prises: dict[tuple[str, int], str] = {}
    for p in points:
        k, v = place(p)
        if p.raccordement == "Communication" or not k or v is None:
            continue
        if (k, v) in prises:
            sortie.append(("Erreur", p.repere, f"{p.nom} : voie {k} / {v} déjà affectée à {prises[(k, v)]}.", p.ident_eq))
        prises.setdefault((k, v), p.nom)
        m = par_cle.get(k)
        if m is None:
            sortie.append(("Erreur", p.repere, f"{p.nom} : module {k} non déclaré.", p.ident_eq))
        elif m.nature != p.point:
            sortie.append(("Erreur", p.repere, f"{p.nom} : {p.point} placée sur le module {k} de nature {m.nature}.",
                           p.ident_eq))
        elif v >= m.voies:
            sortie.append(("Erreur", p.repere, f"{p.nom} : voie {v} hors du module {k} ({m.voies} voies, 0 à "
                                               f"{m.voies - 1}).", p.ident_eq))
    for b in bilan_modules(points, modules, seuil):
        if b["sous_seuil"] and b["occupees"]:
            sortie.append(("Alerte", f"Module {b['module']}",
                           f"Module {b['module']} : réserve {b['taux']:.0%} ({b['reserve']}/{b['voies']}), "
                           f"sous le seuil de {seuil:.0%}.", ""))
    return sortie


def texte_carte(texte):
    """Texte de la carte d'E/S : majuscules sans accents (décision du 5 novembre : DEFAUT RESEAU)."""
    import unicodedata
    t = unicodedata.normalize("NFKD", (texte or "").replace("’", "'"))
    return "".join(c for c in t if not unicodedata.combining(c)).upper()


def adresse(nature, cle, voie):
    return f"{PREFIXES[nature]}{cle}.{int(voie)}"
