"""Fenêtres de saisie de l'interface PySide6. Les règles sont vérifiées par genvar.session."""

import copy
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                               QLineEdit, QComboBox, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
                               QAbstractItemView, QListWidget)

from genvar.catalogue import FAMILLES_CATALOGUE, TYPES_LOGIQUES, POINTS_ES, ORGANES, PRESENCES, STATUTS, CATEGORIES
from genvar.modele import SignalPropre, TAILLE_MOTS, _mot
from genvar.session import Session, RegleMetier

from . import style
from .composants import Numero, Carte, Majuscules, bouton, avertir, informer, confirmer
from .tableaux import Tableau, Colonne, cle_tri_adresse


class Formulaire(QDialog):
    """Fenêtre modale : un formulaire, puis OK / Annuler. `verifier()` renvoie le résultat
    ou lève RegleMetier ; dans ce cas le message s'affiche et la fenêtre reste ouverte."""

    def __init__(self, parent, titre, texte_ok="OK"):
        super().__init__(parent)
        self.setWindowTitle(titre)
        self.setModal(True)
        self.resultat = None
        self.principal = QVBoxLayout(self)
        self.principal.setContentsMargins(18, 16, 18, 14)
        self.principal.setSpacing(12)
        self.formulaire = QFormLayout()
        self.formulaire.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.formulaire.setHorizontalSpacing(12)
        self.formulaire.setVerticalSpacing(8)
        self.principal.addLayout(self.formulaire)
        self.boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok = self.boutons.button(QDialogButtonBox.StandardButton.Ok)
        ok.setText(texte_ok)
        ok.setObjectName("primaire")
        self.boutons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        self.boutons.accepted.connect(self._valider)
        self.boutons.rejected.connect(self.reject)

    def finir(self):
        self.principal.addWidget(self.boutons)

    def verifier(self):
        return True

    def _valider(self):
        try:
            self.resultat = self.verifier()
        except RegleMetier as ex:
            avertir(self, self.windowTitle(), str(ex))
            return
        self.accept()

    def montrer(self):
        return self.resultat if self.exec() else None


def liste(valeurs, courante="", editable=False):
    c = QComboBox()
    c.addItems(valeurs)
    c.setEditable(editable)
    if courante in valeurs:
        c.setCurrentText(courante)
    elif editable:
        c.setEditText(courante)
    return c


# ====================================================================== sous-ensemble
class DialogueSousEnsemble(Formulaire):
    def __init__(self, parent, code="", libelle=""):
        super().__init__(parent, "Sous-ensemble")
        self.code = QLineEdit(code)
        self.code.setValidator(Majuscules(2, self.code))
        self.code.setPlaceholderText("ex. 11")
        self.libelle = QLineEdit(libelle)
        self.libelle.setMinimumWidth(320)
        self.libelle.setPlaceholderText("ex. Réservoir 1 cuve 1")
        self.formulaire.addRow("Code", self.code)
        self.formulaire.addRow("Libellé", self.libelle)
        self.finir()

    def verifier(self):
        return self.code.text().strip().upper(), self.libelle.text().strip()


# ====================================================================== unité fonctionnelle
def choix_sous_ensemble(ouvrage, courant=""):
    """Liste modifiable des sous-ensembles : on choisit un code existant ou on en tape un nouveau (2 car.)."""
    c = QComboBox()
    c.setEditable(True)
    for x in ouvrage.sous_ensembles:
        c.addItem(f"{x.code} — {x.libelle}" if x.libelle else x.code, x.code)
    i = c.findData(courant)
    if i >= 0:
        c.setCurrentIndex(i)
    else:
        c.setEditText(courant)
    c.lineEdit().setPlaceholderText("ex. 11")
    c.setToolTip("Code de 2 caractères qui entre dans le repère (ex. 11 → VLJFRV11MV01).\n"
                 "Choisir un code existant ou en taper un nouveau : il sera créé.")
    return c


def code_sous_ensemble(combo):
    texte = combo.currentText().strip().upper()
    return texte.split()[0] if texte else ""


