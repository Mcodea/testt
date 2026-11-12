"""Proposition du matériel automate (racks et cartes d'E/S) à partir des E/S validées.

Règle (décision du 9 novembre 2026) : le matériel est PROPOSÉ par OGIAS puis validé par l'automaticien.
- Besoin par nature (ET, ST, EA, SA) = E/S câblées de l'ouvrage (les E/S par communication n'occupent pas de voie).
- Carte par nature = profil de densité choisi (défaut : 64 voies TOR, 8 voies analogiques).
- Voies utilisables par carte = voies × (1 − réserve), arrondi à l'entier inférieur (réserve minimale 20 %).
- Racks : rack local avec CPU, le plus court qui contient les cartes ; au-delà, racks d'extension.
Le calcul est déterministe : mêmes E/S, même profil → même proposition. Rien n'est écrit ici.
Les références viennent d'un fichier de données modifiable (data/materiel_schneider.json), à confirmer.
"""
import json
import math
import re
import os
from collections import Counter
from dataclasses import dataclass, field

NATURES = ("ET", "ST", "EA", "SA")
LIBELLES_NATURE = {"ET": "entrées TOR", "ST": "sorties TOR", "EA": "entrées analogiques", "SA": "sorties analogiques"}
_CACHE: dict[str, dict] = {}


class CatalogueMaterielErreur(ValueError):
    """Catalogue matériel absent ou incohérent : aucune proposition n'est faite."""


def chemin_catalogue():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "materiel_schneider.json")


def catalogue(chemin=None):
    """Lit et contrôle le catalogue (mis en cache). Lève CatalogueMaterielErreur s'il est inutilisable."""
    chemin = chemin or chemin_catalogue()
    if chemin in _CACHE:
        return _CACHE[chemin]
    try:
        with open(chemin, encoding="utf-8") as f:
            c = json.load(f)
        cartes = {x["reference"]: x for x in c["cartes"]}
        for x in cartes.values():
            if x["nature"] not in NATURES or int(x["voies"]) < 1:
                raise ValueError(f"carte {x['reference']} invalide")
        for nom, p in c["profils"].items():
            for n in NATURES:
                if cartes.get(p[n], {}).get("nature") != n:
                    raise ValueError(f"profil {nom} : carte {n} absente ou de mauvaise nature")
        for nom, p in c["plateformes"].items():
            if not p["racks"] or not all(int(r["positions"]) > len(p["positions_cpu"]) for r in p["racks"]):
                raise ValueError(f"plateforme {nom} : racks invalides")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise CatalogueMaterielErreur(f"Catalogue matériel illisible ({exc}) : aucune carte n'est proposée.") from exc
    c["_cartes"] = cartes
    _CACHE[chemin] = c
    return c


# Gamme reconnue à partir du nom ou de la référence commerciale (espaces ignorés).
_GAMMES = (("S4W", ("S4W", "SOFREL")), ("STB", ("STBNIP", "STBNIC", "ADVANTYS", "STB")),
           ("M580", ("M580", "BMEP58", "BMEH58")), ("M340", ("M340", "BMXP34")))


def emplacements_libres(racks, modules):
    """{numéro de rack: emplacements libres} d'après les racks et cartes retenus (B3)."""
    sortie = {}
    for r in racks:
        n = int(r.get("numero", 0))
        pris = len(r.get("cpu") or []) + len([m for m in modules
                                              if int(m["rack"] if isinstance(m, dict) else m.rack) == n])
        sortie[n] = int(r.get("positions", 0)) - pris
    return sortie


def gamme(automate):
    """Code de gamme décrite (S4W, STB, M580, M340) ou None si l'automate n'est pas reconnu."""
    a = re.sub(r"\s+", "", (automate or "").upper())
    return next((code for code, motifs in _GAMMES if any(m in a for m in motifs)), None)


def plateforme(automate):
    """Plateforme de calcul selon le champ Automate de la fiche ouvrage : (code, remarque)."""
    g = gamme(automate)
    if g:
        return g, ""
    if not (automate or "").strip():
        return "M340", "Automate non renseigné dans la fiche ouvrage : calcul fait pour un M340."
    return "M340", f"Automate « {automate} » non pris en charge par le calcul : M340 retenu, à vérifier."


