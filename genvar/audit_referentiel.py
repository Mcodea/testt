"""Contrôle de conception du référentiel des équipements (catalogue des signaux et règles).

But : repérer, type par type, les informations fonctionnelles qui risquent d'être oubliées ou générées
sans fondement, AVANT qu'un ouvrage les utilise. Le contrôle ne modifie rien : il signale.

Chaque constat a un code stable, une gravité (« Erreur » : le référentiel produit un résultat faux ;
« Alerte » : décision de conception à confirmer) et la liste des clés concernées.

Constats :
- CALCULEE_SANS_SOURCE  information calculée (discordance, défaut de manœuvre, temps…) générée par défaut
                        alors que le type ne déclare pas les E/S qui permettent de la calculer.
- TYPE_SANS_ES          le type transmet des informations mais ne déclare aucune E/S physique : en projet
                        neuf, l'étape Matériel ne compte aucune voie pour lui.
- CALCULEE_SANS_ORDRE   défaut / temps de manœuvre généré d'office alors que l'ordre n'est qu'optionnel.
- EA_SANS_DEFAUT        entrée analogique sans information de défaut de mesure (rupture, hors plage).
- SEUILS_PAR_DEFAUT     alarmes de seuil générées d'office alors qu'elles ne valent que si l'exploitation
                        les prévoit (ailleurs elles sont en option ou proposées).
- OPTION_SANS_EFFET     option proposée à l'utilisateur qui ne retient aucun signal.
- DOUBLON               même information (famille + code) déclarée deux fois pour un type.
- REGLE_SANS_SOURCE     règle dont une condition « si » n'existe pas dans le type : elle ne s'applique jamais.
- SANS_JUSTIFICATION    information calculée par règle sans texte de logique : l'automaticien ne sait pas
                        quoi programmer.
"""
from dataclasses import dataclass, field

# Informations qui n'existent qu'à partir d'un calcul sur des E/S (retours, ordres, temporisations).
CODES_CALCULES = {"DISC", "INT", "MNV", "DEFTPS", "DEFMNV", "DEFDEM", "TPS", "ABSIMP", "INCOH", "DISCMES", "DEFINT"}
CODES_ORDRE = {"MNV", "DEFTPS", "DEFMNV", "TPS", "DEFDEM"}      # n'existent que si un ordre est envoyé
CODES_SEUILS = {"TB", "B", "H", "TH"}
# Types dont les informations sont produites par l'automate lui-même (diagnostic, mode, mot de vie) :
# l'absence d'E/S physique y est normale.
TYPES_INTERNES = {"UF", "AU", "AP", "LI", "OU"}


@dataclass
class Constat:
    code: str
    gravite: str
    type: str
    message: str
    cles: list = field(default_factory=list)

    def dict(self):
        return dict(self.__dict__)


def _cle(s):
    return f"{s['famille']}_{s['code']}"


