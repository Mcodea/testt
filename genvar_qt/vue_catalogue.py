"""Éditeur du référentiel : types d'équipements, signaux (E/S physiques et fonctionnels), règles.

Les modifications portent sur la copie du référentiel propre à l'ouvrage ouvert (enregistrée avec
lui). « Publier » la recopie dans le référentiel partagé, utilisé par les FUTURS ouvrages ; un ouvrage
déjà enregistré garde toujours sa propre copie.
"""
import copy
import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QDialog,
                               QDialogButtonBox, QFormLayout, QListWidget, QListWidgetItem, QTabWidget,
                               QTextEdit, QSplitter, QFileDialog, QCheckBox)

from genvar.catalogue import (FAMILLES_CATALOGUE, TYPES_LOGIQUES, POINTS_ES, PRESENCES, STATUTS, ORGANES,
                              DOMAINES, CATEGORIES, sens_incoherent)
from . import style
from .composants import Page, Carte, bouton, avertir, informer, confirmer, notifier, legende, champ_recherche
from .tableaux import Tableau, Colonne

RE_CODE_TYPE = re.compile(r"^[A-Z]{2}$")
RE_CODE_SIGNAL = re.compile(r"^[A-Z0-9]+(_[A-Z0-9]+)*$")


def _boutons(dlg, texte_ok="Enregistrer"):
    b = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    b.button(QDialogButtonBox.StandardButton.Ok).setText(texte_ok)
    b.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primaire")
    b.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
    b.accepted.connect(dlg.accept)
    b.rejected.connect(dlg.reject)
    return b


class DialogueType(QDialog):
    def __init__(self, parent, catalogue, ancien=None):
        super().__init__(parent)
        self.setWindowTitle("Type d'équipement")
        self.setMinimumWidth(560)
        self.cat, self.ancien = catalogue, ancien
        lay = QVBoxLayout(self)
        f = QFormLayout()
        lay.addLayout(f)
        a = ancien or {}
        self.code = QLineEdit(a.get("code", ""))
        self.code.setMaxLength(2)
        self.code.setPlaceholderText("2 lettres, ex. CU")
        self.code.setEnabled(ancien is None)               # le code est dans les repères : non modifiable
        self.designation = QLineEdit(a.get("designation", ""))
        self.domaine = QComboBox()
        self.domaine.addItems(DOMAINES)
        self.domaine.setCurrentText(a.get("domaine", "Hydraulique"))
        self.categorie = QComboBox()
        self.categorie.addItems(CATEGORIES)
        self.categorie.setCurrentText(a.get("categorie", "Équipement"))
        self.options = QLineEdit(" ; ".join(a.get("options", [])))
        self.options.setPlaceholderText("variantes séparées par « ; », ex. Télécommandée ; Variateur")
        self.remarque = QTextEdit(a.get("remarque", ""))
        self.remarque.setFixedHeight(70)
        for t, w in (("Code", self.code), ("Désignation", self.designation), ("Domaine", self.domaine),
                     ("Catégorie", self.categorie), ("Options / variantes", self.options), ("Description", self.remarque)):
            f.addRow(t, w)
        lay.addWidget(legende("Le code entre dans le repère des équipements (ex. RV11CU01) : il ne se modifie "
                              "plus une fois créé.", "aide"))
        lay.addWidget(_boutons(self))

    def resultat(self):
        code = self.code.text().strip().upper()
        if not RE_CODE_TYPE.match(code):
            raise ValueError("Code : exactement 2 lettres majuscules.")
        if self.ancien is None and self.cat.type(code) is not None:
            raise ValueError(f"Le type {code} existe déjà.")
        if not self.designation.text().strip():
            raise ValueError("Désignation obligatoire.")
        return {"code": code, "designation": self.designation.text().strip(), "categorie": self.categorie.currentText(),
                "famille_biblio": (self.ancien or {}).get("famille_biblio", ""), "domaine": self.domaine.currentText(),
                "options": [o.strip() for o in self.options.text().split(";") if o.strip()],
                "remarque": self.remarque.toPlainText().strip()}


