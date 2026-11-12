"""Import d'un inventaire d'équipements (liste Excel / ODS / CSV, ou base de supervision existante).

Déterministe et sans écriture tant que l'utilisateur n'a pas confirmé l'aperçu :
1. repérer les colonnes (repère, libellé, type, modèle) ;
2. découper chaque repère : lieu (4) + ouvrage (2) + sous-ensemble (2) + type et numéro (4) ;
3. trouver le type : colonne type fournie, sinon motif du repère (« PM01 » → PM, « A01P » → A--P) ;
4. proposer le modèle : colonne modèle, sinon le modèle unique du type ;
5. classer chaque ligne : à créer, à coder (type inconnu…), déjà présent, refusé (autre ouvrage).
"""
import re
from dataclasses import dataclass, asdict

from .modele import Equipement
from .modeles import code_type, motif

SYNONYMES = {
    "repere": ("COD_EQPT", "REPERE", "REPÈRE", "PCF", "REPERE EQUIPEMENT", "CODE EQUIPEMENT"),
    "libelle": ("LIB_EQPT", "LIBELLE", "LIBELLÉ", "DESIGNATION", "DÉSIGNATION", "LIBELLE EQUIPEMENT"),
    "type": ("COD_TYP_MAT", "TYPE", "TYPE DE MATERIEL", "TYPE MATERIEL"),
    "modele": ("NOM_MODELE", "MODELE", "MODÈLE"),
}
RE_REPERE = re.compile(r"^(?:[A-Z0-9]{12}|[A-Z0-9]{14})$")


@dataclass
class LigneInventaire:
    repere: str
    libelle: str = ""
    sous_ensemble: str = ""
    type: str = ""
    numero: str = ""
    modele: str = ""
    etat: str = ""          # « à créer », « à coder », « déjà présent », « refusé »
    motif: str = ""

    def dict(self):
        return asdict(self)


def _norm(c):
    t = str(c or "").replace("\r", "\n")
    morceaux = [m.strip() for m in re.split(r"\n| / ", t) if m.strip()]
    return morceaux[-1].upper() if morceaux else ""


def _colonnes(feuilles):
    """(index des colonnes, lignes) de la feuille la plus probable."""
    meilleur = None
    for nom, lignes in feuilles.items():
        for i, ligne in enumerate(lignes[:15]):
            noms = [_norm(c) for c in ligne]
            col = {}
            for cle, syn in SYNONYMES.items():
                for k, n in enumerate(noms):
                    if n in syn and cle not in col:
                        col[cle] = k
            if "repere" in col:
                score = len(col) * 10000 + len(lignes)
                if meilleur is None or score > meilleur[0]:
                    meilleur = (score, col, lignes[i + 1:])
                break
    if meilleur is None:
        raise ValueError("Aucune colonne « repère » trouvée (COD_EQPT, Repère, PCF…).")
    return meilleur[1], meilleur[2]


def _type_depuis_repere(fin, types_connus):
    """« PM01 » → (PM, 01) ; « A01P » → (A--P, 01). Le motif le plus spécifique l'emporte."""
    trouves = []
    for code in types_connus:
        m = motif(code)
        rx = "^" + re.escape(m).replace(re.escape("--"), r"(\d\d)", 1) + "$"
        r = re.match(rx, fin)
        if r:
            trouves.append((m.count("-"), code, r.group(1)))
    if not trouves:
        return None, None
    trouves.sort()
    return trouves[0][1], trouves[0][2]


def decouper_repere(rep, charte_12):
    """(préfixe d'ouvrage, sous-ensemble, fin type+numéro) selon le format du repère.

    - 14 caractères : préfixe 8 + sous-ensemble 2 + type/numéro 4 (ouvrages numérotés avant le 9 novembre) ;
    - 12 caractères, ouvrage à la charte ESB/RESO : préfixe 8 + type/numéro 4, sans sous-ensemble
      (le sous-ensemble est alors « 00 », simple regroupement) ;
    - 12 caractères, ouvrage historique : préfixe 6 + sous-ensemble 2 + type/numéro 4."""
    if len(rep) == 14:
        return rep[:8], rep[8:10], rep[10:]
    if charte_12:
        return rep[:8], "00", rep[8:]
    return rep[:6], rep[6:8], rep[8:]