def auditer(catalogue):
    """[Constat] pour tout le catalogue, trié par type puis gravité."""
    constats = []
    regles = getattr(catalogue, "regles", []) or []
    for t in catalogue.types:
        code = t["code"]
        signaux = catalogue.signaux_du_type(code)
        if not signaux:
            continue
        cles = [_cle(s) for s in signaux]
        # E/S physiques : famille ES, ou information (TS, TC…) portée directement par une voie câblée
        es = [s for s in signaux if s["famille"] == "ES" or s.get("es") in ("ET", "ST", "EA", "SA")]
        fonct = [s for s in signaux if s["famille"] != "ES"]
        regles_t = [r for r in regles if r.get("type") == code]
        produites = {c for r in regles_t for c in r.get("propose", [])}

        for c in sorted({c for c in cles if cles.count(c) > 1}):
            constats.append(Constat("DOUBLON", "Erreur", code, f"{c} déclaré {cles.count(c)} fois.", [c]))

        es_base = [x for x in es if x["presence"] in ("Obligatoire", "Par défaut")]
        if fonct and not es and code not in TYPES_INTERNES:
            constats.append(Constat("TYPE_SANS_ES", "Alerte", code,
                                    f"{len(fonct)} information(s) transmise(s) mais aucune E/S physique déclarée : "
                                    "à câbler en E/S personnalisées ou à recevoir par communication.",
                                    [_cle(s) for s in fonct][:6]))

        calc = [s for s in fonct if s["code"] in CODES_CALCULES and s["presence"] in ("Par défaut", "Obligatoire")
                and _cle(s) not in produites]
        if calc and not es_base:
            constats.append(Constat("CALCULEE_SANS_SOURCE", "Alerte", code,
                                    "Information(s) calculée(s) générée(s) d'office alors qu'aucune E/S de retour ou "
                                    "d'ordre n'est retenue par défaut : rien ne permet de les calculer (ex. discordance sans fins de course, "
                                    "temps de manœuvre sans commande).", [_cle(s) for s in calc]))

        ordres = [x for x in signaux if (x.get("es") == "ST" or x["famille"] == "TC")
                  and x["presence"] in ("Obligatoire", "Par défaut")]
        sans_ordre = [s for s in fonct if s["code"] in CODES_ORDRE and s["presence"] in ("Par défaut", "Obligatoire")]
        if sans_ordre and not ordres:
            constats.append(Constat("CALCULEE_SANS_ORDRE", "Erreur", code,
                                    "Défaut ou temps de manœuvre généré d'office alors que la commande n'est qu'en "
                                    "option : une vanne ou un moteur non commandé recevrait un défaut sur un ordre "
                                    "inexistant.", [_cle(s) for s in sans_ordre]))

        for s in es:
            if s.get("es") != "EA":
                continue
            src = _cle(s)
            defauts = [r for r in regles_t if src in r.get("si", []) and
                       any(p.split("_", 1)[1].startswith("DEF") for p in r.get("propose", []))]
            if s["famille"] != "ES" and any(x["famille"] == "TS" and x["code"].startswith("DEF") for x in fonct):
                defauts = [True]          # type « porté » : un défaut de l'appareil est déclaré, à préciser
            if not defauts:
                constats.append(Constat("EA_SANS_DEFAUT", "Alerte", code,
                                        f"{src} ({s.get('information', '')}) : aucune information de défaut de mesure "
                                        "(rupture, hors plage) n'en découle.", [src]))

        seuils = [s for s in fonct if s["famille"] == "TS" and s["code"] in CODES_SEUILS and
                  s["presence"] == "Par défaut"]
        if seuils:
            constats.append(Constat("SEUILS_PAR_DEFAUT", "Alerte", code,
                                    "Alarmes de seuil générées d'office : elles ne valent que si l'exploitation les "
                                    "prévoit (option ou proposition sur d'autres types).", [_cle(s) for s in seuils]))

        utilisees = {s.get("option") for s in signaux if s.get("presence") == "Option"}
        for opt in t.get("options", []):
            if opt not in utilisees:
                constats.append(Constat("OPTION_SANS_EFFET", "Alerte", code,
                                        f"Option « {opt} » : aucun signal ne lui est associé.", []))

        for r in regles_t:
            manquantes = [c for c in r.get("si", []) if "*" not in c and c not in cles]
            if manquantes:
                constats.append(Constat("REGLE_SANS_SOURCE", "Erreur", code,
                                        f"Règle {r.get('id')} : {', '.join(manquantes)} absent(s) du type ; "
                                        "la règle ne s'applique jamais.", manquantes))
            if r.get("mode") == "proposition" and not (r.get("logique") or "").strip() and not r.get("gouvernance"):
                constats.append(Constat("SANS_JUSTIFICATION", "Alerte", code,
                                        f"Règle {r.get('id')} : aucune logique écrite pour l'automaticien.",
                                        list(r.get("propose", []))))
    ordre = {"Erreur": 0, "Alerte": 1}
    return sorted(constats, key=lambda c: (c.type, ordre.get(c.gravite, 2), c.code))


def resume(constats):
    """{code: nombre} pour l'affichage."""
    sortie: dict[str, int] = {}
    for c in constats:
        sortie[c.code] = sortie.get(c.code, 0) + 1
    return sortie