class DialogueSignal(QDialog):
    """Signal du référentiel : E/S physique (famille ES) ou signal fonctionnel."""

    def __init__(self, parent, catalogue, code_type, ancien=None):
        super().__init__(parent)
        self.setWindowTitle("Signal du référentiel")
        self.setMinimumWidth(620)
        self.cat, self.type, self.ancien = catalogue, code_type, ancien
        a = ancien or {}
        lay = QVBoxLayout(self)
        f = QFormLayout()
        lay.addLayout(f)
        self.famille = QComboBox(); self.famille.addItems(FAMILLES_CATALOGUE)
        self.famille.setCurrentText(a.get("famille", "TS"))
        self.code = QLineEdit(a.get("code", ""))
        self.code.setPlaceholderText("ex. OUV ; E/S : FDC_OUV")
        self.information = QLineEdit(a.get("information", ""))
        self.type_logique = QComboBox(); self.type_logique.addItems(TYPES_LOGIQUES)
        self.type_logique.setCurrentText(a.get("type_logique", "BOOL"))
        self.unite = QLineEdit(a.get("unite", ""))
        self.es = QComboBox(); self.es.addItems(POINTS_ES); self.es.setCurrentText(a.get("es", "Interne"))
        self.organe = QComboBox(); self.organe.addItems(ORGANES); self.organe.setCurrentText(a.get("organe", ""))
        self.source = QComboBox()
        self.source.addItem("(aucune)", "")
        for s in catalogue.signaux_du_type(code_type):
            if s["famille"] == "ES":
                self.source.addItem(f"ES_{s['code']} — {s['information']} ({s.get('es')})", f"ES_{s['code']}")
        self.source.setCurrentIndex(max(0, self.source.findData(a.get("source", ""))))
        self.presence = QComboBox(); self.presence.addItems(PRESENCES)
        self.presence.setCurrentText(a.get("presence", "Par défaut"))
        self.option = QComboBox(); self.option.setEditable(True)
        self.option.addItems([""] + catalogue.options_du_type(code_type))
        self.option.setCurrentText(a.get("option", ""))
        self.alarme = QCheckBox("Alarme"); self.alarme.setChecked(bool(a.get("alarme")))
        self.statut = QComboBox(); self.statut.addItems(STATUTS); self.statut.setCurrentText(a.get("statut", "À valider"))
        self.logique = QTextEdit(a.get("logique", ""))
        self.logique.setFixedHeight(64)
        self.logique.setPlaceholderText("Traitement automate nécessaire (vide : acquisition ou commande directe)")
        for t, w in (("Famille", self.famille), ("Code", self.code), ("Information", self.information),
                     ("Type", self.type_logique), ("Unité", self.unite), ("Point E/S direct", self.es),
                     ("Organe (ET)", self.organe), ("Source physique", self.source), ("Présence", self.presence),
                     ("Option", self.option), ("", self.alarme), ("Statut", self.statut), ("Logique automate", self.logique)):
            f.addRow(t, w)
        lay.addWidget(legende("E/S physique : famille ES avec un point ET / ST / EA / SA. Signal fonctionnel acquis "
                              "par une E/S déclarée à part : renseigner la « Source physique » (point direct = Interne). "
                              "Présence « Règle » : le signal n'est proposé que par une règle.", "aide"))
        lay.addWidget(_boutons(self))

    def resultat(self):
        famille, code = self.famille.currentText(), self.code.text().strip().upper()
        info = self.information.text().strip()
        if not RE_CODE_SIGNAL.match(code) or (famille != "ES" and "_" in code):
            raise ValueError("Code : lettres majuscules et chiffres ; « _ » permis seulement pour une E/S (ES).")
        if not info:
            raise ValueError("Information obligatoire.")
        es, source, presence = self.es.currentText(), self.source.currentData(), self.presence.currentText()
        if famille == "ES" and es not in ("ET", "ST", "EA", "SA"):
            raise ValueError("Une E/S physique (ES) doit avoir un point ET, ST, EA ou SA.")
        if source and es != "Interne":
            raise ValueError("Signal avec source physique : son point direct doit être « Interne ».")
        if source:
            src = next(s for s in self.cat.signaux_du_type(self.type) if f"ES_{s['code']}" == source)
            if sens_incoherent(famille, src.get("es")):
                raise ValueError(sens_incoherent(famille, src.get("es")).capitalize() + ".")
        if sens_incoherent(famille, es):
            raise ValueError(sens_incoherent(famille, es).capitalize() + ".")
        if presence == "Option" and not self.option.currentText().strip():
            raise ValueError("Préciser l'option qui conditionne le signal.")
        if self.organe.currentText() and es != "ET":
            raise ValueError("Le code d'organe ne s'emploie que sur une ET.")
        if any(s is not self.ancien and s["type"] == self.type and s["famille"] == famille and s["code"] == code
               for s in self.cat.signaux):
            raise ValueError(f"{famille}_{code} existe déjà pour ce type.")
        return dict(self.ancien or {}, type=self.type, famille=famille, code=code, information=info,
                    type_logique=self.type_logique.currentText(), unite=self.unite.text().strip(), es=es,
                    organe=self.organe.currentText(), source=source, presence=presence,
                    option=self.option.currentText().strip() if presence == "Option" else "",
                    alarme=self.alarme.isChecked(), statut=self.statut.currentText(),
                    logique=self.logique.toPlainText().strip(), remarque=(self.ancien or {}).get("remarque", ""))