class DialogueUF(Formulaire):
    """Unité fonctionnelle : code, libellé et sous-ensemble de repère proposé à ses équipements."""

    def __init__(self, parent, ouvrage, code="", libelle="", sous_ensemble="", titre="Unité fonctionnelle"):
        super().__init__(parent, titre)
        self.code = QLineEdit(code)
        self.code.setValidator(Majuscules(6, self.code))
        self.code.setPlaceholderText("ex. UF01")
        self.libelle = QLineEdit(libelle)
        self.libelle.setMinimumWidth(320)
        self.libelle.setPlaceholderText("ex. Stockage, Distribution, Pompage")
        self.se = choix_sous_ensemble(ouvrage, sous_ensemble)
        self.formulaire.addRow("Code de l'UF", self.code)
        self.formulaire.addRow("Libellé", self.libelle)
        self.formulaire.addRow("Sous-ensemble (repère)", self.se)
        aide = QLabel("L'UF regroupe des équipements. Son code n'entre pas dans les repères ; le sous-ensemble "
                      "est proposé aux équipements créés dans cette UF. Facultatif.")
        aide.setObjectName("aide")
        aide.setWordWrap(True)
        self.formulaire.addRow("", aide)
        self.finir()

    def verifier(self):
        se = code_sous_ensemble(self.se)
        if se and not re.match(r"^[A-Z0-9]{2}$", se):
            raise RegleMetier("Le sous-ensemble fait 2 caractères (ex. 11).")
        return self.code.text().strip().upper(), self.libelle.text().strip(), se


# ====================================================================== signal propre
class DialogueSignalPropre(Formulaire):
    def __init__(self, parent, signal=None, adaptation=False):
        super().__init__(parent, "Adapter le signal pour cet équipement" if adaptation
                         else "Signal propre à l'équipement")
        s = signal or SignalPropre("", "TS", "")
        self.info = QLineEdit(s.information)
        self.info.setMinimumWidth(340)
        self.info.setPlaceholderText("en français, sans abréviation")
        self.famille = liste(FAMILLES_CATALOGUE, s.famille)
        self.code = QLineEdit(s.code)
        self.code.setValidator(Majuscules(12, self.code))
        self.type = liste(TYPES_LOGIQUES, s.type_logique)
        self.unite = QLineEdit(s.unite)
        self.es = liste(POINTS_ES, s.es)
        self.organe = liste(ORGANES, s.organe)
        self.alarme = QCheckBox("Ce signal est une alarme")
        self.alarme.setChecked(s.alarme)
        for t, w in (("Information", self.info), ("Famille", self.famille), ("Code", self.code), ("Type logique", self.type),
                     ("Unité", self.unite), ("Point E/S", self.es), ("Organe", self.organe), ("", self.alarme)):
            self.formulaire.addRow(t, w)
        if adaptation:
            # Famille et code fixent le nom de la variable : ils restent ceux du catalogue.
            self.famille.setEnabled(False)
            self.code.setEnabled(False)
            note = QLabel("Modification valable pour <b>cet équipement seulement</b> ; le catalogue n'est pas "
                          "modifié. Famille et code (donc le nom de la variable et son adresse) sont conservés.")
            note.setObjectName("bandeau")
            note.setWordWrap(True)
            self.principal.insertWidget(0, note)
        aide = QLabel("ES = entrée-sortie locale, sans supervision. Organe (entrées TOR) : BP bouton, FDC fin de course, "
                      "MA retour de marche, DEF contact de défaut.")
        aide.setObjectName("legende")
        aide.setWordWrap(True)
        self.principal.addWidget(aide)
        self.finir()

    def verifier(self):
        s = SignalPropre(self.info.text().strip(), self.famille.currentText(), self.code.text().strip().upper(),
                         self.type.currentText(), self.unite.text().strip(), self.es.currentText(),
                         self.alarme.isChecked(), self.organe.currentText())
        Session.verifier_signal_propre(s)
        return s


# ====================================================================== validation dans le catalogue
class DialoguePromotion(Formulaire):
    def __init__(self, parent, signal, options):
        super().__init__(parent, "Valider dans le catalogue", "Ajouter au catalogue")
        texte = QLabel(f"<b>{signal.famille}_{signal.code}</b> — {signal.information}<br>"
                       "sera proposé pour tous les équipements de ce type.")
        self.principal.insertWidget(0, texte)
        self.presence = liste(PRESENCES, "Par défaut")
        self.option = liste(options, "", editable=True)
        self.statut = liste(STATUTS, "Validé")
        self.formulaire.addRow("Présence", self.presence)
        self.formulaire.addRow("Option", self.option)
        self.formulaire.addRow("Statut", self.statut)
        self.presence.currentTextChanged.connect(lambda t: self.option.setEnabled(t == "Option"))
        self.option.setEnabled(False)
        self.finir()

    def verifier(self):
        if self.presence.currentText() == "Option" and not self.option.currentText().strip():
            raise RegleMetier("Précisez l'option.")
        return self.presence.currentText(), self.option.currentText().strip(), self.statut.currentText()


