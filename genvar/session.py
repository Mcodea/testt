"""Session de travail sur un ouvrage : toutes les opérations, sans aucune interface graphique.

Les interfaces (Tkinter actuelle, PySide6 en cours) appellent ces fonctions ; elles
n'implémentent elles-mêmes aucune règle métier. Une opération refusée lève
`RegleMetier` avec un message à afficher tel quel.
"""

import contextlib
import copy
import json
import os
import re
import shutil
import uuid
from typing import Any

from .regles import retenue_d_office, texte as texte_regle
from . import modeles as _modeles
from dataclasses import dataclass, field

from . import chemins, existant, teletransmission
from .catalogue import Catalogue, sens_incoherent
from .modele import _base_retenue
from .modele import (Ouvrage, Equipement, SousEnsemble, UniteFonctionnelle, SignalPropre, generer, generer_points, controler, catalogue_pour_equipement,
                     plan_adresses, appliquer_plan, signaux_retenus, registre_modbus)
from .export_xsy import exporter_xsy
from .export_xlsx import exporter_table

RE_ADRESSE_ECHANGE = re.compile(r"^%MW\d+(\.\d{1,2})?$")
RE_ADRESSE_PHYSIQUE = re.compile(r"^%(I|Q|IW|QW)[\d.]+$")


class RegleMetier(Exception):
    """Opération refusée par une règle de l'outil ; le message s'affiche tel quel."""


@dataclass
class RecapExport:
    variables: int
    points: int
    locales: int
    avec_adresse: int
    sans_adresse: list = field(default_factory=list)     # noms des E/S exclues
    erreurs: int = 0