class DialogueRegle(QDialog):
    def __init__(self, parent, catalogue, code_type, ancien=None):
        super().__init__(parent)
        self.setWindowTitle("Règle fonctionnelle")
        self.resize(760, 560)
        self.cat, self.type, self.ancien = catalogue, code_type, ancien
        a = ancien or {}
        lay = QVBoxLayout(self)
        f = QFormLayout()
        lay.addLayout(f)
        n = 1 + sum(1 for r in catalogue.regles if r.get("type") == code_type)
        self.ident = QLineEdit(a.get("id", f"{code_type}-{n:02d}"))
        self.libelle = QLineEdit(a.get("libelle", ""))
        self.libelle.setPlaceholderText("ex. Deux fins de course → discordance")
        self.mode = QComboBox()
        self.mode.addItem("Proposition (à accepter par l'utilisateur)", "proposition")
        self.mode.addItem("Automatique (retenu d'office, refusable)", "auto")
        self.mode.setCurrentIndex(max(0, self.mode.findData(a.get("mode", "proposition"))))
        f.addRow("Identifiant", self.ident)
        f.addRow("Libellé", self.libelle)
        f.addRow("Mode", self.mode)
        listes = QHBoxLayout()
        self.si = self._liste("SI tous ces signaux sont présents", a.get("si", []))
        self.propose = self._liste("ALORS proposer", a.get("propose", []), sans_es=True)
        listes.addLayout(self.si[0], 1)
        listes.addLayout(self.propose[0], 1)
        lay.addLayout(listes, 1)
        self.logique = QTextEdit(a.get("logique", ""))
        self.logique.setFixedHeight(80)
        self.logique.setPlaceholderText("Conditions techniques : temporisations, seuils, états normaux / défauts démontrés…")
        lay.addWidget(QLabel("Conditions techniques / logique automate"))
        lay.addWidget(self.logique)
        lay.addWidget(_boutons(self))

    def _liste(self, titre, coches, sans_es=False):
        col = QVBoxLayout()
        col.addWidget(QLabel(f"<b>{titre}</b>"))
        lst = QListWidget()
        for s in self.cat.signaux_du_type(self.type):
            if sans_es and s["famille"] == "ES":
                continue
            cle = f"{s['famille']}_{s['code']}"
            it = QListWidgetItem(f"{cle} — {s['information']}")
            it.setData(Qt.ItemDataRole.UserRole, cle)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if cle in coches else Qt.CheckState.Unchecked)
            lst.addItem(it)
        col.addWidget(lst, 1)
        return col, lst

    @staticmethod
    def _coches(lst):
        return [lst.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lst.count())
                if lst.item(i).checkState() == Qt.CheckState.Checked]

    def resultat(self):
        rid = self.ident.text().strip().upper()
        if not rid:
            raise ValueError("Identifiant obligatoire.")
        if any(r is not self.ancien and r.get("id") == rid for r in self.cat.regles):
            raise ValueError(f"La règle {rid} existe déjà.")
        si, propose = self._coches(self.si[1]), self._coches(self.propose[1])
        if not si or not propose:
            raise ValueError("Cocher au moins une condition et un signal proposé.")
        if set(si) & set(propose):
            raise ValueError("Un signal ne peut pas être à la fois condition et proposition.")
        return {"id": rid, "type": self.type, "libelle": self.libelle.text().strip() or rid, "si": si,
                "propose": propose, "mode": self.mode.currentData(), "logique": self.logique.toPlainText().strip()}