# ====================================================================== équipement
class DialogueEquipement(Formulaire):
    """Type, numéro, options, signaux retenus et signaux propres d'un équipement."""

    def __init__(self, parent, session, equipement, titre, ident_original=None):
        super().__init__(parent, titre)
        self.s = session
        self.eq = copy.deepcopy(equipement)
        self.ident_original = ident_original
        self.catalogue_change = False       # un signal a été validé dans le catalogue (déjà enregistré)
        self.resize(1000, 680)

        haut = QHBoxLayout()
        self.uf = QComboBox()
        self.uf.addItem("— commun à l'ouvrage (hors UF) —", "")
        for u in session.ouvrage.unites:
            self.uf.addItem(f"{u.code} — {u.libelle}" if u.libelle else u.code, u.code)
        self.uf.setCurrentIndex(max(0, self.uf.findData(self.eq.uf)))
        self.se = choix_sous_ensemble(session.ouvrage, self.eq.sous_ensemble)
        self.type = QComboBox()
        self.type.setMinimumWidth(260)
        categorie = None
        for t in sorted(session.catalogue.types, key=lambda t: (CATEGORIES.index(t["categorie"])
                                                                if t["categorie"] in CATEGORIES else 9, t["code"])):
            if categorie is not None and t["categorie"] != categorie:
                self.type.insertSeparator(self.type.count())
            categorie = t["categorie"]
            self.type.addItem(f"{t['code']} — {t['designation']}", t["code"])
        if self.eq.type:
            self.type.setCurrentIndex(self.type.findData(self.eq.type))
        else:
            self.type.setCurrentIndex(-1)
        self.numero = Numero()
        self.numero.setValue(int(self.eq.numero) if (self.eq.numero or "").isdigit() and int(self.eq.numero) else 1)
        self.libelle = QLineEdit(self.eq.libelle)
        self.libelle.setPlaceholderText("texte libre, ex. Pompe de reprise n°1")
        self.formulaire.addRow("Unité fonctionnelle", self.uf)
        self.formulaire.addRow("Sous-ensemble (repère)", self.se)
        self.formulaire.addRow("Type", self.type)
        self.formulaire.addRow("Numéro", self.numero)
        self.formulaire.addRow("Libellé", self.libelle)
        haut.addLayout(self.formulaire, 1)
        bloc = QVBoxLayout()
        leg = QLabel("Repère")
        leg.setObjectName("legende")
        self.repere = QLabel("")
        self.repere.setObjectName("prefixe")
        self.compte = QLabel("")
        self.compte.setObjectName("legende")
        bloc.addWidget(leg)
        bloc.addWidget(self.repere)
        bloc.addWidget(self.compte)
        bloc.addStretch(1)
        haut.addSpacing(30)
        haut.addLayout(bloc)
        self.principal.insertLayout(0, haut)

        self.carte_options = Carte("Options")
        self.grille_options = QGridLayout()
        self.grille_options.setHorizontalSpacing(24)
        self.carte_options.disposition.addLayout(self.grille_options)
        self.principal.addWidget(self.carte_options)
        self.cases = {}

        carte = Carte("Signaux de l'équipement")
        aide = QLabel("E/S physiques en tête, puis signaux fonctionnels. Case : retenir / retirer (ou accepter / refuser "
                      "une proposition). Les signaux « Règle » naissent des E/S présentes ; ⚙ : logique automate à "
                      "programmer. « Modifier… » adapte un signal pour cet équipement seulement. En bleu : propres ou adaptés.")
        aide.setObjectName("legende")
        carte.disposition.addWidget(aide)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(["Retenu", "Nature", "Famille", "Code", "Information", "Origine / état",
                                              "E/S", "Adresse", "Logique"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        en_tete = self.table.horizontalHeader()
        for i, w in enumerate((62, 82, 58, 90, 250, 190, 44, 110, 62)):
            self.table.setColumnWidth(i, w)
        en_tete.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self._case_signal)
        self.table.itemDoubleClicked.connect(lambda it: self._modifier_propre() if it.column() != 0 else None)
        carte.ajouter(self.table, 1)
        self.detail = QLabel("Sélectionner un signal pour voir pourquoi il est proposé et ce qu'il exige.")
        self.detail.setObjectName("legende")
        self.detail.setWordWrap(True)
        self.detail.setMinimumHeight(44)
        carte.ajouter(self.detail)
        self.table.itemSelectionChanged.connect(self._expliquer)
        barre = QHBoxLayout()
        self.b_accepter = bouton("Accepter les propositions", self._accepter_tout,
                                 infobulle="Retient tous les signaux proposés par les règles pour cet équipement.")
        barre.addWidget(self.b_accepter)
        barre.addWidget(bouton("Ajouter un signal…", self._ajouter_propre))
        barre.addWidget(bouton("Modifier…", self._modifier_propre))
        self.b_supprimer = bouton("Supprimer", self._supprimer_propre)
        barre.addWidget(self.b_supprimer)
        self.table.itemSelectionChanged.connect(self._maj_boutons_signal)
        barre.addSpacing(16)
        barre.addWidget(bouton("Valider dans le catalogue…", self._promouvoir,
                               infobulle="Le signal propre sélectionné devient un signal du catalogue pour tout le type."))
        barre.addStretch(1)
        carte.disposition.addLayout(barre)
        self.principal.addWidget(carte, 1)
        self.finir()

        self.se.currentTextChanged.connect(lambda _: self._maj_repere())
        self.uf.currentIndexChanged.connect(self._uf_changee)
        self.numero.valueChanged.connect(self._maj_repere)
        self.type.currentIndexChanged.connect(self._changer_type)
        self._construire_options()
        self._remplir()

    # --- état
    def _code_type(self):
        return self.type.currentData() or ""

    def _uf_changee(self):
        """Nouvel équipement : le sous-ensemble suit celui de l'UF choisie (s'il est défini)."""
        self.eq.uf = self.uf.currentData() or ""
        u = next((x for x in self.s.ouvrage.unites if x.code == self.eq.uf), None)
        if self.ident_original is None and u is not None and u.sous_ensemble:
            i = self.se.findData(u.sous_ensemble)
            if i >= 0:
                self.se.setCurrentIndex(i)
            else:
                self.se.setEditText(u.sous_ensemble)

    def _maj_repere(self):
        self.eq.sous_ensemble = code_sous_ensemble(self.se)
        self.eq.type = self._code_type()
        self.eq.numero = f"{self.numero.value():02d}"
        o = self.s.ouvrage
        self.repere.setText(f"{o.lieu}{o.code_ouvrage}{self.eq.sous_ensemble or '??'}{self.eq.type or '??'}{self.eq.numero}")

    def _changer_type(self):
        self.eq.options, self.eq.exclus = [], []
        self._construire_options()
        self._remplir()

    def _construire_options(self):
        while self.grille_options.count():
            w = self.grille_options.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.cases = {}
        options = self.s.catalogue.options_du_type(self._code_type())
        if not options:
            l = QLabel("Aucune option pour ce type.")
            l.setObjectName("legende")
            self.grille_options.addWidget(l, 0, 0)
        for i, opt in enumerate(options):
            c = QCheckBox(opt)
            c.setChecked(opt in self.eq.options)
            c.toggled.connect(self._options_changees)
            self.grille_options.addWidget(c, i // 4, i % 4)
            self.cases[opt] = c

    def _options_changees(self):
        self.eq.options = [o for o, c in self.cases.items() if c.isChecked()]
        self._remplir()

    def _remplir(self):
        self._maj_repere()
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        lignes = self.s.signaux_proposes(self.eq)
        self._props = self.s.propositions(self.eq)
        n = 0
        gris = QBrush(QColor(style.DISCRET))
        bleu = QBrush(QColor(style.PROPRE))
        orange = QBrush(QColor(style.GRAVITE["Alerte"][0]))
        adaptes = {f"{a.famille}_{a.code}" for a in self.eq.ajouts}
        cles_catalogue = set()
        for signal, retenu, presence, actif in lignes:
            cle = f"{signal['famille']}_{signal['code']}"
            cles_catalogue.add(cle)
            if cle in adaptes:
                continue                    # affiché plus bas, dans sa version adaptée
            r = self.table.rowCount()
            self.table.insertRow(r)
            case = QTableWidgetItem()
            drapeaux = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            if actif or signal["presence"] != "Règle":
                drapeaux |= Qt.ItemFlag.ItemIsUserCheckable
            case.setFlags(drapeaux)
            case.setCheckState(Qt.CheckState.Checked if retenu else Qt.CheckState.Unchecked)
            case.setData(Qt.ItemDataRole.UserRole, ("catalogue", signal, retenu))
            self.table.setItem(r, 0, case)
            physique = signal["famille"] == "ES"
            logique = (self._props[cle].logique if cle in self._props else signal.get("logique", ""))
            valeurs = ("E/S physique" if physique else "Fonctionnel", signal["famille"], signal["code"],
                       signal["information"], presence, self._point(signal), self._adresse(cle, physique),
                       "⚙" if logique else "")
            for c, v in enumerate(valeurs, 1):
                it = QTableWidgetItem(v)
                it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                if not retenu:
                    it.setForeground(orange if presence.startswith("Proposé") else gris)
                if c == 8 and logique:
                    it.setToolTip(logique)
                self.table.setItem(r, c, it)
            n += retenu
        italique = QFont()
        italique.setItalic(True)
        for i, a in enumerate(self.eq.ajouts):
            r = self.table.rowCount()
            self.table.insertRow(r)
            adapte = f"{a.famille}_{a.code}" in cles_catalogue
            case = QTableWidgetItem("Adapté" if adapte else "Propre")
            case.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            case.setData(Qt.ItemDataRole.UserRole, ("propre", i))
            case.setForeground(bleu)
            self.table.setItem(r, 0, case)
            presence_txt = "Catalogue, adapté pour cet équipement" if adapte else "Propre à l'équipement"
            cle = f"{a.famille}_{a.code}"
            for c, v in enumerate(("E/S physique" if a.famille == "ES" else "Fonctionnel", a.famille, a.code,
                                   a.information, presence_txt, a.es if a.es != "Interne" else "",
                                   self._adresse(cle, a.famille == "ES"), ""), 1):
                it = QTableWidgetItem(v)
                it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                it.setForeground(bleu)
                it.setFont(italique)
                self.table.setItem(r, c, it)
            n += 1
        self.table.blockSignals(False)
        en_attente = sum(1 for p in self._props.values() if p.etat == "proposé")
        self.compte.setText(f"{n} signaux retenus" + (f" · {en_attente} proposé(s)" if en_attente else ""))
        self.b_accepter.setEnabled(bool(en_attente))
        self._expliquer()

    def _point(self, signal):
        if signal.get("source"):
            src = next((x for x in self.s.catalogue.signaux_du_type(self.eq.type)
                        if f"{x['famille']}_{x['code']}" == signal["source"]), None)
            return f"← {src['es']}" if src else ""
        es = signal.get("es") or ""
        return "" if es == "Interne" else es

    def _adresse(self, cle, physique):
        if physique:
            return self.eq.adresses_es.get(cle, "")
        adr = self.eq.adresses.get(cle, "")
        return f"{adr} ✓" if adr and cle in self.eq.validees else adr

    def _expliquer(self):
        genre, valeur = self._ligne()
        if genre != "catalogue":
            self.detail.setText("Signal propre ou adapté : défini pour cet équipement seulement." if genre else
                                "Sélectionner un signal pour voir pourquoi il est proposé et ce qu'il exige.")
            return
        s = valeur
        cle = f"{s['famille']}_{s['code']}"
        p = self._props.get(cle)
        parties = [f"<b>{cle}</b> — {s['information']}"]
        if s.get("source"):
            parties.append(f"Source physique : {s['source']}")
        if p is not None:
            parties.append(f"Pourquoi : {p.raison}.")
            if p.logique:
                parties.append(f"⚙ Conditions / logique automate : {p.logique}")
        elif s["presence"] == "Règle":
            regles = [r for r in getattr(self.s.catalogue, "regles", []) if cle in r.get("propose", [])
                      and r.get("type") == self.eq.type]
            conds = " ou ".join("[" + " + ".join(r.get("si", [])) + "]" for r in regles)
            parties.append(f"Proposé seulement si présent(s) : {conds or '—'}.")
        elif s.get("logique"):
            parties.append(f"⚙ Logique automate : {s['logique']}")
        self.detail.setText("<br>".join(parties))

    def _accepter_tout(self):
        for cle, p in self.s.propositions(self.eq).items():
            if p.etat == "proposé":
                Session.accepter_proposition(self.eq, cle)
        self._remplir()

    def _case_signal(self, item):
        if item.column() != 0:
            return
        donnee = item.data(Qt.ItemDataRole.UserRole)
        if not donnee or donnee[0] != "catalogue":
            return
        _, signal, retenu = donnee
        try:
            Session.basculer_signal(self.eq, signal, retenu)
        except RegleMetier as ex:
            informer(self, "Signal en option", str(ex))
        self._remplir()

    def _ligne(self):
        """(« catalogue », signal) ou (« propre », indice) de la ligne sélectionnée, ou (None, None)."""
        r = self.table.currentRow()
        if r < 0 or self.table.item(r, 0) is None:
            return None, None
        d = self.table.item(r, 0).data(Qt.ItemDataRole.UserRole)
        return (d[0], d[1]) if d else (None, None)

    def _retenu_ligne(self):
        r = self.table.currentRow()
        d = self.table.item(r, 0).data(Qt.ItemDataRole.UserRole) if r >= 0 and self.table.item(r, 0) else None
        return bool(d and len(d) > 2 and d[2])

    def _ligne_propre(self):
        genre, valeur = self._ligne()
        return valeur if genre == "propre" else None

    def _est_adapte(self, i):
        a = self.eq.ajouts[i]
        return any(f"{s['famille']}_{s['code']}" == f"{a.famille}_{a.code}"
                   for s in self.s.catalogue.signaux_du_type(self.eq.type))

    def _maj_boutons_signal(self):
        genre, valeur = self._ligne()
        if genre == "propre" and self._est_adapte(valeur):
            self.b_supprimer.setText("Rétablir le catalogue")
        else:
            self.b_supprimer.setText("Retirer" if genre == "catalogue" else "Supprimer")

    def _exiger_propre(self):
        i = self._ligne_propre()
        if i is None:
            informer(self, "Signal propre", "Sélectionnez un signal propre à l'équipement (en bleu).")
        return i

    def _ajouter_propre(self):
        r = DialogueSignalPropre(self).montrer()
        if r:
            self.eq.ajouts.append(r)
            self._remplir()

    def _modifier_propre(self):
        genre, valeur = self._ligne()
        if genre is None:
            informer(self, "Modifier un signal", "Sélectionnez d'abord un signal dans le tableau.")
            return
        if genre == "catalogue":
            signal = valeur
            if not self._retenu_ligne():
                informer(self, "Modifier un signal", "Ce signal n'est pas retenu : cochez-le d'abord.")
                return
            depart = SignalPropre(signal["information"], signal["famille"], signal["code"],
                                  signal.get("type_logique", "BOOL"), signal.get("unite", ""),
                                  signal.get("es") or "Interne", bool(signal.get("alarme")), signal.get("organe", ""))
            r = DialogueSignalPropre(self, depart, adaptation=True).montrer()
            if not r:
                return
            try:
                Session.personnaliser_signal(self.eq, signal, r)
            except RegleMetier as ex:
                avertir(self, "Modifier un signal", str(ex))
                return
            self._remplir()
            return
        i = valeur
        ancien = self.eq.ajouts[i]
        r = DialogueSignalPropre(self, ancien, adaptation=self._est_adapte(i)).montrer()
        if r:
            a, n = f"{ancien.famille}_{ancien.code}", f"{r.famille}_{r.code}"
            if a != n:
                for d in (self.eq.adresses, self.eq.adresses_es, self.eq.commentaires, self.eq.libelles):
                    if a in d:
                        d[n] = d.pop(a)
                if a in self.eq.validees:
                    self.eq.validees.remove(a)
            self.eq.ajouts[i] = r
            self._remplir()

    def _supprimer_propre(self):
        genre, valeur = self._ligne()
        if genre is None:
            return
        if genre == "catalogue":                     # même effet que décocher la case
            try:
                Session.basculer_signal(self.eq, valeur, self._retenu_ligne())
            except RegleMetier as ex:
                informer(self, "Signal en option", str(ex))
            self._remplir()
            return
        a = self.eq.ajouts[valeur]
        cle = f"{a.famille}_{a.code}"
        if self._est_adapte(valeur):
            if confirmer(self, "Rétablir le catalogue", f"Revenir à la version du catalogue pour {cle} ?\n"
                         "Le nom de la variable, son adresse et ses textes saisis sont conservés."):
                Session.retablir_signal(self.eq, cle)
                self._remplir()
            return
        self.eq.ajouts.pop(valeur)
        for d in (self.eq.adresses, self.eq.adresses_es, self.eq.commentaires, self.eq.libelles):
            d.pop(cle, None)
        if cle in self.eq.validees:
            self.eq.validees.remove(cle)
        self._remplir()

    def _promouvoir(self):
        i = self._exiger_propre()
        if i is None:
            return
        if self._est_adapte(i):
            informer(self, "Catalogue", "Ce signal existe déjà dans le catalogue : son adaptation reste propre "
                                        "à cet équipement. Modifier le catalogue depuis l'écran Catalogue.")
            return
        r = DialoguePromotion(self, self.eq.ajouts[i], self.s.catalogue.options_du_type(self.eq.type)).montrer()
        if not r:
            return
        try:
            signal = self.s.promouvoir_signal(self.eq, i, *r)
        except RegleMetier as ex:
            avertir(self, "Catalogue", str(ex))
            return
        self.catalogue_change = True
        self._construire_options()
        self._remplir()
        informer(self, "Catalogue", f"{signal['famille']}_{signal['code']} ajouté au catalogue du type {self.eq.type}.")

    def verifier(self):
        self._maj_repere()
        self.eq.uf = self.uf.currentData() or ""
        self.eq.libelle = self.libelle.text().strip()
        self.eq.options = [o for o, c in self.cases.items() if c.isChecked()]
        if not self.eq.sous_ensemble:
            raise RegleMetier("Indiquez le sous-ensemble du repère (2 caractères, ex. 11).")
        # Sous-ensemble tapé à la main : déclaré à la validation, retiré si l'équipement est refusé.
        nouveau = not any(x.code == self.eq.sous_ensemble for x in self.s.ouvrage.sous_ensembles)
        if nouveau:
            u = next((x for x in self.s.ouvrage.unites if x.code == self.eq.uf), None)
            self.s.ajouter_sous_ensemble(self.eq.sous_ensemble, u.libelle if u else "")
        try:
            self.s.verifier_equipement(self.eq, self.ident_original)
        except RegleMetier:
            if nouveau:
                self.s.supprimer_sous_ensemble(self.eq.sous_ensemble)
            raise
        return self.eq


# ====================================================================== adresses d'une variable
class DialogueAdresses(Formulaire):
    """Fiche de propriétés d'une variable : adresses, validation, commentaire et libellé."""

    def __init__(self, parent, session, variable):
        super().__init__(parent, "Propriétés de la variable", "Enregistrer")
        self.s, self.v = session, variable
        self.setMinimumWidth(620)
        titre = QLabel(f"<b style='font-size:12pt'>{variable.nom}</b><br>"
                       f"<span style='color:{style.SECONDAIRE}'>{variable.repere} · {variable.famille} · "
                       f"{variable.type_logique} · {variable.information}</span>")
        titre.setTextFormat(Qt.TextFormat.RichText)
        self.principal.insertWidget(0, titre)

        self.adresse = QLineEdit(variable.adresse)
        self.adresse.setPlaceholderText("%MW1000.3 pour un bit, %MW1400 pour un mot")
        self.formulaire.addRow("Adresse d'échange", self.adresse)
        self.validee = QCheckBox("Adresse validée par l'automaticien (ne sera plus recalculée)")
        self.validee.setChecked(variable.adresse_validee)
        self.formulaire.addRow("", self.validee)
        self.es = None
        if variable.nom_es:
            exemple = {"ET": "%I0.3.5", "ST": "%Q0.4.2", "EA": "%IW0.5.0", "SA": "%QW0.6.0"}[variable.es]
            self.es = QLineEdit(variable.adresse_es)
            self.es.setPlaceholderText(f"ex. {exemple}")
            self.formulaire.addRow(f"Adresse physique ({variable.es})", self.es)
            l = QLabel(variable.nom_es)
            l.setObjectName("legende")
            self.formulaire.addRow("", l)

        self.commentaire = QLineEdit(variable.commentaire if variable.commentaire_saisi else "")
        self.commentaire.setPlaceholderText(variable.commentaire_propose)
        self.commentaire.setToolTip("Laisser vide pour utiliser le texte proposé par le dictionnaire métier.")
        self.formulaire.addRow("Commentaire automate", self.commentaire)
        eq = session.ouvrage.equipement(variable.ident_eq)
        libelle_saisi = eq.libelles.get(variable.cle, "") if eq else ""
        self.libelle = QLineEdit(libelle_saisi)
        self.libelle.setMaxLength(40)
        self.libelle.setPlaceholderText(variable.libelle_topkapi if not libelle_saisi else "")
        self.formulaire.addRow("Libellé supervision", self.libelle)
        aide = QLabel("Champs vides : texte proposé (affiché en gris). Une adresse validée ne change "
                      "qu'après confirmation ; elle repasse alors « proposée ».")
        aide.setObjectName("legende")
        aide.setWordWrap(True)
        self.principal.addWidget(aide)
        self.finir()

    def verifier(self):
        from .composants import confirmer
        nouvelle = self.adresse.text().strip().upper()
        deverrouiller = False
        if self.v.adresse_validee and nouvelle != self.v.adresse.upper():
            if not confirmer(self, "Adresse validée",
                             f"{self.v.nom} a l'adresse validée {self.v.adresse}.\n"
                             f"La remplacer par {nouvelle or '(aucune)'} ? L'automate et la supervision "
                             "devront suivre.", defaut_non=True):
                raise RegleMetier("Modification annulée : l'adresse validée est conservée.")
            deverrouiller = True
        self.s.definir_adresses(self.v.ident_eq, self.v.cle, self.adresse.text(),
                                self.es.text() if self.es is not None else None, deverrouiller=deverrouiller)
        self.s.definir_textes(self.v.ident_eq, self.v.cle, self.commentaire.text(), self.libelle.text())
        paire = [(self.v.ident_eq, self.v.cle)]
        if self.validee.isChecked():
            ok, refus = self.s.valider_adresses(paire)
            if refus:
                raise RegleMetier("Textes et adresse enregistrés, validation refusée : " + " ".join(refus))
        else:
            self.s.devalider_adresses(paire)
        return True


# ====================================================================== aperçu du plan d'adresses
class DialoguePlan(Formulaire):
    def __init__(self, parent, session, propositions, erreurs, tout_refaire):
        super().__init__(parent, "Adresses proposées", "Appliquer")
        self.resize(1040, 620)
        texte = QLabel(f"<b>{len(propositions)} adresse(s) à attribuer</b> — "
                       + ("toutes les adresses sont recalculées." if tout_refaire else "les adresses existantes ne bougent pas.")
                       + " Rien n'est modifié avant « Appliquer ».")
        self.principal.insertWidget(0, texte)
        cols = [Colonne("fam", "Famille", lambda p: p.variable.famille, 70),
                Colonne("nom", "Variable", lambda p: p.variable.nom, 250),
                Colonne("type", "Type", lambda p: p.variable.type_logique, 60),
                Colonne("adr", "Adresse", lambda p: _plage(p.adresse, p.variable.type_logique), 120,
                        tri=lambda p: cle_tri_adresse(p.adresse)),
                Colonne("mb", "Registre Modbus", lambda p: session.registre_modbus(p.adresse), 110),
                Colonne("rem", "Remarque", lambda p: p.remarque, 320, etirable=True)]
        t = Tableau(cols, "apercu_plan", self)
        t.definir(propositions)
        t.sortByColumn(3, Qt.SortOrder.AscendingOrder)
        self.principal.insertWidget(1, t, 1)
        if erreurs:
            l = QLabel(f"<b>{len(erreurs)} variable(s) sans place</b> (plage pleine) : agrandir la plage dans les paramètres.<br>"
                       + "<br>".join(erreurs[:6]))
            l.setStyleSheet(f"color: {style.GRAVITE['Erreur'][0]};")
            l.setWordWrap(True)
            self.principal.insertWidget(2, l)
        self.finir()
        if erreurs:
            # Ne jamais appliquer un plan PARTIEL : cela risquerait de vider les
            # adresses déjà confirmées en mode « tout refaire ».
            self.boutons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)


def _plage(adresse, type_logique):
    taille = TAILLE_MOTS.get(type_logique, 1)
    p = _mot(adresse)
    if taille >= 2 and p and p[1] is None:
        return f"{adresse}–{p[0] + taille - 1}"
    return adresse


# ====================================================================== récapitulatif d'export
class DialogueRecap(Formulaire):
    def __init__(self, parent, recap):
        incomplet = bool(recap.sans_adresse)
        super().__init__(parent, "Récapitulatif avant export", "Exporter quand même" if incomplet else "Exporter")
        for t, v in (("Variables d'échange", recap.variables), ("E/S déclarées", f"{recap.points} (dont {recap.locales} locales)"),
                     ("E/S avec adresse, exportées", recap.avec_adresse),
                     ("E/S sans adresse, exclues", len(recap.sans_adresse)), ("Erreurs de contrôle", recap.erreurs)):
            l = QLabel(f"<b>{v}</b>")
            self.formulaire.addRow(t, l)
        if incomplet:
            avert = QLabel("Le fichier sera incomplet pour les E/S suivantes : une variable d'E/S doit être localisée.")
            avert.setStyleSheet(f"color: {style.GRAVITE['Alerte'][0]};")
            avert.setWordWrap(True)
            self.principal.addWidget(avert)
            lst = QListWidget()
            lst.addItems(recap.sans_adresse)
            lst.setMaximumHeight(200)
            self.principal.addWidget(lst)
        self.finir()
