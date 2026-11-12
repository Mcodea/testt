"""Référentiel métier OGIAS : UN seul dépôt versionné (types, signaux, règles, modèles).

Cycle (décision du 9 novembre 2026, module 2 étendu à tout le référentiel) :
    révision publiée ──créer──▶ brouillon ──modifier / importer Excel──▶ contrôler ──valider──▶ publier ▶ révision n+1

- La révision PUBLIÉE est celle des fichiers en service (catalogue.json et referentiel_modeles.json du dossier de
  données). Elle n'est jamais modifiée directement : toute modification passe par le brouillon.
- Un seul brouillon à la fois, enregistré sur disque (brouillon.json) ; il garde l'empreinte de la révision dont il
  part : si la révision publiée change entre-temps, la publication est refusée.
- Valider fige l'empreinte du brouillon ; toute modification ultérieure annule la validation.
- Publier écrit les deux fichiers sous verrou, avec retour à l'état antérieur en cas d'échec, archive la révision
  (revisions/Rnnnn.json, immuable) et met à jour head.json. Un fichier en service modifié hors de ce cycle est
  détecté (empreinte) et bloque toute publication.
- Restaurer une ancienne révision crée un NOUVEAU brouillon : l'historique n'est jamais réécrit.
- Les ouvrages ne sont jamais lus ni modifiés ici : chacun garde son référentiel figé et l'adopte sur décision.
- Excel n'est qu'une interface d'échange (referentiel_excel) : la vérité est ce dépôt JSON. Aucune formule, macro
  ou lien externe n'est accepté dans un classeur importé ; une règle qui exige un algorithme reste décrite en texte.
"""
import copy
import hashlib
import json
import os
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import datetime

from . import chemins, dictionnaire_es as _dico, lexique as _lexique, modeles as _modeles
from .catalogue import Catalogue, PRESENCES, FAMILLES_CATALOGUE, TYPES_LOGIQUES, anomalies_interne

CHAMPS_INSTALLATION = {"adresse", "adresses", "voie", "module", "phys_min", "phys_max", "signal_min", "signal_max",
                       "brut_min", "brut_max", "analogique", "impulsion", "poids", "adresse_ip", "ip", "password",
                       "mot_de_passe"}


class DepotRefuse(ValueError):
    """Opération refusée ; ni la révision publiée ni le brouillon n'ont été modifiés."""


def _canonique(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def empreinte(donnees):
    return hashlib.sha256(_canonique(donnees).encode("utf-8")).hexdigest()


def _ecrire_json(chemin, donnees, indent=1):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".ogias-", suffix=".tmp", dir=os.path.dirname(chemin))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(donnees, f, ensure_ascii=False, indent=indent)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, chemin)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _lire_json(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError) as exc:
        raise DepotRefuse(f"Fichier du référentiel illisible : {os.path.basename(chemin)}.") from exc
    if not isinstance(d, dict):
        raise DepotRefuse(f"{os.path.basename(chemin)} : objet JSON attendu.")
    return d


def maintenant():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def auteur_par_defaut():
    try:
        import getpass
        return os.environ.get("USERNAME") or getpass.getuser()
    except Exception:                                    # noqa: BLE001
        return ""


