"""Écran « Variables » : table d'échange générée, adresses, contrôles et exports."""

import os
import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QComboBox, QCheckBox, QSplitter, QToolButton, QMenu,
                               QFileDialog)

from genvar import chemins
from genvar.catalogue import FAMILLES
from genvar.session import RegleMetier

from . import style
from .composants import Page, Carte, Indicateur, Segment, bouton, avertir, informer, confirmer, champ_recherche
from .dialogues import DialogueAdresses, DialoguePlan, DialogueRecap, _plage
from .tableaux import Tableau, Colonne, cle_tri_adresse, ROLE_OBJET

TOUS = "__tous__"
ORDRE_GRAVITE = {"Erreur": 0, "Alerte": 1}


def _cite(message, v):
    """Le message de contrôle cite-t-il la variable ou sa variable d'E/S (nom entier, pas un préfixe) ?"""
    return any(nom and re.search(rf"(?<![A-Z0-9_]){re.escape(nom)}(?![A-Z0-9_])", message) for nom in (v.nom, v.nom_es))


class VueVariables(Page):
    modifie = Signal()
    message = Signal(str)          # texte pour la barre d'état
    export_demande = Signal(str)  # tous les exports passent par l'écran contrôlé

    def __init__(self, session, parent=None):
        super().__init__("Variables", "Table d'échange de l'ouvrage : noms, commentaires, adresses et contrôles", parent)
        self.s = session
        self.variables, self.anomalies, self.etats = [], [], {}
        self._a_jour = False

        # ---------------------------------------------------------- actions de page
        self.b_attribuer = bouton("Attribuer les adresses…", self.attribuer, primaire=True, icone="memoire",
                                  infobulle="Donne une adresse aux variables qui n'en ont pas. Les adresses existantes ne bougent pas.")
        self.b_export = QToolButton()
        self.b_export.setObjectName("bouton")
        self.b_export.setText("Exporter")
        self.b_export.setIcon(style.icone("export", style.SECONDAIRE, 16))
        self.b_export.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.b_export.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.b_export)
        self.a_xsy = QAction("Fichier XSY pour Control Expert…", self)
        self.a_xsy.triggered.connect(lambda: self.export_demande.emit('xsy'))
        self.a_xlsx = QAction("Table d'échange Excel…", self)
        self.a_xlsx.triggered.connect(lambda: self.export_demande.emit('xlsx'))
        menu.addAction(self.a_xsy)
        menu.addAction(self.a_xlsx)
        self.b_export.setMenu(menu)
        plus = QToolButton()
        plus.setObjectName("bouton")
        plus.setText("Plus")
        plus.setToolTip("Modifier les adresses d'une variable, réattribuer toute la table")
        plus.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        m2 = QMenu(plus)
        m2.addAction("Propriétés de la variable…", self.modifier_adresses)
        m2.addAction("Valider les adresses sélectionnées", self.valider_selection)
        m2.addAction("Valider toutes les adresses affichées", self.valider_affichees)
        m2.addAction("Repasser la sélection en « proposée »", self.devalider_selection)
        m2.addSeparator()
        m2.addAction("Réattribuer toutes les adresses…", self.reattribuer)
        plus.setMenu(m2)
        for w in (plus, self.b_export, self.b_attribuer):
            self.entete.droite.addWidget(w)

        # ---------------------------------------------------------- bandeau mode existant
        self.bandeau = QLabel("Projet existant : les variables et adresses réelles viennent du XSY de l'automate. "
                              "Consultez l'écran « Projet existant » pour identifier les informations "
                              "et préparer leur intégration TOPKAPI ; aucune adresse n'est réattribuée.")
        self.bandeau.setObjectName("bandeau")
        self.bandeau.setWordWrap(True)
        self.disposition.addWidget(self.bandeau)

        # ---------------------------------------------------------- indicateurs
        ligne = QHBoxLayout()
        ligne.setSpacing(10)
        self.i_var = Indicateur("variables d'échange")
        self.i_es = Indicateur("E/S automate")
        self.i_sans = Indicateur("sans adresse")
        self.i_err = Indicateur("autres erreurs")
        self.i_err.setToolTip("Erreurs de contrôle hors « variable sans adresse » (qui se règle avec « Attribuer les adresses »).")
        self.i_al = Indicateur("alertes")
        for i in (self.i_var, self.i_es, self.i_sans, self.i_err, self.i_al):
            ligne.addWidget(i)
        ligne.addStretch(1)
        self.disposition.addLayout(ligne)

        # ---------------------------------------------------------- table des variables
        separateur = QSplitter(Qt.Orientation.Vertical)
        separateur.setChildrenCollapsible(False)
        c_var = Carte("Variables d'échange")
        self.compte = QLabel("")
        self.compte.setObjectName("legende")
        c_var.ajouter_action(self.compte)
        filtres = QHBoxLayout()
        self.recherche = champ_recherche("Rechercher un nom, un commentaire, une adresse…")
        self.f_famille = QComboBox()
        self.f_famille.addItem("Toutes", TOUS)
        for f in FAMILLES:
            self.f_famille.addItem(f, f)
        self.f_eq = QComboBox()
        self.f_eq.setMinimumWidth(170)
        self.f_eq.setToolTip("Afficher les variables d'un seul équipement")
        self.f_se = QComboBox()
        self.f_se.setMinimumWidth(160)
        self.f_anomalie = QCheckBox("Avec anomalie")
        self.f_sans = QCheckBox("Sans adresse")
        filtres.addWidget(self.recherche, 1)
        filtres.addWidget(QLabel("Famille"))
        filtres.addWidget(self.f_famille)
        filtres.addWidget(QLabel("Sous-ensemble"))
        filtres.addWidget(self.f_se)
        filtres.addWidget(QLabel("Équipement"))
        filtres.addWidget(self.f_eq)
        filtres.addSpacing(8)
        filtres.addWidget(self.f_anomalie)
        filtres.addWidget(self.f_sans)
        c_var.disposition.addLayout(filtres)

        a = Qt.AlignmentFlag.AlignCenter
        self.t = Tableau([
            Colonne("etat", "", lambda v: "", 28, icone=lambda v: style.icone_gravite(self._etat(v)),
                    tri=lambda v: ORDRE_GRAVITE.get(self._etat(v), 2),
                    infobulle=lambda v: self._infobulle(v)),
            Colonne("fam", "Famille", lambda v: v.famille, 60, alignement=a),
            Colonne("nom", "Nom de variable", lambda v: v.nom, 230),
            Colonne("com", "Commentaire", lambda v: v.commentaire, 300, etirable=True),
            Colonne("type", "Type", lambda v: v.type_logique, 60, alignement=a),
            Colonne("unite", "Unité", lambda v: v.unite, 55, alignement=a, visible=False),
            Colonne("val", "Validée", lambda v: "✓" if v.adresse_validee else ("proposée" if v.adresse else ""), 72,
                    alignement=a, infobulle=lambda v: "Adresse validée par l'automaticien" if v.adresse_validee
                    else "Adresse proposée par le calcul : à valider" if v.adresse else "Sans adresse"),
            Colonne("adr", "Adresse", lambda v: _plage(v.adresse, v.type_logique) if v.adresse else "", 115,
                    tri=lambda v: cle_tri_adresse(v.adresse) or "~"),
            Colonne("mb", "Registre Modbus", lambda v: self.s.registre_modbus(v.adresse) if v.adresse else "", 100,
                    alignement=a, tri=lambda v: cle_tri_adresse(v.adresse) or "~", visible=False),
            Colonne("es", "E/S", lambda v: v.es if v.es != "Interne" else "", 45, alignement=a, visible=False),
            Colonne("nom_es", "Variable d'E/S", lambda v: v.nom_es, 230, visible=False),
            Colonne("adr_es", "Adresse E/S", lambda v: v.adresse_es, 100, tri=lambda v: cle_tri_adresse(v.adresse_es) or "~", visible=False),
            Colonne("alarme", "Alarme", lambda v: "Oui" if v.alarme else "", 60, alignement=a, visible=False),
            Colonne("repere", "Repère", lambda v: v.repere, 140, visible=False),
            Colonne("origine", "Origine", lambda v: v.origine, 130),
            Colonne("logique", "⚙", lambda v: "⚙" if v.logique else "", 32, alignement=a,
                    infobulle=lambda v: ("Logique automate à programmer : " + v.logique) if v.logique else None),
            Colonne("topkapi", "Libellé Topkapi", lambda v: v.libelle_topkapi, 220, visible=False),
        ], "variables_v1")
        self.t.modele.couleur = lambda v: style.ALARME if v.alarme else (style.PROPRE if v.origine != "Catalogue" else None)
        self.t.modele.italique = lambda v: not v.adresse
        self.t.texte_vide = ("Aucune variable.\nAjouter des équipements dans la fiche ouvrage : "
                             "leurs signaux génèrent la table d'échange.")
        self.t.objet_active.connect(lambda _: self.modifier_adresses())
        self.t.selection_changee.connect(self._maj_detail)
        c_var.ajouter(self.t, 1)
        self.detail = QLabel("Sélectionner une variable pour consulter son origine, ses E/S et ses adresses.")
        self.detail.setObjectName("legende")
        self.detail.setWordWrap(True)
        self.detail.setTextFormat(Qt.TextFormat.PlainText)
        c_var.ajouter(self.detail)
        legende = QLabel(f"<span style='color:{style.ALARME}'>■</span> alarme &nbsp; "
                         f"<span style='color:{style.PROPRE}'>■</span> signal propre ou issu d'une règle &nbsp; "
                         "<i>italique</i> : sans adresse &nbsp; · &nbsp; ⚙ : logique automate à programmer &nbsp; · &nbsp; "
                         "<b>double-clic : fiche de la variable</b> (adresses, commentaire, validation)")
        legende.setObjectName("legende")
        c_var.ajouter(legende)
        separateur.addWidget(c_var)

        # ---------------------------------------------------------- contrôles
        c_ctl = Carte("Contrôles")
        self.niveau = Segment([("Tous", "Tous"), ("Erreur", "Erreurs"), ("Alerte", "Alertes")])
        self.niveau.definir("Tous")
        c_ctl.ajouter_action(self.niveau)
        self.t_ctl = Tableau([
            Colonne("niv", "Niveau", lambda x: x.niveau, 90, icone=lambda x: style.icone_gravite(x.niveau),
                    tri=lambda x: ORDRE_GRAVITE.get(x.niveau, 2)),
            Colonne("rep", "Repère", lambda x: x.repere, 150),
            Colonne("msg", "Message", lambda x: x.message, 600, etirable=True),
        ], "variables_controles")
        self.t_ctl.objet_active.connect(self._aller_a)
        self.t_ctl.setToolTip("Double-clic : afficher la variable concernée")
        self.t_ctl.texte_vide = "Aucune anomalie sur la table d'échange." 
        c_ctl.ajouter(self.t_ctl, 1)
        separateur.addWidget(c_ctl)
        separateur.setStretchFactor(0, 3)
        separateur.setStretchFactor(1, 1)
        separateur.setSizes([520, 170])
        self.disposition.addWidget(separateur, 1)

        self.recherche.textChanged.connect(self._filtrer)
        for w in (self.f_famille, self.f_se, self.f_eq):
            w.currentIndexChanged.connect(self._filtrer)
        for w in (self.f_anomalie, self.f_sans):
            w.toggled.connect(self._filtrer)
        self.niveau.change.connect(self._filtrer_controles)

    # ============================================================== données
    def invalider(self):
        """L'ouvrage a changé : la table sera recalculée au prochain affichage."""
        self._a_jour = False
        if self.isVisible():
            self.rafraichir()

    def showEvent(self, e):
        super().showEvent(e)
        if not self._a_jour:
            self.rafraichir()

    def rafraichir(self):
        o = self.s.ouvrage
        existant = o.mode == "Existant"
        self.bandeau.setVisible(existant)
        for w in (self.b_attribuer, self.b_export):
            w.setEnabled(not existant)
        if existant:
            self.variables, self.anomalies, points = [], [], []
        else:
            self.variables = self.s.variables()
            self.anomalies = self.s.anomalies(self.variables)
            points = self.s.points()
        self.etats = self.s.anomalies_par_variable(self.variables, self.anomalies)
        courant = self.f_se.currentData()
        self.f_se.blockSignals(True)
        self.f_se.clear()
        self.f_se.addItem("Tous", TOUS)
        for x in o.sous_ensembles:
            self.f_se.addItem(x.code, x.code)
        self.f_se.setCurrentIndex(max(0, self.f_se.findData(courant)))
        self.f_se.blockSignals(False)
        self._se_par_eq = {e.ident: e.sous_ensemble for e in o.equipements}
        courant_eq = self.f_eq.currentData()
        self.f_eq.blockSignals(True)
        self.f_eq.clear()
        self.f_eq.addItem("Tous", TOUS)
        for e in self.s.equipements_tries():
            self.f_eq.addItem(o.repere(e), e.ident)
        self.f_eq.setCurrentIndex(max(0, self.f_eq.findData(courant_eq)))
        self.f_eq.blockSignals(False)

        sans = sum(1 for v in self.variables if not v.adresse)
        from .guide import categoriser
        ne = sum(1 for x in self.anomalies if x.niveau == "Erreur" and categoriser(x) != "sans_adresse")
        na = sum(1 for x in self.anomalies if x.niveau == "Alerte")
        self.i_var.definir(len(self.variables))
        self.i_es.definir(len(points))
        self.i_sans.definir(sans, "Alerte" if sans else "OK")
        self.i_err.definir(ne, "Erreur" if ne else "OK")
        self.i_al.definir(na, "Alerte" if na else "OK")

        self.t.definir(self.variables)
        self.t_ctl.definir(sorted(self.anomalies, key=lambda x: (ORDRE_GRAVITE.get(x.niveau, 2), x.repere)))
        self._filtrer()
        self._filtrer_controles()
        self._a_jour = True
        self._maj_detail()

    def _maj_detail(self):
        from .guide import expliquer_nom, expliquer_adresse
        v = self.t.objet_courant()
        if v is None:
            self.detail.setText("Sélectionner une variable : son nom, son adresse et ce qu'elle exige sont expliqués ici.")
            return
        lignes = [f"Nom : {v.nom}  =  {expliquer_nom(self.s.ouvrage, v)}",
                  f"Adresse : {expliquer_adresse(self.s.ouvrage, v, self.s.ouvrage.decalage_modbus)}",
                  f"E/S physique : {v.nom_es + ' — ' + (v.adresse_es or 'adresse à saisir (écran E/S automate)') if v.nom_es else 'aucune (information interne ou calculée)'}",
                  f"Supervision : {v.libelle_topkapi}   ·   Origine : {v.origine}   ·   État : {self._etat(v)}"]
        if v.logique:
            lignes.append(f"⚙ À programmer dans l'automate : {v.logique}")
        self.detail.setText("\n".join(lignes))

    def _etat(self, v):
        """Niveau le plus grave des contrôles qui citent la variable ou sa variable d'E/S."""
        niveaux = {self.etats.get(v.nom), self.etats.get(v.nom_es) if v.nom_es else None}
        return "Erreur" if "Erreur" in niveaux else "Alerte" if "Alerte" in niveaux else "OK"

    def _infobulle(self, v):
        lignes = [a.message for a in self.anomalies if _cite(a.message, v)]
        return "\n".join(lignes[:5]) if lignes else "Aucune anomalie"

    def _filtrer(self):
        fam, se, eq = self.f_famille.currentData(), self.f_se.currentData(), self.f_eq.currentData()
        avec_ano, sans_adr = self.f_anomalie.isChecked(), self.f_sans.isChecked()

        def condition(v):
            if fam not in (None, TOUS) and v.famille != fam:
                return False
            if eq not in (None, TOUS) and v.ident_eq != eq:
                return False
            if se not in (None, TOUS) and self._se_par_eq.get(v.ident_eq) != se:
                return False
            if avec_ano and self._etat(v) == "OK":
                return False
            if sans_adr and v.adresse:
                return False
            return True

        self.t.filtre.definir_condition(condition)
        self.t.filtre.definir_texte(self.recherche.text())
        vus, total = self.t.nombre_visible(), len(self.variables)
        self.compte.setText(f"{total} variable(s)" if vus == total else f"{vus} affichée(s) sur {total}")

    def _filtrer_controles(self, *_):
        n = self.niveau.valeur()
        self.t_ctl.filtre.definir_condition(None if n in (None, "Tous") else (lambda x, n=n: x.niveau == n))

    def _aller_a(self, anomalie):
        """Montre la première variable citée par le contrôle (ou une variable de l'équipement)."""
        noms = [v.nom for v in self.variables if _cite(anomalie.message, v)]
        cible = (lambda v: v.nom == noms[0]) if noms else (lambda v: anomalie.ident_eq and v.ident_eq == anomalie.ident_eq)
        if not self.t.selectionner(cible):
            self._effacer_filtres()
            if not self.t.selectionner(cible):
                self.message.emit("Aucune variable de la table ne correspond à ce contrôle.")
                return
        self.t.setFocus()

    def _effacer_filtres(self):
        for w in (self.f_famille, self.f_se, self.f_eq):
            w.setCurrentIndex(0)
        for w in (self.f_anomalie, self.f_sans):
            w.setChecked(False)
        self.recherche.clear()

    # ============================================================== adresses
    def modifier_adresses(self):
        v = self.t.objet_courant()
        if v is None:
            informer(self, "Adresses", "Sélectionnez une variable.")
            return
        if DialogueAdresses(self, self.s, v).montrer():
            self.rafraichir()
            self.modifie.emit()
            self.t.selectionner(lambda x: x.nom == v.nom)

    def _valider(self, variables):
        if not variables:
            informer(self, "Validation", "Aucune variable sélectionnée.")
            return
        ok, refus = self.s.valider_adresses([(v.ident_eq, v.cle) for v in variables])
        self.rafraichir()
        self.modifie.emit()
        texte = f"{ok} adresse(s) validée(s)."
        if refus:
            avertir(self, "Validation des adresses", texte + f"\n{len(refus)} refus :\n" + "\n".join(refus[:15]))
        else:
            self.message.emit(texte)

    def valider_selection(self):
        self._valider(self.t.objets_selectionnes())

    def valider_affichees(self):
        visibles = [self.t.filtre.data(self.t.filtre.index(r, 0), ROLE_OBJET) for r in range(self.t.nombre_visible())]
        a_valider = [v for v in visibles if v.adresse and not v.adresse_validee]
        if a_valider and confirmer(self, "Valider les adresses",
                                   f"Valider {len(a_valider)} adresse(s) affichée(s) ?\n"
                                   "Elles ne seront plus recalculées automatiquement."):
            self._valider(a_valider)

    def devalider_selection(self):
        n = self.s.devalider_adresses([(v.ident_eq, v.cle) for v in self.t.objets_selectionnes()])
        if n:
            self.rafraichir()
            self.modifie.emit()
            self.message.emit(f"{n} adresse(s) repassée(s) en « proposée ».")

    def attribuer(self, tout_refaire=False):
        """Calcule les adresses, les montre, et ne les applique qu'après confirmation."""
        props, erreurs = self.s.plan(tout_refaire)
        if not props and not erreurs:
            informer(self, "Adresses", "Toutes les variables ont déjà une adresse.")
            return False
        if DialoguePlan(self, self.s, props, erreurs, tout_refaire).montrer():
            self.s.appliquer(props, tout_refaire)
            self.rafraichir()
            self.modifie.emit()
            self.message.emit(f"{len(props)} adresse(s) attribuée(s)."
                              + (f" {len(erreurs)} variable(s) sans place." if erreurs else ""))
            return True
        return False

    def reattribuer(self):
        if confirmer(self, "Réattribuer", "Toutes les adresses d'échange seront recalculées.\n"
                                          "À ne faire que si l'automate et la supervision n'utilisent pas encore cette table.\n\n"
                                          "Continuer ?", defaut_non=True):
            self.attribuer(tout_refaire=True)

    # ============================================================== exports
    def _avant_export(self):
        if self.s.manque_adresses() and confirmer(self, "Adresses", "Des variables n'ont pas d'adresse. Les attribuer maintenant ?"):
            self.attribuer()
        ne = sum(1 for a in self.s.anomalies() if a.niveau == "Erreur")
        if ne and not confirmer(self, "Contrôles", f"{ne} erreur(s) restent à corriger.\nExporter quand même ?", defaut_non=True):
            return False
        return True

    def _chemin(self, titre, nom, filtre):
        p, _ = QFileDialog.getSaveFileName(self, titre, os.path.join(chemins.dossier_exports(), nom), filtre)
        return p

    def exporter_xsy(self):
        if self.s.ouvrage.mode == "Existant":
            informer(self, "Export XSY", "En projet existant, les noms de l'automate sont gardés : Topkapi reprend directement "
                                         "le fichier XSY de l'automate par Softlink.\n"
                                         "Utilisez la table de correspondance Excel pour l'intégration.")
            return
        if not self.s.variables():
            informer(self, "Export", "L'ouvrage ne contient aucune variable.")
            return
        if not self._avant_export():
            return
        p = self._chemin("Exporter le fichier XSY", f"{self.s.nom_fichier_propose()}_variables.xsy",
                         "Variables Unity / Control Expert (*.xsy)")
        if not p:
            return
        if not DialogueRecap(self, self.s.recap_export()).montrer():
            return
        try:
            n = self.s.exporter_xsy(p)
        except (RegleMetier, OSError) as ex:
            avertir(self, "Export XSY", str(ex))
            return
        self.message.emit(f"{n} variables exportées dans {p}")
        informer(self, "Export XSY", f"{n} variables exportées.\n\n"
                                     "Control Expert : Données > clic droit sur Variables > Importer.\n"
                                     "Topkapi : Softlink, import d'un fichier constructeur Unity (.xsy).")

    def exporter_excel(self):
        if self.s.ouvrage.mode == "Existant":
            informer(self, "Export", "En projet existant, la table de correspondance s'exporte depuis l'application actuelle "
                                     "(lancer.pyw), écran « Variables de l'automate ».")
            return
        if not self._avant_export():
            return
        p = self._chemin("Exporter la table d'échange", f"{self.s.nom_fichier_propose()}_table_echange.xlsx",
                         "Classeur Excel (*.xlsx)")
        if not p:
            return
        try:
            self.s.exporter_excel(p)
        except PermissionError:
            avertir(self, "Export", "Le fichier est ouvert dans Excel : fermez-le puis recommencez.")
            return
        self.message.emit(f"Table d'échange exportée : {p}")