class VueCatalogue(Page):
    modifie = Signal()

    def __init__(self, session, parent=None):
        super().__init__("Référentiel des équipements",
                         "Types, E/S physiques, signaux fonctionnels et règles de proposition. Les modifications "
                         "portent sur la copie de l'ouvrage ; « Publier » les rend disponibles pour les futurs ouvrages.",
                         parent)
        self.s = session
        self.entete.droite.addWidget(bouton("Référentiel livré…", self.reprendre_livre, icone="catalogue", nom="discret",
                                            infobulle="Remplacer la copie de l'ouvrage par le référentiel livré avec l'outil."))
        self.entete.droite.addWidget(bouton("Exporter Excel…", self.exporter_excel, icone="export", nom="discret"))
        self.entete.droite.addWidget(bouton("Importer Excel…", self.importer_excel, icone="import", nom="discret"))
        self.entete.droite.addWidget(bouton("Publier comme référentiel partagé…", self.sauver_commun, icone="export",
                                            infobulle="Les ouvrages déjà enregistrés conservent leur propre version."))
        sep = QSplitter(Qt.Orientation.Horizontal)
        sep.setChildrenCollapsible(False)

        # ---------------------------------------------------------- types
        gauche = Carte("Types d'équipements")
        self.recherche = champ_recherche("Rechercher un type…")
        gauche.ajouter(self.recherche)
        self.liste = QListWidget()
        gauche.ajouter(self.liste, 1)
        r = QHBoxLayout()
        r.addWidget(bouton("Nouveau type…", self.ajouter_type, icone="ajouter"))
        r.addWidget(bouton("Modifier…", self.modifier_type, icone="modifier"))
        r.addStretch(1)
        gauche.disposition.addLayout(r)
        gauche.setMinimumWidth(290)
        sep.addWidget(gauche)

        # ---------------------------------------------------------- détail du type
        droite = Carte()
        self.titre_type = QLabel("")
        self.titre_type.setObjectName("prefixe")
        droite.ajouter(self.titre_type)
        self.desc_type = legende("")
        droite.ajouter(self.desc_type)
        self.onglets = QTabWidget()
        self.onglets.setDocumentMode(True)

        page_s = QWidget()
        ls = QVBoxLayout(page_s)
        ls.setContentsMargins(0, 8, 0, 0)
        self.recherche_sig = champ_recherche("Rechercher un code, une information…")
        ls.addWidget(self.recherche_sig)
        self.t_sig = Tableau([
            Colonne("nat", "Nature", lambda s: "E/S physique" if s["famille"] == "ES" else "Fonctionnel", 95),
            Colonne("fam", "Famille", lambda s: s["famille"], 60),
            Colonne("code", "Code", lambda s: s["code"], 95),
            Colonne("info", "Information", lambda s: s["information"], 220, etirable=True),
            Colonne("type", "Type", lambda s: s.get("type_logique", ""), 60),
            Colonne("es", "E/S", lambda s: s.get("es", "") if s.get("es") != "Interne" else "", 45),
            Colonne("src", "Source", lambda s: s.get("source", ""), 105),
            Colonne("pres", "Présence", lambda s: s.get("presence", "") + (f" : {s['option']}" if s.get("option") else ""), 150),
            Colonne("log", "⚙", lambda s: "⚙" if s.get("logique") else "", 32, infobulle=lambda s: s.get("logique") or None),
            Colonne("stat", "Statut", lambda s: s.get("statut", ""), 80),
        ], "referentiel_signaux_v1")
        self.t_sig.modele.couleur = lambda s: style.DISCRET if s.get("statut") == "Écarté" else None
        self.t_sig.objet_active.connect(lambda _: self.modifier_signal())
        ls.addWidget(self.t_sig, 1)
        b = QHBoxLayout()
        b.addWidget(bouton("Ajouter un signal…", self.ajouter_signal, primaire=True, icone="ajouter"))
        b.addWidget(bouton("Modifier…", self.modifier_signal, icone="modifier"))
        b.addWidget(bouton("Écarter / rétablir", self.ecarter, icone="supprimer", nom="danger"))
        b.addStretch(1)
        ls.addLayout(b)
        self.onglets.addTab(page_s, "Signaux")

        page_r = QWidget()
        lr = QVBoxLayout(page_r)
        lr.setContentsMargins(0, 8, 0, 0)
        lr.addWidget(legende("Une règle propose des signaux lorsque d'autres sont présents. « Automatique » : liaison "
                             "directe, retenue d'office. « Proposition » : information calculée par l'automate, à "
                             "accepter équipement par équipement.", "aide"))
        self.t_reg = Tableau([
            Colonne("id", "Règle", lambda r: r.get("id", ""), 80),
            Colonne("lib", "Libellé", lambda r: r.get("libelle", ""), 240),
            Colonne("si", "Si présents", lambda r: " + ".join(r.get("si", [])), 180),
            Colonne("prop", "Propose", lambda r: ", ".join(r.get("propose", [])), 200),
            Colonne("mode", "Mode", lambda r: r.get("mode", ""), 95),
            Colonne("log", "Conditions techniques", lambda r: r.get("logique", ""), 300, etirable=True),
        ], "referentiel_regles_v1")
        self.t_reg.texte_vide = "Aucune règle pour ce type."
        self.t_reg.objet_active.connect(lambda _: self.modifier_regle())
        lr.addWidget(self.t_reg, 1)
        b = QHBoxLayout()
        b.addWidget(bouton("Ajouter une règle…", self.ajouter_regle, primaire=True, icone="ajouter"))
        b.addWidget(bouton("Modifier…", self.modifier_regle, icone="modifier"))
        b.addWidget(bouton("Supprimer", self.supprimer_regle, icone="supprimer", nom="danger"))
        b.addStretch(1)
        lr.addLayout(b)
        self.onglets.addTab(page_r, "Règles")
        droite.ajouter(self.onglets, 1)
        self.controle = legende("", "aide")
        droite.ajouter(self.controle)
        sep.addWidget(droite)
        sep.setStretchFactor(0, 1)
        sep.setStretchFactor(1, 3)
        sep.setSizes([300, 1000])
        self.disposition.addWidget(sep, 1)

        self.recherche.textChanged.connect(self._remplir_liste)
        self.liste.currentItemChanged.connect(lambda *_: self.charger_lignes())
        self.recherche_sig.textChanged.connect(self.t_sig.filtre.definir_texte)
    def currentData(self):
        """Code du type sélectionné."""
        it = self.liste.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    # ================================================================== chargement
    def charger(self):
        self._remplir_liste()

    def _remplir_liste(self, *_):
        courant = self.currentData()
        filtre = self.recherche.text().casefold()
        self.liste.blockSignals(True)
        self.liste.clear()
        domaine = None
        for t in sorted(self.s.catalogue.types, key=lambda t: (DOMAINES.index(t.get("domaine")) if t.get("domaine") in DOMAINES else 9,
                                                              t["code"])):
            if filtre and filtre not in f"{t['code']} {t['designation']} {t.get('domaine', '')}".casefold():
                continue
            if t.get("domaine") != domaine:
                domaine = t.get("domaine")
                titre = QListWidgetItem((domaine or "Autres").upper())
                titre.setFlags(Qt.ItemFlag.NoItemFlags)
                f = titre.font(); f.setBold(True); f.setPointSizeF(8); titre.setFont(f)
                self.liste.addItem(titre)
            n = len(self.s.catalogue.signaux_du_type(t["code"]))
            it = QListWidgetItem(f"{t['code']}  —  {t['designation']}   ({n})")
            it.setData(Qt.ItemDataRole.UserRole, t["code"])
            self.liste.addItem(it)
            if t["code"] == courant:
                self.liste.setCurrentItem(it)
        if self.liste.currentItem() is None:
            for i in range(self.liste.count()):
                if self.liste.item(i).data(Qt.ItemDataRole.UserRole):
                    self.liste.setCurrentRow(i)
                    break
        self.liste.blockSignals(False)
        self.charger_lignes()

    def charger_lignes(self, *_):
        code = self.currentData()
        t = self.s.catalogue.type(code) if code else None
        self.titre_type.setText(f"{code} — {t['designation']}" if t else "")
        self.desc_type.setText((f"{t.get('domaine', '')} · options : {', '.join(t.get('options', [])) or 'aucune'}"
                                + (f"\n{t['remarque']}" if t.get("remarque") else "")) if t else "")
        signaux = [s for s in self.s.catalogue.signaux if s["type"] == code]
        signaux.sort(key=lambda s: 0 if s["famille"] == "ES" else 1)
        self.t_sig.definir(signaux)
        self.t_reg.definir([r for r in self.s.catalogue.regles if r.get("type") in (code, "*")])
        self.onglets.setTabText(0, f"Signaux ({len(signaux)})")
        self.onglets.setTabText(1, f"Règles ({self.t_reg.modele.rowCount()})")
        anomalies = [m for m in self.s.catalogue.anomalies() if code and (f"Type {code}" in m or f"type {code}" in m
                                                                           or m.startswith(f"Règle {code}-"))]
        self.controle.setText(("⚠ " + " · ".join(anomalies[:4])) if anomalies else "Contrôle du référentiel : aucune anomalie pour ce type.")

    def _apres(self):
        # Une évolution du référentiel peut changer les signaux générés :
        # aucune validation globale de l'ouvrage ne doit être conservée en silence.
        self.s._change()
        self.modifie.emit()
        self.charger_lignes()

    # ================================================================== types
    def ajouter_type(self):
        d = DialogueType(self, self.s.catalogue)
        while d.exec():
            try:
                t = d.resultat()
            except ValueError as ex:
                avertir(self, "Type", str(ex)); continue
            self.s.catalogue.types.append(t)
            self._apres()
            self._remplir_liste()
            return

    def modifier_type(self):
        code = self.currentData()
        t = self.s.catalogue.type(code) if code else None
        if not t:
            return
        d = DialogueType(self, self.s.catalogue, t)
        while d.exec():
            try:
                t.update(d.resultat())
            except ValueError as ex:
                avertir(self, "Type", str(ex)); continue
            self._apres()
            self._remplir_liste()
            return

    # ================================================================== signaux
    def ajouter_signal(self):
        code = self.currentData()
        if not code:
            return
        d = DialogueSignal(self, self.s.catalogue, code)
        while d.exec():
            try:
                self.s.catalogue.signaux.append(d.resultat())
            except ValueError as ex:
                avertir(self, "Signal", str(ex)); continue
            self._apres()
            return

    def modifier_signal(self):
        ancien = self.t_sig.objet_courant()
        if ancien is None:
            return
        d = DialogueSignal(self, self.s.catalogue, ancien["type"], ancien)
        while d.exec():
            try:
                nouveau = d.resultat()
            except ValueError as ex:
                avertir(self, "Signal", str(ex)); continue
            avant, apres = f"{ancien['famille']}_{ancien['code']}", f"{nouveau['famille']}_{nouveau['code']}"
            if avant != apres and any(avant in r.get("si", []) + r.get("propose", []) for r in self.s.catalogue.regles):
                if not confirmer(self, "Signal utilisé par des règles",
                                 f"{avant} est cité par des règles : elles seront mises à jour vers {apres}. Continuer ?"):
                    return
                for r in self.s.catalogue.regles:
                    r["si"] = [apres if c == avant else c for c in r.get("si", [])]
                    r["propose"] = [apres if c == avant else c for c in r.get("propose", [])]
                for s in self.s.catalogue.signaux:
                    if s["type"] == ancien["type"] and s.get("source") == avant:
                        s["source"] = apres
            ancien.clear()
            ancien.update(nouveau)
            self._apres()
            return

    def ecarter(self):
        s = self.t_sig.objet_courant()
        if s is None:
            return
        if s.get("statut") == "Écarté":
            s["statut"] = "À valider"
        elif confirmer(self, "Écarter", f"Écarter {s['famille']}_{s['code']} du référentiel de l'ouvrage ?\n"
                       "Il n'est plus proposé ; les règles qui le citent sont signalées au contrôle."):
            s["statut"] = "Écarté"
        else:
            return
        self._apres()

    # ================================================================== règles
    def ajouter_regle(self):
        code = self.currentData()
        if not code:
            return
        d = DialogueRegle(self, self.s.catalogue, code)
        while d.exec():
            try:
                self.s.catalogue.regles.append(d.resultat())
            except ValueError as ex:
                avertir(self, "Règle", str(ex)); continue
            self._apres()
            return

    def modifier_regle(self):
        r = self.t_reg.objet_courant()
        if r is None:
            return
        if r.get("type") == "*":
            informer(self, "Règle générique", "Cette règle s'applique à tous les types ; elle se modifie par "
                     "l'import Excel du référentiel.")
            return
        d = DialogueRegle(self, self.s.catalogue, r["type"], r)
        while d.exec():
            try:
                nouvelle = d.resultat()
            except ValueError as ex:
                avertir(self, "Règle", str(ex)); continue
            r.clear()
            r.update(nouvelle)
            self._apres()
            return

    def supprimer_regle(self):
        r = self.t_reg.objet_courant()
        if r is not None and confirmer(self, "Supprimer la règle", f"Supprimer la règle {r.get('id')} ?\n"
                                       "Les signaux qu'elle proposait ne seront plus proposés.", defaut_non=True):
            self.s.catalogue.regles.remove(r)
            self._apres()

    # ================================================================== échange et publication
    def exporter_excel(self):
        from genvar import catalogue_excel
        p, _ = QFileDialog.getSaveFileName(self, "Exporter le référentiel", "referentiel_SOREP.xlsx", "Excel (*.xlsx)")
        if p:
            catalogue_excel.exporter(self.s.catalogue, p if p.lower().endswith(".xlsx") else p + ".xlsx")
            notifier(self, "Référentiel exporté (onglets Catalogue, Types, Règles).")

    def importer_excel(self):
        from genvar import catalogue_excel
        p, _ = QFileDialog.getOpenFileName(self, "Importer un référentiel", "", "Excel (*.xlsx)")
        if not p:
            return
        try:
            cat, messages = catalogue_excel.importer(p)
        except (ValueError, OSError, KeyError) as ex:
            avertir(self, "Import du référentiel", str(ex))
            return
        anomalies = cat.anomalies()
        texte = (f"{len(cat.types)} types, {len(cat.signaux)} signaux, {len(cat.regles)} règles.\n"
                 + ("\n".join(messages[:10]) + "\n" if messages else "")
                 + (f"\n{len(anomalies)} anomalie(s) :\n" + "\n".join(anomalies[:15]) if anomalies else "\nAucune anomalie.")
                 + "\n\nRemplacer le référentiel de l'ouvrage ouvert ?")
        if confirmer(self, "Import du référentiel", texte, defaut_non=True):
            self.s.catalogue.types, self.s.catalogue.signaux, self.s.catalogue.regles = cat.types, cat.signaux, cat.regles
            self._apres()
            self._remplir_liste()

    def reprendre_livre(self):
        from genvar import chemins
        from genvar.catalogue import Catalogue
        livre = Catalogue.charger(chemins.fichier_catalogue_origine())
        if not confirmer(self, "Référentiel livré",
                         f"Remplacer le référentiel de l'ouvrage ouvert par celui livré avec l'outil ?\n"
                         f"Version : {livre.version} — {len(livre.types)} types, {len(livre.signaux)} signaux, "
                         f"{len(livre.regles)} règles.\n\nLes équipements déjà déclarés sont conservés ; leurs signaux "
                         "seront recalculés avec ce référentiel (vérifier ensuite les contrôles).", defaut_non=True):
            return
        self.s.catalogue.types, self.s.catalogue.signaux, self.s.catalogue.regles = livre.types, livre.signaux, livre.regles
        self.s.catalogue.version = livre.version
        self._apres()
        self._remplir_liste()

    def sauver_commun(self):
        anomalies = self.s.catalogue.anomalies()
        if anomalies and not confirmer(self, "Référentiel partagé", f"{len(anomalies)} anomalie(s) dans le référentiel, "
                                       f"par exemple :\n{anomalies[0]}\n\nPublier quand même ?", defaut_non=True):
            return
        if not confirmer(self, "Référentiel partagé", "Publier ce référentiel pour les FUTURS ouvrages ?\n"
                         "Les ouvrages déjà enregistrés conservent leur propre version.", defaut_non=True):
            return
        self.s.enregistrer_catalogue()
        self.s._catalogue_commun = copy.deepcopy(self.s.catalogue)
        notifier(self, "Référentiel partagé publié. Les ouvrages enregistrés ne sont pas modifiés.")