class Depot:
    def __init__(self, base=None):
        self.base = base or chemins.dossier_donnees()
        self.racine = os.path.join(self.base, "Referentiel")
        self.dossier_revisions = os.path.join(self.racine, "revisions")
        self.f_head = os.path.join(self.racine, "head.json")
        self.f_brouillon = os.path.join(self.racine, "brouillon.json")
        self.f_catalogue = os.path.join(self.base, "catalogue.json")
        self.f_modeles = os.path.join(self.base, "referentiel_modeles.json")

    # ------------------------------------------------------------------ verrou
    @contextmanager
    def _verrou(self):
        os.makedirs(self.racine, exist_ok=True)
        f = os.path.join(self.racine, ".operation.lock")
        try:
            fd = os.open(f, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise DepotRefuse("Référentiel occupé : une autre opération est en cours (verrou local).") from exc
        try:
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            yield
        finally:
            try:
                os.unlink(f)
            except OSError:
                pass

    # ------------------------------------------------------------------ révision publiée
    def publie(self):
        """{"catalogue": {...}, "modeles": {...}} : le référentiel en service."""
        cat = Catalogue.charger(self.f_catalogue if os.path.isfile(self.f_catalogue)
                                else chemins.fichier_catalogue_origine())
        if os.path.isfile(self.f_modeles):
            ref = _lire_json(self.f_modeles)
        elif os.path.isfile(_modeles.fichier_origine()):
            ref = _lire_json(_modeles.fichier_origine())
        else:
            ref = _modeles.vide()
        return {"catalogue": {"version": cat.version, "types": cat.types, "signaux": cat.signaux, "regles": cat.regles},
                "modeles": ref}

    def head(self):
        return _lire_json(self.f_head) if os.path.isfile(self.f_head) else None

    def _coherent(self):
        """Révision publiée + tête ; refuse si les fichiers en service ont été modifiés hors du cycle."""
        p, h = self.publie(), self.head()
        if h is not None:
            if empreinte(p) != h.get("empreinte"):
                raise DepotRefuse("Le référentiel en service a été modifié hors du cycle brouillon → publication "
                                  "(fichier édité à la main ?). Publication bloquée : restaurez une révision ou faites "
                                  "contrôler le fichier.")
            r = self.revision(int(h["revision"]))
            if empreinte(r["donnees"]) != h["empreinte"]:
                raise DepotRefuse("Historique des révisions incohérent : publication bloquée.")
        return p, h

    # ------------------------------------------------------------------ historique
    def revisions(self):
        """[{numero, date, auteur, motif, empreinte}] de la plus récente à la plus ancienne."""
        if not os.path.isdir(self.dossier_revisions):
            return []
        sortie = []
        for f in sorted(os.listdir(self.dossier_revisions), reverse=True):
            if f.startswith("R") and f.endswith(".json"):
                try:
                    d = _lire_json(os.path.join(self.dossier_revisions, f))
                    sortie.append({"numero": d["numero"], "date": d.get("date", ""), "auteur": d.get("auteur", ""),
                                   "motif": d.get("motif", ""), "empreinte": d.get("empreinte", "")[:16]})
                except (DepotRefuse, KeyError):
                    continue
        return sortie

    def revision(self, numero):
        f = os.path.join(self.dossier_revisions, f"R{int(numero):04d}.json")
        if not os.path.isfile(f):
            raise DepotRefuse(f"Révision R{int(numero):04d} introuvable.")
        d = _lire_json(f)
        if "donnees" not in d:                      # révision archivée par la V0.27 (catalogue + modèles à plat)
            d["donnees"] = {"catalogue": d.get("catalogue", {}), "modeles": d.get("modeles", {})}
            d["empreinte"] = empreinte(d["donnees"])
        if d.get("empreinte") and empreinte(d["donnees"]) != d["empreinte"]:
            raise DepotRefuse(f"Révision R{int(numero):04d} altérée (empreinte).")
        return d

    def _initialiser_historique(self):
        """Première utilisation : la révision en service devient R0001 (rien n'est modifié)."""
        if self.head() is not None:
            return
        p = self.publie()
        anciennes = self.revisions()
        n = (max(r["numero"] for r in anciennes) + 1) if anciennes else 1
        e = empreinte(p)
        _ecrire_json(os.path.join(self.dossier_revisions, f"R{n:04d}.json"),
                     {"numero": n, "date": maintenant(), "auteur": "", "motif": "Référentiel en service au démarrage "
                      "du cycle de révisions", "empreinte": e, "donnees": p})
        _ecrire_json(self.f_head, {"revision": n, "empreinte": e, "date": maintenant(), "auteur": "",
                                   "motif": "Référentiel en service au démarrage du cycle de révisions"})

    # ------------------------------------------------------------------ brouillon
    def brouillon(self):
        return _lire_json(self.f_brouillon) if os.path.isfile(self.f_brouillon) else None

    def _brouillon_exige(self):
        b = self.brouillon()
        if b is None:
            raise DepotRefuse("Aucun brouillon : créez d'abord un brouillon depuis la révision publiée.")
        return b

    def creer_brouillon(self, auteur=""):
        with self._verrou():
            self._initialiser_historique()
            p, h = self._coherent()
            if self.brouillon() is not None:
                raise DepotRefuse("Un brouillon existe déjà : terminez-le ou abandonnez-le avant d'en créer un autre.")
            b = {"base_revision": int(h["revision"]), "base_empreinte": h["empreinte"], "cree_le": maintenant(),
                 "modifie_le": maintenant(), "auteur": auteur or auteur_par_defaut(), "etat": "brouillon",
                 "empreinte_validee": "", "journal": [], "donnees": p}
            _ecrire_json(self.f_brouillon, b)
            return b

    def restaurer_en_brouillon(self, numero, auteur=""):
        with self._verrou():
            self._initialiser_historique()
            _, h = self._coherent()
            if self.brouillon() is not None:
                raise DepotRefuse("Un brouillon existe déjà : terminez-le ou abandonnez-le avant une restauration.")
            ancien = self.revision(numero)["donnees"]
            b = {"base_revision": int(h["revision"]), "base_empreinte": h["empreinte"], "cree_le": maintenant(),
                 "modifie_le": maintenant(), "auteur": auteur or auteur_par_defaut(), "etat": "brouillon",
                 "empreinte_validee": "", "restauration_de": int(numero),
                 "journal": [f"{maintenant()} — contenu repris de la révision R{int(numero):04d}"], "donnees": ancien}
            _ecrire_json(self.f_brouillon, b)
            return b

    def abandonner(self):
        """Supprime le brouillon (la révision publiée n'est jamais touchée). Une copie est gardée dans
        `brouillons_supprimes/` (les 5 dernières) pour le récupérer après une erreur ; renvoie son nom."""
        with self._verrou():
            if not os.path.isfile(self.f_brouillon):
                return ""
            dossier = os.path.join(self.racine, "brouillons_supprimes")
            os.makedirs(dossier, exist_ok=True)
            nom = f"brouillon-{datetime.now():%Y%m%d-%H%M%S-%f}.json"
            os.replace(self.f_brouillon, os.path.join(dossier, nom))
            for ancien in sorted(f for f in os.listdir(dossier) if f.startswith("brouillon-"))[:-5]:
                try:
                    os.unlink(os.path.join(dossier, ancien))
                except OSError:
                    pass
            return nom

    def brouillons_supprimes(self):
        """Copies des brouillons supprimés, le plus récent d'abord (lecture seule)."""
        dossier = os.path.join(self.racine, "brouillons_supprimes")
        try:
            return sorted((f for f in os.listdir(dossier) if f.startswith("brouillon-")), reverse=True)
        except OSError:
            return []

    def recuperer_brouillon(self, nom):
        """Remet en brouillon une copie supprimée, s'il n'y a pas déjà un brouillon en cours."""
        with self._verrou():
            if os.path.isfile(self.f_brouillon):
                raise DepotRefuse("Un brouillon est déjà en cours : publiez-le ou supprimez-le d'abord.")
            if nom not in self.brouillons_supprimes() or os.path.basename(nom) != nom:
                raise DepotRefuse("Copie de brouillon introuvable.")
            os.replace(os.path.join(self.racine, "brouillons_supprimes", nom), self.f_brouillon)

    def remplacer_donnees(self, donnees, motif):
        """Nouveau contenu du brouillon (édition à l'écran ou import Excel contrôlé) ; annule la validation."""
        with self._verrou():
            b = self._brouillon_exige()
            b["donnees"] = donnees
            b["etat"], b["empreinte_validee"] = "brouillon", ""
            b["modifie_le"] = maintenant()
            b.setdefault("journal", []).append(f"{maintenant()} — {motif}")
            b["journal"] = b["journal"][-200:]
            _ecrire_json(self.f_brouillon, b)
            return b

    # ------------------------------------------------------------------ objets métier
    @staticmethod
    def objets(donnees):
        c = donnees["catalogue"]
        return Catalogue(copy.deepcopy(c["types"]), copy.deepcopy(c["signaux"]), c.get("version", ""),
                         copy.deepcopy(c.get("regles", []))), copy.deepcopy(donnees["modeles"])

    # ------------------------------------------------------------------ contrôles
    def controler(self, donnees=None):
        """{"erreurs": [...], "alertes": [...]} : bloquants et points de conception du brouillon."""
        from . import audit_referentiel
        if donnees is None:
            donnees = self._brouillon_exige()["donnees"]
        cat, ref = self.objets(donnees)
        erreurs = list(cat.anomalies())
        e_mod, a_mod = controler_modeles(ref, cat)
        erreurs += e_mod
        alertes = a_mod + [f"{c.type} — {c.code} : {c.message}" for c in audit_referentiel.auditer(cat) if c.gravite != "Erreur"]
        erreurs += [f"{c.type} — {c.code} : {c.message}" for c in audit_referentiel.auditer(cat) if c.gravite == "Erreur"]
        return {"erreurs": erreurs, "alertes": alertes}

    def differences(self, avant=None, apres=None):
        from . import referentiel_excel as rx
        if avant is None:
            avant = self.publie()
        if apres is None:
            apres = self._brouillon_exige()["donnees"]
        e = lambda d: rx.etat(*self.objets(d))
        return rx.differences(e(avant), e(apres), rx.ouvrages_par_type())

    # ------------------------------------------------------------------ validation et publication
    def valider(self, auteur=""):
        with self._verrou():
            b = self._brouillon_exige()
            _, h = self._coherent()
            if b["base_empreinte"] != h["empreinte"]:
                raise DepotRefuse("La révision publiée a changé depuis la création du brouillon : recréez-le.")
            c = self.controler(b["donnees"])
            if c["erreurs"]:
                raise DepotRefuse(f"Validation refusée : {len(c['erreurs'])} erreur(s), dont « {c['erreurs'][0]} ».")
            if empreinte(b["donnees"]) == h["empreinte"]:
                raise DepotRefuse("Le brouillon est identique à la révision publiée : rien à publier.")
            b["etat"], b["empreinte_validee"] = "validé", empreinte(b["donnees"])
            b["valide_par"], b["valide_le"] = auteur or auteur_par_defaut(), maintenant()
            _ecrire_json(self.f_brouillon, b)
            return b

    def publier(self, motif, empreinte_attendue, auteur=""):
        if not (motif or "").strip():
            raise DepotRefuse("Indiquez le motif de la révision.")
        with self._verrou():
            b = self._brouillon_exige()
            precedent, h = self._coherent()
            if b["base_empreinte"] != h["empreinte"]:
                raise DepotRefuse("La révision publiée a changé depuis la création du brouillon : recréez-le.")
            e = empreinte(b["donnees"])
            if b.get("etat") != "validé" or b.get("empreinte_validee") != e or e != empreinte_attendue:
                raise DepotRefuse("Publication refusée : brouillon non validé, ou modifié depuis sa validation.")
            if self.controler(b["donnees"])["erreurs"]:
                raise DepotRefuse("Publication refusée : le brouillon ne passe plus les contrôles.")
            n = int(h["revision"]) + 1
            f_rev = os.path.join(self.dossier_revisions, f"R{n:04d}.json")
            if os.path.exists(f_rev):
                raise DepotRefuse("Numéro de révision déjà utilisé : historique à contrôler.")
            donnees = copy.deepcopy(b["donnees"])
            donnees["catalogue"]["version"] = f"R{n:04d} du {datetime.now():%d/%m/%Y} — {motif.strip()[:80]}"
            e = empreinte(donnees)
            qui = auteur or auteur_par_defaut()
            sauvegardes = {f: (open(f, "rb").read() if os.path.isfile(f) else None)
                           for f in (self.f_catalogue, self.f_modeles, self.f_head)}
            try:
                _ecrire_json(f_rev, {"numero": n, "date": maintenant(), "auteur": qui, "motif": motif.strip(),
                                     "base": int(h["revision"]), "empreinte": e, "donnees": donnees})
                _ecrire_json(self.f_catalogue, donnees["catalogue"])
                _ecrire_json(self.f_modeles, donnees["modeles"])
                _ecrire_json(self.f_head, {"revision": n, "empreinte": e, "date": maintenant(), "auteur": qui,
                                           "motif": motif.strip()})
                if empreinte(self.publie()) != e:
                    raise DepotRefuse("Contrôle après publication : empreinte inattendue.")
            except Exception:
                for f, octets in sauvegardes.items():
                    if octets is None:
                        if os.path.isfile(f):
                            os.unlink(f)
                    else:
                        with open(f + ".restauration", "wb") as h_:
                            h_.write(octets)
                        os.replace(f + ".restauration", f)
                if os.path.isfile(f_rev):
                    os.unlink(f_rev)
                raise
            os.unlink(self.f_brouillon)
            return {"revision": n, "empreinte": e}

    # ------------------------------------------------------------------ état pour l'écran
    def etat(self):
        h = self.head()
        p = self.publie()
        b = self.brouillon()
        try:
            self._coherent()
            incoherence = ""
        except DepotRefuse as exc:
            incoherence = str(exc)
        c = p["catalogue"]
        sortie = {"revision": int(h["revision"]) if h else 0, "publie_le": h.get("date", "") if h else "",
                  "auteur": h.get("auteur", "") if h else "", "motif": h.get("motif", "") if h else "",
                  "empreinte": empreinte(p)[:16], "incoherence": incoherence,
                  "compteurs": {"types": len(c["types"]), "signaux": len(c["signaux"]), "regles": len(c.get("regles", [])),
                                "modeles": len(p["modeles"].get("modeles", {}))},
                  "brouillon": None}
        if b is not None:
            sortie["brouillon"] = {"etat": b["etat"], "base_revision": b["base_revision"], "cree_le": b["cree_le"],
                                   "modifie_le": b["modifie_le"], "auteur": b.get("auteur", ""),
                                   "empreinte": empreinte(b["donnees"]), "empreinte_validee": b.get("empreinte_validee", ""),
                                   "restauration_de": b.get("restauration_de"), "journal": b.get("journal", [])[-20:],
                                   "perime": bool(h) and b["base_empreinte"] != h.get("empreinte")}
        return sortie


# ============================================================================ contrôles des modèles
def controler_modeles(ref, cat):
    """(erreurs, alertes) du référentiel des modèles : index des types, noms, lignes, signaux propres, paramètres
    d'installation interdits (contrôles du module 2 sur le format en service). Un modèle proposé pour plusieurs
    types est une relation historique conservée : alerte, pas erreur."""
    msg, partages = [], []
    types, mods = ref.get("types", {}), ref.get("modeles", {})
    if not isinstance(types, dict) or not isinstance(mods, dict):
        return ["Référentiel des modèles : « types » et « modeles » doivent être des objets."], []
    for code, t in types.items():
        noms = t.get("modeles", [])
        if len(noms) != len(set(noms)):
            msg.append(f"Type de modèles {code} : modèle cité deux fois.")
        for n in noms:
            if n not in mods:
                msg.append(f"Type de modèles {code} : modèle « {n} » introuvable.")
            elif mods[n].get("type") != code:
                partages.append(f"Modèle « {n} » (type {mods[n].get('type')}) proposé aussi pour le type {code}.")
    for nom, m in mods.items():
        if m.get("nom") != nom:
            msg.append(f"Modèle « {nom} » : nom et clé différents.")
        ids, couples = set(), set()
        for l in m.get("lignes", []):
            if l.get("id") in ids:
                msg.append(f"Modèle « {nom} » : identifiant de ligne {l.get('id')} en double.")
            ids.add(l.get("id"))
            c = (l.get("role"), l.get("suffixe"))
            if c in couples:
                msg.append(f"Modèle « {nom} » : ligne {c[0]}_{c[1]} en double.")
            couples.add(c)
        cles = set()
        for s in m.get("signaux", []) or []:
            k = f"{s.get('famille')}_{s.get('code')}"
            if k in cles:
                msg.append(f"Modèle « {nom} » : signal {k} en double.")
            cles.add(k)
            if s.get("famille") not in FAMILLES_CATALOGUE or s.get("presence") not in PRESENCES:
                msg.append(f"Modèle « {nom} », signal {k} : famille ou présence inconnue.")
            if s.get("famille") == "ES" and s.get("es") not in ("ET", "ST", "EA", "SA"):
                msg.append(f"Modèle « {nom} », E/S {k} : nature ET, ST, EA ou SA obligatoire.")
            if s.get("type_logique") and s.get("type_logique") not in TYPES_LOGIQUES:
                msg.append(f"Modèle « {nom} », signal {k} : type logique inconnu.")
            for m_interne in anomalies_interne(s):
                msg.append(f"Modèle « {nom} », signal {k} : {m_interne}.")
        for champ in _champs_installation(m):
            msg.append(f"Modèle « {nom} » : « {champ} » est un paramètre d'installation, il appartient à la fiche "
                       "de l'équipement, pas au référentiel.")
        for l in m.get("lignes", []):
            if _lexique.alerte(l.get("suffixe")):
                partages.append(f"Modèle « {nom} », ligne {l.get('role')}_{l.get('suffixe')} : "
                                f"{_lexique.ALERTE_LONGUEUR} (plus de {_lexique.LONGUEUR_MAX_SUFFIXE} caractères).")
    e_lex, a_lex = _lexique.controler(ref.get("lexique", []))
    e_dic, a_dic = _dico.controler(ref.get("dictionnaire_es", []))
    a_dic += _dico.codes_non_standard(getattr(cat, "signaux", []), ref.get("dictionnaire_es", []))
    a_dic += _dico.codes_hors_regle_3_lettres(ref.get("dictionnaire_es", []), _dictionnaire_livre())
    if cat is not None and ref.get("correspondances"):
        from .adoption import controler_correspondances
        e_dic += controler_correspondances(ref["correspondances"], cat)
    return msg + e_lex + e_dic, partages + a_lex + a_dic


def _dictionnaire_livre():
    """Dictionnaire des E/S livré avec le programme : référence des codes existants (P3). Vide s'il est illisible."""
    try:
        with open(_modeles.fichier_origine(), encoding="utf-8") as f:
            return json.load(f).get("dictionnaire_es", [])
    except (OSError, ValueError, AttributeError):
        return []


def _champs_installation(objet, trouves=None):
    trouves = set() if trouves is None else trouves
    if isinstance(objet, dict):
        for k, v in objet.items():
            if k in CHAMPS_INSTALLATION:
                trouves.add(k)
            _champs_installation(v, trouves)
    elif isinstance(objet, list):
        for v in objet:
            _champs_installation(v, trouves)
    return sorted(trouves)


# ============================================================================ classeur : garde-fous
def classeur_sain(chemin):
    """Refuse formules, macros et liens externes dans un classeur importé (aucun calcul n'est exécuté)."""
    try:
        with zipfile.ZipFile(chemin) as z:
            noms = z.namelist()
            if any(n.lower().endswith("vbaproject.bin") for n in noms):
                raise DepotRefuse("Classeur refusé : il contient des macros.")
            if any(n.startswith("xl/externalLinks/") for n in noms):
                raise DepotRefuse("Classeur refusé : il contient des liens vers d'autres classeurs.")
            for n in noms:
                if n.startswith("xl/worksheets/") and n.endswith(".xml"):
                    xml = z.read(n)
                    if b"<f>" in xml or b"<f " in xml or b"<f/>" in xml:
                        raise DepotRefuse(f"Classeur refusé : formule dans {n.split('/')[-1]} (valeurs seulement).")
    except zipfile.BadZipFile as exc:
        raise DepotRefuse("Classeur illisible (fichier .xlsx attendu).") from exc


# ============================================================================ édition du brouillon (écran)
CHAMPS_SIGNAL_EDITABLES = ("information", "type_logique", "unite", "es", "alarme", "presence", "option", "statut",
                           "remarque", "organe", "source", "logique", "suffixe_es")
CHAMPS_REGLE_EDITABLES = ("libelle", "si", "propose", "mode", "logique", "gouvernance")
CHAMPS_TYPE_EDITABLES = ("designation", "categorie", "famille_biblio", "domaine", "options", "remarque")


def _signal_par_id(donnees, ident):
    """« TYPE.FAMILLE_CODE » (signal du type) → (index, signal)."""
    try:
        t, cle = ident.split(".", 1)
        fam, code = cle.split("_", 1)
    except ValueError as exc:
        raise DepotRefuse(f"Identifiant de signal « {ident} » illisible (TYPE.FAMILLE_CODE).") from exc
    for i, s in enumerate(donnees["catalogue"]["signaux"]):
        if s.get("type") == t and s.get("famille") == fam and s.get("code") == code:
            return i, s
    raise DepotRefuse(f"Signal {ident} absent du brouillon.")


def _nettoyer(champs, autorises):
    inconnus = set(champs) - set(autorises)
    if inconnus:
        raise DepotRefuse(f"Champ(s) non modifiable(s) : {', '.join(sorted(inconnus))}. Les identifiants ne se "
                          "renomment pas : supprimez puis recréez.")
    sortie = {}
    for k, v in champs.items():
        if k in ("si", "propose", "options"):
            v = [x.strip() for x in (v.split(";") if isinstance(v, str) else v) if str(x).strip()]
            if k != "options":
                v = [x.upper() for x in v]
        elif k == "alarme":
            v = bool(v) and str(v).lower() not in ("non", "false", "0")
        elif isinstance(v, str):
            v = v.strip()
            if k in ("type_logique", "organe", "source", "suffixe_es"):
                v = v.upper()
        sortie[k] = v
    return sortie


def editer(donnees, action, cible="", champs=None):
    """Applique une modification élémentaire à une COPIE des données du brouillon et la renvoie avec un libellé
    de journal. Les contrôles complets sont faits à la validation ; ici, seulement l'intégrité des identifiants."""
    d = copy.deepcopy(donnees)
    champs = dict(champs or {})
    cat = d["catalogue"]
    if action == "modifier_signal":
        i, s = _signal_par_id(d, cible)
        s.update(_nettoyer(champs, CHAMPS_SIGNAL_EDITABLES))
        return d, f"signal {cible} modifié"
    if action == "ajouter_signal":
        t, fam, code = (str(champs.pop(k, "")).strip().upper() for k in ("type", "famille", "code"))
        if not (t and fam and code):
            raise DepotRefuse("Type, famille et code obligatoires pour un nouveau signal.")
        if not any(x["code"] == t for x in cat["types"]):
            raise DepotRefuse(f"Type {t} absent du brouillon.")
        if fam not in FAMILLES_CATALOGUE:
            raise DepotRefuse(f"Famille {fam} inconnue.")
        if any(s["type"] == t and s["famille"] == fam and s["code"] == code for s in cat["signaux"]):
            raise DepotRefuse(f"{t}.{fam}_{code} existe déjà.")
        s = {"type": t, "information": "", "famille": fam, "code": code, "type_logique": "BOOL", "unite": "",
             "es": "Interne", "alarme": False, "presence": "Option", "option": "", "statut": "Validé", "remarque": "",
             "organe": "", "source": "", "logique": ""}
        s.update(_nettoyer(champs, CHAMPS_SIGNAL_EDITABLES))
        rang = max([i for i, x in enumerate(cat["signaux"]) if x["type"] == t] + [len(cat["signaux"]) - 1])
        cat["signaux"].insert(rang + 1, s)
        return d, f"signal {t}.{fam}_{code} ajouté"
    if action == "supprimer_signal":
        i, s = _signal_par_id(d, cible)
        cle = f"{s['famille']}_{s['code']}"
        utilise = [r["id"] for r in cat.get("regles", []) if r.get("type") == s["type"] and cle in r.get("si", []) + r.get("propose", [])]
        if utilise:
            raise DepotRefuse(f"{cible} est utilisé par la règle {utilise[0]} : modifiez d'abord la règle.")
        del cat["signaux"][i]
        return d, f"signal {cible} supprimé"
    if action in ("modifier_regle", "supprimer_regle"):
        i = next((k for k, r in enumerate(cat.get("regles", [])) if r.get("id") == cible), None)
        if i is None:
            raise DepotRefuse(f"Règle {cible} absente du brouillon.")
        if action == "supprimer_regle":
            del cat["regles"][i]
            return d, f"règle {cible} supprimée"
        cat["regles"][i].update(_nettoyer(champs, CHAMPS_REGLE_EDITABLES))
        return d, f"règle {cible} modifiée"
    if action == "ajouter_regle":
        rid, t = str(champs.pop("id", "")).strip().upper(), str(champs.pop("type", "")).strip().upper()
        if not rid or not t:
            raise DepotRefuse("Identifiant et type obligatoires pour une nouvelle règle.")
        if any(r.get("id") == rid for r in cat.get("regles", [])):
            raise DepotRefuse(f"La règle {rid} existe déjà.")
        r = {"id": rid, "type": t, "libelle": "", "si": [], "propose": [], "mode": "proposition", "logique": ""}
        r.update(_nettoyer(champs, CHAMPS_REGLE_EDITABLES))
        cat.setdefault("regles", []).append(r)
        return d, f"règle {rid} ajoutée"
    if action in ("ajouter_lexique", "modifier_lexique", "supprimer_lexique"):
        lex = d["modeles"].setdefault("lexique", [])
        cle = _lexique.normaliser(cible if action != "ajouter_lexique" else champs.get("mot", ""))
        i = next((k for k, e in enumerate(lex) if _lexique.normaliser(e.get("mot")) == cle), None)
        if not cle:
            raise DepotRefuse("Mot ou expression du lexique obligatoire.")
        if action == "ajouter_lexique":
            if i is not None:
                raise DepotRefuse(f"« {champs.get('mot')} » est déjà dans le lexique.")
            inconnus = set(champs) - {"mot", "abreviation", "nature", "dictionnaire_es"}
            if inconnus:
                raise DepotRefuse(f"Champ(s) inconnu(s) : {', '.join(sorted(inconnus))}.")
            lex.append(_lexique.entree(champs.get("mot"), champs.get("abreviation"), champs.get("nature"),
                                       champs.get("dictionnaire_es")))
            return d, f"lexique « {champs.get('mot')} » ajouté"
        if i is None:
            raise DepotRefuse(f"« {cible} » absent du lexique du brouillon.")
        if action == "supprimer_lexique":
            del lex[i]
            return d, f"lexique « {cible} » supprimé"
        inconnus = set(champs) - {"abreviation", "nature", "dictionnaire_es"}
        if inconnus:
            raise DepotRefuse(f"Champ(s) non modifiable(s) : {', '.join(sorted(inconnus))}. Le mot ne se renomme "
                              "pas : supprimez puis recréez.")
        e = lex[i]
        lex[i] = _lexique.entree(e["mot"], champs.get("abreviation", e.get("abreviation")),
                                 champs.get("nature", e.get("nature")), champs.get("dictionnaire_es", e.get("dictionnaire_es")))
        return d, f"lexique « {cible} » modifié"
    if action in ("ajouter_correspondance", "supprimer_correspondance"):
        corr = d["modeles"].setdefault("correspondances", [])
        if action == "ajouter_correspondance":
            inconnus = set(champs) - {"type", "ancienne", "type_nouveau", "nouvelle", "motif"}
            if inconnus:
                raise DepotRefuse(f"Champ(s) inconnu(s) : {', '.join(sorted(inconnus))}.")
            c = {k: str(champs.get(k) or "").strip().upper() for k in ("type", "ancienne", "type_nouveau", "nouvelle")}
            c["type_nouveau"] = c["type_nouveau"] or c["type"]
            c["motif"] = str(champs.get("motif") or "").strip()
            if not (c["type"] and c["ancienne"] and c["nouvelle"]):
                raise DepotRefuse("Type, ancienne clé et nouvelle clé obligatoires.")
            if not c["motif"]:
                raise DepotRefuse("Le motif de la correspondance est obligatoire.")
            if any((x.get("type"), x.get("ancienne")) == (c["type"], c["ancienne"]) for x in corr):
                raise DepotRefuse(f"{c['type']}.{c['ancienne']} a déjà une correspondance (ambiguïté refusée).")
            corr.append(c)
            return d, f"correspondance {c['type']}.{c['ancienne']} → {c['type_nouveau']}.{c['nouvelle']} ajoutée"
        i = next((k for k, x in enumerate(corr) if f"{x.get('type')}.{x.get('ancienne')}" == str(cible).upper()), None)
        if i is None:
            raise DepotRefuse(f"Correspondance {cible} absente du brouillon (forme TYPE.ANCIENNE_CLE).")
        del corr[i]
        return d, f"correspondance {cible} supprimée"
    if action in ("ajouter_code_es", "modifier_code_es", "supprimer_code_es"):
        dico = d["modeles"].setdefault("dictionnaire_es", [])
        cle = (_dico.cle(_dico.entree(champs.get("code"), champs.get("nature"))) if action == "ajouter_code_es"
               else str(cible).strip().upper())
        i = next((k for k, e in enumerate(dico) if _dico.cle(e) == cle), None)
        if action == "ajouter_code_es":
            inconnus = set(champs) - {"code", "nature", "libelle", "categorie", "teletransmission", "types"}
            if inconnus:
                raise DepotRefuse(f"Champ(s) inconnu(s) : {', '.join(sorted(inconnus))}.")
            nouvelle = _dico.entree(**champs)
            erreurs = _dico.controler([nouvelle])[0]
            if erreurs:
                raise DepotRefuse(erreurs[0])
            if i is not None:
                raise DepotRefuse(f"Le code {cle} existe déjà dans le dictionnaire des E/S.")
            dico.append(nouvelle)
            return d, f"code {cle} ajouté au dictionnaire des E/S"
        if i is None:
            raise DepotRefuse(f"Code {cible} absent du dictionnaire des E/S du brouillon (forme NATURE.CODE).")
        if action == "supprimer_code_es":
            del dico[i]
            return d, f"code {cle} supprimé du dictionnaire des E/S"
        inconnus = set(champs) - {"libelle", "categorie", "teletransmission", "types"}
        if inconnus:
            raise DepotRefuse(f"Champ(s) non modifiable(s) : {', '.join(sorted(inconnus))}. Un code ne se renomme "
                              "pas : supprimez puis recréez.")
        dico[i] = _dico.entree(dico[i]["code"], dico[i]["nature"], **{k: champs.get(k, dico[i].get(k))
                                                                       for k in ("libelle", "categorie",
                                                                                 "teletransmission", "types")})
        return d, f"code {cle} modifié dans le dictionnaire des E/S"
    if action == "modifier_type":
        type_objet = next((x for x in cat["types"] if x["code"] == cible), None)
        if type_objet is None:
            raise DepotRefuse(f"Type {cible} absent du brouillon.")
        type_objet.update(_nettoyer(champs, CHAMPS_TYPE_EDITABLES))
        return d, f"type {cible} modifié"
    raise DepotRefuse(f"Modification « {action} » inconnue.")


# ============================================================================ vue de consultation
def modeles_utilises() -> dict[str, list[str]]:
    """{nom de modèle: [repères des ouvrages enregistrés qui l'emploient]} (lecture seule)."""
    sortie: dict[str, list[str]] = {}
    try:
        from . import projets
        for f in projets.lister():
            try:
                with open(f.chemin, encoding="utf-8") as h:
                    o = json.load(h)
            except (OSError, ValueError):
                continue
            o = o.get("ouvrage", o)
            for nom in sorted({e.get("modele") for e in o.get("equipements", []) if e.get("modele")}):
                sortie.setdefault(nom, []).append(f.repere)
    except Exception:                                   # noqa: BLE001 — un dossier illisible ne bloque rien
        return sortie
    return sortie


def ouvrages_utilisant():
    """{type: [{repere, revision}]} des ouvrages enregistrés (lecture seule des fichiers de projets)."""
    sortie: dict[str, list[dict]] = {}
    try:
        from . import projets
        for f in projets.lister():
            try:
                with open(f.chemin, encoding="utf-8") as h:
                    d = json.load(h)
            except (OSError, ValueError):
                continue
            o = d.get("ouvrage", d)
            version = (o.get("catalogue_snapshot") or {}).get("version", "") or "non figée (jamais enregistré)"
            for t in sorted({e.get("type") for e in o.get("equipements", [])}):
                n = sum(1 for e in o.get("equipements", []) if e.get("type") == t)
                sortie.setdefault(t, []).append({"repere": f.repere, "revision": version, "equipements": n})
    except Exception:                                   # noqa: BLE001 — information de confort
        return {}
    return sortie


def vue(donnees, reference=None):
    """Données de l'écran Référentiel, par type du catalogue. `reference` (révision publiée) sert à marquer ce
    que le brouillon a changé."""
    from . import audit_referentiel
    from .regles import regles_du_type
    cat, ref = Depot.objets(donnees)
    modifies = set()
    if reference is not None:
        from . import referentiel_excel as rx
        for x in rx.differences(rx.etat(*Depot.objets(reference)), rx.etat(cat, ref)):
            modifies.add((x["objet"], x["id"]))
    audit: dict[str, list[dict]] = {}
    for c in audit_referentiel.auditer(cat):
        audit.setdefault(c.type, []).append(c.dict())
    usages = ouvrages_utilisant()
    types = []
    for t in cat.types:
        code = t["code"]
        sig = cat.signaux_du_type(code, avec_ecartes=True)
        ident = lambda s: f"{code}.{s['famille']}_{s['code']}"
        porte = lambda s: s.get("famille") == "ES" or s.get("es") in ("ET", "ST", "EA", "SA")
        lignes_sig = [dict(s, id=ident(s), modifie=("signal", ident(s)) in modifies, physique=porte(s)) for s in sig]
        noms = list(dict.fromkeys(list(ref.get("types", {}).get(code, {}).get("modeles", [])) +
                                  [n for n, m in ref.get("modeles", {}).items() if m.get("type") == code]))
        mods = [{"nom": n, "statut": ref["modeles"][n].get("statut", "à valider"),
                 "lignes": ref["modeles"][n].get("lignes", []), "signaux_propres": "signaux" in ref["modeles"][n],
                 "modifie": ("modèle", n) in modifies or any(o == "ligne de modèle" for o, _ in modifies)}
                for n in noms if n in ref.get("modeles", {})]
        regles = [dict(r, modifie=("règle", r.get("id")) in modifies) for r in regles_du_type(cat, code)]
        types.append({"code": code, "designation": t.get("designation", ""), "domaine": t.get("domaine", ""),
                      "categorie": t.get("categorie", ""), "options": t.get("options", []),
                      "archivable": code in ref.get("types", {}),
                      "archive": bool(ref.get("types", {}).get(code, {}).get("archive")),
                      "modifie": ("type", code) in modifies or any(o == "signal" and i.startswith(code + ".") for o, i in modifies)
                      or any(r["modifie"] for r in regles),
                      "es": [s for s in lignes_sig if s["physique"]], "fonctionnelles": [s for s in lignes_sig if not s["physique"] or s["famille"] != "ES"],
                      "regles": regles, "modeles": mods, "audit": audit.get(code, []), "usages": usages.get(code, [])})
    return {"types": types, "nb_modifications": len(modifies),
            "lexique": [dict(e, cle=_lexique.normaliser(e.get("mot"))) for e in ref.get("lexique", [])],
            "dictionnaire_es": [dict(e, cle=_dico.cle(e)) for e in ref.get("dictionnaire_es", [])],
            "correspondances": [dict(e, cle=f"{e['type']}.{e['ancienne']}") for e in ref.get("correspondances", [])]}