class Session:
    def __init__(self, catalogue=None, ouvrage=None, chemin=None):
        self._edition_brouillon = False
        self.modeles = _modeles.charger()                 # référentiel des modèles de supervision
        self._catalogue_commun = catalogue or Catalogue.charger()
        self.catalogue = copy.deepcopy(self._catalogue_commun)
        self.ouvrage = ouvrage or Ouvrage()
        if self.ouvrage.catalogue_snapshot:
            self.catalogue = Catalogue(**self.ouvrage.catalogue_snapshot)
        _modeles.completer_signaux(self.modeles, self._catalogue_commun)
        self.chemin = chemin
        self.modifie = False
        self.catalogue_modifie = False
        self.avertissement_ouverture = ""
        self._avant_adoption: tuple | None = None          # état avant la dernière adoption (retour arrière)
        self.sauvegarde_adoption = ""
        self.sauvegarde_annulation_adoption = ""
        self._chemin_adoption = ""
        self.derniere_copie = ""                         # dernière copie horodatée (V1-7-03)

    def _oublier_adoption(self):
        self._avant_adoption = None
        self.sauvegarde_adoption = self.sauvegarde_annulation_adoption = self._chemin_adoption = ""

    # ================================================================== fichiers
    def nouveau(self, lieu_dans_le_nom=True):
        """Ouvrage vierge. L'interface crée les projets neufs sans le lieu dans les noms (règle R2,
        décision du 5 novembre) ; l'option reste modifiable par ouvrage."""
        self.ouvrage, self.chemin, self.modifie = Ouvrage(), None, False
        self.ouvrage.lieu_dans_le_nom = lieu_dans_le_nom
        self.ouvrage.format_repere = "12"             # charte ESB/RESO : ATMSRV01HV01
        self.catalogue = copy.deepcopy(self._catalogue_commun)
        self.avertissement_ouverture = ""
        self._oublier_adoption()

    def ouvrir(self, chemin):
        ouvrage = Ouvrage.ouvrir(chemin)  # En cas d'erreur : ne pas modifier la session en cours.
        catalogue = (Catalogue(**ouvrage.catalogue_snapshot) if ouvrage.catalogue_snapshot
                     else copy.deepcopy(self._catalogue_commun))
        self.ouvrage, self.catalogue = ouvrage, catalogue
        self.chemin, self.modifie = chemin, False
        self._oublier_adoption()
        self.avertissement_ouverture = ""
        if ouvrage.mode == "Neuf":
            # Une ancienne validation de paramétrage ne couvre pas les nouvelles
            # règles de correspondance analogique : réexaminer EN MÉMOIRE seulement.
            points = self.points()
            a_revoir = {p.ident_eq for p in points if p.point in ('EA', 'SA') and
                        p.raccordement == 'Câblé' and
                        not ouvrage.equipement(p.ident_eq).es_meta.get(p.cle, {}).get('analogique')}
            for eq in ouvrage.equipements:
                if eq.valide and eq.ident in a_revoir:
                    eq.valide = False
                    self.modifie = True
            if a_revoir and self.modifie:
                if ouvrage.statut == 'Validé':
                    ouvrage.statut = 'À contrôler'
                self.avertissement_ouverture = (
                    'Des équipements anciennement validés nécessitent maintenant leur échelle '
                    'analogique. Ils ont été remis « à valider » en mémoire : le fichier d’origine '
                    'reste inchangé tant que vous n’enregistrez pas.')
        if ouvrage.mode == "Existant" and ouvrage.statut == "Validé":
            # Migrer prudemment le statut d'un ancien dossier déjà clôturé sous
            # l'ancienne règle ; on ne modifie jamais le fichier sur disque ici.
            try:
                self._verifier_pret_pour_validation()
            except RegleMetier as exc:
                ouvrage.statut = "À contrôler"
                self.modifie = True
                self.avertissement_ouverture = (
                    "L'ancien statut « Validé » n'est plus justifié : " + str(exc) +
                    " Le fichier d'origine n'a pas été modifié. Enregistrer pour conserver le statut « À contrôler »."
                )

    def _verifier_pret_pour_validation(self):
        """Vérification métier commune à la sélection du statut et à l'enregistrement.

        Ne modifie jamais les données ; l'utilisateur corrige ou valide explicitement.
        """
        # Le statut global « Validé » n'est pas un simple acquittement d'erreurs.
        # Un ouvrage vide ou un dossier sans source ne peut pas être validé.
        if not self.ouvrage.equipements:
            raise RegleMetier("Impossible de valider un ouvrage sans équipement déclaré.")
        if self.ouvrage.mode == "Existant" and not self.ouvrage.existantes:
            raise RegleMetier("Projet existant : importer les variables sources avant validation.")
        # Vérifier d'abord la complétude de la table afin d'afficher un motif précis
        # (plutôt qu'une erreur générique) à l'interface et à la sauvegarde.
        if self.ouvrage.mode == "Existant":
            problemes = teletransmission.verifier_cloture(self.ouvrage, self.catalogue)
            if problemes:
                raise RegleMetier(problemes[0] +
                                  (f" ({len(problemes)} point(s) à corriger au total.)"
                                   if len(problemes) > 1 else ""))
        bilan = self.bilan()
        if bilan["erreurs"]:
            raise RegleMetier(f"Impossible de déclarer l'ouvrage validé : {bilan['erreurs']} erreur(s) bloquante(s).")
        if self.ouvrage.mode == "Neuf":
            non_valides = [self.ouvrage.repere(e) for e in self.ouvrage.equipements if not e.valide]
            if non_valides:
                raise RegleMetier(f"Projet neuf : le paramétrage de {len(non_valides)} équipement(s) "
                                  f"n’est pas validé (ex. {non_valides[0]}).")
            variables = self.variables()
            points = self.points()
            sans_validation = [v.nom for v in variables if not v.adresse_validee]
            if sans_validation:
                raise RegleMetier(f"Projet neuf : {len(sans_validation)} adresse(s) d'échange restent à "
                                  f"valider (ex. {sans_validation[0]}).")
            incompletes = [p.nom for p in points if not p.validee or
                           (p.raccordement != "Communication" and not p.adresse)]
            if incompletes:
                raise RegleMetier(f"Projet neuf : {len(incompletes)} E/S physiques restent à "
                                  f"adresser ou valider (ex. {incompletes[0]}).")

    def enregistrer(self, chemin=None):
        chemin = chemin or self.chemin
        if not chemin:
            raise RegleMetier("Aucun fichier : choisissez où enregistrer l'ouvrage.")
        if self.ouvrage.statut == "Validé":
            self._verifier_pret_pour_validation()
        # Le catalogue retenu pour ce projet est figé dans son fichier : une évolution du
        # catalogue partagé ne doit pas modifier silencieusement un ouvrage historique.
        self.ouvrage.catalogue_snapshot = self.catalogue_fige()
        if os.path.isfile(chemin):
            shutil.copy2(chemin, chemin + ".bak")
        self.ouvrage.enregistrer(chemin)
        if self._chemin_adoption and os.path.realpath(chemin) != self._chemin_adoption:
            self._oublier_adoption()   # Enregistrer sous ne transporte pas l'annulation vers un autre fichier.
        self.chemin, self.modifie = chemin, False

    def catalogue_fige(self):
        """Référentiel retenu pour cet ouvrage, tel qu'il est figé dans son fichier."""
        return {"types": copy.deepcopy(self.catalogue.types), "signaux": copy.deepcopy(self.catalogue.signaux),
                "version": self.catalogue.version, "regles": copy.deepcopy(self.catalogue.regles)}

    # ------------------------------------------------- copies horodatées avant opération lourde (V1-7-03)
    def _a_un_fichier(self):
        return bool(self.chemin) and os.path.isfile(self.chemin)

    @contextlib.contextmanager
    def _operation_lourde(self, operation):
        """Encadre une opération lourde : si elle réussit et modifie l'ouvrage, l'état d'avant est copié à côté
        du fichier. Opération refusée ou sans effet : aucune copie. Copie impossible : opération annulée."""
        from . import copies
        if not self._a_un_fichier():
            yield                                   # ouvrage jamais enregistré : rien à protéger sur disque
            return
        avant, modifie, catalogue_avant = copies.etat(self), self.modifie, copy.deepcopy(self.catalogue)
        yield
        if copies.etat(self) == avant:
            return
        try:
            self.derniere_copie = copies.ecrire(self.chemin, operation, avant)
        except OSError as exc:
            self.ouvrage = Ouvrage.depuis_dict(json.loads(avant)["ouvrage"])   # rien de partiel
            self.catalogue = catalogue_avant                                   # y compris l'adoption
            self.modifie = modifie
            raise RegleMetier(f"Copie horodatée impossible ({exc.strerror or exc}) : opération annulée, "
                              "l'ouvrage est inchangé. Libérez de la place ou vérifiez les droits du dossier.") from exc

    def creer_copie(self, operation):
        """Copie horodatée de l'état courant (pour une opération appliquée hors de la session, l'import)."""
        from . import copies
        if not self._a_un_fichier():
            return ""
        try:
            self.derniere_copie = copies.ecrire(self.chemin, operation, copies.etat(self))
        except OSError as exc:
            raise RegleMetier(f"Copie horodatée impossible ({exc.strerror or exc}) : opération refusée.") from exc
        return self.derniere_copie

    def copies_horodatees(self):
        """Copies de cet ouvrage, la plus récente d'abord (lecture seule)."""
        from . import copies
        return copies.lister(self.chemin) if self._a_un_fichier() else []

    def restaurer_copie(self, nom):
        """Charge en mémoire l'état d'une copie de cet ouvrage, après une copie de l'état courant (réversible).
        Le fichier de l'ouvrage n'est écrit qu'à l'enregistrement ; le référentiel figé de la copie est repris."""
        from . import copies
        if not self._a_un_fichier():
            raise RegleMetier("Ouvrage non enregistré : aucune copie horodatée à restaurer.")
        try:
            chemin = copies.resoudre(self.chemin, nom)
        except ValueError as exc:
            raise RegleMetier(str(exc)) from exc
        try:
            ouvrage = Ouvrage.ouvrir(chemin)
            catalogue = (Catalogue(**ouvrage.catalogue_snapshot) if ouvrage.catalogue_snapshot
                         else copy.deepcopy(self._catalogue_commun))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise RegleMetier("Copie illisible : restauration refusée, l'ouvrage est inchangé.") from exc
        avant = self.creer_copie("restauration")
        self.ouvrage, self.catalogue, self.modifie = ouvrage, catalogue, True
        self._oublier_adoption()            # l'annulation d'une adoption ne s'applique plus à cet état
        return {"restauree": nom, "copie_avant_restauration": os.path.basename(avant)}

    # ------------------------------------------------------------ référentiel figé dans l'ouvrage
    def ecarts_referentiel(self):
        """Différences entre le référentiel figé dans cet ouvrage et celui de l'outil, limitées aux types
        utilisés : [{"type", "ajoutees", "retirees", "modifiees", "regles"}]. Rien n'est appliqué."""
        commun, propre = self._catalogue_commun, self.catalogue
        if commun.version == propre.version and commun.signaux == propre.signaux and commun.regles == propre.regles:
            return []
        sortie = []
        for t in sorted({e.type for e in self.ouvrage.equipements}):
            a = {f"{s['famille']}_{s['code']}": s for s in propre.signaux_du_type(t)}
            b = {f"{s['famille']}_{s['code']}": s for s in commun.signaux_du_type(t)}
            ra = {r.get("id"): r for r in propre.regles if r.get("type") == t}
            rb = {r.get("id"): r for r in commun.regles if r.get("type") == t}
            ecart = {"type": t, "ajoutees": sorted(set(b) - set(a)), "retirees": sorted(set(a) - set(b)),
                     "modifiees": sorted(k for k in set(a) & set(b) if a[k] != b[k]),
                     "regles": sorted(k for k in set(ra) | set(rb) if ra.get(k) != rb.get(k))}
            if any(ecart[k] for k in ("ajoutees", "retirees", "modifiees", "regles")):
                sortie.append(ecart)
        return sortie

    def apercu_adoption(self):
        """Aperçu type par type de l'adoption du référentiel actuel (ajouts, retraits, renommages physiques et
        fonctionnels, blocages). Rien n'est appliqué."""
        from . import adoption
        return adoption.apercu(self.ouvrage, self.catalogue, self._catalogue_commun,
                               self.modeles.get("correspondances", []))

    def adopter_referentiel(self, types=None, renommages_confirmes=False, action="adoption"):
        """Acte explicite : l'ouvrage prend le référentiel actuel pour les types choisis.

        - `types` absent : seuls les types adoptables **sans renommage** sont adoptés (comportement prudent) ;
        - un type dont l'adoption renomme une variable exige `renommages_confirmes=True` ;
        - un type bloqué (données sans correspondance, écrasement, changement de type) est refusé ;
        - les adresses et décisions suivent les correspondances ; une sauvegarde horodatée du fichier est faite
          et `annuler_adoption` rétablit l'état antérieur. Les équipements adoptés repassent « à valider »."""
        from . import adoption
        apercu = {x["type"]: x for x in self.apercu_adoption()}
        if types is None:
            choisis = [t for t, x in apercu.items() if x["adoptable"] and not x["renommages"]]
        else:
            choisis = list(dict.fromkeys(types))
            for t in choisis:
                if t not in apercu:
                    raise RegleMetier(f"Type {t} : aucun écart à adopter dans cet ouvrage.")
                if not apercu[t]["adoptable"]:
                    raise RegleMetier(f"Type {t} non adoptable : {apercu[t]['bloquants'][0]}")
                if apercu[t]["renommages"] and not renommages_confirmes:
                    raise RegleMetier(f"Type {t} : {len(apercu[t]['renommages'])} renommage(s) à confirmer "
                                      "explicitement avant l'adoption.")
        if not choisis:
            return []
        sauvegarde = adoption.sauvegarder(self.chemin)   # Une erreur de copie ne crée pas de faux retour arrière.
        self._avant_adoption = (copy.deepcopy(self.ouvrage), copy.deepcopy(self.catalogue), self.modifie)
        self.sauvegarde_adoption = sauvegarde
        self.sauvegarde_annulation_adoption = ""
        self._chemin_adoption = os.path.realpath(self.chemin) if self.chemin else ""
        utilises = {e.type for e in self.ouvrage.equipements}
        for t in choisis:
            for r in apercu[t]["renommages"]:
                if r["ancienne"] != r["nouvelle"]:
                    for e in self.ouvrage.equipements:
                        if e.type == t:
                            adoption._renommer(self.ouvrage, e, r["ancienne"], r["nouvelle"])
        self.catalogue = adoption.catalogue_fusionne(self.catalogue, self._catalogue_commun, choisis, utilises)
        versions = self._versions_profils()
        for e in self.ouvrage.equipements:
            if e.type in choisis:
                e.valide = False
                x = apercu[e.type]
                self._journaliser(action, e, f"{len(x['renommages'])} renommage(s), {len(x['ajoutees'])} ajout(s), "
                                  f"{len(x['retirees'])} retrait(s), {len(x['modifiees'])} modification(s)",
                                  sauvegarde=sauvegarde, versions=versions)
        self._change()
        return [apercu[t] for t in choisis]

    # ------------------------------------------------------------------ journal des décisions (R7)
    @staticmethod
    def _versions_profils():
        from . import profils
        from .referentiel_depot import Depot
        try:
            return profils.versions(Depot())
        except Exception:                               # noqa: BLE001 — la trace reste écrite sans la version
            return {}

    def _journaliser(self, action, eq, detail="", sauvegarde="", versions=None):
        from datetime import datetime, timezone
        from . import profils
        from .referentiel_depot import auteur_par_defaut
        hist = versions if versions is not None else self._versions_profils()
        v = profils.version_publiee(None, eq.type, hist)
        self.ouvrage.journal_referentiel.append({
            "le": datetime.now(timezone.utc).isoformat(timespec="seconds"), "par": auteur_par_defaut(),
            "action": action, "profil": eq.type, "version": v["version"] if v else None,
            "equipement": self.ouvrage.repere(eq), "ident_eq": eq.ident, "detail": detail,
            "sauvegarde": os.path.basename(sauvegarde) if sauvegarde else ""})

    def apercu_propagation(self):
        """R6 : aperçu de l'acceptation en un geste. Seulement pour un ouvrage neuf jamais validé ni exporté
        (historique connu), et seulement pour les types adoptables sans renommage ni conflit de surcharge."""
        from .referentiel_depot import empreinte
        o = self.ouvrage
        raisons = []
        if o.mode != "Neuf":
            raisons.append("Projet existant : adoption contrôlée ligne à ligne.")
        if o.deja_valide is not False or o.statut in ("Validé", "À contrôler"):
            raisons.append("Ouvrage déjà validé, ou historique de validation inconnu : adoption ligne à ligne.")
        if o.deja_exporte is not False:
            raisons.append("Ouvrage déjà exporté, ou historique d'export inconnu : adoption ligne à ligne.")
        types: list[dict] = []
        exclus: list[dict] = []
        for x in self.apercu_adoption():
            motif = (x["bloquants"][0] if x["bloquants"] else
                     "renommage(s) à confirmer" if x["renommages"] else
                     "surcharge(s) locale(s) en conflit" if x.get("conflits") else "")
            (exclus if motif else types).append(dict(x, motif=motif) if motif else x)
        resume = [{"type": x["type"], "motif": x["motif"]} for x in exclus]
        return {"eligible": not raisons and bool(types), "raisons": raisons, "types": types, "exclus": resume,
                "empreinte": empreinte({"raisons": raisons, "types": types})}

    def accepter_propagation(self, empreinte_attendue):
        """R6 : applique, en un geste, exactement l'aperçu affiché ; refusé si l'aperçu a changé."""
        a = self.apercu_propagation()
        if not a["eligible"]:
            raise RegleMetier("Acceptation en un geste impossible : " + (a["raisons"] or ["aucun type éligible."])[0])
        if a["empreinte"] != empreinte_attendue:
            raise RegleMetier("L'ouvrage ou le référentiel a changé depuis l'aperçu : rouvrez-le avant d'accepter.")
        return self.adopter_referentiel([t["type"] for t in a["types"]], action="acceptation en un geste")

    def refuser_mise_a_jour(self, types, motif):
        """Décision tracée de ne pas adopter, pour l'instant, la mise à jour des profils `types` (R7).
        Rien n'est adopté ni modifié en dehors du journal ; un motif écrit est obligatoire."""
        motif = (motif or "").strip()
        if not motif:
            raise RegleMetier("Indiquez le motif du refus de la mise à jour.")
        ecarts = {x["type"] for x in self.apercu_adoption()}
        types = list(dict.fromkeys(types or []))
        for t in types:
            if t not in ecarts:
                raise RegleMetier(f"Type {t} : aucune mise à jour à refuser dans cet ouvrage.")
        versions = self._versions_profils()
        for e in self.ouvrage.equipements:
            if e.type in types:
                self._journaliser("refus", e, motif, versions=versions)
        self.modifie = True

    def annuler_adoption(self, enregistrer=False):
        """Rétablit l'état précédent ; l'interface peut aussi restaurer le fichier à l'octet."""
        from . import adoption
        etat = self._avant_adoption
        if etat is None:
            raise RegleMetier("Aucune adoption à annuler dans cette session.")
        if enregistrer:
            if not self.chemin or os.path.realpath(self.chemin) != self._chemin_adoption:
                raise RegleMetier("L'annulation appartient à un autre fichier d'ouvrage.")
            try:
                self.sauvegarde_annulation_adoption = adoption.restaurer(self.sauvegarde_adoption, self.chemin)
            except adoption.AdoptionRefusee as exc:
                raise RegleMetier(str(exc)) from exc
        self.ouvrage, self.catalogue, self.modifie = etat
        self._avant_adoption = None
        return True

    def nom_fichier_propose(self):
        return self.ouvrage.prefixe() or "ouvrage"

    def _change(self, devalider=True):
        """Toute évolution technique fait repasser un ouvrage validé en contrôle.

        Le statut « Validé » est seulement rétabli par un acte explicite de
        l'utilisateur, puis vérifié lors de l'enregistrement.
        """
        if devalider and self.ouvrage.statut == "Validé":
            self.ouvrage.statut = "À contrôler"
        self.modifie = True

    # ================================================================== identification
    def definir(self, champ, valeur):
        """lieu, code_ouvrage, libelle, automate, nom_projet, mode."""
        if champ in ("lieu", "code_ouvrage", "numero_ouvrage"):
            valeur = valeur.strip().upper()
        if champ == "mode" and valeur not in ("Neuf", "Existant"):
            raise RegleMetier("Mode inconnu.")
        if getattr(self.ouvrage, champ) != valeur:
            if champ == "statut" and valeur == "Validé":
                # Ne jamais présenter comme « Validé » un ouvrage qui n'est pas prêt,
                # même avant son enregistrement sur disque.
                self._verifier_pret_pour_validation()
            if champ == "mode" and (self.ouvrage.existantes or
                                    any(e.adresses or e.adresses_es for e in self.ouvrage.equipements)):
                raise RegleMetier("Impossible de changer de mode : le projet contient déjà des adresses ou des variables sources.")
            # Les validations d'accès qui utilisaient le protocole global ne sont
            # plus valables si ce protocole change (les protocoles par ligne restent autonomes).
            if champ == "communication":
                for ligne in self.ouvrage.table_tt:
                    if not ligne.protocole:
                        ligne.acces_verifie = False
            setattr(self.ouvrage, champ, valeur)
            if champ == "statut" and valeur == "Validé":
                self.ouvrage.deja_valide = True
            self._change(devalider=(champ != "statut"))

    # ================================================================== sous-ensembles
    def _verifier_se(self, code, ancien=None):
        code = (code or "").strip().upper()
        if not re.match(r"^[A-Z0-9]{2}$", code):
            raise RegleMetier("Le code d'un sous-ensemble fait 2 caractères (lettres majuscules ou chiffres).")
        if code != ancien and any(s.code == code for s in self.ouvrage.sous_ensembles):
            raise RegleMetier(f"Le sous-ensemble {code} existe déjà.")
        return code

    def ajouter_sous_ensemble(self, code, libelle=""):
        code = self._verifier_se(code)
        self.ouvrage.sous_ensembles.append(SousEnsemble(code, libelle.strip()))
        self.ouvrage.sous_ensembles.sort(key=lambda s: s.code)
        self._change()
        return code

    def modifier_sous_ensemble(self, ancien, code, libelle=""):
        code = self._verifier_se(code, ancien)
        se = next(s for s in self.ouvrage.sous_ensembles if s.code == ancien)
        se.code, se.libelle = code, libelle.strip()
        for e in self.ouvrage.equipements:          # les équipements suivent le nouveau code
            if e.sous_ensemble == ancien:
                e.sous_ensemble = code
        self.ouvrage.sous_ensembles.sort(key=lambda s: s.code)
        self._change()

    def supprimer_sous_ensemble(self, code):
        if any(e.sous_ensemble == code for e in self.ouvrage.equipements):
            raise RegleMetier("Des équipements utilisent ce sous-ensemble : déplacez-les ou supprimez-les d'abord.")
        self.ouvrage.sous_ensembles = [s for s in self.ouvrage.sous_ensembles if s.code != code]
        self._change()

    # ================================================================== unités fonctionnelles
    def _verifier_uf(self, code, ancien=None):
        code = (code or "").strip().upper()
        if not re.match(r"^[A-Z0-9]{1,6}$", code):
            raise RegleMetier("Code d'unité fonctionnelle : 1 à 6 lettres majuscules ou chiffres (ex. UF01).")
        if code != ancien and any(u.code == code for u in self.ouvrage.unites):
            raise RegleMetier(f"L'unité fonctionnelle {code} existe déjà.")
        return code

    def assurer_sous_ensemble(self, code, libelle=""):
        """Déclare le sous-ensemble s'il n'existe pas encore ; retourne son code normalisé."""
        code = (code or "").strip().upper()
        if any(s.code == code for s in self.ouvrage.sous_ensembles):
            return code
        return self.ajouter_sous_ensemble(code, libelle)

    def ajouter_uf(self, code, libelle="", sous_ensemble=""):
        code = self._verifier_uf(code)
        if sous_ensemble:
            sous_ensemble = self.assurer_sous_ensemble(sous_ensemble, libelle)
        self.ouvrage.unites.append(UniteFonctionnelle(code, libelle.strip(), sous_ensemble))
        self.ouvrage.unites.sort(key=lambda u: u.code)
        self._change()
        return code

    def modifier_uf(self, ancien, code, libelle="", sous_ensemble=None):
        """Renomme l'UF. Changer son sous-ensemble ne modifie que la valeur proposée aux NOUVEAUX
        équipements : les repères existants ne sont jamais changés en silence."""
        code = self._verifier_uf(code, ancien)
        if sous_ensemble:
            sous_ensemble = self.assurer_sous_ensemble(sous_ensemble, libelle)
        for u in self.ouvrage.unites:
            if u.code == ancien:
                u.code, u.libelle = code, libelle.strip()
                if sous_ensemble is not None:
                    u.sous_ensemble = sous_ensemble
        for e in self.ouvrage.equipements:
            if e.uf == ancien:
                e.uf = code
        self.ouvrage.unites.sort(key=lambda u: u.code)
        self._change()

    def supprimer_uf(self, code):
        # Les équipements de l'UF ne sont pas supprimés : ils redeviennent « sans UF ».
        self.ouvrage.unites = [u for u in self.ouvrage.unites if u.code != code]
        for e in self.ouvrage.equipements:
            if e.uf == code:
                e.uf = ""
        self._change()

    def affecter_uf(self, idents, code):
        if code and not any(u.code == code for u in self.ouvrage.unites):
            raise RegleMetier(f"Unité fonctionnelle {code} inconnue.")
        n = 0
        for e in self.ouvrage.equipements:
            if e.ident in idents and e.uf != code:
                e.uf, n = code, n + 1
        if n:
            self._change()
        return n

    LIBELLE_COMMUNS = "Équipements communs (hors UF)"

    def libelle_communs(self):
        return self.ouvrage.libelle_communs or self.LIBELLE_COMMUNS

    def renommer_communs(self, libelle):
        """Nom du groupe des équipements hors UF (affichage seulement : n'entre dans aucun repère)."""
        libelle = (libelle or "").strip()
        self.ouvrage.libelle_communs = "" if libelle == self.LIBELLE_COMMUNS else libelle
        self._change(devalider=False)

    def equipements_communs(self):
        codes = {u.code for u in self.ouvrage.unites}
        return [e for e in self.ouvrage.equipements if not e.uf or e.uf not in codes]

    # ================================================================== référentiel des modèles
    def types_disponibles(self):
        """Types proposés à la création d'un équipement : référentiel des modèles + types du catalogue SOREP."""
        types = {}
        for code, t in self.modeles["types"].items():
            if t.get("archive"):                       # type archivé : non proposé aux nouveaux équipements
                continue
            types[code] = {"code": code, "designation": t.get("designation") or self.catalogue.designation(code),
                           "domaine": t.get("domaine", ""),
                           "modeles": [n for n in t["modeles"]
                                       if self.modeles["modeles"].get(n, {}).get("statut") != "archivé"]}
        for t in self.catalogue.types:
            if t.get("categorie") == "Équipement" and t["code"] not in types:
                d, dom = _modeles.TYPES_CONNUS.get(t["code"], (t["designation"], ""))
                types[t["code"]] = {"code": t["code"], "designation": t["designation"], "domaine": dom, "modeles": []}
        return sorted(types.values(), key=lambda t: t["code"])

    def designation_type(self, code):
        t = self.modeles["types"].get(code, {})
        return t.get("designation") or (self.catalogue.designation(code) if self.catalogue.type(code)
                                        else _modeles.TYPES_CONNUS.get(code, ("à nommer",))[0])

    def domaine_type(self, code):
        t = self.modeles["types"].get(code, {})
        return t.get("domaine") or _modeles.TYPES_CONNUS.get(code, ("", ""))[1]

    def _sauver_modeles(self):
        """Écriture des modèles par l'éditeur historique.

        Pendant une édition de brouillon (`edition_brouillon`), rien n'est écrit : le serveur reprend les modèles
        modifiés et les range dans le brouillon. Hors brouillon, l'écriture directe n'est permise que tant que le
        cycle de révisions n'a pas commencé (compatibilité) ; ensuite, toute modification passe par un brouillon.
        """
        if getattr(self, "_edition_brouillon", False):
            return
        from .referentiel_depot import Depot
        if Depot().head() is not None:
            self.modeles = _modeles.charger()               # annule la mutation mémoire refusée
            _modeles.completer_signaux(self.modeles, self._catalogue_commun)
            raise RegleMetier("Référentiel en lecture seule : créez un brouillon (écran Référentiel) pour le modifier.")
        _modeles.enregistrer(self.modeles)

    def edition_brouillon(self, donnees):
        """Contexte : l'éditeur historique des modèles travaille sur une COPIE des données du brouillon.
        Renvoie un objet dont `.donnees` contient le résultat à ranger dans le brouillon."""
        session = self

        class _Edition:
            def __enter__(self_):
                from .referentiel_depot import Depot
                self_.avant = (session.modeles, session._catalogue_commun, session.catalogue)
                cat, ref = Depot.objets(donnees)
                session._catalogue_commun, session.modeles, session.catalogue = cat, ref, cat
                session._edition_brouillon = True
                return self_

            def __exit__(self_, exc_type, exc, tb):
                cat, ref = session._catalogue_commun, session.modeles
                self_.donnees = {"catalogue": {"version": cat.version, "types": cat.types, "signaux": cat.signaux,
                                               "regles": cat.regles}, "modeles": ref}
                session.modeles, session._catalogue_commun, session.catalogue = self_.avant
                session._edition_brouillon = False
                return False
        return _Edition()

    def catalogue_equipement(self, eq):
        return catalogue_pour_equipement(self.ouvrage, self.catalogue, eq)

    def options_equipement(self, eq):
        return self.catalogue_equipement(eq).options_du_type(eq.type)

    def creer_type(self, code, designation="", domaine=""):
        code = _modeles.code_type(code)
        if not re.fullmatch(r"[A-Z]{2}|[A-Z0-9]-{2}[A-Z0-9]|[A-Z0-9]{2}-{2}", code):
            raise RegleMetier("Code du type : 2 lettres (ex. HV) ou motif sur 4 positions avec « -- » pour le numéro (ex. A--P).")
        if code in self.modeles["types"]:
            raise RegleMetier(f"Le type {code} existe déjà.")
        if domaine and domaine not in _modeles.DOMAINES:
            raise RegleMetier("Domaine : " + ", ".join(_modeles.DOMAINES) + ".")
        d0, dom0 = _modeles.TYPES_CONNUS.get(code, ("", ""))
        self.modeles["types"][code] = {"code": code, "designation": designation.strip() or d0 or
                                       (self.catalogue.designation(code) if self.catalogue.type(code) else ""),
                                       "domaine": domaine or dom0, "modeles": []}
        self._sauver_modeles()
        return code

    def modifier_type(self, code, designation, domaine):
        t = self.modeles["types"].get(code)
        if t is None:
            raise RegleMetier("Type introuvable.")
        if domaine and domaine not in _modeles.DOMAINES:
            raise RegleMetier("Domaine : " + ", ".join(_modeles.DOMAINES) + ".")
        t["designation"], t["domaine"] = designation.strip(), domaine
        self._sauver_modeles()

    def supprimer_type(self, code):
        t = self.modeles["types"].get(code)
        if t is None:
            return
        if t["modeles"]:
            raise RegleMetier("Supprimez d'abord les modèles de ce type.")
        from .referentiel_depot import ouvrages_utilisant
        projets = ouvrages_utilisant().get(code, [])
        if projets:
            raise RegleMetier(f"Le type {code} est employé par {len(projets)} projet(s) enregistré(s) "
                              f"({projets[0]['repere']}…) : archivez-le plutôt que de le supprimer.")
        del self.modeles["types"][code]
        self._sauver_modeles()

    def creer_modele(self, code_type, nom, depuis_catalogue=False):
        nom = (nom or "").strip()
        if not nom:
            raise RegleMetier("Donnez un nom au modèle (ex. Vanne manuelle 2 fins de course).")
        if nom in self.modeles["modeles"]:
            raise RegleMetier(f"Le modèle « {nom} » existe déjà.")
        if code_type not in self.modeles["types"]:
            self.creer_type(code_type)
        lignes = _modeles.lignes_depuis_catalogue(self.catalogue, code_type) if depuis_catalogue else []
        signaux = (copy.deepcopy(self.catalogue.signaux_du_type(code_type, avec_ecartes=True))
                   if depuis_catalogue else [])
        self.modeles["modeles"][nom] = {"nom": nom, "type": code_type,
                                         "statut": "à valider", "lignes": lignes,
                                         "signaux": signaux, "origine_signaux": "copie du type" if depuis_catalogue else "saisie manuelle"}
        self.modeles["types"][code_type]["modeles"].append(nom)
        self._sauver_modeles()
        return nom

    def dupliquer_modele(self, nom, nouveau_nom):
        """Copie d'un modèle sous un nouveau nom : nouvelles lignes (identifiants neufs), statut « à valider »."""
        source = self._modele(nom)
        nouveau_nom = (nouveau_nom or "").strip()
        if not nouveau_nom:
            raise RegleMetier("Donnez un nom au nouveau modèle.")
        if nouveau_nom in self.modeles["modeles"]:
            raise RegleMetier(f"Le modèle « {nouveau_nom} » existe déjà.")
        copie = copy.deepcopy(source)
        copie.update(nom=nouveau_nom, statut="à valider", duplique_de=nom)
        copie["lignes"] = [dict(l, id=_modeles.nouvelle_ligne()["id"]) for l in copie.get("lignes", [])]
        self.modeles["modeles"][nouveau_nom] = copie
        self.modeles["types"].setdefault(copie["type"], {"modeles": []})["modeles"].append(nouveau_nom)
        self._sauver_modeles()
        return nouveau_nom

    def archiver_modele(self, nom, archive=True):
        """Archivé : conservé (projets existants), non proposé aux nouveaux équipements ; réversible."""
        m = self._modele(nom)
        m["statut"] = "archivé" if archive else "à valider"
        self._sauver_modeles()

    def archiver_type(self, code, archive=True):
        t = self.modeles["types"].get(code)
        if t is None:
            raise RegleMetier(f"Type {code} absent du référentiel des modèles.")
        t["archive"] = bool(archive)
        self._sauver_modeles()

    def supprimer_modele(self, nom):
        from .referentiel_depot import modeles_utilises
        projets = modeles_utilises().get(nom, [])
        if projets:
            raise RegleMetier(f"Le modèle « {nom} » est employé par {len(projets)} projet(s) enregistré(s) "
                              f"({projets[0]}…) : archivez-le plutôt que de le supprimer.")
        m = self.modeles["modeles"].pop(nom, None)
        if m:
            t = self.modeles["types"].get(m["type"])
            if t and nom in t["modeles"]:
                t["modeles"].remove(nom)
            self._sauver_modeles()

    def _modele(self, nom):
        m = self.modeles["modeles"].get(nom)
        if m is None:
            raise RegleMetier("Modèle introuvable.")
        return m

    @staticmethod
    def _ligne(champs):
        try:
            return _modeles.verifier_ligne(champs)
        except ValueError as ex:
            raise RegleMetier(str(ex)) from ex

    def ajouter_ligne_modele(self, nom, champs):
        m = self._modele(nom)
        m["statut"] = "à valider"
        l = self._ligne(champs)
        if any(x["role"] == l["role"] and x["suffixe"] == l["suffixe"] for x in m["lignes"]):
            raise RegleMetier(f"Une ligne {l['role']} …_{l['suffixe']} existe déjà dans ce modèle.")
        m["lignes"].append({"id": uuid.uuid4().hex[:8], **l})
        self._sauver_modeles()

    def modifier_ligne_modele(self, nom, ident, champs):
        m = self._modele(nom)
        m["statut"] = "à valider"
        l = self._ligne(champs)
        cible = next((x for x in m["lignes"] if x["id"] == ident), None)
        if cible is None:
            raise RegleMetier("Ligne introuvable.")
        if any(x is not cible and x["role"] == l["role"] and x["suffixe"] == l["suffixe"] for x in m["lignes"]):
            raise RegleMetier(f"Une ligne {l['role']} …_{l['suffixe']} existe déjà dans ce modèle.")
        cible.update(l)
        self._sauver_modeles()

    def supprimer_lignes_modele(self, nom, idents):
        m = self._modele(nom)
        m["statut"] = "à valider"
        m["lignes"] = [x for x in m["lignes"] if x["id"] not in set(idents)]
        self._sauver_modeles()

    def ajouter_signal_modele(self, nom, champs):
        m = self._modele(nom)
        try:
            s = _modeles.verifier_signal_saisi(champs, m["type"])
        except ValueError as exc:
            raise RegleMetier(str(exc)) from exc
        if any(x["famille"] == s["famille"] and x["code"] == s["code"]
               for x in m["signaux"]):
            raise RegleMetier("Ce signal existe déjà dans le modèle.")
        m["signaux"].append(s)
        m["statut"] = "à valider"
        self._sauver_modeles()

    def modifier_signal_modele(self, nom, famille, code, champs):
        m = self._modele(nom)
        cible = next((x for x in m["signaux"]
                      if x["famille"] == famille and x["code"] == code), None)
        if cible is None:
            raise RegleMetier("Signal introuvable.")
        try:
            nouveau = _modeles.verifier_signal_saisi(champs, m["type"])
        except ValueError as exc:
            raise RegleMetier(str(exc)) from exc
        if (nouveau["famille"], nouveau["code"]) != (famille, code):
            raise RegleMetier("Famille et code immuables : supprimer puis recréer le signal.")
        cible.update(nouveau)
        m["statut"] = "à valider"
        self._sauver_modeles()

    def supprimer_signal_modele(self, nom, famille, code):
        m = self._modele(nom)
        avant = len(m["signaux"])
        m["signaux"] = [x for x in m["signaux"]
                        if (x["famille"], x["code"]) != (famille, code)]
        if len(m["signaux"]) == avant:
            raise RegleMetier("Signal introuvable.")
        m["statut"] = "à valider"
        self._sauver_modeles()

    def valider_modele(self, nom, valide=True):
        m = self._modele(nom)
        if valide:
            erreurs = _modeles.verifier_signaux_modele(m.get("signaux", []), m["type"])
            if erreurs:
                raise RegleMetier("Modèle incohérent : " + erreurs[0])
            if not m.get("signaux") and not m["lignes"]:
                raise RegleMetier("Un modèle sans signal ne peut pas être validé.")
        m["statut"] = "validé" if valide else "à valider"
        self._sauver_modeles()

    def manques_parametrage(self, e, points=None):
        """Ce qui empêche de valider le paramétrage d'un équipement : [message], vide si rien ne manque.
        Ordre : échelles analogiques, impulsions, puis informations proposées à décider."""
        rep = self.ouvrage.repere(e)
        points = [p for p in (points if points is not None else self.points()) if p.ident_eq == e.ident]
        manques = []
        for p in points:
            if p.point in ('EA', 'SA') and p.raccordement == 'Câblé' and not e.es_meta.get(p.cle, {}).get('analogique'):
                manques.append(f"{rep} : paramétrez l'échelle analogique de {p.nom} avant de valider l'équipement. "
                               "L'adresse physique sera renseignée à l'étape E/S.")
        if any(e.type == 'FT' and p.cle == 'ES_IMP' and not e.es_meta.get(p.cle, {}).get('impulsion') for p in points):
            manques.append(f"{rep} : paramétrez le poids d'impulsion et le front de comptage avant de valider le débitmètre.")
        attente = self.propositions_en_attente(e)
        if attente:
            manques.append(f"{rep} : {len(attente)} information(s) fonctionnelle(s) proposée(s) à décider avant validation "
                           f"(ex. {attente[0].cle} « {attente[0].signal.get('information', '')} ») : "
                           "retenez-la ou écartez-la avec un motif.")
        return manques

    def valider_equipements(self, idents, valide=True):
        """Validation EXPLICITE du périmètre d'E/S et des informations de l'équipement.

        La validation du paramétrage ne vaut ni validation des voies/adresses physiques,
        ni qualification des traitements fonctionnels dans l'automate.
        """
        idents = set(idents)
        if valide and self.ouvrage.mode == 'Neuf':
            points = self.points()
            for e in self.ouvrage.equipements:
                if e.ident in idents:
                    manques = self.manques_parametrage(e, points)
                    if manques:
                        raise RegleMetier(manques[0])
        n = 0
        for e in self.ouvrage.equipements:
            if e.ident in idents and e.valide != valide:
                e.valide, n = valide, n + 1
        if n:
            self._change(devalider=False)
        return n

    def importer_modeles(self, chemin):
        """Ajoute au référentiel les modèles d'une base fournie par l'utilisateur ; ne modifie aucun ouvrage."""
        from . import tableur
        nouveau = _modeles.extraire(tableur.lire_classeur(chemin), os.path.basename(chemin),
                                    lexique=self.modeles.get("lexique") or None, catalogue=self.catalogue)
        ref, ajoutes, conflits = _modeles.fusionner(self.modeles, nouveau)
        self.modeles = ref
        self._sauver_modeles()
        return ajoutes, conflits

    # ================================================================== lignes d'un équipement
    def informations(self, eq):
        """Lignes de l'équipement : celles du modèle (copie figée dans l'ouvrage), avec les adaptations
        propres à l'équipement (modifiées, retirées, ajoutées), et le mnémonique calculé."""
        m = self.ouvrage.modeles_snapshot.get(eq.modele) or self.modeles["modeles"].get(eq.modele) or {"lignes": []}
        rep = self.ouvrage.repere_nom(eq)
        sortie = []
        for l in m.get("lignes", []):
            if l["id"] in eq.lignes_retirees:
                continue
            mod = eq.lignes_modifiees.get(l["id"])
            ligne = {**l, **(mod or {}), "origine": "modifiée" if mod else "modèle"}
            sortie.append(ligne)
        sortie += [{**l, "origine": "ajoutée"} for l in eq.lignes_ajoutees]
        for l in sortie:
            l["mnemonique"] = f"{l['role']}_{rep}_{l['suffixe']}"
        return sortie

    def _verifier_unicite_eq(self, eq, l, ident=None):
        for x in self.informations(eq):
            if x["id"] != ident and x["role"] == l["role"] and x["suffixe"] == l["suffixe"]:
                raise RegleMetier(f"La ligne {x['mnemonique']} existe déjà pour cet équipement.")

    def ajouter_ligne_eq(self, ident_eq, champs):
        eq = self.ouvrage.equipement(ident_eq)
        eq.valide = False
        l = self._ligne(champs)
        self._verifier_unicite_eq(eq, l)
        eq.lignes_ajoutees.append({"id": uuid.uuid4().hex[:8], **l})
        self._change(devalider=False)

    def modifier_ligne_eq(self, ident_eq, ident, champs):
        eq = self.ouvrage.equipement(ident_eq)
        eq.valide = False
        l = self._ligne(champs)
        self._verifier_unicite_eq(eq, l, ident)
        ajoutee = next((x for x in eq.lignes_ajoutees if x["id"] == ident), None)
        if ajoutee is not None:
            ajoutee.update(l)
        else:
            eq.lignes_modifiees[ident] = l
        self._change(devalider=False)

    def supprimer_lignes_eq(self, ident_eq, idents):
        eq = self.ouvrage.equipement(ident_eq)
        eq.valide = False
        idents = set(idents)
        eq.lignes_ajoutees = [x for x in eq.lignes_ajoutees if x["id"] not in idents]
        for i in idents:
            eq.lignes_modifiees.pop(i, None)
            if i not in eq.lignes_retirees and not any(x["id"] == i for x in eq.lignes_ajoutees):
                eq.lignes_retirees.append(i)
        self._change(devalider=False)

    def retablir_lignes_eq(self, ident_eq):
        """Revient aux lignes du modèle (annule toutes les adaptations de l'équipement)."""
        eq = self.ouvrage.equipement(ident_eq)
        eq.valide = False
        eq.lignes_ajoutees, eq.lignes_retirees, eq.lignes_modifiees = [], [], {}
        self._change(devalider=False)

    def apercu_modele(self, nom):
        """Aperçu de la reprise du modèle figé `nom` par sa version publiée. Rien n'est modifié."""
        from . import adoption
        return adoption.apercu_modele(self.ouvrage, nom, self.modeles.get("modeles", {}).get(nom), self.catalogue,
                                      self.modeles.get("correspondances", []))

    def adopter_modele(self, nom, renommages_confirmes=False):
        """Reprise contrôlée d'un modèle figé : refus si bloqué, renommages confirmés, données reportées par
        correspondance (jamais recalculées), sauvegarde horodatée, journal, retour arrière (`annuler_adoption`).
        Tous les équipements du modèle repassent « à valider » ; leurs adaptations locales sont conservées."""
        from . import adoption
        a = self.apercu_modele(nom)
        if a["identique"]:
            raise RegleMetier(f"Modèle « {nom} » déjà à jour dans cet ouvrage.")
        if not a["adoptable"]:
            raise RegleMetier(a["bloquants"][0])
        if a["renommages"] and not renommages_confirmes:
            raise RegleMetier(f"Modèle « {nom} » : {len(a['renommages'])} renommage(s) à confirmer explicitement.")
        sauvegarde = adoption.sauvegarder(self.chemin)
        self._avant_adoption = (copy.deepcopy(self.ouvrage), copy.deepcopy(self.catalogue), self.modifie)
        self.sauvegarde_adoption, self.sauvegarde_annulation_adoption = sauvegarde, ""
        self._chemin_adoption = os.path.realpath(self.chemin) if self.chemin else ""
        eqs = [e for e in self.ouvrage.equipements if e.modele == nom]
        for r in a["renommages"]:
            if r["ancienne"] != r["nouvelle"]:
                for e in eqs:
                    adoption._renommer(self.ouvrage, e, r["ancienne"], r["nouvelle"])
        self._remplacer_modele_fige(nom)
        versions = self._versions_profils()
        for e in eqs:
            self._journaliser("adoption du modèle", e, f"Modèle « {nom} » : {len(a['renommages'])} renommage(s), "
                              f"{len(a['ajoutees'])} ajout(s), {len(a['retirees'])} retrait(s), "
                              f"{len(a['modifiees'])} modification(s)", sauvegarde=sauvegarde, versions=versions)
        self._change()
        return a

    def _remplacer_modele_fige(self, nom):
        self.ouvrage.modeles_snapshot[nom] = copy.deepcopy(self.modeles["modeles"][nom])
        for autre in self.ouvrage.equipements:
            if autre.modele == nom:
                autre.valide = False
                autre.validees.clear()
                for meta in autre.es_meta.values():
                    meta["validee"] = False

    def actualiser_modele_eq(self, ident_eq):
        """Reprend la version actuelle du modèle dans le référentiel (les adaptations sont conservées).
        Refusé si la reprise renomme ou fait disparaître une donnée : passer par `adopter_modele`."""
        eq = self.ouvrage.equipement(ident_eq)
        if eq.modele in self.modeles["modeles"]:
            a = self.apercu_modele(eq.modele)
            if not a["adoptable"]:
                raise RegleMetier(a["bloquants"][0])
            if a["renommages"]:
                raise RegleMetier(f"Modèle « {eq.modele} » : la reprise renomme {len(a['renommages'])} variable(s) ; "
                                  "utilisez la reprise contrôlée avec confirmation.")
            # Le snapshot est commun aux équipements du même modèle dans un ouvrage.
            # On invalide TOUS ceux qui en dépendent, jamais les anciens fichiers sur disque.
            self._remplacer_modele_fige(eq.modele)
            self._change()

    def apercu_inventaire(self, chemin):
        from . import tableur, inventaire
        return inventaire.analyser(tableur.lire_classeur(chemin), self)

    def appliquer_inventaire(self, lignes):
        from . import inventaire
        with self._operation_lourde("inventaire"):
            return inventaire.appliquer(lignes, self)

    def nombre_equipements_uf(self, code):
        return sum(1 for e in self.ouvrage.equipements if e.uf == code)

    def nombre_equipements(self, code_se):
        return sum(1 for e in self.ouvrage.equipements if e.sous_ensemble == code_se)

    # ================================================================== équipements
    def equipement_vierge(self, sous_ensemble=None, uf=""):
        """Équipement à compléter : dans l'UF donnée, avec le sous-ensemble de l'UF s'il est défini."""
        u = next((x for x in self.ouvrage.unites if x.code == uf), None) if uf else None
        se = (sous_ensemble or (u.sous_ensemble if u else "")
              or (self.ouvrage.sous_ensembles[0].code if self.ouvrage.sous_ensembles else ""))
        eq = Equipement(se, "", "01")
        eq.uf = u.code if u else ""
        return eq

    def verifier_equipement(self, eq, ident_original=None):
        o = self.ouvrage
        if not eq.sous_ensemble or eq.sous_ensemble not in [s.code for s in o.sous_ensembles]:
            raise RegleMetier("Choisissez un sous-ensemble déclaré dans l'ouvrage.")
        if self.catalogue.type(eq.type) is None and eq.type not in self.modeles["types"]:
            raise RegleMetier("Choisissez un type du référentiel.")
        if eq.modele:
            t = self.modeles["types"].get(eq.type)
            deja = any(e.type == eq.type and e.modele == eq.modele for e in self.ouvrage.equipements)
            if not deja and (t is None or eq.modele not in t["modeles"]):
                raise RegleMetier(f"Le modèle {eq.modele} n'appartient pas au type {eq.type}.")
            if not deja and self.modeles["modeles"].get(eq.modele, {}).get("statut") == "archivé":
                raise RegleMetier(f"Le modèle {eq.modele} est archivé : il n'est plus proposé aux nouveaux équipements.")
        if not re.match(r"^\d{2}$", eq.numero or "") or eq.numero == "00":
            raise RegleMetier("Le numéro va de 01 à 99.")
        rep = o.repere(eq)
        for autre in o.equipements:
            if autre.ident != ident_original and o.repere(autre) == rep:
                raise RegleMetier(f"Le repère {rep} existe déjà dans l'ouvrage.")
        for a in eq.ajouts:
            sens = sens_incoherent(a.famille, a.es)
            if sens:
                raise RegleMetier(f"Signal {a.famille}_{a.code} : {sens}.")

    def _figer_modele(self, eq):
        if eq.modele and eq.modele not in self.ouvrage.modeles_snapshot and eq.modele in self.modeles["modeles"]:
            self.ouvrage.modeles_snapshot[eq.modele] = copy.deepcopy(self.modeles["modeles"][eq.modele])

    def ajouter_equipement(self, eq):
        self.verifier_equipement(eq)
        self._figer_modele(eq)
        self.ouvrage.equipements.append(eq)
        self._change()
        return eq

    def remplacer_equipement(self, ident, eq):
        self.verifier_equipement(eq, ident)
        self._figer_modele(eq)
        eq.ident = ident
        eq.valide = False                 # toute modification repasse l'équipement « à valider »
        i = next(k for k, e in enumerate(self.ouvrage.equipements) if e.ident == ident)
        self.ouvrage.equipements[i] = eq
        self._change()

    def copie_pour_duplication(self, ident):
        """Copie d'un équipement avec le premier numéro libre ; ses adresses ne sont pas reprises."""
        eq = self.ouvrage.equipement(ident)
        nouveau = copy.deepcopy(eq)
        nouveau.ident = uuid.uuid4().hex[:8]
        nouveau.adresses, nouveau.adresses_es = {}, {}
        pris = {int(e.numero) for e in self.ouvrage.equipements
                if e.type == eq.type and (self.ouvrage.charte_12() or e.sous_ensemble == eq.sous_ensemble)
                and e.numero.isdigit()}
        libres = [n for n in range(1, 100) if n not in pris]
        if not libres:
            raise RegleMetier("Plus aucun numéro libre pour ce type dans l'ouvrage."
                              if self.ouvrage.charte_12() else "Plus aucun numéro libre pour ce type dans ce sous-ensemble.")
        nouveau.numero = f"{libres[0]:02d}"
        return nouveau

    def supprimer_equipement(self, ident):
        self.ouvrage.equipements = [e for e in self.ouvrage.equipements if e.ident != ident]
        self._change()

    def equipements_tries(self):
        return sorted(self.ouvrage.equipements, key=lambda e: self.ouvrage.repere(e))

    def signaux_proposes(self, eq):
        """Signaux du catalogue pour le type de l'équipement : (signal, retenu, présence affichée, activable).

        Ordre : E/S physiques (famille ES) d'abord, puis signaux fonctionnels, chacun dans l'ordre du
        catalogue. Pour un signal « Règle », `présence` explique son état et `activable` indique si la
        condition de sa règle est remplie (sinon il ne peut pas être retenu)."""
        props = self.propositions(eq)
        lignes = []
        for s in self.catalogue_equipement(eq).signaux_du_type(eq.type):
            cle = f"{s['famille']}_{s['code']}"
            if s["presence"] == "Règle":
                p = props.get(cle)
                if p is None:
                    lignes.append((s, False, "Règle : condition absente", False))
                else:
                    ids = ", ".join(r.get("id", "?") for r in p.regles)
                    etat = {"retenu": "Règle " + ids + (" (auto)" if p.auto else " (acceptée)"),
                            "proposé": "Proposé par " + ids, "refusé": "Refusé (" + ids + ")"}[p.etat]
                    lignes.append((s, p.etat == "retenu", etat, True))
                continue
            if s["presence"] == "Option":
                actif = s.get("option") in eq.options
                presence = f"Option : {s.get('option')}"
            else:
                actif, presence = True, s["presence"]
            lignes.append((s, actif and cle not in eq.exclus, presence, actif))
        lignes.sort(key=lambda x: 0 if x[0]["famille"] == "ES" else 1)      # tri stable : ordre du catalogue
        return lignes

    def propositions(self, eq):
        """Signaux proposés par les règles fonctionnelles pour cet équipement : {clé: Proposition}."""
        from .modele import propositions_regles
        return propositions_regles(self.catalogue_equipement(eq), eq)

    CATEGORIES = {"TS": "Information de supervision (TS)", "TM": "Mesure transmise (TM)",
                  "CP": "Comptage (CP)", "TC": "Commande fonctionnelle (TC)",
                  "TR": "Téléréglage (TR)", "RTR": "Retour de téléréglage (RTR)",
                  **{f: f"Variable interne déclarée ({f})" for f in ("BI", "EI", "MI", "RI")}}

    def informations_fonctionnelles(self, eq):
        """Toutes les informations non physiques que le modèle prévoit pour l'équipement, avec leur état
        (retenue, proposée, écartée, non retenue), leur provenance et leur justification. Les E/S
        physiques sont présentées à part (paramétrage des E/S)."""
        cat = self.catalogue_equipement(eq)
        props = self.propositions(eq)
        base = {f"{s['famille']}_{s['code']}" for s in _base_retenue(cat, eq)}
        sortie = []
        for s in cat.signaux_du_type(eq.type):
            if s["famille"] == "ES":
                continue
            cle = f"{s['famille']}_{s['code']}"
            p = props.get(cle)
            ligne = {"cle": cle, "famille": s["famille"], "code": s["code"], "information": s.get("information", ""),
                     "categorie": self.CATEGORIES.get(s["famille"], s["famille"]), "presence": s.get("presence", ""),
                     "alarme": bool(s.get("alarme")), "sources": [], "regles": [], "logique": s.get("logique", ""),
                     "motif": (eq.motifs or {}).get(cle, ""), "decidable": False}
            if cle in base:
                ligne["etat"] = "retenue"
                ligne["origine"] = ({"Obligatoire": "Obligatoire (modèle)", "Par défaut": "Par défaut (modèle)"}
                                    .get(s["presence"]) or f"Option « {s.get('option', '')} »")
            elif p is not None:
                # Retenue d'office : seule la règle automatique la justifie (ex. CP_VOL par impulsions, pas
                # par intégration du débit) ; une même information n'est jamais créée deux fois.
                regles = [r for r in p.regles if retenue_d_office(r)] if p.auto else p.regles
                ligne["regles"] = [r.get("id", "?") for r in regles]
                ligne["sources"] = sorted({c for r in regles for c in r.get("si", [])})
                ligne["logique"] = " ".join(dict.fromkeys(texte_regle(r) for r in regles if texte_regle(r))) or p.logique
                ligne["decidable"] = not p.auto
                ligne["etat"] = {"retenu": "retenue", "proposé": "proposée", "refusé": "écartée"}[p.etat]
                ids = ", ".join(ligne["regles"])
                ligne["origine"] = (f"Règle {ids} (automatique)" if p.auto and p.etat == "retenu" else
                                    f"Règle {ids}, retenue par l'automaticien" if p.etat == "retenu" else
                                    f"Règle {ids}, à décider" if p.etat == "proposé" else f"Règle {ids}, écartée")
            elif cle in eq.exclus:
                ligne["etat"], ligne["origine"] = "écartée", "Retirée de cet équipement"
            elif s["presence"] == "Option":
                ligne["etat"], ligne["origine"] = "non retenue", f"Option « {s.get('option', '')} » non choisie"
            else:
                ligne["etat"], ligne["origine"] = "non retenue", "Conditions de la règle non réunies"
            sortie.append(ligne)
        return sortie

    def propositions_en_attente(self, eq):
        """Informations fonctionnelles proposées par une règle et pas encore décidées (ni retenues,
        ni écartées). Elles bloquent la validation de l'équipement : rien n'est oublié en silence."""
        return [p for p in self.propositions(eq).values() if p.etat == "proposé"]

    def decider_proposition(self, ident, cle, decision, motif=""):
        """« retenir » ou « ecarter » (motif obligatoire) une information proposée ; « reouvrir » annule
        la décision. Toute décision remet l'équipement « à valider »."""
        eq = self.ouvrage.equipement(ident)
        if eq is None:
            raise RegleMetier("Équipement introuvable.")
        props = self.propositions(eq)
        if cle not in props:
            raise RegleMetier(f"{cle} n'est pas une information proposée pour cet équipement.")
        motif = (motif or "").strip()
        if decision == "retenir":
            self.accepter_proposition(eq, cle)
            eq.motifs.pop(cle, None)
        elif decision == "ecarter":
            if len(motif) < 3:
                raise RegleMetier("Indiquez pourquoi cette information est écartée (ex. « pas de traitement prévu »).")
            self.refuser_proposition(eq, cle)
            eq.motifs[cle] = motif[:200]
        elif decision == "reouvrir":
            if cle in eq.acceptes:
                eq.acceptes.remove(cle)
            if cle in eq.exclus:
                eq.exclus.remove(cle)
            eq.motifs.pop(cle, None)
        else:
            raise RegleMetier("Décision inconnue : retenir, ecarter ou reouvrir.")
        eq.valide = False
        self._change()

    def decider_propositions(self, ident, decision, motif="", cles=None):
        """Même décision pour plusieurs informations proposées (par défaut : toutes celles en attente)."""
        eq = self.ouvrage.equipement(ident)
        if eq is None:
            raise RegleMetier("Équipement introuvable.")
        cles = list(cles) if cles is not None else [p.cle for p in self.propositions_en_attente(eq)]
        if decision == "ecarter" and len((motif or "").strip()) < 3:
            raise RegleMetier("Indiquez pourquoi ces informations sont écartées.")
        for cle in cles:                   # une information retenue peut en faire proposer d'autres :
            self.decider_proposition(ident, cle, decision, motif)   # elles restent à décider, rien d'implicite
        return len(cles)

    @staticmethod
    def accepter_proposition(eq, cle):
        """Accepte un signal proposé par une règle (il sera généré)."""
        if cle in eq.exclus:
            eq.exclus.remove(cle)
        if cle not in eq.acceptes:
            eq.acceptes.append(cle)

    @staticmethod
    def refuser_proposition(eq, cle):
        """Refuse (non applicable) un signal proposé par une règle : il n'est plus proposé."""
        if cle in eq.acceptes:
            eq.acceptes.remove(cle)
        if cle not in eq.exclus:
            eq.exclus.append(cle)

    def nombre_signaux(self, eq):
        return len(signaux_retenus(self.catalogue_equipement(eq), eq))

    @staticmethod
    def basculer_signal(eq, signal, retenu=None):
        """Retire un signal retenu ou le remet. Un signal en option exige d'abord son option.
        Un signal « Règle » se retient en l'acceptant et se retire en le refusant ; `retenu` (état
        affiché) distingue un signal retenu d'office d'une simple proposition."""
        cle = f"{signal['famille']}_{signal['code']}"
        if signal["presence"] == "Règle":
            if retenu is None:
                retenu = cle in eq.acceptes
            if retenu:
                Session.refuser_proposition(eq, cle)
            else:
                Session.accepter_proposition(eq, cle)
            return
        if signal["presence"] == "Option" and signal.get("option") not in eq.options:
            raise RegleMetier(f"Cochez d'abord l'option « {signal.get('option')} ».")
        cle = f"{signal['famille']}_{signal['code']}"
        if cle in eq.exclus:
            eq.exclus.remove(cle)
        else:
            eq.exclus.append(cle)

    @staticmethod
    def signal_personnalise(eq, cle):
        """Indice du signal propre qui remplace le signal du catalogue `cle` sur cet équipement, ou None."""
        return next((i for i, a in enumerate(eq.ajouts) if f"{a.famille}_{a.code}" == cle), None)

    @staticmethod
    def personnaliser_signal(eq, signal, nouveau):
        """Adapte un signal du catalogue pour CET équipement seulement (information, type, unité, E/S,
        organe, alarme). Le catalogue n'est pas modifié. Famille et code restent ceux du catalogue :
        nom de variable, adresses, commentaires et validations sont conservés."""
        cle = f"{signal['famille']}_{signal['code']}"
        if f"{nouveau.famille}_{nouveau.code}" != cle:
            raise RegleMetier("La famille et le code d'un signal du catalogue ne se modifient pas : "
                              "ajouter plutôt un signal propre.")
        Session.verifier_signal_propre(nouveau)
        i = Session.signal_personnalise(eq, cle)
        if i is None:
            if cle in eq.exclus:
                raise RegleMetier("Ce signal n'est pas retenu : le cocher d'abord.")
            eq.ajouts.append(nouveau)
            eq.exclus.append(cle)          # la version du catalogue est remplacée par la version adaptée
        else:
            eq.ajouts[i] = nouveau

    @staticmethod
    def retablir_signal(eq, cle):
        """Revient à la version du catalogue d'un signal adapté (adresses et textes conservés)."""
        i = Session.signal_personnalise(eq, cle)
        if i is not None:
            eq.ajouts.pop(i)
        if cle in eq.exclus:
            eq.exclus.remove(cle)

    @staticmethod
    def verifier_signal_propre(s):
        if not s.information.strip():
            raise RegleMetier("L'information est obligatoire.")
        from .modele import TAILLE_MOTS
        if s.type_logique not in TAILLE_MOTS:
            raise RegleMetier(f"Type logique {s.type_logique} non pris en charge.")
        if not re.match(r"^[A-Z0-9]+$", s.code or ""):
            raise RegleMetier("Le code s'écrit en lettres majuscules et chiffres, sans espace.")
        if s.alarme and s.famille != "TS":
            raise RegleMetier("Seule une TS peut être une alarme.")
        if s.famille == "ES" and s.es not in ("ET", "ST", "EA", "SA"):
            raise RegleMetier("Une E/S locale doit être une ET, ST, EA ou SA.")
        if s.organe and s.es != "ET":
            raise RegleMetier("Le code d'organe ne s'emploie que sur une ET.")
        sens = sens_incoherent(s.famille, s.es)
        if sens:
            raise RegleMetier(sens[:1].upper() + sens[1:] + ".")
        from .catalogue import anomalies_interne
        interne = anomalies_interne({"famille": s.famille, "es": s.es, "alarme": s.alarme})
        if interne:
            raise RegleMetier(interne[0][:1].upper() + interne[0][1:] + ".")

    def promouvoir_signal(self, eq, index, presence="Par défaut", option="", statut="Validé"):
        """Promouvoir vers le modèle si choisi, sinon vers le catalogue de type historique.

        Cette action ne modifie jamais les copies des ouvrages existants.
        """
        a = eq.ajouts[index]
        if eq.modele and eq.modele in self.modeles["modeles"]:
            if presence == "Option" and not option:
                raise RegleMetier("Précisez l'option.")
            signal = {"type": eq.type, "information": a.information, "famille": a.famille, "code": a.code,
                      "type_logique": a.type_logique, "unite": a.unite, "es": a.es, "organe": a.organe,
                      "alarme": a.alarme, "presence": presence,
                      "option": option if presence == "Option" else "", "statut": statut}
            self.ajouter_signal_modele(eq.modele, signal)
            # Garder le signal propre sur cet équipement tant que le modèle n'est
            # pas réactualisé volontairement ; évite toute disparition silencieuse.
            return signal
        if any(s["famille"] == a.famille and s["code"] == a.code
               for s in self.catalogue.signaux_du_type(eq.type, avec_ecartes=True)):
            raise RegleMetier(f"Le type {eq.type} a déjà un signal {a.famille}_{a.code} dans le catalogue.")
        if presence == "Option" and not option:
            raise RegleMetier("Précisez l'option.")
        signal = {"type": eq.type, "information": a.information, "famille": a.famille, "code": a.code,
                  "type_logique": a.type_logique, "unite": a.unite, "es": a.es, "organe": a.organe, "alarme": a.alarme,
                  "presence": presence, "option": option if presence == "Option" else "", "statut": statut,
                  "remarque": f"Ajouté depuis l'équipement {self.ouvrage.repere(eq)}."}
        idx = [k for k, s in enumerate(self.catalogue.signaux) if s["type"] == eq.type]
        self.catalogue.signaux.insert(idx[-1] + 1 if idx else len(self.catalogue.signaux), signal)
        del eq.ajouts[index]
        if presence == "Option" and option not in eq.options:
            eq.options.append(option)
        self.enregistrer_catalogue()
        return signal

    def enregistrer_catalogue(self):
        cible = chemins.fichier_catalogue_utilisateur()
        if os.path.exists(cible) and not getattr(self, "_copie_catalogue", False):
            shutil.copy2(cible, cible + ".sauvegarde")
            self._copie_catalogue = True
        self.catalogue.enregistrer()
        self.catalogue_modifie = False

    # ================================================================== référentiel ↔ Excel (révisions)
    def exporter_referentiel(self, chemin, source="publie"):
        """Classeur Excel du référentiel : révision publiée (« publie »), brouillon (« brouillon ») ou révision
        archivée (« R<n> »). Jamais le référentiel figé dans l'ouvrage ouvert."""
        from . import referentiel_excel as rx
        from .referentiel_depot import Depot, DepotRefuse
        depot = Depot()
        if source == "brouillon":
            b = depot.brouillon()
            if b is None:
                raise RegleMetier("Aucun brouillon à exporter.")
            donnees, libelle = b["donnees"], f"Brouillon basé sur R{b['base_revision']:04d}"
        elif str(source).startswith("R"):
            try:
                donnees = depot.revision(int(str(source)[1:]))["donnees"]
            except (DepotRefuse, ValueError) as exc:
                raise RegleMetier(str(exc)) from exc
            libelle = f"Révision {source}"
        else:
            donnees, libelle = depot.publie(), "Révision publiée"
        cat, ref = Depot.objets(donnees)
        return rx.exporter(cat, ref, chemin, libelle)

    def analyser_classeur_referentiel(self, chemin):
        """Classeur modifié → contrôles et différences avec le BROUILLON ; rien n'est appliqué. Le résultat
        contrôlé est gardé jusqu'à `integrer_classeur_referentiel` (même empreinte)."""
        from . import referentiel_excel as rx
        from .referentiel_depot import Depot, classeur_sain
        depot = Depot()
        b = depot.brouillon()
        if b is None:
            raise RegleMetier("Créez d'abord un brouillon : un classeur s'importe dans un brouillon, jamais "
                              "directement dans la révision publiée.")
        self._classeur_en_attente = None
        classeur_sain(chemin)
        cat_b, ref_b = Depot.objets(b["donnees"])
        actuel = rx.etat(cat_b, ref_b)
        nouveau, lect, meta = rx.lire(chemin)
        rx.controler(nouveau, actuel, lect)
        base = meta.get("Empreinte", "")
        if base and base != rx.empreinte(actuel):
            lect.alertes.insert(0, "Le brouillon a changé depuis cet export : vérifiez que vous n'annulez pas une "
                                   "modification faite entre-temps.")
        resultat = {"erreurs": lect.erreurs, "alertes": lect.alertes, "differences": [], "integrable": False,
                    "base": meta.get("Révision exportée", "")}
        if lect.erreurs:
            return resultat
        cat, ref = rx.construire(nouveau, cat_b, ref_b)
        donnees = {"catalogue": {"version": cat_b.version, "types": cat.types, "signaux": cat.signaux,
                                 "regles": cat.regles}, "modeles": ref}
        resultat["differences"] = depot.differences(b["donnees"], donnees)
        c = depot.controler(donnees)
        resultat["erreurs_brouillon"] = c["erreurs"]
        resultat["integrable"] = bool(resultat["differences"])
        from .referentiel_depot import empreinte
        resultat["empreinte"] = empreinte(donnees)
        self._classeur_en_attente = (donnees, resultat["empreinte"], b["modifie_le"])
        return resultat

    def integrer_classeur_referentiel(self, empreinte_attendue):
        from .referentiel_depot import Depot
        attente = getattr(self, "_classeur_en_attente", None)
        depot = Depot()
        b = depot.brouillon()
        if not attente or attente[1] != empreinte_attendue or b is None or b["modifie_le"] != attente[2]:
            raise RegleMetier("Le classeur ou le brouillon a changé depuis l'aperçu : relancez l'analyse.")
        depot.remplacer_donnees(attente[0], "classeur Excel intégré")
        self._classeur_en_attente = None

    def revisions_referentiel(self):
        from .referentiel_depot import Depot
        return Depot().revisions()

    def _recharger_referentiel(self):
        self._catalogue_commun = Catalogue.charger()
        self.modeles = _modeles.charger()
        _modeles.completer_signaux(self.modeles, self._catalogue_commun)
        if not self.ouvrage.equipements and not self.chemin:
            self.catalogue = copy.deepcopy(self._catalogue_commun)   # ouvrage vierge : nouvelle révision

    # ================================================================== variables, contrôles
    def variables(self):
        return generer(self.ouvrage, self.catalogue)

    def points(self):
        return generer_points(self.ouvrage, self.catalogue)

    def variables_internes(self):
        """Variables internes déclarées et sélectionnées (P1) : non localisées, jamais télétransmises."""
        from .modele import generer_internes
        return generer_internes(self.ouvrage, self.catalogue)

    def anomalies(self, variables=None):
        return controler(self.ouvrage, self.catalogue, variables)

    def anomalies_existant(self):
        return existant.controler_existant(self.ouvrage, self.catalogue)

    def revenir_au_standard(self, ident_eq, cle, propriete, confirme=False):
        """Retire une surcharge locale d'un équipement pour revenir à la propriété du référentiel (R4).

        Une propriété à la fois, seulement après confirmation explicite ; les autres surcharges sont conservées.
        Retirer une exclusion remet le signal dans l'équipement, qui repasse « à valider »."""
        from .adoption import PROPRIETES_STANDARD, SURCHARGES
        if propriete not in PROPRIETES_STANDARD:
            raise RegleMetier(f"Propriété « {propriete} » : retour au standard impossible.")
        eq = self.ouvrage.equipement(ident_eq)
        if eq is None:
            raise RegleMetier("Équipement introuvable.")
        if propriete == "exclusion":
            present = cle in eq.exclus
        else:
            _, champ, sous_cle, _ = next(x for x in SURCHARGES if x[0] == propriete)
            valeur = getattr(eq, champ).get(cle)
            present = (isinstance(valeur, dict) and sous_cle in valeur) if sous_cle else cle in getattr(eq, champ)
        if not present:
            raise RegleMetier(f"{cle} : aucune surcharge « {propriete} » sur {self.ouvrage.repere(eq)}.")
        if not confirme:
            raise RegleMetier("Confirmez le retour au standard : la valeur locale sera retirée.")
        ancienne = "exclu" if propriete == "exclusion" else (
            getattr(eq, champ)[cle][sous_cle] if sous_cle else getattr(eq, champ)[cle])
        self._journaliser("retour au standard", eq, f"{cle} — {propriete} : valeur locale « {ancienne} » retirée")
        if propriete == "exclusion":
            eq.exclus.remove(cle)
            eq.valide = False
        elif sous_cle:
            del getattr(eq, champ)[cle][sous_cle]
            if propriete == "type":
                eq.valide = False
        else:
            del getattr(eq, champ)[cle]
        self._change()

    def synchronisation(self):
        """État de synchronisation des profils et des équipements avec le référentiel en service (R2 / R3).
        Version publiée et version figée de chaque profil utilisé. Lecture seule."""
        from . import profils
        from .referentiel_depot import Depot
        c = self._catalogue_commun
        publie = {"catalogue": {"version": c.version, "types": c.types, "signaux": c.signaux, "regles": c.regles},
                  "modeles": self.modeles}
        etat = profils.etat_synchronisation(self.ouvrage, self.catalogue, publie)
        try:
            historique = profils.versions(Depot())
        except Exception:                               # noqa: BLE001 — l'état reste utile sans les versions
            historique = {}
        for code, x in etat["types"].items():
            pub = profils.version_publiee(None, code, historique)
            fig = profils.version_figee(self.catalogue, code, historique)
            x["version_publiee"] = pub["version"] if pub else None
            x["version_figee"] = fig["version"] if fig else None
        return etat

    def rapport_impact(self):
        """R5 : impact du brouillon du référentiel sur tous les ouvrages enregistrés (lecture seule).
        Les fichiers illisibles sont listés à part ; rien n'est modifié ni adopté."""
        from . import profils, projets
        from .referentiel_depot import Depot
        depot = Depot()
        b = depot.brouillon()
        if b is None:
            raise RegleMetier("Aucun brouillon du référentiel : rien à évaluer.")
        ouvrages, illisibles = [], []
        for f in projets.lister():
            if f.erreur:
                illisibles.append(os.path.basename(f.chemin))
                continue
            try:
                o = Ouvrage.ouvrir(f.chemin)
                cat = Catalogue(**o.catalogue_snapshot) if o.catalogue_snapshot else self._catalogue_commun
            except Exception:                           # noqa: BLE001 — signalé, ne bloque pas le rapport
                illisibles.append(os.path.basename(f.chemin))
                continue
            ouvrages.append((f.repere, os.path.basename(f.chemin), o, cat, f.archive))
        r = profils.rapport_impact(depot.publie(), b["donnees"], ouvrages, self._versions_profils())
        r["illisibles"] = sorted(illisibles)
        return r

    def dossier_recette(self, chemin_zip):
        """Dossier de recette en zip (genvar/dossier_recette.py) : pièces produites, pièces non produites et
        leur motif. Renvoie le manifeste."""
        import tempfile
        from . import dossier_recette
        with tempfile.TemporaryDirectory(prefix="ogias_recette_") as dossier:
            return dossier_recette.archive(self, dossier, chemin_zip)

    def parcours(self):
        """Points bloquants et à vérifier de chaque étape du parcours (genvar/parcours.py). Lecture seule."""
        from .parcours import etat_parcours
        return etat_parcours(self)

    def anomalies_homonymes(self):
        """Homonymes avec les autres ouvrages enregistrés du même programme automate (P8 / R9).
        Lecture seule des fichiers ; un fichier illisible ou archivé est ignoré."""
        from . import homonymes, projets
        if not homonymes.perimetre(self.ouvrage):
            return []
        moi = os.path.abspath(self.chemin) if self.chemin else ""
        autres = []
        for f in projets.lister():
            if f.erreur or f.archive or os.path.abspath(f.chemin) == moi:
                continue
            try:
                o = Ouvrage.ouvrir(f.chemin)
                cat = Catalogue(**o.catalogue_snapshot) if o.catalogue_snapshot else self._catalogue_commun
            except Exception:                           # noqa: BLE001 — un fichier illisible ne bloque pas
                continue
            if homonymes.perimetre(o) == homonymes.perimetre(self.ouvrage):
                autres.append((f.repere, o, cat))
        return homonymes.homonymes(self.ouvrage, self.catalogue, autres)

    def registre_modbus(self, adresse):
        return registre_modbus(adresse, self.ouvrage.decalage_modbus)

    @staticmethod
    def anomalies_par_variable(variables, anomalies):
        """{nom de variable: niveau le plus grave} d'après les messages de contrôle."""
        resultat: dict[str, str] = {}
        noms = {v.nom for v in variables} | {v.nom_es for v in variables if v.nom_es}
        for a in anomalies:
            for nom in re.findall(r"[A-Z]{2,3}_[A-Z0-9]+_[A-Z0-9_]+", a.message):
                if nom in noms and resultat.get(nom) != "Erreur":
                    resultat[nom] = a.niveau
        return resultat

    def definir_adresses(self, ident_eq, cle, adresse=None, adresse_es=None, deverrouiller=False):
        """Valide intégralement les adresses avant d'enregistrer la moindre valeur.

        Ne modifie jamais les adresses des projets repris d'un automate existant.
        """
        from .modele import _mot, Memoire, TAILLE_MOTS, zone
        if self.ouvrage.mode != "Neuf":
            raise RegleMetier("Projet existant : les adresses d'origine sont conservées et non réattribuées.")
        eq = self.ouvrage.equipement(ident_eq)
        if eq is None:
            raise RegleMetier("Équipement introuvable.")
        variables = self.variables()
        v = next((x for x in variables if x.ident_eq == ident_eq and x.cle == cle), None)
        cle_es = (v.cle_es if v is not None and v.cle_es else cle)    # un signal peut lire l'E/S d'une source
        es = next((x for x in self.points() if x.ident_eq == ident_eq and x.cle == cle_es), None)
        if adresse is not None:
            adresse = adresse.strip().upper()
            if v is not None and v.adresse_validee and adresse != v.adresse.upper() and not deverrouiller:
                raise RegleMetier(f"L'adresse {v.adresse} de {v.nom} est validée : confirmer explicitement sa "
                                  "modification (elle repassera « proposée »).")
            if v is None:
                raise RegleMetier("Le signal choisi ne possède pas de variable d'échange.")
            if adresse and not RE_ADRESSE_ECHANGE.fullmatch(adresse):
                raise RegleMetier("Adresse d'échange : format %MW1000.3 (bit) ou %MW1400 (mot).")
            if adresse:
                p = _mot(adresse)
                if p is None:
                    raise RegleMetier("Bit invalide : l'indice doit être compris entre 0 et 15.")
                if (v.type_logique == "BOOL") != (p[1] is not None):
                    raise RegleMetier("BOOL : adresse %MWn.bit ; INT, REAL, DINT : adresse %MWn.")
                largeur = max(1, TAILLE_MOTS.get(v.type_logique, 1))
                if largeur == 2 and p[0] % 2:
                    raise RegleMetier("Variable 32 bits : adresse de départ paire obligatoire.")
                debut, fin = zone(self.ouvrage, v.famille)
                if p[0] < debut or p[0] + (largeur - 1 if p[1] is None else 0) > fin:
                    raise RegleMetier(f"Adresse hors de la plage réservée {v.famille} : %MW{debut} à %MW{fin}.")
                occupation = Memoire()
                for autre in variables:
                    if autre.ident_eq == ident_eq and autre.cle == cle:
                        continue
                    if autre.adresse:
                        occupation.occuper(autre.adresse, autre.type_logique, autre.nom)
                conflit = occupation.conflit(adresse, v.type_logique)
                if conflit:
                    raise RegleMetier(f"Adresse {adresse} déjà occupée par {conflit}.")
                # Interdire de rendre une paire TR/RTR déjà affectée incohérente.
                if v.famille in ("TR", "RTR"):
                    oppose = "RTR" if v.famille == "TR" else "TR"
                    liee = next((a for a in variables if a.ident_eq == ident_eq
                                 and a.famille == oppose and a.code == v.code), None)
                    if liee and liee.adresse:
                        ref = zone(self.ouvrage, v.famille)[0] + (
                            _mot(liee.adresse)[0] - zone(self.ouvrage, oppose)[0])
                        if p[0] != ref:
                            raise RegleMetier(f"Correspondance TR/RTR : l'adresse doit être %MW{ref} "
                                              f"pour rester liée à {liee.nom} ({liee.adresse}).")
                        if liee.type_logique != v.type_logique:
                            raise RegleMetier("Types TR/RTR différents : une conversion explicite est requise.")
        if adresse_es is not None:
            adresse_es = adresse_es.strip().upper()
            if es is None:
                raise RegleMetier("Ce signal ne possède pas d'entrée/sortie physique.")
            if adresse_es and not RE_ADRESSE_PHYSIQUE.fullmatch(adresse_es):
                raise RegleMetier("Adresse physique : format %I…, %Q…, %IW… ou %QW….")
            if adresse_es:
                attendu = {"ET": "%I", "ST": "%Q", "EA": "%IW", "SA": "%QW"}[es.point]
                if not adresse_es.startswith(attendu) or (es.point in ("ET", "ST") and adresse_es.startswith(attendu + "W")):
                    raise RegleMetier(f"Pour une {es.point}, l'adresse doit commencer par {attendu}.")
                for autre in self.points():
                    if autre.ident_eq == ident_eq and autre.cle == cle_es:
                        continue
                    if autre.adresse and autre.adresse.upper() == adresse_es:
                        raise RegleMetier(f"Adresse physique déjà utilisée par {autre.nom}.")
        # Toutes les vérifications sont passées : écriture atomique dans l'objet.
        if adresse is not None:
            if adresse:
                eq.adresses[cle] = adresse
            else:
                eq.adresses.pop(cle, None)
            if v is not None and adresse != v.adresse.upper() and cle in eq.validees:
                eq.validees.remove(cle)
        if adresse_es is not None:
            if adresse_es:
                eq.adresses_es[cle_es] = adresse_es
            else:
                eq.adresses_es.pop(cle_es, None)
        if adresse is not None or adresse_es is not None:
            self._change()

    # ================================================================== commentaires et validation
    def definir_textes(self, ident_eq, cle, commentaire=None, libelle=None):
        # Commentaire automate et libellé de supervision saisis. Chaîne vide : retour au texte proposé.
        eq = self.ouvrage.equipement(ident_eq)
        if eq is None:
            raise RegleMetier("Équipement introuvable.")
        from .modele import LONGUEUR_MAX_LIBELLE
        if libelle is not None and len(libelle.strip()) > LONGUEUR_MAX_LIBELLE:
            raise RegleMetier(f"Libellé de supervision : {LONGUEUR_MAX_LIBELLE} caractères au plus.")
        for valeur, cible in ((commentaire, eq.commentaires), (libelle, eq.libelles)):
            if valeur is None:
                continue
            valeur = valeur.strip()
            if valeur:
                cible[cle] = valeur
            else:
                cible.pop(cle, None)
        self._change()

    def valider_adresses(self, paires):
        # Valide les adresses d'échange de (ident_eq, clé). Seules les adresses présentes et sans
        # erreur de contrôle sont validées. Renvoie (nombre validé, liste des refus motivés).
        variables = {(v.ident_eq, v.cle): v for v in self.variables()}
        etats = self.anomalies_par_variable(list(variables.values()), self.anomalies(list(variables.values())))
        ok, refus = 0, []
        for ident, cle in paires:
            v = variables.get((ident, cle))
            if v is None:
                continue
            if not v.adresse:
                refus.append(f"{v.nom} : pas d'adresse.")
            elif etats.get(v.nom) == "Erreur":
                refus.append(f"{v.nom} : erreur de contrôle à corriger avant validation.")
            elif not v.adresse_validee:
                self.ouvrage.equipement(ident).validees.append(cle)
                from .adressage import tracer_validation
                tracer_validation(self, "automate", [(ident, cle)])
                ok += 1
        if ok:
            self._change()
        return ok, refus

    def adresses_orphelines(self, eq):
        """Adresses conservées pour des signaux qui ne sont plus retenus : {clé: adresse}."""
        retenues = {f"{x['famille']}_{x['code']}" for x, _ in signaux_retenus(self.catalogue_equipement(eq), eq)}
        return {c: a for c, a in eq.adresses.items() if c not in retenues}

    def liberer_adresses_orphelines(self, ident_eq):
        eq = self.ouvrage.equipement(ident_eq)
        orph = self.adresses_orphelines(eq) if eq else {}
        for c in orph:
            eq.adresses.pop(c, None)
            if c in eq.validees:
                eq.validees.remove(c)
        if orph:
            self._change()
        return len(orph)

    def devalider_adresses(self, paires):
        n = 0
        for ident, cle in paires:
            eq = self.ouvrage.equipement(ident)
            if eq and cle in eq.validees:
                eq.validees.remove(cle)
                n += 1
        if n:
            self._change()
        return n

    def plan(self, tout_refaire=False):
        return plan_adresses(self.ouvrage, self.catalogue, tout_refaire)

    def appliquer(self, propositions, tout_refaire=False):
        # Une réattribution partielle pourrait supprimer des adresses confirmées.
        attendues, erreurs = self.plan(tout_refaire)
        if erreurs:
            raise RegleMetier("Plan incomplet : " + " | ".join(erreurs[:5]))
        attendu = {(p.variable.ident_eq, p.variable.cle, p.adresse) for p in attendues}
        fourni = {(p.variable.ident_eq, p.variable.cle, p.adresse) for p in propositions}
        if attendu != fourni:
            raise RegleMetier("Le plan d'adressage a évolué : recalculer l'aperçu avant application.")
        with self._operation_lourde("adressage"):
            n = appliquer_plan(self.ouvrage, propositions, tout_refaire)
        if n or tout_refaire:
            self._change()
        return n

    # ------------------------------------------------------------ moteur d'adressage centralisé
    def plan_adressage(self):
        from . import adressage
        return adressage.calculer(self)

    def appliquer_adressage(self, empreinte, niveaux=("physique", "automate")):
        from . import adressage
        try:
            with self._operation_lourde("adressage"):
                return adressage.appliquer(self, empreinte, tuple(niveaux))
        except adressage.AdressageRefuse as exc:
            raise RegleMetier(str(exc)) from exc

    def valider_affectations(self, niveau, paires):
        """Validation explicite d'affectations par niveau, avec date et auteur. Une affectation sans adresse
        ou en conflit n'est jamais validée."""
        from . import adressage
        paires = [tuple(x) for x in paires]
        if niveau == "physique":
            sans = [c for i, c in paires if not next((p.adresse for p in self.points() if p.ident_eq == i and p.cle == c), "")]
            if sans:
                raise RegleMetier(f"{len(sans)} E/S sans voie : appliquez d'abord l'affectation (ex. {sans[0]}).")
            n = self.valider_es(paires)
        elif niveau == "automate":
            n, refus = self.valider_adresses(paires)
            if refus and not n:
                raise RegleMetier(refus[0] if isinstance(refus[0], str) else str(refus[0]))
        else:
            raise RegleMetier("Les points de télétransmission se valident par leur variable source (niveau automate).")
        adressage.tracer_validation(self, niveau, paires)
        self._change(devalider=False)
        return n

    def ajouter_reservation(self, niveau, cible, motif):
        from . import adressage
        from datetime import datetime
        try:
            cible = adressage.verifier_reservation(niveau, cible)
        except adressage.AdressageRefuse as exc:
            raise RegleMetier(str(exc)) from exc
        if not (motif or "").strip():
            raise RegleMetier("Indiquez le motif de la réservation.")
        if any(r["niveau"] == niveau and r["cible"] == cible for r in self.ouvrage.reservations):
            raise RegleMetier(f"{cible} est déjà réservé.")
        self.ouvrage.reservations.append({"niveau": niveau, "cible": cible, "motif": motif.strip()[:120],
                                          "par": adressage.auteur(), "le": datetime.now().strftime("%Y-%m-%d %H:%M")})
        self._change(devalider=False)

    def retirer_reservation(self, niveau, cible):
        avant = len(self.ouvrage.reservations)
        self.ouvrage.reservations = [r for r in self.ouvrage.reservations if not (r["niveau"] == niveau and r["cible"] == cible)]
        if len(self.ouvrage.reservations) == avant:
            raise RegleMetier("Réservation introuvable.")
        self._change(devalider=False)

    def declarer_protocole(self, declare, decalage=0):
        """Convention « registre = mot %MW + décalage » confirmée par l'automaticien pour cet ouvrage."""
        if int(decalage) not in (0, 1):
            raise RegleMetier("Décalage : 0 ou 1.")
        self.ouvrage.protocole_declare, self.ouvrage.decalage_modbus = bool(declare), int(decalage)
        self._change(devalider=False)

    def declarer_disponibilite(self, verifiee):
        """Projet existant : l'automaticien atteste que l'import couvre toute la mémoire utilisée."""
        self.ouvrage.disponibilite_verifiee = bool(verifiee)
        self._change(devalider=False)

    def exporter_topkapi(self, chemin_zip):
        """Fichier d'import de variables TOPKAPI (.$$t, format relevé sur un projet réel, NON qualifié en 6.3)
        et compte rendu des points exclus. Refusé s'il reste un conflit d'adressage."""
        from . import adressage, formats_topkapi as ft
        plan = adressage.calculer(self)
        if plan.conflits:
            raise RegleMetier(f"Export TOPKAPI refusé : {len(plan.conflits)} conflit(s) d'adressage (ex. {plan.conflits[0][1]}).")
        if not self.ouvrage.protocole_declare:
            raise RegleMetier("Déclarez d'abord la convention protocolaire (registre = mot %MW + décalage) dans "
                              "l'écran Adressage : sans elle, aucune adresse TOPKAPI n'est certaine.")
        variables = {(v.ident_eq, v.cle): v for v in self.variables()}
        points, exclus = [], []
        for a in plan.affectations:
            if a.niveau != "teletransmission":
                continue
            v = variables[(a.ident_eq, a.cle)]
            if not v.adresse:
                exclus.append(f"{a.nom} : variable sans adresse %MW (appliquez puis validez l'adressage).")
                continue
            if v.type_logique in ("BOOL", "EBOOL"):
                code = "0"
            elif v.type_logique == "INT":
                code = "2"
            else:
                exclus.append(f"{a.nom} : {v.type_logique} sur deux mots ; le code de format TOPKAPI (102 ou 105 "
                              "relevés) n'est pas confirmé : point à créer à la main ou après confirmation.")
                continue
            texte = " " + (v.libelle_topkapi or v.information)[:60].replace("\t", " ") + " "
            points.append(ft.PointTopkapi(v.nom, adressage.adresse_topkapi(v.adresse, self.ouvrage.decalage_modbus),
                                          code, texte))
        erreurs = ft.controler(points)
        if erreurs:
            raise RegleMetier("Export TOPKAPI refusé : " + erreurs[0])
        base = self.nom_fichier_propose() or "ouvrage"
        rapport = [f"Export TOPKAPI d'OGIAS — {base}", "",
                   "STATUT : NON QUALIFIÉ. Format .$$t « Version 1 » relevé sur un projet TOPKAPI réel (2008-2018) ;",
                   "à importer d'abord dans une COPIE d'application TOPKAPI 6.3, puis à vérifier point par point.", "",
                   f"Convention déclarée : adresse TOPKAPI = mot %MW + décalage {self.ouvrage.decalage_modbus} ; bit en hexadécimal (mot$bit).",
                   "Codes de format écrits : 0 = bit (TS, TC), 2 = mot 16 bits (INT).",
                   "Dans le projet de référence, les télécommandes étaient des mots entiers (format 0 sur une adresse de mot) :",
                   "les TC d'OGIAS sont des bits ; vérifiez la commande attendue par le programme automate.", "",
                   f"{len(points)} point(s) exporté(s), {len(exclus)} exclu(s) :"] + [f"- {x}" for x in exclus]
        try:                                    # fichier préparé avant l'archive : aucun zip partiel en cas de refus
            table = ft.ecrire_octets(points)
        except ft.FormatTopkapiInvalide as exc:
            raise RegleMetier(f"Export TOPKAPI refusé : {exc}") from exc
        ft.ecrire_archive(chemin_zip, {f"{base}.$$t": table,
                                       "LISEZ-MOI_export_TOPKAPI.txt": "\r\n".join(rapport).encode("utf-8")})
        return self._marquer_exporte((len(points), exclus))

    def manque_adresses(self):
        return any(not v.adresse for v in self.variables())

    # ================================================================== exports
    def recap_export(self):
        variables, points = self.variables(), self.points()
        sans = [p.nom for p in points if not p.adresse and p.raccordement != "Communication"]
        erreurs = sum(1 for a in self.anomalies(variables) if a.niveau == "Erreur")
        return RecapExport(len(variables), len(points), sum(1 for p in points if not p.variable),
                           len(points) - len(sans), sans, erreurs)

    def _marquer_exporte(self, resultat=None):
        """Mémorise qu'un ouvrage neuf a été exporté : il ne relève plus de la propagation en un geste (R6)."""
        if self.ouvrage.mode == "Neuf" and self.ouvrage.deja_exporte is not True:
            self.ouvrage.deja_exporte = True
            self.modifie = True
        return resultat

    def exporter_xsy(self, chemin):
        if self.ouvrage.mode == "Existant":
            raise RegleMetier("Projet existant : produire la table de correspondances Excel. L'import TOPKAPI/SOFTLINK dépend du format et doit être validé séparément.")
        from .modele import TAILLE_MOTS
        variables, points, internes = self.variables(), self.points(), self.variables_internes()
        inconnues = [v.nom for v in variables if v.type_logique not in TAILLE_MOTS]
        inconnues += [p.nom for p in points if p.type_logique not in TAILLE_MOTS]
        inconnues += [x.nom for x in internes if x.type_logique not in TAILLE_MOTS]
        if inconnues:
            raise RegleMetier(f"Export XSY refusé : type de donnée non pris en charge (ex. {inconnues[0]}).")
        from .formats_control_expert import FormatInvalide
        try:
            return self._marquer_exporte(exporter_xsy(chemin, self.ouvrage, variables, points, internes=internes))
        except FormatInvalide as exc:
            raise RegleMetier(f"Export XSY refusé : {exc}") from exc

    def exporter_excel(self, chemin):
        if self.ouvrage.mode == "Existant" and self.ouvrage.table_tt:
            teletransmission.exporter(chemin, self.ouvrage, self.catalogue)
        elif self.ouvrage.mode == "Existant":
            existant.exporter_correspondance(chemin, self.ouvrage, self.catalogue)
        else:
            v = self.variables()
            exporter_table(chemin, self.ouvrage, self.catalogue, v, self.anomalies(v), self.points())
            self._marquer_exporte()

    # ================================================================== bilan
    def bilan(self):
        if self.ouvrage.mode == "Existant":
            an = self.anomalies_existant()
            return {"variables": len(self.ouvrage.existantes), "points": 0,
                    "erreurs": sum(1 for a in an if a.niveau == "Erreur"),
                    "alertes": sum(1 for a in an if a.niveau == "Alerte")}
        v = self.variables()
        an = self.anomalies(v)
        return {"variables": len(v), "points": len(self.points()),
                "erreurs": sum(1 for a in an if a.niveau == "Erreur"),
                "alertes": sum(1 for a in an if a.niveau == "Alerte")}

    # ================================================================== télétransmission (projet existant)
    def _tt(self, fonction, *args, **kw):
        try:
            r = fonction(self.ouvrage, *args, **kw)
        except teletransmission.RegleTT as ex:
            raise RegleMetier(str(ex)) from None
        self._change()
        return r

    def construire_table(self):
        if self.ouvrage.mode != "Existant":
            raise RegleMetier("La table de télétransmission concerne les projets existants.")
        return self._tt(teletransmission.construire, self.catalogue)

    def table(self):
        return teletransmission.vue(self.ouvrage, self.catalogue)

    def candidats(self):
        return teletransmission.candidats(self.ouvrage, self.catalogue)

    def proposer_associations(self):
        return self._tt(teletransmission.proposer_associations, self.catalogue)

    def associer(self, ident_eq, cle, nom, preuves=(), origine="Choix manuel"):
        return self._tt(teletransmission.associer, self.catalogue, ident_eq, cle, nom, preuves, origine)

    def dissocier(self, ident_eq, cle):
        return self._tt(teletransmission.dissocier, ident_eq, cle)

    def valider_fonction(self, ident_eq, cle, valide=True):
        from .referentiel_depot import auteur_par_defaut
        return self._tt(teletransmission.valider_fonction, ident_eq, cle, valide, auteur_par_defaut())

    def confirmables_en_lot(self):
        return teletransmission.confirmables_en_lot(self.ouvrage, self.catalogue)

    def confirmer_en_lot(self):
        """Confirme en un geste les lignes de confiance élevée ; None (ouvrage inchangé) s'il n'y en a pas."""
        from .referentiel_depot import auteur_par_defaut
        if not self.confirmables_en_lot():
            return None
        with self._operation_lourde("rapprochement-lot"):
            return self._tt(teletransmission.confirmer_en_lot, self.catalogue, auteur_par_defaut())

    def annuler_lot(self, id_lot):
        from .referentiel_depot import auteur_par_defaut
        return self._tt(teletransmission.annuler_lot, id_lot, auteur_par_defaut())

    def definir_acces(self, ident_eq, cle, adresse_acquisition=None, protocole=None, verifie=None):
        return self._tt(teletransmission.definir_acces, ident_eq, cle, adresse_acquisition, protocole, verifie)

    def declarer_non_accessible(self, ident_eq, cle, motif):
        return self._tt(teletransmission.declarer_non_accessible, ident_eq, cle, motif)

    def reouvrir(self, ident_eq, cle):
        return self._tt(teletransmission.reouvrir, ident_eq, cle)

    def signal_non_applicable(self, ident_eq, cle):
        return self._tt(teletransmission.non_applicable, self.catalogue, ident_eq, cle)

    def equipements_detectes(self):
        return teletransmission.equipements_detectes(self.ouvrage, self.catalogue)

    def ajouter_detectes(self, detectes):
        n = teletransmission.ajouter_detectes(self.ouvrage, detectes)
        if n:
            self._change()
        return n

    # ================================================================== liste des E/S (projet neuf)
    @staticmethod
    def adresse_module(point, module, voie):
        """Adresse Schneider M340 / M580 d'une voie : %I0.3.5 (ET), %Q, %IW, %QW. `module` = rack.emplacement
        (ou emplacement seul, rack 0). Calcul déterministe à partir de la configuration saisie."""
        module, voie = (module or "").strip(), str(voie if voie is not None else "").strip()
        if not module and not voie:
            return ""
        if not re.fullmatch(r"\d{1,2}(\.\d{1,2})?", module):
            raise RegleMetier("Module : emplacement « 3 » ou rack.emplacement « 0.3 ».")
        if not re.fullmatch(r"\d{1,3}", voie):
            raise RegleMetier("Voie : nombre entier (0, 1, 2…).")
        if "." not in module:
            module = "0." + module
        prefixe = {"ET": "%I", "ST": "%Q", "EA": "%IW", "SA": "%QW"}[point]
        return f"{prefixe}{module}.{int(voie)}"

    def liste_es(self):
        return self.points()

    def definir_es(self, ident_eq, cle, designation=None, type_logique=None, raccordement=None, module=None,
                   voie=None, adresse=None, validee=None, sens=None, note=None):
        """Modifie une E/S de la liste, après contrôle complet (rien n'est écrit si une valeur est refusée).
        Module + voie donnent l'adresse si l'adresse n'est pas saisie. Une E/S validée qui change
        d'adresse, de type ou de raccordement repasse « à valider » (sauf validation dans le même geste)."""
        from .modele import TYPES_POINT, RACCORDEMENTS
        eq = self.ouvrage.equipement(ident_eq)
        p = next((x for x in self.points() if x.ident_eq == ident_eq and x.cle == cle), None)
        if eq is None or p is None:
            raise RegleMetier("E/S introuvable.")
        meta = dict(eq.es_meta.get(cle, {}))
        if type_logique is not None and type_logique not in TYPES_POINT[p.point]:
            raise RegleMetier(f"Type {type_logique} impossible pour une {p.point} ({', '.join(TYPES_POINT[p.point])}).")
        if raccordement is not None and raccordement not in RACCORDEMENTS:
            raise RegleMetier("Raccordement : câblé ou communication.")
        rac = raccordement if raccordement is not None else p.raccordement
        mod = module.strip() if module is not None else p.module
        voi = str(voie).strip() if voie is not None else p.voie
        if adresse is None and (module is not None or voie is not None):
            adresse = self.adresse_module(p.point, mod, voi) if (mod or voi) else ""
        if rac == "Communication":
            adresse, mod, voi = "", "", ""
        change_tech = ((adresse is not None and adresse.strip().upper() != p.adresse.upper())
                       or (type_logique is not None and type_logique != p.type_logique) or rac != p.raccordement)
        if adresse is not None:
            self._verifier_adresse_es(p, adresse)     # format, sens, unicité : refus avant toute écriture
        if designation is not None:
            meta["designation"] = designation.strip()
        if sens is not None:
            meta["sens"] = sens.strip()
        if note is not None:
            if len(note.strip()) > 500:
                raise RegleMetier("Commentaire de l’E/S : 500 caractères maximum.")
            meta["note"] = note.strip()
        if type_logique is not None:
            meta["type"] = type_logique
        meta["raccordement"] = rac
        meta["module"], meta["voie"] = mod, voi
        if validee is not None:
            meta["validee"] = bool(validee)
        elif change_tech:
            meta["validee"] = False
        change_contenu = ((designation is not None and designation.strip() != p.designation)
                          or (sens is not None and sens.strip() != p.sens)
                          or (note is not None and note.strip() != p.note)
                          or (type_logique is not None and type_logique != p.type_logique) or rac != p.raccordement)
        if change_contenu and validee is None:
            meta["contenu_valide"] = False          # le contenu a changé : à revalider à l'étape Liste des E/S
            meta["validee"] = False
        eq.es_meta[cle] = {k: v for k, v in meta.items()
                           if v not in ("", None, False) or k in ("validee", "contenu_valide")}
        if adresse is not None:
            if adresse.strip():
                eq.adresses_es[cle] = adresse.strip().upper()
            else:
                eq.adresses_es.pop(cle, None)
        self._change()

    def definir_analogique(self, ident_eq, cle, params, *, devalider_equipement=True):
        """Enregistre la correspondance linéaire d'une EA/SA, sans inventer le brut du module.

        Pour une mesure en courant, les 2 points instrument de référence sont exprimés en mA.
        Des points en comptes automates sont facultatifs et dépendent du module configuré.
        """
        import math
        eq = self.ouvrage.equipement(ident_eq)
        p = next((x for x in self.points() if x.ident_eq == ident_eq and x.cle == cle), None)
        if eq is None or p is None or p.point not in ('EA', 'SA'):
            raise RegleMetier("Cette configuration est réservée à une E/S analogique EA ou SA.")
        try:
            d: dict[str, Any] = {k: float(params[k]) for k in ('signal_min', 'signal_max', 'phys_min', 'phys_max')}
        except (KeyError, TypeError, ValueError):
            raise RegleMetier('Renseignez les deux points mA et les deux valeurs physiques.')
        if not all(math.isfinite(v) for v in d.values()):
            raise RegleMetier('Une échelle analogique ne peut contenir NaN ou infini.')
        if not (0 <= d['signal_min'] < d['signal_max'] <= 30):
            raise RegleMetier('Points de courant invalides : renseignez par exemple 4 et 20 mA.')
        if d['phys_min'] == d['phys_max']:
            raise RegleMetier('Les valeurs physiques aux deux points doivent être différentes.')
        unite = str(params.get('unite') or '').strip()
        if not unite or len(unite)>24:
            raise RegleMetier('L’unité physique est obligatoire (24 caractères au maximum).')
        d['unite'] = unite
        brut_min = params.get('brut_min', '')
        brut_max = params.get('brut_max', '')
        if (brut_min in ('', None)) != (brut_max in ('', None)):
            raise RegleMetier('Valeurs brutes : renseignez les deux extrémités ou aucune.')
        if brut_min not in ('', None):
            try:
                d['brut_min'], d['brut_max'] = float(brut_min), float(brut_max)
            except (TypeError, ValueError):
                raise RegleMetier('Les valeurs brutes doivent être numériques.')
            if not all(math.isfinite(d[k]) for k in ('brut_min', 'brut_max')) or d['brut_min']==d['brut_max']:
                raise RegleMetier('Les valeurs brutes doivent être finies et distinctes.')
        meta = dict(eq.es_meta.get(cle, {}))
        if meta.get('analogique') != d:
            meta['analogique'] = d
            meta['validee'] = False   # la voie doit être revalidée après changement d'échelle
            meta['contenu_valide'] = False
            eq.es_meta[cle] = meta
            if devalider_equipement:
                eq.valide = False
            self._change()
        return d

    def definir_impulsion(self, ident_eq, cle, params):
        """Poids d'une impulsion ET, front de comptage et unité, fournis par l'automaticien."""
        import math
        eq = self.ouvrage.equipement(ident_eq)
        pt = next((x for x in self.points() if x.ident_eq == ident_eq and x.cle == cle), None)
        if eq is None or pt is None or pt.point != 'ET':
            raise RegleMetier('Le poids d’impulsion s’applique à une entrée TOR présente.')
        if cle != 'ES_IMP':
            raise RegleMetier('La configuration impulsions est réservée au signal de comptage prévu.')
        try:
            poids = float(params.get('poids'))
        except (TypeError, ValueError):
            raise RegleMetier('Poids d’impulsion numérique obligatoire.')
        front = str(params.get('front', '')).strip()
        unite = str(params.get('unite') or '').strip()
        if not math.isfinite(poids) or poids <= 0:
            raise RegleMetier('Le poids d’impulsion doit être strictement positif.')
        if front not in ('Montant', 'Descendant'):
            raise RegleMetier('Choisissez le front de comptage réellement utilisé.')
        if not unite or len(unite) > 24:
            raise RegleMetier('Unité de comptage obligatoire (24 caractères maximum).')
        v = {'poids': poids, 'front': front, 'unite': unite}
        meta = dict(eq.es_meta.get(cle, {}))
        if meta.get('impulsion') != v:
            meta['impulsion'] = v
            meta['validee'] = False
            eq.es_meta[cle] = meta
            eq.valide = False
            self._change()
        return v

    def choisir_option_es(self, ident_eq, option, active):
        eq = self.ouvrage.equipement(ident_eq)
        if eq is None:
            raise RegleMetier('Équipement introuvable.')
        if option not in self.options_equipement(eq):
            raise RegleMetier('Option absente du référentiel de ce type.')
        if active and option not in eq.options:
            eq.options.append(option)
        elif not active and option in eq.options:
            eq.options.remove(option)
        else:
            return
        eq.valide = False
        self._change()

    def choisir_es_catalogue(self, ident_eq, cle, retenu):
        eq = self.ouvrage.equipement(ident_eq)
        if eq is None:
            raise RegleMetier('Équipement introuvable.')
        signal = next((s for s in self.catalogue_equipement(eq).signaux_du_type(eq.type)
                       if s['famille'] == 'ES' and f"ES_{s['code']}" == cle), None)
        if signal is None:
            raise RegleMetier('E/S absente du référentiel de cet équipement.')
        if signal['presence'] == 'Obligatoire' and not retenu:
            raise RegleMetier('Cette E/S est obligatoire : modifiez le référentiel si ce choix est incorrect.')
        if signal['presence'] == 'Option' and retenu and signal.get('option') not in eq.options:
            raise RegleMetier('Activez d’abord l’option associée à cette E/S.')
        est_retenu = any(p.cle == cle and p.ident_eq == ident_eq for p in self.points())
        if est_retenu != bool(retenu):
            self.basculer_signal(eq, signal)
            eq.valide = False
            self._change()

    # ================================================================== cartes d'E/S (modules)
    def ajouter_module(self, rack, position, nature, voies, reference="", libelle=""):
        from .cartes_es import Module, NATURES
        try:
            rack, position, voies = int(rack), int(position), int(voies)
        except (TypeError, ValueError):
            raise RegleMetier("Rack, position et nombre de voies : nombres entiers.")
        if nature not in NATURES:
            raise RegleMetier("Nature du module : ET, ST, EA ou SA.")
        if not (0 <= rack <= 15 and 0 <= position <= 31 and 1 <= voies <= 128):
            raise RegleMetier("Rack 0 à 15, position 0 à 31, 1 à 128 voies.")
        if any(m.rack == rack and m.position == position for m in self.ouvrage.modules):
            raise RegleMetier(f"Un module est déjà déclaré en {rack}.{position}.")
        m = Module(rack, position, nature, voies, reference.strip(), libelle.strip())
        self.ouvrage.modules.append(m)
        self.ouvrage.modules.sort(key=lambda x: (x.rack, x.position))
        self.ouvrage.materiel_valide = False
        self._change(devalider=False)
        return m.cle

    def modifier_module(self, cle, rack, position, nature, voies, reference="", libelle=""):
        """Modifie une carte déclarée. Les E/S placées suivent un changement de rack ou de position (adresses
        recalculées), sauf si l'une d'elles est validée : il faut d'abord la dévalider ou libérer les voies."""
        from .cartes_es import NATURES, place
        m = next((x for x in self.ouvrage.modules if x.cle == cle), None)
        if m is None:
            raise RegleMetier(f"Carte {cle} introuvable.")
        try:
            rack, position, voies = int(rack), int(position), int(voies)
        except (TypeError, ValueError):
            raise RegleMetier("Rack, position et nombre de voies : nombres entiers.")
        if nature not in NATURES:
            raise RegleMetier("Nature de la carte : ET, ST, EA ou SA.")
        if not (0 <= rack <= 15 and 0 <= position <= 31 and 1 <= voies <= 128):
            raise RegleMetier("Rack 0 à 15, position 0 à 31, 1 à 128 voies.")
        nouvelle = f"{rack}.{position}"
        if nouvelle != cle and any(x.cle == nouvelle for x in self.ouvrage.modules):
            raise RegleMetier(f"Une carte est déjà déclarée en {nouvelle}.")
        places = [p for p in self.points() if place(p)[0] == cle]
        if places and nature != m.nature:
            raise RegleMetier(f"{len(places)} E/S sont placées sur cette carte : la nature ne peut pas changer "
                              "(libérez d'abord les voies).")
        if places and voies <= max(place(p)[1] for p in places):
            raise RegleMetier(f"La voie {max(place(p)[1] for p in places)} est occupée : au moins "
                              f"{max(place(p)[1] for p in places) + 1} voies sont nécessaires.")
        if nouvelle != cle and any(p.validee for p in places):
            raise RegleMetier("Des E/S validées sont placées sur cette carte : dévalidez-les avant de la déplacer, "
                              "pour ne pas changer une adresse validée en silence.")
        for p in places if nouvelle != cle else []:
            eq = self.ouvrage.equipement(p.ident_eq)
            meta = dict(eq.es_meta.get(p.cle, {}))
            voie = place(p)[1]
            meta["module"], meta["voie"] = nouvelle, str(voie)
            eq.es_meta[p.cle] = meta
            eq.adresses_es[p.cle] = self.adresse_module(p.point, nouvelle, voie)
        m.rack, m.position, m.nature, m.voies = rack, position, nature, voies
        m.reference, m.libelle = reference.strip(), libelle.strip()
        self.ouvrage.modules.sort(key=lambda x: (x.rack, x.position))
        self.ouvrage.materiel_valide = False
        self._change(devalider=False)
        return nouvelle

    def supprimer_module(self, cle):
        from .cartes_es import cle_module
        utilises = [p.nom for p in self.points() if cle_module(p.module) == cle]
        if utilises:
            raise RegleMetier(f"{len(utilises)} E/S sont placées sur le module {cle} (ex. {utilises[0]}) : "
                              "retirez-les d'abord (« Libérer les voies proposées »).")
        self.ouvrage.modules = [m for m in self.ouvrage.modules if m.cle != cle]
        self.ouvrage.materiel_valide = False
        self._change(devalider=False)

    def definir_reserve(self, taux):
        taux = float(taux)
        if not 0 <= taux < 1:
            raise RegleMetier("Réserve minimale : entre 0 et 99 %.")
        self.ouvrage.reserve_min = taux
        self.ouvrage.materiel_valide = False
        self._change(devalider=False)

    def apercu_implantation(self, rapport=None):
        """Implantation proposée, sans rien écrire : (affectations, manquantes, dépassements).
        `rapport` (dict) reçoit le motif de chaque affectation et les groupes de secours non séparés."""
        from .cartes_es import implanter
        rang = {e.ident: i for i, e in enumerate(self.equipements_tries())}
        return implanter(self.points(), self.ouvrage.modules, [u.code for u in self.ouvrage.unites], rang,
                         self.ouvrage.reserve_min, groupes=self.groupes_secours_actifs(), rapport=rapport)

    # ------------------------------------------------------------------ groupes de secours (B4) et rack (B3)
    def groupes_secours_actifs(self):
        """Groupes confirmés réellement appliqués : séparation active, membres encore présents (au moins 2)."""
        o = self.ouvrage
        if not o.separation_secours:
            return []
        presents = {e.ident for e in o.equipements}
        return [g for g in ([i for i in grp if i in presents] for grp in o.groupes_secours) if len(g) > 1]

    def groupes_secours_proposes(self):
        """Groupes PROBABLES (équipements de même type dans le même sous-ensemble), non encore confirmés ni
        refusés. Proposition seulement : rien n'est appliqué sans confirmation (B4)."""
        o = self.ouvrage
        confirmes = {i for g in o.groupes_secours for i in g}
        refuses = {tuple(sorted(g)) for g in o.groupes_secours_refuses}
        par_cle: dict[tuple, list] = {}
        for e in self.equipements_tries():
            if e.ident not in confirmes:
                par_cle.setdefault((e.type, e.sous_ensemble), []).append(e)
        sortie = []
        for (typ, se), eqs in par_cle.items():
            if len(eqs) > 1 and tuple(sorted(e.ident for e in eqs)) not in refuses:
                sortie.append({"type": typ, "sous_ensemble": se, "designation": self.catalogue.designation(typ),
                               "membres": [{"ident": e.ident, "repere": o.repere(e)} for e in eqs]})
        return sortie

    def _verifier_groupe(self, idents):
        idents = list(dict.fromkeys(str(i) for i in idents))
        if len(idents) < 2:
            raise RegleMetier("Un groupe de secours réunit au moins deux équipements.")
        connus = {e.ident for e in self.ouvrage.equipements}
        inconnus = [i for i in idents if i not in connus]
        if inconnus:
            raise RegleMetier(f"Équipement inconnu dans le groupe de secours : {inconnus[0]}.")
        return idents

    def confirmer_groupe_secours(self, idents):
        """Confirme un groupe (proposé ou composé par l'automaticien). Un équipement n'appartient qu'à un groupe :
        il quitte son ancien groupe. Les voies déjà placées ne bougent pas (B7) ; le contrôle signale les cartes
        partagées."""
        idents = self._verifier_groupe(idents)
        o = self.ouvrage
        restes = [[i for i in g if i not in idents] for g in o.groupes_secours]
        o.groupes_secours = [g for g in restes if len(g) > 1] + [idents]
        cle = sorted(idents)
        o.groupes_secours_refuses = [g for g in o.groupes_secours_refuses if sorted(g) != cle]
        self._change(devalider=False)
        return idents

    def retirer_groupe_secours(self, idents):
        """Supprime le groupe confirmé qui contient exactement ces équipements."""
        cle = sorted(str(i) for i in idents)
        avant = len(self.ouvrage.groupes_secours)
        self.ouvrage.groupes_secours = [g for g in self.ouvrage.groupes_secours if sorted(g) != cle]
        if len(self.ouvrage.groupes_secours) == avant:
            raise RegleMetier("Ce groupe de secours n'est pas confirmé.")
        self._change(devalider=False)

    def refuser_groupe_secours(self, idents):
        """Écarte une proposition : elle n'est plus proposée."""
        idents = self._verifier_groupe(idents)
        cle = sorted(idents)
        if cle not in [sorted(g) for g in self.ouvrage.groupes_secours_refuses]:
            self.ouvrage.groupes_secours_refuses.append(cle)
            self._change(devalider=False)

    def regles_repartition(self, separation_secours=None, emplacements_libres_rack=None):
        """Lit ou modifie les règles de répartition de l'ouvrage (B3, B4) ; renvoie leur état."""
        o, change = self.ouvrage, False
        if separation_secours is not None and bool(separation_secours) != o.separation_secours:
            o.separation_secours, change = bool(separation_secours), True
        if emplacements_libres_rack is not None:
            n = int(emplacements_libres_rack)
            if not 0 <= n <= 6:
                raise RegleMetier("Emplacements libres par rack : de 0 à 6.")
            if n != o.emplacements_libres_rack:
                o.emplacements_libres_rack, change = n, True
        if change:
            self._change(devalider=False)
        return {"separation_secours": o.separation_secours, "emplacements_libres_rack": o.emplacements_libres_rack,
                "reserve_min": o.reserve_min, "groupes_secours": [
                    [{"ident": i, "repere": o.repere(o.equipement(i))} for i in g]
                    for g in self.groupes_secours_actifs()] if o.separation_secours else [],
                "groupes_secours_confirmes": len(o.groupes_secours),
                "groupes_secours_proposes": self.groupes_secours_proposes()}

    def _cartes_minimales_secours(self, points):
        """{nature: n} : cartes nécessaires pour séparer les membres de chaque groupe de secours actif."""
        minimum: dict[str, int] = {}
        for g in self.groupes_secours_actifs():
            for nature in {p.point for p in points}:
                n = len({p.ident_eq for p in points if p.point == nature and p.ident_eq in g})
                minimum[nature] = max(minimum.get(nature, 0), n)
        return minimum

    def implanter_es(self):
        """Écrit l'implantation proposée (R9) : module + voie des E/S câblées sans place, NON validées.
        Les E/S déjà placées ou validées ne bougent pas."""
        if not self.ouvrage.modules:
            raise RegleMetier("Déclarez d'abord les modules d'E/S (rack, position, nature, voies).")
        affectations, manquantes, depassements = self.apercu_implantation()
        with self._operation_lourde("implantation"):
            self._implanter(affectations)
        return len(affectations), manquantes, depassements

    def _implanter(self, affectations):
        for p, cle, voie in affectations:
            eq = self.ouvrage.equipement(p.ident_eq)
            meta = dict(eq.es_meta.get(p.cle, {}))
            meta["module"], meta["voie"], meta["validee"] = cle, str(voie), False
            eq.es_meta[p.cle] = meta
            eq.adresses_es[p.cle] = self.adresse_module(p.point, cle, voie)
        if affectations:
            self._change(devalider=False)

    def liberer_voies_proposees(self):
        """Retire module, voie et adresse des E/S placées mais NON validées (pour refaire l'implantation)."""
        n = 0
        for p in self.points():
            if p.validee or p.raccordement == "Communication" or not (p.module or p.adresse):
                continue
            eq = self.ouvrage.equipement(p.ident_eq)
            meta = dict(eq.es_meta.get(p.cle, {}))
            meta.pop("module", None), meta.pop("voie", None)
            eq.es_meta[p.cle] = meta
            eq.adresses_es.pop(p.cle, None)
            n += 1
        if n:
            self._change(devalider=False)
        return n

    def bilan_modules(self):
        from .cartes_es import bilan_modules
        return bilan_modules(self.points(), self.ouvrage.modules, self.ouvrage.reserve_min)

    def definir_config_materiel(self, alimentation=None, processeur=None, communication=None, cartes=None):
        """Choix matériel M340 / M580 de l'automaticien, contrôlé contre le catalogue (référence inconnue refusée).
        Une valeur None laisse le choix actuel ; une chaîne vide le retire. Le matériel repasse « à valider »."""
        from . import materiel
        try:
            plat = materiel.plateforme_materiel(self.ouvrage.automate)[0]
            cat = materiel.catalogue()
        except materiel.CatalogueMaterielErreur as exc:
            raise RegleMetier(str(exc)) from exc
        if plat not in cat["plateformes"]:
            raise RegleMetier(f"Choix d'alimentation, de processeur et de communication réservés aux M340 / M580 "
                              f"(plateforme {plat}).")
        actuel = dict(self.ouvrage.materiel_config or {})
        demande = {k: v for k, v in (("alimentation", alimentation), ("processeur", processeur),
                                     ("communication", communication), ("cartes", cartes)) if v is not None}
        nouveau = {**actuel, **demande}
        retenu = materiel.config_materiel(cat, plat, "", nouveau)
        for cle in ("alimentation", "processeur"):
            if str(demande.get(cle) or "").strip() and not retenu[cle]:
                raise RegleMetier(f"Référence inconnue du catalogue {plat} : {demande[cle]}.")
        if "communication" in demande and len(retenu["communication"]) != len([c for c in demande["communication"] if c]):
            raise RegleMetier(f"Module de communication inconnu du catalogue {plat}.")
        if "cartes" in demande and len(retenu["cartes"]) != len([r for r in demande["cartes"].values() if r]):
            raise RegleMetier("Carte inconnue ou de mauvaise nature.")
        self.ouvrage.materiel_config = {"alimentation": retenu["alimentation"], "processeur": retenu["processeur"],
                                        "communication": retenu["communication"], "cartes": retenu["cartes"]}
        self.ouvrage.materiel_valide = False
        self._change(devalider=False)
        return self.ouvrage.materiel_config

    def nomenclature_materiel(self):
        """Nomenclature de commande du matériel retenu (M340 / M580) ; [] sans racks retenus."""
        from . import materiel
        if not self.ouvrage.racks or any(r.get("nim") for r in self.ouvrage.racks):
            return []
        return materiel.nomenclature(self.ouvrage.racks, self.ouvrage.modules)

    def exporter_nomenclature(self, chemin):
        from .export_xlsx import ecrire_xlsx
        lignes = self.nomenclature_materiel()
        if not lignes:
            raise RegleMetier("Aucun matériel retenu : calculez et appliquez d'abord le matériel.")
        o = self.ouvrage
        ecrire_xlsx(chemin, [("Nomenclature", ["Référence", "Désignation", "Quantité", "Rôle"],
                              [[x["reference"], x["designation"], x["quantite"], x["role"]] for x in lignes],
                              [26, 60, 10, 26]),
                             ("Ouvrage", ["Champ", "Valeur"], [["Ouvrage", o.prefixe()], ["Libellé", o.libelle],
                                                               ["Automate", o.automate], ["Révision", o.revision],
                                                               ["Matériel validé", "oui" if o.materiel_valide else "non"],
                                                               ["Remarque", "Bilan de consommation à vérifier ; "
                                                                "références à confirmer à la commande."]], [24, 60])])
        return chemin

    def exporter_cartes_es(self, chemin):
        from .export_cartes_es import exporter
        return self._marquer_exporte(exporter(chemin, self.ouvrage, self.points()))

    def _verifier_adresse_es(self, p, adresse):
        a = (adresse or "").strip().upper()
        if not a:
            return
        if not RE_ADRESSE_PHYSIQUE.fullmatch(a):
            raise RegleMetier("Adresse physique : format %I…, %Q…, %IW… ou %QW….")
        attendu = {"ET": "%I", "ST": "%Q", "EA": "%IW", "SA": "%QW"}[p.point]
        if not a.startswith(attendu) or (p.point in ("ET", "ST") and a.startswith(attendu + "W")):
            raise RegleMetier(f"Pour une {p.point}, l'adresse commence par {attendu}.")
        for autre in self.points():
            if (autre.ident_eq, autre.cle) != (p.ident_eq, p.cle) and autre.adresse.upper() == a:
                raise RegleMetier(f"Adresse {a} déjà utilisée par {autre.nom}.")

    def ajouter_es(self, ident_eq, point, code, designation, type_logique=None):
        """E/S supplémentaire propre à l'équipement (famille ES). Renvoie sa clé."""
        from .modele import TYPES_POINT
        eq = self.ouvrage.equipement(ident_eq)
        if eq is None:
            raise RegleMetier("Équipement introuvable.")
        if point not in TYPES_POINT:
            raise RegleMetier("Point : ET, ST, EA ou SA.")
        code = (code or "").strip().upper()
        if not re.fullmatch(r"[A-Z0-9]+(_[A-Z0-9]+)*", code):
            raise RegleMetier("Code de l'E/S : lettres majuscules et chiffres, « _ » permis (ex. FDC_OUV).")
        if not (designation or "").strip():
            raise RegleMetier("Désignation obligatoire.")
        cle = f"ES_{code}"
        nom = f"{point}_{self.ouvrage.repere_nom(eq)}_{code}"
        if any(p.nom == nom for p in self.points()) or any(f"{a.famille}_{a.code}" == cle for a in eq.ajouts):
            raise RegleMetier(f"L'E/S {nom} existe déjà pour cet équipement.")
        tl = type_logique or TYPES_POINT[point][0]
        if tl not in TYPES_POINT[point]:
            raise RegleMetier(f"Type logique {tl} incompatible avec une {point}.")
        eq.ajouts.append(SignalPropre(designation.strip(), "ES", code, tl, "", point))
        eq.valide = False
        if cle in eq.exclus:
            eq.exclus.remove(cle)
        self._change()
        return cle

    def retirer_es(self, ident_eq, cle):
        """Retire une E/S de la liste : supprime une E/S ajoutée, ou écarte une E/S du référentiel (réversible :
        ses réglages sont conservés). Une E/S portée directement par un signal se retire avec ce signal."""
        eq = self.ouvrage.equipement(ident_eq)
        if eq is None:
            raise RegleMetier("Équipement introuvable.")
        i = next((k for k, a in enumerate(eq.ajouts) if f"{a.famille}_{a.code}" == cle), None)
        if i is not None:
            eq.ajouts.pop(i)
            eq.es_meta.pop(cle, None)
            eq.adresses_es.pop(cle, None)
        elif cle.startswith("ES_"):
            if cle not in eq.exclus:
                eq.exclus.append(cle)
        else:
            raise RegleMetier(f"Cette E/S est portée par le signal {cle} : le retirer dans la fiche de l'équipement.")
        eq.valide = False
        self._change()

    def valider_es(self, paires, valide=True):
        n = 0
        points = {(p.ident_eq, p.cle) for p in self.points()}
        for ident, cle in paires:
            eq = self.ouvrage.equipement(ident)
            if eq is None or (ident, cle) not in points:
                continue
            meta = eq.es_meta.setdefault(cle, {})
            if bool(meta.get("validee")) != valide:
                meta["validee"] = valide
                n += 1
                from .adressage import tracer_validation
                tracer_validation(self, "physique", [(ident, cle)], valide)
        if n:
            self._change()
        return n

    def valider_contenu_es(self, paires, valide=True):
        """Étape Liste des E/S : l'automaticien atteste le contenu (nature, sens, désignation) des E/S.
        Dévalider le contenu d'une E/S retire aussi la validation de sa voie."""
        n = 0
        points = {(p.ident_eq, p.cle) for p in self.points()}
        for ident, cle in paires:
            eq = self.ouvrage.equipement(ident)
            if eq is None or (ident, cle) not in points:
                continue
            meta = eq.es_meta.setdefault(cle, {})
            actuel = bool(meta.get("contenu_valide") or meta.get("validee"))
            if actuel != bool(valide):
                meta["contenu_valide"] = bool(valide)
                if not valide:
                    meta["validee"] = False
                n += 1
        if n:
            self._change()
        return n

    # ------------------------------------------------------------------ matériel (étape 3)
    def proposer_materiel(self, profil=None):
        """Proposition de racks et cartes depuis les E/S (rien n'est écrit). Exige des E/S au contenu validé."""
        from .materiel import proposer, CatalogueMaterielErreur
        pts = self.points()
        a_valider = [p for p in pts if not p.contenu_valide]
        if a_valider:
            raise RegleMetier(f"{len(a_valider)} E/S n'ont pas leur contenu validé (ex. {a_valider[0].nom}) : "
                              "validez la liste des E/S avant de calculer le matériel.")
        try:
            cables = [p for p in pts if p.raccordement != "Communication"]
            return proposer(pts, self.ouvrage.automate, profil if profil is not None else self.ouvrage.profil_cartes,
                            self.ouvrage.reserve_min, min_cartes=self._cartes_minimales_secours(cables),
                            emplacements_libres=self.ouvrage.emplacements_libres_rack,
                            config=self.ouvrage.materiel_config)
        except CatalogueMaterielErreur as exc:
            raise RegleMetier(str(exc)) from exc

    def appliquer_materiel(self, profil=None):
        """Remplace racks et cartes par la proposition. Refusé si des E/S sont déjà placées sur des voies
        (libérer d'abord les voies proposées ; une E/S validée sur sa voie ne bouge jamais en silence)."""
        from .cartes_es import Module
        prop = self.proposer_materiel(profil)
        if not prop.applicable:
            if prop.plateforme == "STB":
                raise RegleMetier("Proposition indicative pour un îlot Advantys STB : elle ne peut pas encore être "
                                  "appliquée (correspondance des voies avec l'automate maître à établir).")
            raise RegleMetier("Proposition indicative pour un poste SOFREL S4W : elle ne peut pas encore être appliquée "
                              "(format des voies S4W-Tools à établir).")
        places = [p for p in self.points() if p.module or p.adresse]
        if places:
            valides = [p for p in places if p.validee]
            raise RegleMetier(
                f"{len(places)} E/S occupent déjà des voies" + (f", dont {len(valides)} validée(s)" if valides else "")
                + " : libérez les voies proposées (et dévalidez les autres) avant de remplacer le matériel.")
        with self._operation_lourde("materiel"):
            self.ouvrage.profil_cartes = prop.profil
            self.ouvrage.racks = [dict(r) for r in prop.racks]
            self.ouvrage.modules = [Module(m["rack"], m["position"], m["nature"], m["voies"], m["reference"])
                                    for m in prop.modules]
            self.ouvrage.materiel_valide = False
            self._change(devalider=False)
        return prop

    def valider_materiel(self, valide=True):
        if valide:
            if not self.ouvrage.modules:
                raise RegleMetier("Aucune carte : calculez ou déclarez d'abord le matériel.")
            _, manquantes, _ = self.apercu_implantation()
            if manquantes:
                detail = ", ".join(f"{n} {k}" for k, n in manquantes.items())
                raise RegleMetier(f"Capacité insuffisante ({detail} sans voie possible) : ajoutez des cartes.")
        self.ouvrage.materiel_valide = bool(valide)
        self._change(devalider=False)

    def bilan_es(self):
        from collections import Counter
        pts = self.points()
        cables = [p for p in pts if p.raccordement != "Communication"]
        return {"total": len(pts), "par_point": Counter(p.point for p in cables),
                "communication": len(pts) - len(cables), "sans_adresse": sum(1 for p in cables if not p.adresse),
                "non_validees": sum(1 for p in pts if not p.validee),
                "contenu_non_valide": sum(1 for p in pts if not p.contenu_valide),
                "voies_non_validees": sum(1 for p in cables if not p.validee)}

    def exporter_liste_es(self, chemin):
        from .export_liste_es import exporter_liste_es
        return self._marquer_exporte(exporter_liste_es(chemin, self.ouvrage, self.points()))

    def html_liste_es(self):
        from .export_liste_es import html_liste_es
        return html_liste_es(self.ouvrage, self.points())

    def exporter_xsy_es(self, chemin):
        """XSY des E/S câblées adressées + voies de réserve des cartes (format de l'export Control Expert)."""
        from .export_xsy import exporter_xsy
        from .formats_control_expert import FormatInvalide
        try:
            return self._marquer_exporte(exporter_xsy(chemin, self.ouvrage, [], self.points(), avec_echange=False))
        except FormatInvalide as exc:
            raise RegleMetier(f"Export XSY refusé : {exc}") from exc

    def exporter_txt_es(self, chemin):
        """Même contenu en texte tabulé, comme l'export texte des variables de Control Expert."""
        from .export_xsy import exporter_txt
        from .formats_control_expert import FormatInvalide
        try:
            return self._marquer_exporte(exporter_txt(chemin, self.ouvrage, [], self.points(), avec_echange=False))
        except FormatInvalide as exc:
            raise RegleMetier(f"Export TXT refusé : {exc}") from exc