def plateforme_materiel(automate):
    """Plateforme pour le **calcul du matériel** : comme `plateforme`, mais un automate renseigné d'une gamme non
    décrite dans le catalogue (Premium, Quantum…) est refusé : aucune configuration d'une autre gamme n'est jamais
    proposée à sa place (retour d'essai n° 8 du 12/11/2026)."""
    if (automate or "").strip() and gamme(automate) is None:
        raise CatalogueMaterielErreur(
            f"Automate « {automate} » : cette gamme n'est pas décrite dans le catalogue matériel d'OGIAS. Aucune "
            "configuration n'est proposée, pour ne pas présenter le matériel d'une autre gamme. Gammes prises en "
            "charge : Modicon M340 (BMX P34…), Modicon M580 (BME P58 / H58…), Advantys STB (STB NIP 2212), "
            "SOFREL S4W.")
    return plateforme(automate)


def chemin_catalogue_stb():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "materiel_stb.json")


def catalogue_stb(chemin=None):
    """Catalogue Advantys STB (références des guides Schneider, voir `sources`). Mis en cache."""
    chemin = chemin or chemin_catalogue_stb()
    if chemin in _CACHE:
        return _CACHE[chemin]
    try:
        with open(chemin, encoding="utf-8") as f:
            c = json.load(f)
        cartes = {x["reference"]: x for x in c["cartes"]}
        for x in cartes.values():
            if x["nature"] not in NATURES or int(x["voies"]) < 1 or int(x["courant_bus_ma"]) < 0 or not x["source"]:
                raise ValueError(f"module {x['reference']} invalide")
        for nom, pr in c["profils"].items():
            for n in NATURES:
                if cartes.get(pr[n], {}).get("nature") != n:
                    raise ValueError(f"profil {nom} : module {n} absent ou de mauvaise nature")
        int(c["nim"]["courant_bus_ma"]), int(c["nim"]["modules_max"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise CatalogueMaterielErreur(f"Catalogue Advantys STB illisible ({exc}) : aucun module n'est proposé.") from exc
    c["_cartes"] = cartes
    _CACHE[chemin] = c
    return c


@dataclass
class Besoin:
    nature: str
    es: int
    reference: str
    voies: int
    utilisables: int
    cartes: int
    capacite: int = 0                 # voies totales (S4W : intégrées + modules) ; 0 = cartes × voies

    @property
    def reserve(self):
        """Part de voies libres une fois les E/S placées (0 si aucune voie)."""
        total = self.capacite or self.cartes * self.voies
        return round(1 - self.es / total, 3) if total else 0.0


@dataclass
class Proposition:
    plateforme: str
    profil: str
    besoins: list = field(default_factory=list)       # [Besoin]
    racks: list = field(default_factory=list)         # [{"numero", "reference", "positions", "cpu": [..]}]
    modules: list = field(default_factory=list)       # [{"rack", "position", "nature", "voies", "reference"}]
    remarques: list = field(default_factory=list)
    applicable: bool = True                           # False : proposition à titre indicatif (S4W)
    config: dict = field(default_factory=dict)        # choix retenus (alimentation, processeur, communication…)

    def dict(self):
        return {"plateforme": self.plateforme, "profil": self.profil, "racks": self.racks, "modules": self.modules,
                "remarques": self.remarques, "applicable": self.applicable, "config": self.config,
                "besoins": [dict(b.__dict__, reserve=b.reserve) for b in self.besoins]}


def compter(points):
    """E/S câblées par nature (les E/S par communication n'occupent aucune voie)."""
    c = Counter(p.point for p in points if p.raccordement != "Communication" and p.point in NATURES)
    return {n: c.get(n, 0) for n in NATURES}


# ---------------------------------------------------------------------------- SOFREL S4W
NATURE_S4W = {"ET": "DI", "ST": "DO", "EA": "AI", "SA": "AO"}


def chemin_catalogue_s4w():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "materiel_sofrel_s4w.json")


def catalogue_s4w(chemin=None):
    chemin = chemin or chemin_catalogue_s4w()
    if chemin in _CACHE:
        return _CACHE[chemin]
    try:
        with open(chemin, encoding="utf-8") as f:
            c = json.load(f)
        boitiers = {b["modele"]: b for b in c["boitiers"]}
        modules = {m["designation"]: m for m in c["modules_es"]}
        for n, noms in c["modules_proposes"].items():
            for nom in noms:
                if modules[nom][NATURE_S4W[n]] < 1:
                    raise ValueError(f"module {nom} sans voie {NATURE_S4W[n]}")
        for b in c["boitiers_proposes"]:
            boitiers[b]
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise CatalogueMaterielErreur(f"Catalogue SOFREL S4W illisible ({exc}) : aucun matériel n'est proposé.") from exc
    c["_boitiers"], c["_modules"] = boitiers, modules
    _CACHE[chemin] = c
    return c


def _modules_pour(reste, choix, modules):
    """Modules d'extension pour couvrir `reste` voies : le plus grand module, le plus petit pour finir."""
    grand, petit = modules[choix[0]], modules[choix[-1]]
    nature_cle = next(k for k in ("DI", "DO", "AI", "AO") if grand[k])
    sortie = []
    while reste > 0:
        m = petit if reste <= petit[nature_cle] else grand
        sortie.append(m)
        reste -= m[nature_cle]
    return sortie


def proposer_s4w(points, reserve=0.2, chemin=None):
    """Boîtier S4W le plus petit (Small, Medium, Large) dont les voies intégrées et les extensions
    d'E/S couvrent le besoin avec la réserve. Proposition indicative : l'implantation sur S4W attend
    le format des voies de S4W-Tools."""
    cat = catalogue_s4w(chemin)
    besoin = compter(points)
    voies_requises = {n: (math.ceil(nb / (1 - reserve)) if nb else 0) for n, nb in besoin.items()}
    retenu = None
    for nom in cat["boitiers_proposes"]:
        b = cat["_boitiers"][nom]
        ext = []
        for n in NATURES:
            reste = voies_requises[n] - b.get(NATURE_S4W[n], 0)
            ext += [(n, m) for m in _modules_pour(reste, cat["modules_proposes"][n], cat["_modules"])] if reste > 0 else []
        if len(ext) <= b["extensions_es"]:
            retenu = (b, ext)
            break
    p = Proposition("S4W", "s4w", applicable=False,
                    remarques=["Proposition indicative : l'implantation des E/S sur un poste S4W et l'export S4W-Tools "
                               "attendent un fichier de configuration S4W-Tools de référence.",
                               "Références de commande à confirmer auprès de LACROIX."])
    if retenu is None:
        b = cat["_boitiers"][cat["boitiers_proposes"][-1]]
        p.remarques.insert(0, f"Besoin supérieur à la capacité d'un {b['modele']} ({b['extensions_es']} extensions) : "
                              "prévoir un automate ou plusieurs postes.")
        return p
    b, ext = retenu
    p.racks = [{"numero": 0, "reference": b["modele"], "positions": 3 + len(ext), "cpu": []}]
    pos = 0
    for n in ("ET", "EA", "ST"):
        v = b.get(NATURE_S4W[n], 0)
        if v:
            p.modules.append({"rack": 0, "position": pos, "nature": n, "voies": v,
                              "reference": f"{b['modele']} — {NATURE_S4W[n]} intégrées"})
        pos += 1
    for n, m in ext:
        p.modules.append({"rack": 0, "position": pos, "nature": n, "voies": m[NATURE_S4W[n]],
                          "reference": f"Module {m['designation']}"})
        pos += 1
    for n in NATURES:
        integre = b.get(NATURE_S4W[n], 0)
        mods = [m for x, m in ext if x == n]
        total = integre + sum(m[NATURE_S4W[n]] for m in mods)
        if besoin[n] or integre:
            ref = " + ".join(([f"{integre} intégrées"] if integre else []) +
                             [f"{sum(1 for m in mods if m is mm)} × {mm['designation']}" for mm in {id(m): m for m in mods}.values()])
            p.besoins.append(Besoin(n, besoin[n], ref or "—", total, math.floor(total * (1 - reserve)), len(mods), total))
    return p


def _sans_espace(ref):
    return re.sub(r"\s+", "", str(ref or "")).upper()


def config_materiel(cat, plat, automate="", config=None):
    """Choix de l'automaticien (alimentation, processeur, modules de communication, carte par nature), contrôlés
    contre le catalogue. Le processeur se déduit du champ Automate s'il en porte la référence exacte."""
    config = dict(config or {})
    alims = {_sans_espace(a["reference"]): a["reference"] for a in cat.get("alimentations", [])}
    cpus = {_sans_espace(c["reference"]): c["reference"] for c in cat.get("processeurs", {}).get(plat, [])}
    coms = {_sans_espace(c["reference"]): c["reference"] for c in cat.get("communication", {}).get(plat, [])}
    sortie = {"alimentation": alims.get(_sans_espace(config.get("alimentation")), ""),
              "processeur": cpus.get(_sans_espace(config.get("processeur")))
              or cpus.get(_sans_espace(automate), ""),
              "communication": [coms[_sans_espace(c)] for c in config.get("communication") or []
                                if _sans_espace(c) in coms],
              "cartes": {n: r for n, r in (config.get("cartes") or {}).items()
                         if n in NATURES and cat["_cartes"].get(r, {}).get("nature") == n}}
    return sortie


def proposer(points, automate="", profil="", reserve=0.2, chemin=None, min_cartes=None, emplacements_libres=0,
             config=None):
    """Proposition déterministe de racks et cartes. N'écrit rien.

    `min_cartes` {nature: n} : nombre minimal de cartes par nature (n = taille du plus grand groupe de secours
    confirmé ayant des E/S de cette nature, B4 : un équipement et son secours sur des cartes distinctes).
    `emplacements_libres` : emplacements laissés libres dans chaque rack pour une extension (B3).
    `config` : choix de l'automaticien (alimentation, processeur, communication, carte par nature) ; ce qui n'est
    pas choisi reste « à choisir » dans la nomenclature, jamais deviné."""
    if not 0 <= reserve < 1:
        raise ValueError("Réserve minimale : entre 0 et 100 % exclus.")
    plat, remarque = plateforme_materiel(automate)
    if plat == "S4W":
        return proposer_s4w(points, reserve)
    if plat == "STB":
        return proposer_stb(points, reserve, min_cartes=min_cartes, emplacements_libres=emplacements_libres)
    cat = catalogue(chemin)
    profil = profil if profil in cat["profils"] else cat["profil_defaut"]
    p = Proposition(plat, profil, remarques=[remarque] if remarque else [])
    choix = config_materiel(cat, plat, automate, config)
    p.config = choix
    pc = cat["plateformes"][plat]
    cartes = []
    for nature, nb in compter(points).items():
        ref = choix["cartes"].get(nature) or cat["profils"][profil][nature]
        voies = int(cat["_cartes"][ref]["voies"])
        utiles = max(1, math.floor(voies * (1 - reserve)))
        n = math.ceil(nb / utiles) if nb else 0
        separation = int((min_cartes or {}).get(nature, 0))
        if nb and separation > n:
            p.remarques.append(f"{nature} : {separation} cartes au lieu de {n} pour séparer les équipements "
                               "d'un même groupe de secours (cartes distinctes).")
            n = separation
        p.besoins.append(Besoin(nature, nb, ref, voies, utiles, n))
        cartes += [(nature, ref, voies)] * n
    if not cartes:
        p.remarques.append("Aucune E/S câblée : aucune carte à proposer.")
        return p
    racks = sorted(pc["racks"], key=lambda r: int(r["positions"]))
    cpu = list(pc["positions_cpu"])
    coms = choix["communication"]
    numero, reste, libres_voulus = 0, cartes, max(0, int(emplacements_libres))
    manque_libres = False
    while reste:
        fixes = len(cpu) + len(coms) if numero == 0 else 0
        libres_max = int(racks[-1]["positions"]) - fixes - libres_voulus
        if libres_max < 1:                         # rack trop petit pour garder les emplacements libres
            libres_max, manque_libres = int(racks[-1]["positions"]) - fixes, True
        lot, reste = reste[:libres_max], reste[libres_max:]
        besoin = len(lot) + fixes + libres_voulus
        rack = next((r for r in racks if int(r["positions"]) >= besoin), racks[-1])
        if int(rack["positions"]) < besoin:
            manque_libres = True
        occupation = []
        if numero == 0:
            occupation = [{"position": x, "reference": choix["processeur"] or "Processeur à choisir",
                           "role": "processeur"} for x in cpu]
            debut = max(cpu) + 1 if cpu else 0
            occupation += [{"position": debut + i, "reference": c, "role": "communication"}
                           for i, c in enumerate(coms)]
        occupees = [o["position"] for o in occupation]
        p.racks.append({"numero": numero, "reference": rack["reference"], "positions": int(rack["positions"]),
                        "cpu": occupees, "occupation": occupation,
                        "alimentation": choix["alimentation"] or "Alimentation à choisir"})
        pos = [x for x in range(int(rack["positions"])) if x not in occupees]
        for (nature, ref, voies), position in zip(lot, pos):
            p.modules.append({"rack": numero, "position": position, "nature": nature, "voies": voies,
                              "reference": ref})
        numero += 1
    if libres_voulus:
        p.remarques.append(f"{libres_voulus} emplacement(s) laissé(s) libre(s) par rack pour une extension"
                           + (" ; impossible pour au moins un rack (rack le plus grand atteint)." if manque_libres
                              else "."))
    if len(p.racks) > 1:
        ext = cat.get("extension", {})
        p.remarques.append(f"{len(p.racks) - 1} rack(s) d'extension : {ext.get('regle', 'liaison d’extension à prévoir.')}")
        maxi = next((c.get("racks_max") for c in cat.get("processeurs", {}).get(plat, [])
                     if c["reference"] == choix["processeur"]), None)
        if maxi and len(p.racks) > int(maxi):
            p.remarques.append(f"{len(p.racks)} racks pour un {choix['processeur']} limité à {maxi} : choisissez un "
                               "processeur plus puissant ou des cartes plus denses.")
    if not choix["alimentation"]:
        p.remarques.append("Alimentation à choisir (emplacement CPS de chaque rack).")
    if not choix["processeur"]:
        p.remarques.append("Processeur à choisir (référence exacte du catalogue).")
    p.remarques.append("Bilan de consommation des racks non calculé (consommations non intégrées) : à vérifier "
                       "avec l'outil Schneider.")
    return p


def nomenclature(racks, modules, chemin=None):
    """Nomenclature de commande : [{reference, designation, quantite, role}] d'après les racks et cartes retenus
    (alimentation, processeur, communication, cartes, extension, caches des emplacements libres)."""
    cat = catalogue(chemin)
    desig = {c["reference"]: c.get("description", "") for c in cat["cartes"] + cat.get("cartes_speciales", [])}
    for a in cat.get("alimentations", []):
        desig[a["reference"]] = f"Alimentation {a['entree']}, {a['puissance_w']} W" + (" (redondante)" if a["redondante"] else "")
    for plat in cat.get("processeurs", {}).values():
        for c in plat:
            desig[c["reference"]] = "Processeur — " + c["description"]
    for plat in cat.get("communication", {}).values():
        for c in plat:
            desig[c["reference"]] = "Communication — " + c["description"]
    for nom, plat in cat.get("plateformes", {}).items():
        for r in plat["racks"]:
            desig[r["reference"]] = f"Rack {nom} {r['positions']} emplacements (+ emplacement d'alimentation)"
    ext = cat.get("extension", {})
    desig.update({ext.get("module", ""): "Module d'extension de rack", ext.get("terminaison", ""): "Terminaison de bus X",
                  ext.get("cache", ""): "Cache de protection d'emplacement libre", ext.get("cable", ""): "Câble d'extension de bus X"})
    lignes: dict[tuple, int] = {}

    def ajouter(ref, role, n=1):
        if n > 0:
            lignes[(ref, role)] = lignes.get((ref, role), 0) + n
    get = lambda m, k: m[k] if isinstance(m, dict) else getattr(m, k)  # noqa: E731
    for r in racks:
        ajouter(r.get("reference", ""), "rack")
        ajouter(r.get("alimentation") or "Alimentation à choisir", "alimentation")
        for o in r.get("occupation", []):
            if o["role"] == "processeur" and o["position"] != min(x["position"] for x in r["occupation"]
                                                                  if x["role"] == "processeur"):
                continue                               # un processeur M580 occupe deux emplacements
            ajouter(o["reference"], o["role"])
    for m in modules:
        ajouter(get(m, "reference") or f"Carte {get(m, 'nature')} (référence à préciser)", "carte")
    if len(racks) > 1:
        ajouter(ext.get("module", "Module d'extension"), "extension", len(racks))
        ajouter(ext.get("cable", "Câble d'extension"), "extension", len(racks) - 1)
        ajouter(ext.get("terminaison", "Terminaison"), "extension", 2)
    libres = sum(max(0, v) for v in emplacements_libres(racks, modules).values())
    if libres and ext.get("cache"):
        ajouter(ext["cache"], "cache d'emplacement libre", libres)
    ordre = {"rack": 0, "alimentation": 1, "processeur": 2, "communication": 3, "carte": 4, "extension": 5}
    return [{"reference": ref, "designation": desig.get(ref, ""), "quantite": n, "role": role}
            for (ref, role), n in sorted(lignes.items(), key=lambda x: (ordre.get(x[0][1], 9), x[0][0]))]


# ---------------------------------------------------------------------------- Advantys STB
def proposer_stb(points, reserve=0.2, chemin=None, min_cartes=None, emplacements_libres=0):
    """Composition d'îlot(s) Advantys STB : interface réseau (NIM), distribution 24 V CC (PDM), modules d'E/S
    (profil du catalogue), embases, plaque de terminaison. Contrôles des guides Schneider : 32 modules d'E/S au
    plus par îlot, courant du bus logique fourni par le NIM (1 200 mA de 0 à 60 °C).

    Proposition **indicative** (non applicable) : les E/S d'un îlot sont lues par l'automate maître (scrutation
    Modbus TCP) ; la correspondance voie → mot de l'automate n'est pas encore établie dans OGIAS, aucune adresse
    n'est donc proposée ni inventée."""
    cat = catalogue_stb(chemin)
    profil = cat["profil_defaut"]
    pr, nim, pdm = cat["profils"][profil], cat["nim"], cat["pdm"]
    p = Proposition("STB", profil, applicable=False, remarques=[
        "Îlot à saisir dans le logiciel Advantys dans l'ordre de la composition (emplacement / nœud), puis à "
        "télécharger dans le NIM.",
        "Proposition indicative (nomenclature d'îlot) : les E/S sont lues par l'automate maître par scrutation "
        "Modbus TCP ; la correspondance des voies avec les mots de l'automate n'est pas établie dans OGIAS, aucune "
        "adresse n'est proposée.",
        "Gamme Advantys STB commercialisée avec annonce de fin de vie (fin de fabrication 01/12/2027) : pour un "
        "ouvrage neuf, vérifier la gamme de remplacement (Edge I/O NTS)."])
    modules = []
    for nature, nb in compter(points).items():
        ref = pr[nature]
        carte = cat["_cartes"][ref]
        voies = int(carte["voies"])
        utiles = max(1, math.floor(voies * (1 - reserve)))
        n = math.ceil(nb / utiles) if nb else 0
        separation = int((min_cartes or {}).get(nature, 0))
        if nb and separation > n:
            p.remarques.append(f"{nature} : {separation} modules au lieu de {n} pour séparer les équipements "
                               "d'un même groupe de secours (modules distincts).")
            n = separation
        p.besoins.append(Besoin(nature, nb, ref, voies, utiles, n))
        modules += [(nature, carte)] * n
    if not modules:
        p.remarques.append("Aucune E/S câblée : aucun module à proposer.")
        return p
    maxi = int(nim["modules_max"])
    libres = max(0, min(int(emplacements_libres), maxi - 1))
    par_ilot = maxi - libres
    budget = int(nim["courant_bus_ma"])
    for numero in range(math.ceil(len(modules) / par_ilot)):
        lot = modules[numero * par_ilot:(numero + 1) * par_ilot]
        # Numérotation du logiciel Advantys : emplacement 1 = NIM (nœud 127), 2 = PDM (sans nœud), modules d'E/S à
        # partir de l'emplacement 3 avec les nœuds 1, 2, 3…, plaque de terminaison en dernier (sans nœud).
        fin = len(lot) + 3
        composition = ([{"emplacement": 1, "reference": nim["reference"], "noeud": 127, "role": "Interface réseau"},
                        {"emplacement": 2, "reference": pdm["reference"], "noeud": None, "role": "Alimentation 24 V CC",
                         "embase": pdm["embase"]}]
                       + [{"emplacement": i + 3, "reference": c["reference"], "noeud": i + 1, "role": c["description"],
                           "embase": c["embase"]} for i, (_n, c) in enumerate(lot)]
                       + [{"emplacement": fin, "reference": cat["terminaison"]["reference"], "noeud": None,
                           "role": "Terminaison du bus d'îlot"}])
        p.racks.append({"numero": numero, "reference": f"Îlot {nim['reference']}", "positions": fin + libres,
                        "cpu": [1, 2], "nim": nim["reference"], "pdm": pdm["reference"],
                        "embase_pdm": pdm["embase"], "terminaison": cat["terminaison"]["reference"],
                        "composition": composition,
                        "image_es": image_ilot([c["reference"] for _n, c in lot], chemin)})
        for i, (nature, carte) in enumerate(lot):
            p.modules.append({"rack": numero, "position": i + 3, "noeud": i + 1, "nature": nature,
                              "voies": int(carte["voies"]), "reference": carte["reference"], "embase": carte["embase"]})
        courant = sum(int(c["courant_bus_ma"]) for _, c in lot)
        if courant > budget:
            ext = cat["extension"]
            p.remarques.append(
                f"Îlot {numero} : courant du bus logique {courant} mA, au-delà des {budget} mA fournis par le "
                f"{nim['reference']} : segment d'extension à prévoir ({ext['eos']} / {ext['bos']}) ; "
                + ext["remarque"])
    if len(p.racks) > 1:
        p.remarques.append(f"{len(p.racks)} îlots : au plus {maxi} modules d'E/S par îlot "
                           f"({libres} gardé(s) libre(s) pour une extension).")
    elif libres:
        p.remarques.append(f"{libres} module(s) d'E/S gardé(s) disponible(s) sur l'îlot pour une extension "
                           f"(limite {maxi}).")
    p.remarques.append("Alimentation : un seul groupe 24 V CC derrière le PDM ; un module 115 / 230 V CA "
                       "demanderait son propre PDM (règle des groupes de tension).")
    return p


def _voies_image(type_image, nb, sortie, entree):
    """[{voie, registre, etat}] : registre de donnée (et d'état s'il existe) de chaque voie (1 à nb). Voies TOR :
    toutes dans le même registre ; le rang du bit de chaque voie n'est pas documenté (à confirmer)."""
    if type_image == "TOR_E" and entree:
        return [{"voie": v, "registre": entree[0], "etat": entree[1] if len(entree) > 1 else None}
                for v in range(1, nb + 1)]
    if type_image == "TOR_S" and sortie:
        return [{"voie": v, "registre": sortie[0], "etat": entree[1] if len(entree) > 1 else None}
                for v in range(1, nb + 1)]
    if type_image == "ANA_E" and len(entree) >= 2 * nb:
        return [{"voie": v, "registre": entree[2 * v - 2], "etat": entree[2 * v - 1]} for v in range(1, nb + 1)]
    if type_image == "ANA_S" and len(sortie) >= nb:
        return [{"voie": v, "registre": sortie[v - 1], "etat": entree[v - 1] if len(entree) >= nb else None}
                for v in range(1, nb + 1)]
    return []


def image_ilot(references, chemin=None):
    """Image d'E/S d'un îlot STB vue par le maître Modbus TCP (guide STB NIP 2212) : pour chaque module d'E/S, dans
    l'ordre des nœuds, {noeud, reference, sortie: [registres 4x], entree: [registres 4x], connu}. Un module dont le
    format d'image n'est pas documenté dans le catalogue arrête le calcul : les modules suivants sont marqués
    inconnus (leurs registres dépendent de lui), rien n'est deviné."""
    cat = catalogue_stb(chemin)
    regle = cat["image_es"]
    sortie, entree, connu, lignes = int(regle["debut_sortie"]), int(regle["debut_entree"]), True, []
    for noeud, ref in enumerate(references, start=1):
        img = cat["_cartes"].get(ref, {}).get("image_es")
        connu = connu and img is not None
        if not connu:
            lignes.append({"noeud": noeud, "reference": ref, "sortie": [], "entree": [], "connu": False})
            continue
        ns, ne = int(img["registres_sortie"]), int(img["registres_entree"])
        rs, re_ = list(range(sortie, sortie + ns)), list(range(entree, entree + ne))
        lignes.append({"noeud": noeud, "reference": ref, "sortie": rs, "entree": re_, "connu": True,
                       "voies": _voies_image(img.get("type", ""), int(cat["_cartes"][ref]["voies"]), rs, re_)})
        sortie, entree = sortie + ns, entree + ne
    return lignes
