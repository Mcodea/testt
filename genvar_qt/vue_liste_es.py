"""Liste des E/S du projet neuf : premier livrable, construit à partir des équipements configurés.

Trois zones : bilan matériel en tête, tableau filtrable au centre, propriétés de l'E/S sélectionnée à
droite (désignation, type, raccordement, module / voie, adresse, validation). La liste est indépendante
des variables de supervision : elle s'exporte dès que les équipements sont déclarés.
"""
import os

from PySide6.QtCore import Qt, Signal, QMarginsF
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
                               QSplitter, QFormLayout, QCheckBox, QToolButton, QMenu, QFileDialog, QDialog,
                               QDialogButtonBox, QScrollArea)

from genvar import chemins
from genvar.modele import TYPES_POINT, RACCORDEMENTS
from genvar.session import RegleMetier
from . import style
from .composants import (Page, Carte, Indicateur, Segment, bouton, avertir, informer, confirmer, notifier,
                         legende, separateur, champ_recherche)
from .tableaux import Tableau, Colonne, cle_tri_adresse, ROLE_OBJET

TOUS = "__tous__"


class DialogueAjoutES(QDialog):
    def __init__(self, parent, session, ident_defaut=None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter une E/S")
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        f = QFormLayout()
        lay.addLayout(f)
        self.eq = QComboBox()
        for e in session.equipements_tries():
            self.eq.addItem(f"{session.ouvrage.repere(e)} — {session.catalogue.designation(e.type)}", e.ident)
        self.eq.setCurrentIndex(max(0, self.eq.findData(ident_defaut)))
        self.point = QComboBox(); self.point.addItems(["ET", "ST", "EA", "SA"])
        self.code = QLineEdit(); self.code.setPlaceholderText("ex. DEF_COUPLE → ET_…_DEF_COUPLE")
        self.designation = QLineEdit(); self.designation.setPlaceholderText("ex. Défaut couple actionneur")
        for t, w in (("Équipement", self.eq), ("Point", self.point), ("Code", self.code), ("Désignation", self.designation)):
            f.addRow(t, w)
        lay.addWidget(legende("L'E/S est propre à cet équipement (le référentiel n'est pas modifié). Pour qu'elle "
                              "produise une TS ou une TM, ajouter aussi le signal dans la fiche de l'équipement.", "aide"))
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        b.button(QDialogButtonBox.StandardButton.Ok).setText("Ajouter")
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        lay.addWidget(b)


class DialogueModules(QDialog):
    """Cartes d'E/S déclarées (R5), réserve minimale et implantation automatique proposée (R9, R10).

    L'outil n'invente aucun module : il place les E/S sur les cartes déclarées ici. Les voies
    implantées restent « proposées » jusqu'à la validation de chaque E/S.
    """

    def __init__(self, parent, session):
        from PySide6.QtWidgets import QSpinBox
        from genvar.cartes_es import CARTES, NATURES
        super().__init__(parent)
        self.s = session
        self.change = False
        self.setWindowTitle("Modules d'E/S et implantation")
        self.resize(820, 560)
        lay = QVBoxLayout(self)
        lay.addWidget(legende("1. Déclarer les cartes réellement prévues (rack, position, référence). "
                              "2. « Implanter » : l'outil propose une voie à chaque E/S câblée sans voie, équipement "
                              "par équipement, en gardant la réserve minimale. 3. Vérifier puis valider les E/S.",
                              "aide"))
        self.t = Tableau([
            Colonne("mod", "Rack.pos", lambda b: b["module"], 70),
            Colonne("nat", "Nature", lambda b: b["nature"], 60, alignement=Qt.AlignmentFlag.AlignCenter),
            Colonne("ref", "Référence", lambda b: b["reference"], 140, etirable=True),
            Colonne("v", "Voies", lambda b: b["voies"], 60, alignement=Qt.AlignmentFlag.AlignCenter),
            Colonne("o", "Occupées", lambda b: b["occupees"], 70, alignement=Qt.AlignmentFlag.AlignCenter),
            Colonne("r", "Réserve", lambda b: f"{b['reserve']} ({b['taux']:.0%})", 90,
                    alignement=Qt.AlignmentFlag.AlignCenter),
            Colonne("al", "", lambda b: "sous le seuil" if b["sous_seuil"] and b["occupees"] else "", 100),
        ], "modules_es")
        self.t.texte_vide = "Aucun module déclaré : ajouter les cartes ci-dessous."
        lay.addWidget(self.t, 1)
        ajout = QHBoxLayout()
        self.carte = QComboBox()
        self.carte.addItem("Autre carte…", None)
        for ref, nat, voies in CARTES:
            self.carte.addItem(f"{ref} — {voies} {nat}", (ref, nat, voies))
        self.rack = QSpinBox(); self.rack.setRange(0, 15)
        self.position = QSpinBox(); self.position.setRange(0, 31); self.position.setValue(2)
        self.nature = QComboBox(); self.nature.addItems(list(NATURES))
        self.voies = QSpinBox(); self.voies.setRange(1, 128); self.voies.setValue(16)
        self.carte.currentIndexChanged.connect(self._carte)
        for t, w in (("Carte", self.carte), ("Rack", self.rack), ("Position", self.position),
                     ("Nature", self.nature), ("Voies", self.voies)):
            ajout.addWidget(QLabel(t))
            ajout.addWidget(w)
        ajout.addWidget(bouton("Ajouter", self.ajouter, icone="ajouter"))
        lay.addLayout(ajout)
        actions = QHBoxLayout()
        actions.addWidget(bouton("Supprimer le module", self.supprimer, icone="supprimer", nom="discret"))
        actions.addWidget(QLabel("Réserve minimale"))
        self.reserve = QSpinBox(); self.reserve.setRange(0, 90); self.reserve.setSuffix(" %")
        self.reserve.setValue(round(session.ouvrage.reserve_min * 100))
        self.reserve.valueChanged.connect(self._reserve)
        actions.addWidget(self.reserve)
        actions.addStretch(1)
        actions.addWidget(bouton("Libérer les voies proposées", self.liberer, icone="supprimer",
                                 infobulle="Retire module et voie des E/S non validées, pour refaire l'implantation."))
        actions.addWidget(bouton("Implanter les E/S sans voie", self.implanter, primaire=True, icone="valider"))
        lay.addLayout(actions)
        self.etat = legende("", "aide")
        lay.addWidget(self.etat)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        b.rejected.connect(self.reject)
        b.accepted.connect(self.accept)
        lay.addWidget(b)
        self.rafraichir()

    def _carte(self):
        d = self.carte.currentData()
        if d:
            self.nature.setCurrentText(d[1])
            self.voies.setValue(d[2])

    def _reserve(self, v):
        self.s.definir_reserve(v / 100)
        self.change = True
        self.rafraichir()

    def rafraichir(self):
        lignes = self.s.bilan_modules()
        self.t.definir(lignes)
        a_placer = sum(1 for p in self.s.points() if p.raccordement != "Communication" and not p.adresse)
        self.etat.setText(f"{len(lignes)} module(s) déclaré(s) · {a_placer} E/S câblée(s) sans voie.")

    def ajouter(self):
        d = self.carte.currentData()
        try:
            self.s.ajouter_module(self.rack.value(), self.position.value(), self.nature.currentText(),
                                  self.voies.value(), d[0] if d else "")
        except RegleMetier as ex:
            avertir(self, "Module", str(ex))
            return
        self.change = True
        self.position.setValue(min(31, self.position.value() + 1))
        self.rafraichir()

    def supprimer(self):
        b = self.t.objet_courant()
        if b is None:
            return
        try:
            self.s.supprimer_module(b["module"])
        except RegleMetier as ex:
            avertir(self, "Module", str(ex))
            return
        self.change = True
        self.rafraichir()

    def implanter(self):
        try:
            affectations, manquantes, depassements = self.s.apercu_implantation()
        except RegleMetier as ex:
            avertir(self, "Implantation", str(ex))
            return
        if not self.s.ouvrage.modules:
            avertir(self, "Implantation", "Déclarez d'abord les modules d'E/S.")
            return
        if not affectations and not manquantes:
            informer(self, "Implantation", "Toutes les E/S câblées ont déjà une voie.")
            return
        texte = f"{len(affectations)} E/S recevront une voie proposée (non validée)."
        if manquantes:
            texte += "\nVoies manquantes : " + ", ".join(f"{n} {k}" for k, n in manquantes.items()) + \
                     " — ajouter des modules ; rien n'est inventé."
        if depassements:
            texte += "\nRéserve sous le seuil sur : " + ", ".join(depassements) + "."
        if not affectations or not confirmer(self, "Implanter les E/S", texte + "\n\nContinuer ?"):
            if not affectations:
                avertir(self, "Implantation", texte)
            return
        self.s.implanter_es()
        self.change = True
        self.rafraichir()

    def liberer(self):
        if confirmer(self, "Libérer", "Retirer module, voie et adresse de toutes les E/S NON validées ?",
                     defaut_non=True):
            n = self.s.liberer_voies_proposees()
            self.change = self.change or bool(n)
            self.rafraichir()


class VueES(Page):
    modifie = Signal()

    def __init__(self, session, parent=None):
        super().__init__("Liste des E/S", "Entrées / sorties physiques construites à partir des équipements configurés. "
                         "Premier livrable du projet neuf : schémas, choix des modules, études d'automatisme.", parent)
        self.s = session
        self.points = []
        self._courant = None
        self.b_ajout = bouton("Ajouter une E/S…", self.ajouter, icone="ajouter")
        self.b_export = QToolButton()
        self.b_export.setObjectName("bouton")
        self.b_export.setText("Exporter la liste")
        self.b_export.setIcon(style.icone("export", style.SECONDAIRE, 16))
        self.b_export.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.b_export.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.b_export)
        menu.addAction("Excel — liste de travail (.xlsx)…", self.exporter_excel)
        menu.addAction("PDF — diffusion (.pdf)…", self.exporter_pdf)
        menu.addAction("Excel — cartes d'E/S par module (.xlsx)…", self.exporter_cartes)
        menu.addSeparator()
        menu.addAction("Control Expert — variables d'E/S adressées (.xsy)…", self.exporter_xsy)
        a = menu.addAction("SOFREL S4W — format à établir sur fichier réel")
        a.setEnabled(False)
        self.b_export.setMenu(menu)
        self.b_modules = bouton("Modules et implantation…", self.modules, icone="es",
                                infobulle="Déclarer les cartes d'E/S et proposer une voie à chaque E/S (règles R5 à R10).")
        self.entete.droite.addWidget(self.b_modules)
        self.entete.droite.addWidget(self.b_ajout)
        self.entete.droite.addWidget(self.b_export)

        # ---------------------------------------------------------- bilan matériel
        chiffres = QHBoxLayout()
        chiffres.setSpacing(10)
        self.k = {}
        for cle, libelle in (("ET", "entrées TOR"), ("ST", "sorties TOR"), ("EA", "entrées ana."),
                             ("SA", "sorties ana."), ("COM", "par communication"), ("VAL", "à valider"),
                             ("ADR", "sans adresse")):
            ind = Indicateur(libelle, cliquable=True)
            ind.clique.connect(lambda c=cle: self._filtre_rapide(c))
            self.k[cle] = ind
            chiffres.addWidget(ind, 1)
        self.disposition.addLayout(chiffres)

        sep = QSplitter(Qt.Orientation.Horizontal)
        sep.setChildrenCollapsible(False)
        # ---------------------------------------------------------- tableau
        centre = Carte()
        filtres = QHBoxLayout()
        filtres.setSpacing(8)
        self.recherche = champ_recherche("Rechercher une E/S, un repère, une désignation…")
        self.f_point = Segment([("Tous", "Tous"), ("ET", "ET"), ("ST", "ST"), ("EA", "EA"), ("SA", "SA")])
        self.f_point.definir("Tous")
        self.f = QComboBox()
        self.f.addItems(["Toutes", "À valider", "Sans adresse", "Communication", "Validées"])
        self.f_eq = QComboBox()
        self.f_eq.setMinimumWidth(150)
        filtres.addWidget(self.recherche, 1)
        filtres.addWidget(self.f_point)
        filtres.addWidget(self.f)
        filtres.addWidget(self.f_eq)
        centre.disposition.addLayout(filtres)
        self.t = Tableau([
            Colonne("etat", "", lambda p: "", 26, icone=lambda p: style.icone_gravite(
                "OK" if p.validee and (p.adresse or p.raccordement == "Communication") else "Alerte" if p.validee else "Info"),
                tri=lambda p: (p.validee, bool(p.adresse))),
            Colonne("rep", "Repère", lambda p: p.repere, 125),
            Colonne("uf", "UF", lambda p: p.uf or "—", 55),
            Colonne("pt", "Point", lambda p: p.point, 50, alignement=Qt.AlignmentFlag.AlignCenter),
            Colonne("nom", "Nom de l'E/S", lambda p: p.nom, 210),
            Colonne("des", "Désignation", lambda p: p.commentaire, 260, etirable=True),
            Colonne("sens", "Sens contact", lambda p: p.sens, 120),
            Colonne("type", "Type", lambda p: p.type_logique, 60),
            Colonne("rac", "Raccord.", lambda p: "Comm." if p.raccordement == "Communication" else "Câblé", 70),
            Colonne("mod", "Module", lambda p: p.module, 60),
            Colonne("voie", "Voie", lambda p: p.voie, 45),
            Colonne("adr", "Adresse", lambda p: p.adresse or ("—" if p.raccordement == "Communication" else "à saisir"), 95,
                    tri=lambda p: cle_tri_adresse(p.adresse) or "~"),
            Colonne("val", "Statut", lambda p: "Validée" if p.validee else "À valider", 80),
            Colonne("var", "Variable liée", lambda p: p.variable or "(locale)", 200, visible=False),
        ], "liste_es_v1")
        self.t.texte_vide = ("Aucune E/S.\nAjouter des équipements dans « Ouvrage & équipements » : leurs E/S "
                             "physiques apparaissent ici selon les options choisies.")
        self.t.modele.italique = lambda p: not p.validee
        self.t.selection_changee.connect(self._choisie)
        self.t.objet_active.connect(lambda _: self.d_designation.setFocus())
        centre.ajouter(self.t, 1)
        bas = QHBoxLayout()
        bas.addWidget(bouton("Valider la sélection", self.valider_selection, primaire=True, icone="valider"))
        bas.addWidget(bouton("Valider tout l'affichage", self.valider_affichees, icone="valider"))
        bas.addWidget(bouton("Retirer de la liste", self.retirer, icone="supprimer", nom="danger"))
        bas.addStretch(1)
        self.compte = legende("", retour=False)
        bas.addWidget(self.compte)
        centre.disposition.addLayout(bas)
        sep.addWidget(centre)

        # ---------------------------------------------------------- propriétés de l'E/S
        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setFrameShape(QFrame.Shape.NoFrame)
        zone.setMinimumWidth(330)
        self.panneau = Carte("Propriétés de l'E/S")
        d = self.panneau.disposition
        self.d_nom = QLabel("Sélectionner une E/S")
        self.d_nom.setObjectName("titreLigne")
        self.d_nom.setWordWrap(True)
        d.addWidget(self.d_nom)
        self.d_info = legende("")
        d.addWidget(self.d_info)
        form = QFormLayout()
        self.d_designation = QLineEdit()
        self.d_sens = QLineEdit(); self.d_sens.setPlaceholderText("ex. 1 = Défaut")
        self.d_sens.setToolTip("État de la voie à 1 (règle R7). Proposé par le référentiel, modifiable ici.")
        self.d_type = QComboBox()
        self.d_rac = QComboBox(); self.d_rac.addItems(list(RACCORDEMENTS))
        self.d_module = QLineEdit(); self.d_module.setPlaceholderText("rack.emplacement, ex. 0.3")
        self.d_voie = QLineEdit(); self.d_voie.setPlaceholderText("ex. 5")
        self.d_adresse = QLineEdit(); self.d_adresse.setPlaceholderText("calculée depuis module + voie, ou saisie")
        self.d_valide = QCheckBox("E/S vérifiée (validée)")
        for t, w in (("Désignation", self.d_designation), ("Sens contact", self.d_sens), ("Type", self.d_type), ("Raccordement", self.d_rac),
                     ("Module", self.d_module), ("Voie", self.d_voie), ("Adresse", self.d_adresse), ("", self.d_valide)):
            form.addRow(t, w)
        d.addLayout(form)
        self.d_apercu = legende("", "aide")
        d.addWidget(self.d_apercu)
        self.b_enreg = bouton("Enregistrer l'E/S", self.enregistrer, primaire=True, icone="enregistrer")
        d.addWidget(self.b_enreg)
        d.addWidget(separateur())
        d.addWidget(legende("Adresse : jamais inventée. Elle est calculée à partir du module (rack.emplacement) et "
                            "de la voie que vous saisissez (M340 / M580 : %I0.3.5), ou saisie telle quelle. "
                            "« Communication » : information reçue par bus, sans voie ni adresse %I/%Q.", "aide"))
        d.addStretch(1)
        zone.setWidget(self.panneau)
        sep.addWidget(zone)
        sep.setStretchFactor(0, 3)
        sep.setStretchFactor(1, 1)
        sep.setSizes([980, 360])
        self.disposition.addWidget(sep, 1)

        self.recherche.textChanged.connect(self.filtrer)
        self.f_point.change.connect(self.filtrer)
        self.f.currentIndexChanged.connect(self.filtrer)
        self.f_eq.currentIndexChanged.connect(self.filtrer)
        for w in (self.d_module, self.d_voie):
            w.textChanged.connect(self._apercu_adresse)
        self.d_rac.currentTextChanged.connect(self._apercu_adresse)
        self._choisie()

    # ================================================================== données
    def charger(self):
        actif = self.s.ouvrage.mode == "Neuf"
        self.setEnabled(actif)
        self.points = self.s.liste_es() if actif else []
        self.t.definir(self.points)
        courant = self.f_eq.currentData()
        self.f_eq.blockSignals(True)
        self.f_eq.clear()
        self.f_eq.addItem("Tous les équipements", TOUS)
        for e in self.s.equipements_tries():
            self.f_eq.addItem(self.s.ouvrage.repere(e), e.ident)
        self.f_eq.setCurrentIndex(max(0, self.f_eq.findData(courant)))
        self.f_eq.blockSignals(False)
        b = self.s.bilan_es() if actif else {"par_point": {}, "communication": 0, "non_validees": 0, "sans_adresse": 0}
        for pt in ("ET", "ST", "EA", "SA"):
            self.k[pt].definir(b["par_point"].get(pt, 0))
        self.k["COM"].definir(b["communication"])
        self.k["VAL"].definir(b["non_validees"], "Alerte" if b["non_validees"] else "OK")
        self.k["ADR"].definir(b["sans_adresse"], "Alerte" if b["sans_adresse"] else "OK")
        self.filtrer()
        self._choisie()

    def filtrer(self, *_):
        pt, etat, eq = self.f_point.valeur() or "Tous", self.f.currentText(), self.f_eq.currentData()

        def ok(p):
            if pt != "Tous" and p.point != pt:
                return False
            if eq not in (None, TOUS) and p.ident_eq != eq:
                return False
            return {"Toutes": True, "À valider": not p.validee, "Validées": p.validee,
                    "Sans adresse": not p.adresse and p.raccordement != "Communication",
                    "Communication": p.raccordement == "Communication"}.get(etat, True)
        self.t.filtre.definir_condition(ok)
        self.t.filtre.definir_texte(self.recherche.text())
        vus, total = self.t.nombre_visible(), len(self.points)
        self.compte.setText(f"{total} E/S" if vus == total else f"{vus} affichée(s) sur {total}")

    def _filtre_rapide(self, cle):
        if cle in ("ET", "ST", "EA", "SA"):
            self.f_point.definir(cle)
            self.f.setCurrentIndex(0)
        else:
            self.f_point.definir("Tous")
            self.f.setCurrentText({"COM": "Communication", "VAL": "À valider", "ADR": "Sans adresse"}[cle])
        self.filtrer()

    # ================================================================== panneau
    def _choisie(self, *_):
        p = self.t.objet_courant()
        self._courant = p
        for w in (self.d_designation, self.d_sens, self.d_type, self.d_rac, self.d_module, self.d_voie,
                  self.d_adresse, self.d_valide, self.b_enreg):
            w.setEnabled(p is not None)
        if p is None:
            self.d_nom.setText("Sélectionner une E/S dans la liste")
            self.d_info.setText("")
            self.d_apercu.setText("")
            return
        self.d_nom.setText(p.nom)
        self.d_info.setText(f"{p.repere} · {p.point} · {p.information}\n"
                            f"Variable liée : {p.variable or 'aucune (E/S locale)'} · origine : {p.origine}")
        self.d_designation.setText(p.designation)
        self.d_designation.setPlaceholderText(p.commentaire if not p.designation else "")
        self.d_sens.setText(p.sens)
        self.d_type.blockSignals(True)
        self.d_type.clear()
        self.d_type.addItems(list(TYPES_POINT[p.point]))
        self.d_type.setCurrentText(p.type_logique)
        self.d_type.blockSignals(False)
        self.d_rac.setCurrentText(p.raccordement)
        self.d_module.setText(p.module)
        self.d_voie.setText(p.voie)
        self.d_adresse.setText(p.adresse)
        self.d_valide.setChecked(p.validee)
        self._apercu_adresse()

    def _apercu_adresse(self, *_):
        p = self._courant
        if p is None:
            return
        com = self.d_rac.currentText() == "Communication"
        for w in (self.d_module, self.d_voie, self.d_adresse):
            w.setEnabled(not com)
        if com:
            self.d_apercu.setText("Information par communication : aucune adresse physique.")
            return
        try:
            adr = self.s.adresse_module(p.point, self.d_module.text(), self.d_voie.text())
        except RegleMetier as ex:
            self.d_apercu.setText(f"⚠ {ex}")
            return
        if adr:
            self.d_apercu.setText(f"Adresse calculée : {adr}")
            self.d_adresse.setText(adr)
        else:
            self.d_apercu.setText("Saisir module + voie, ou l'adresse directement (elle peut rester vide pour l'instant).")

    def enregistrer(self):
        p = self._courant
        if p is None:
            return
        com = self.d_rac.currentText() == "Communication"
        try:
            self.s.definir_es(p.ident_eq, p.cle, designation=self.d_designation.text(),
                              type_logique=self.d_type.currentText(), raccordement=self.d_rac.currentText(),
                              module="" if com else self.d_module.text(), voie="" if com else self.d_voie.text(),
                              adresse="" if com else self.d_adresse.text(), validee=self.d_valide.isChecked(),
                              sens=self.d_sens.text())
        except RegleMetier as ex:
            avertir(self, "E/S", str(ex))
            return
        cle = (p.ident_eq, p.cle)
        self.charger()
        self.modifie.emit()
        self.t.selectionner(lambda x: (x.ident_eq, x.cle) == cle)
        notifier(self, f"{p.nom} enregistrée.")

    # ================================================================== actions de liste
    def valider_selection(self):
        choisis = self.t.objets_selectionnes()
        if not choisis:
            informer(self, "Valider", "Sélectionner une ou plusieurs E/S.")
            return
        n = self.s.valider_es([(p.ident_eq, p.cle) for p in choisis])
        self.charger(); self.modifie.emit()
        notifier(self, f"{n} E/S validée(s).")

    def valider_affichees(self):
        visibles = [self.t.filtre.data(self.t.filtre.index(r, 0), ROLE_OBJET) for r in range(self.t.nombre_visible())]
        a_valider = [p for p in visibles if not p.validee]
        if a_valider and confirmer(self, "Valider", f"Valider {len(a_valider)} E/S affichée(s) ?\n"
                                   "Vous attestez qu'elles correspondent à l'installation prévue."):
            n = self.s.valider_es([(p.ident_eq, p.cle) for p in a_valider])
            self.charger(); self.modifie.emit()
            notifier(self, f"{n} E/S validée(s).")

    def retirer(self):
        choisis = self.t.objets_selectionnes()
        if not choisis or not confirmer(self, "Retirer", f"Retirer {len(choisis)} E/S de la liste ?\n"
                                        "Une E/S du référentiel est seulement écartée (réversible dans la fiche de "
                                        "l'équipement) ; une E/S ajoutée à la main est supprimée.", defaut_non=True):
            return
        refus = []
        for p in choisis:
            try:
                self.s.retirer_es(p.ident_eq, p.cle)
            except RegleMetier as ex:
                refus.append(f"{p.nom} : {ex}")
        self.charger(); self.modifie.emit()
        if refus:
            avertir(self, "Retirer", "\n".join(refus[:10]))

    def ajouter(self):
        if not self.s.ouvrage.equipements:
            informer(self, "Ajouter une E/S", "Ajouter d'abord un équipement.")
            return
        d = DialogueAjoutES(self, self.s, self._courant.ident_eq if self._courant else None)
        while d.exec():
            try:
                cle = self.s.ajouter_es(d.eq.currentData(), d.point.currentText(), d.code.text(), d.designation.text())
            except RegleMetier as ex:
                avertir(self, "Ajouter une E/S", str(ex))
                continue
            ident = d.eq.currentData()
            self.charger(); self.modifie.emit()
            self.t.selectionner(lambda x: (x.ident_eq, x.cle) == (ident, cle))
            return

    # ================================================================== exports
    def _chemin(self, titre, extension, filtre):
        nom = f"{self.s.nom_fichier_propose()}_liste_ES.{extension}"
        p, _ = QFileDialog.getSaveFileName(self, titre, os.path.join(chemins.dossier_exports(), nom), filtre)
        if p and not p.lower().endswith("." + extension):
            p += "." + extension
        return p

    def _avertir_manques(self):
        b = self.s.bilan_es()
        if b["non_validees"] or b["sans_adresse"]:
            return confirmer(self, "Liste incomplète", f"{b['non_validees']} E/S à valider et {b['sans_adresse']} "
                             "sans adresse physique.\nLe document les signalera comme « à compléter ». Continuer ?")
        return True

    def exporter_excel(self):
        if not self._avertir_manques():
            return
        p = self._chemin("Exporter la liste des E/S", "xlsx", "Excel (*.xlsx)")
        if not p:
            return
        try:
            n = self.s.exporter_liste_es(p)
        except PermissionError:
            avertir(self, "Export", "Le fichier est ouvert dans Excel : le fermer puis recommencer.")
            return
        notifier(self, f"Liste des E/S exportée ({n} E/S) : {os.path.basename(p)}")

    def exporter_pdf(self):
        if not self._avertir_manques():
            return
        p = self._chemin("Exporter la liste des E/S en PDF", "pdf", "PDF (*.pdf)")
        if not p:
            return
        self.ecrire_pdf(p)
        notifier(self, f"PDF créé : {os.path.basename(p)}")

    def ecrire_pdf(self, p):
        """Imprime la liste (HTML produit par le moteur) dans un PDF A4 paysage."""
        from PySide6.QtGui import QTextDocument, QPdfWriter, QPageSize, QPageLayout
        doc = QTextDocument()
        doc.setHtml(self.s.html_liste_es())
        ecrivain = QPdfWriter(p)
        ecrivain.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        ecrivain.setPageOrientation(QPageLayout.Orientation.Landscape)
        ecrivain.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)
        ecrivain.setTitle(f"Liste des E/S — {self.s.ouvrage.prefixe()}")
        doc.print_(ecrivain)

    def modules(self):
        d = DialogueModules(self, self.s)
        d.exec()
        if d.change:
            self.charger()
            self.modifie.emit()

    def exporter_cartes(self):
        if not self.s.ouvrage.modules:
            informer(self, "Cartes d'E/S", "Déclarez d'abord les modules (bouton « Modules et implantation… »).")
            return
        nom = f"{self.s.nom_fichier_propose()}_cartes_ES.xlsx"
        p, _ = QFileDialog.getSaveFileName(self, "Exporter les cartes d'E/S",
                                           os.path.join(chemins.dossier_exports(), nom), "Excel (*.xlsx)")
        if not p:
            return
        if not p.lower().endswith(".xlsx"):
            p += ".xlsx"
        try:
            n = self.s.exporter_cartes_es(p)
        except PermissionError:
            avertir(self, "Export", "Le fichier est ouvert dans Excel : le fermer puis recommencer.")
            return
        notifier(self, f"Cartes d'E/S exportées ({n} voies occupées) : {os.path.basename(p)}")

    def exporter_xsy(self):
        b = self.s.bilan_es()
        if b["sans_adresse"] and not confirmer(self, "XSY des E/S", f"{b['sans_adresse']} E/S câblée(s) sans adresse "
                                               "physique ne seront PAS exportées (une variable d'E/S doit être localisée). "
                                               "Continuer ?", defaut_non=True):
            return
        p = self._chemin("Exporter les variables d'E/S pour Control Expert", "xsy", "Fichier XSY (*.xsy)")
        if not p:
            return
        try:
            n = self.s.exporter_xsy_es(p)
        except (RegleMetier, OSError) as ex:
            avertir(self, "Export XSY", str(ex))
            return
        informer(self, "Export XSY", f"{n} variable(s) d'E/S exportée(s).\nFichier de travail : import à vérifier "
                 "dans Control Expert (Données › Variables › Importer) sur une application d'essai.")