def analyser(feuilles, session):
    o = session.ouvrage
    charte = o.format_repere == "12"
    col, lignes = _colonnes(feuilles)
    g = lambda r, c: (str(r[col[c]]).strip() if c in col and col[c] < len(r) else "")
    connus = set(session.modeles["types"]) | {t["code"] for t in session.catalogue.types}
    existants = {o.repere(e) for e in o.equipements}
    prefixe = o.prefixe() if (o.lieu and o.code_ouvrage) else ""
    if not prefixe:                                      # ouvrage vierge : préfixe le plus fréquent du fichier
        from collections import Counter
        c = Counter(decouper_repere(g(r, "repere").upper(), charte)[0] for r in lignes if RE_REPERE.match(g(r, "repere").upper()))
        prefixe = c.most_common(1)[0][0] if c else ""
    vus, resultat = set(), []
    for r in lignes:
        rep = g(r, "repere").upper()
        if not rep or rep in vus:
            continue
        vus.add(rep)
        l = LigneInventaire(rep, g(r, "libelle"))
        if not RE_REPERE.match(rep):
            l.etat, l.motif = "à coder", "repère hors format (12 caractères, ou 14 pour un ouvrage numéroté avant le 9 novembre)"
            resultat.append(l)
            continue
        if charte and len(rep) == 14:
            l.etat, l.motif = "à coder", ("repère à 14 caractères (avec sous-ensemble) : la charte ESB/RESO "
                                          "en compte 12 ; à recoder, aucun renommage automatique")
            resultat.append(l)
            continue
        pref, l.sous_ensemble, fin = decouper_repere(rep, charte)
        if prefixe and pref != prefixe:
            l.etat, l.motif = "refusé", f"autre ouvrage ({pref} au lieu de {prefixe})"
            resultat.append(l)
            continue
        fourni = code_type(g(r, "type")) if g(r, "type") else ""
        typ, num = _type_depuis_repere(fin, [fourni] if fourni else connus)
        if fourni and typ is None:
            typ, num = fourni, ""
        l.type, l.numero = typ or "", num or ""
        t = session.modeles["types"].get(l.type)
        modele_fichier = g(r, "modele")
        # Le modèle doit exister dans le référentiel SOREP ; un nom venu du fichier n'est jamais créé d'office.
        l.modele = modele_fichier if (t and modele_fichier in t["modeles"]) else ""
        if not l.modele and t and len(t["modeles"]) == 1:
            l.modele = t["modeles"][0]
        note_modele = (f"modèle « {modele_fichier} » absent du référentiel : à choisir après création"
                       if modele_fichier and not l.modele else "")
        if rep in existants:
            l.etat, l.motif = "déjà présent", "rien n'est modifié"
        elif not l.type or l.type not in connus:
            l.etat, l.motif = "à coder", f"type {l.type or fin} absent du référentiel"
        elif not l.numero:
            l.etat, l.motif = "à coder", f"le repère ne suit pas le motif du type {motif(l.type)}"
        else:
            l.etat = "à créer"
            if not l.modele and t and len(t["modeles"]) > 1:
                l.motif = f"modèle à choisir ({len(t['modeles'])} possibles)"
            elif note_modele:
                l.motif = note_modele
            elif not l.modele:
                l.motif = "aucun modèle pour ce type dans le référentiel"
        resultat.append(l)
    return resultat


def appliquer(lignes, session):
    """Crée les équipements « à créer » (et leurs sous-ensembles). Rien d'autre n'est modifié."""
    o = session.ouvrage
    if not o.lieu and not o.code_ouvrage:
        a_creer = [l for l in lignes if (l.etat if isinstance(l, LigneInventaire) else l["etat"]) == "à créer"]
        prefixes = {decouper_repere(l.repere if isinstance(l, LigneInventaire) else l["repere"],
                                    o.format_repere == "12")[0] for l in a_creer}
        if len(prefixes) == 1:                        # tous du même ouvrage (garanti par analyser)
            p = prefixes.pop()
            session.definir("lieu", p[:4])
            session.definir("code_ouvrage", p[4:6])
            if len(p) == 8:
                session.definir("numero_ouvrage", p[6:8])
    crees = 0
    for l in lignes:
        l = l if isinstance(l, LigneInventaire) else LigneInventaire(**l)
        if l.etat != "à créer":
            continue
        if l.sous_ensemble not in {s.code for s in o.sous_ensembles}:
            session.ajouter_sous_ensemble(l.sous_ensemble, "")
        session.ajouter_equipement(Equipement(l.sous_ensemble, l.type, l.numero, l.libelle[:32], modele=l.modele))
        crees += 1
    return crees
