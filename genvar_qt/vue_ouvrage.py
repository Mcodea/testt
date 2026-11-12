"""Écran « Ouvrage & équipements », en mode explorateur.

À gauche, l'arborescence de l'ouvrage sur toute la hauteur ; à droite, une seule vue à la fois,
choisie par la sélection dans l'arbre : identification (et sous-ensembles), liste des équipements,
ou propriétés de l'équipement sélectionné.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QSplitter, QWidget, QVBoxLayout,
                               QStackedWidget, QScrollArea, QFrame, QInputDialog)

from genvar.session import RegleMetier

from . import style
from .composants import Page, Carte, Segment, Majuscules, bouton, avertir, informer, confirmer, champ_recherche, caption
from .dialogues import DialogueSousEnsemble, DialogueEquipement, DialogueUF
from .tableaux import Tableau, Colonne
from .arbre_ouvrage import ArbreOuvrage

TOUS = "__tous__"


class VueOuvrage(Page):
    modifie = Signal()            # l'ouvrage a changé : la fenêtre met à jour titre, badges et autres écrans
    mode_change = Signal()
    voir_es = Signal(str)         # ouvrir la liste des E/S filtrée sur un équipement

    def __init__(self, session, parent=None):
        super().__init__("Ouvrage & équipements",
                         "À gauche la structure de l'ouvrage ; à droite ce qui est sélectionné.", parent)
        self.s = session
        self._chargement = False
        self._anomalies = {}

        # ---------------------------------------------------------- repère en en-tête
        bloc = QVBoxLayout()
        bloc.setSpacing(0)
        leg = QLabel("Préfixe des repères")
        leg.setObjectName("legende")
        leg.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.prefixe = QLabel("—")
        self.prefixe.setObjectName("prefixe")
        self.prefixe.setAlignment(Qt.AlignmentFlag.AlignRight)
        bloc.addWidget(leg)
        bloc.addWidget(self.prefixe)
        self.entete.droite.addLayout(bloc)

        # ============================================================ explorateur
        explorateur = QSplitter(Qt.Orientation.Horizontal)
        explorateur.setChildrenCollapsible(False)
        explorateur.addWidget(self._construire_arbre())

        # à droite : le détail du nœud sélectionné dans l'arbre (ouvrage, UF, équipement)
        self.pile_droite = QStackedWidget()
        self.pile_droite.addWidget(self._construire_identification())
        self.pile_droite.addWidget(self._construire_equipements())
        self.pile_droite.addWidget(self._construire_panneau())
        explorateur.addWidget(self.pile_droite)
        explorateur.setStretchFactor(0, 2)
        explorateur.setStretchFactor(1, 5)
        explorateur.setSizes([400, 1000])
        self.disposition.addWidget(explorateur, 1)

        self.recherche.textChanged.connect(self._filtrer)
        self.f_se.currentIndexChanged.connect(self._filtrer)
        self.f_uf.currentIndexChanged.connect(self._filtrer)
        self.t_se.selection_changee.connect(self._se_choisi)
        self.montrer("ident")

    # ============================================================== construction
    VUES = ("ident", "eqs", "eq")

    def montrer(self, vue):
        """Affiche le détail de droite : ident (ouvrage), eqs (équipements d'une UF) ou eq (un équipement)."""
        if vue not in self.VUES:
            return
        self._vue = vue
        self.pile_droite.setCurrentIndex(self.VUES.index(vue))

    def vue_courante(self):
        return getattr(self, "_vue", "ident")

    def _construire_arbre(self):
        c = Carte("Structure de l'ouvrage")
        c.setMinimumWidth(320)
        self.b_deplier = bouton("Tout déplier", self._deplier_tout, nom="lien")
        c.ajouter_action(self.b_deplier)
        outils = QHBoxLayout()
        outils.setSpacing(6)
        outils.addWidget(bouton("Unité fonctionnelle", self._ajouter_uf, icone="ajouter",
                                infobulle="Ajouter une UF (ex. UF01 Stockage, sous-ensemble 11). Facultatif."))
        outils.addWidget(bouton("Équipement", lambda: self._ajouter_eq(self._uf_courante()), primaire=True,
                                icone="ajouter", infobulle="Ajouter un équipement dans l'UF sélectionnée"))
        outils.addStretch(1)
        c.disposition.addLayout(outils)
        self.arbre = ArbreOuvrage()
        self.arbre.action.connect(self._action_arbre)
        c.ajouter(self.arbre, 1)
        aide = QLabel("Clic : détail à droite · double-clic : fiche · clic droit : autres actions")
        aide.setObjectName("aide")
        aide.setWordWrap(True)
        c.ajouter(aide)
        return c

    def _construire_identification(self):
        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setFrameShape(QFrame.Shape.NoFrame)
        contenu = QWidget()
        v = QVBoxLayout(contenu)
        v.setContentsMargins(0, 0, 4, 0)
        v.setSpacing(10)

        carte = Carte("Identification de l'ouvrage")
        self.b_tous = bouton("Voir tous les équipements", lambda: self._voir_liste(TOUS), nom="lien")
        carte.ajouter_action(self.b_tous)
        self.lieu = QLineEdit()
        self.lieu.setValidator(Majuscules(4, self.lieu))
        self.lieu.setMaxLength(4)
        self.lieu.setPlaceholderText("ex. ATMS")
        self.lieu.setToolTip("Code de lieu : 4 lettres ou chiffres (ex. ATMS). Premier morceau de chaque repère.")
        self.lieu.setMaximumWidth(110)
        self.code = QLineEdit()
        self.code.setValidator(Majuscules(2, self.code))
        self.code.setMaxLength(2)
        self.code.setPlaceholderText("ex. RV")
        self.code.setToolTip("Code de l'ouvrage : 2 lettres (ex. RV réservoir, SP station de pompage).")
        self.code.setMaximumWidth(110)
        self.libelle = QLineEdit()
        self.libelle.setPlaceholderText("ex. Réservoir de la Croix")
        self.automate = QComboBox()
        self.automate.addItems(["M580", "M340", "TSX Premium", "TSX Micro"])
        self.projet = QLineEdit()
        self.projet.setPlaceholderText("nom du projet Control Expert (facultatif)")
        self.mode = Segment([("Neuf", "Projet neuf"), ("Existant", "Projet existant")])
        self.mode.setToolTip("Projet neuf : variables générées depuis le catalogue.\n"
                             "Projet existant : variables lues dans le XSY de l'automate, jamais renommées.")
        self.aide_mode = QLabel("")
        self.aide_mode.setObjectName("legende")
        from PySide6.QtWidgets import QCheckBox
        self.lieu_nom = QCheckBox("Lieu dans les noms")
        self.lieu_nom.setToolTip("Décoché (règle R2) : ET_RV01EX02_DISPO. Coché : ET_ATMSRV01EX02_DISPO.\n"
                                 "Le repère (PCF) garde toujours le lieu.")
        self.revision = QLineEdit()
        self.revision.setMaximumWidth(95)
        self.revision.setPlaceholderText("A")
        self.statut = QComboBox()
        self.statut.addItems(["Brouillon", "En cours", "À contrôler", "Validé"])
        self.localisation = QLineEdit()
        self.localisation.setPlaceholderText("commune, adresse du site")
        self.type_ouvrage = QComboBox()
        self.type_ouvrage.setEditable(True)
        self.type_ouvrage.addItems(["", "Réservoir", "Station de pompage", "Forage", "Usine de traitement",
                                    "Poste de rechloration", "Surpresseur", "Chambre de vannes"])
        self.environnement = QComboBox()
        self.environnement.addItems(["Control Expert", "Unity Pro", "PL7 Pro"])
        self.communication = QComboBox()
        self.communication.setEditable(True)
        self.communication.addItems(["", "Modbus TCP", "Modbus RTU", "SOFREL S4W", "OPC / OFS"])
        self.communication.setToolTip("Protocole de télétransmission par défaut (repris dans la table de "
                                      "télétransmission, modifiable ligne par ligne).")

        def etiquette(t):
            l = QLabel(t)
            l.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return l

        def section(titre, champs):
            """Petite grille à deux colonnes (étiquette, champ) × 2, précédée d'un intertitre."""
            carte.ajouter(caption(titre))
            g = QGridLayout()
            g.setHorizontalSpacing(10)
            g.setVerticalSpacing(6)
            for i, (lib, w) in enumerate(champs):
                ligne, col = divmod(i, 2)
                g.addWidget(etiquette(lib), ligne, col * 2)
                g.addWidget(w, ligne, col * 2 + 1)
            g.setColumnMinimumWidth(0, 120)
            g.setColumnMinimumWidth(2, 120)
            g.setColumnStretch(1, 1)
            g.setColumnStretch(3, 1)
            carte.disposition.addLayout(g)

        section("Repère", [("Lieu", self.lieu), ("Libellé", self.libelle), ("Code ouvrage", self.code),
                           ("Type d'ouvrage", self.type_ouvrage)])
        # composition du repère, morceau par morceau, avec la règle de chacun
        self.aide_repere = QLabel("")
        self.aide_repere.setTextFormat(Qt.TextFormat.RichText)
        self.aide_repere.setWordWrap(True)
        self.aide_repere.setObjectName("legende")
        carte.ajouter(self.aide_repere)
        section("Projet", [("Mode", self.mode), ("Automate", self.automate), ("Révision", self.revision),
                           ("Environnement", self.environnement), ("Avancement", self.statut),
                           ("Projet Control Expert", self.projet), ("Noms", self.lieu_nom)])
        carte.ajouter(self.aide_mode)
        section("Site", [("Localisation", self.localisation), ("Communication", self.communication)])
        v.addWidget(carte)

        self.lieu.textEdited.connect(lambda t: self._champ("lieu", t))
        self.code.textEdited.connect(lambda t: self._champ("code_ouvrage", t))
        self.libelle.textEdited.connect(lambda t: self._champ("libelle", t))
        self.projet.textEdited.connect(lambda t: self._champ("nom_projet", t))
        self.automate.currentTextChanged.connect(lambda t: self._champ("automate", t))
        self.revision.textEdited.connect(lambda t: self._champ("revision", t.strip().upper()))
        self.statut.currentTextChanged.connect(lambda t: self._champ("statut", t))
        self.mode.change.connect(self._changer_mode)
        self.lieu_nom.toggled.connect(lambda c: self._champ("lieu_dans_le_nom", bool(c)))
        self.localisation.textEdited.connect(lambda t: self._champ("localisation", t))
        self.type_ouvrage.currentTextChanged.connect(lambda t: self._champ("type_ouvrage", t))
        self.environnement.currentTextChanged.connect(lambda t: self._champ("environnement", t))
        self.communication.currentTextChanged.connect(lambda t: self._champ("communication", t))

        # --- sous-ensembles (entrent dans le repère)
        c_se = Carte("Codes sous-ensemble du repère",
                     sous_titre="Créés automatiquement avec les UF ou les équipements ; à gérer ici si besoin.")
        c_se.ajouter_action(bouton("Ajouter…", self._ajouter_se, icone="ajouter"))
        c_se.ajouter_action(bouton("Modifier…", self._modifier_se, icone="modifier", nom="discret"))
        self.b_sup_se = bouton("Supprimer", self._supprimer_se, icone="supprimer", nom="discret")
        c_se.ajouter_action(self.b_sup_se)
        self.t_se = Tableau([Colonne("code", "Code", lambda s: s.code, 70),
                             Colonne("lib", "Libellé", lambda s: s.libelle, 220, etirable=True),
                             Colonne("nb", "Équipements", lambda s: self.s.nombre_equipements(s.code), 100,
                                     alignement=Qt.AlignmentFlag.AlignCenter)], "ouvrage_sous_ensembles")
        self.t_se.texte_vide = "Aucun sous-ensemble : « Ajouter… » (ex. 11 Réservoir 1)."
        self.t_se.setSelectionMode(Tableau.SelectionMode.SingleSelection)
        self.t_se.objet_active.connect(lambda _: self._modifier_se())
        self.t_se.setMinimumHeight(110)
        self.t_se.setMaximumHeight(170)
        c_se.ajouter(self.t_se)
        v.addWidget(c_se)
        v.addStretch(1)
        zone.setWidget(contenu)
        return zone

    def _construire_equipements(self):
        c_eq = Carte("Équipements")
        self.ctx_titre = c_eq.titre
        self.b_mod_uf = bouton("Modifier l'UF…", self._modifier_groupe, icone="modifier", nom="discret")
        self.b_ranger = bouton("Ranger dans une UF…", self._ranger_communs, icone="dossier", nom="discret",
                               infobulle="Déplacer tous les équipements hors UF dans une unité fonctionnelle.")
        self.b_sup_uf = bouton("Supprimer l'UF", self._supprimer_groupe, icone="supprimer", nom="discret")
        for b in (self.b_mod_uf, self.b_ranger, self.b_sup_uf):
            c_eq.ajouter_action(b)
        self.ctx_info = QLabel("")
        self.ctx_info.setObjectName("legende")
        self.ctx_info.setWordWrap(True)
        c_eq.ajouter(self.ctx_info)
        self.compte_eq = QLabel("")
        self.compte_eq.setObjectName("legende")
        c_eq.ajouter_action(self.compte_eq)
        filtres = QHBoxLayout()
        self.recherche = champ_recherche("Rechercher un repère, un type, un libellé…")
        self.recherche.setMinimumWidth(220)
        self.f_se = QComboBox()
        self.f_se.setMinimumWidth(150)
        self.f_se.setToolTip("Filtrer par sous-ensemble")
        self.f_uf = QComboBox()
        self.f_uf.setMinimumWidth(150)
        self.f_uf.setToolTip("Filtrer par unité fonctionnelle (ou cliquer une UF dans l'arborescence)")
        filtres.addWidget(self.recherche, 1)
        filtres.addWidget(QLabel("Sous-ensemble"))
        filtres.addWidget(self.f_se)
        filtres.addWidget(QLabel("UF"))
        filtres.addWidget(self.f_uf)
        filtres.addWidget(bouton("Effacer", self._effacer_filtres, nom="lien", infobulle="Afficher tous les équipements"))
        c_eq.disposition.addLayout(filtres)

        a = Qt.AlignmentFlag.AlignCenter
        self.t_eq = Tableau([
            Colonne("etat", "", lambda e: "", 28, icone=lambda e: style.icone_gravite(self._etat(e)),
                    tri=lambda e: {"Erreur": 0, "Alerte": 1}.get(self._etat(e), 2),
                    infobulle=lambda e: self._infobulle(e)),
            Colonne("repere", "Repère", lambda e: self.s.ouvrage.repere(e), 140),
            Colonne("uf", "UF", lambda e: e.uf, 60, alignement=a),
            Colonne("type", "Type", lambda e: e.type, 50, alignement=a),
            Colonne("desig", "Désignation", lambda e: self.s.catalogue.designation(e.type), 180),
            Colonne("lib", "Libellé", lambda e: e.libelle, 180, etirable=True),
            Colonne("opt", "Options", lambda e: ", ".join(e.options), 160, visible=False),
            Colonne("sig", "Signaux", lambda e: self.s.nombre_signaux(e), 64, alignement=a),
            Colonne("propres", "Propres", lambda e: len(e.ajouts) or "", 64, alignement=a, visible=False),
            Colonne("ano", "Anomalies", lambda e: self._texte_anomalies(e), 80, alignement=a),
        ], "ouvrage_equipements_v2")
        self.t_eq.texte_vide = "Aucun équipement ici.\n« Ajouter un équipement… » ci-dessous."
        self.t_eq.objet_active.connect(lambda _: self._modifier_eq())
        self.t_eq.selection_changee.connect(self._maj_boutons)
        self.t_eq.selection_changee.connect(self._maj_aide_repere)
        self.t_eq.selection_changee.connect(self._maj_panneau)
        c_eq.ajouter(self.t_eq, 1)
        barre = QHBoxLayout()
        barre.addWidget(bouton("Ajouter un équipement…", self._ajouter_eq, primaire=True, icone="ajouter"))
        self.b_mod = bouton("Modifier…", self._modifier_eq, icone="modifier")
        self.b_dup = bouton("Dupliquer", self._dupliquer_eq, icone="copier",
                            infobulle="Copie avec le premier numéro libre, sans les adresses.")
        self.b_uf = bouton("Affecter à une UF…", self._affecter_uf, icone="dossier",
                           infobulle="Ranger les équipements sélectionnés dans une unité fonctionnelle.")
        self.b_sup = bouton("Supprimer", self._supprimer_eq, icone="supprimer", nom="danger")
        for b in (self.b_mod, self.b_dup, self.b_uf):
            barre.addWidget(b)
        barre.addStretch(1)
        barre.addWidget(self.b_sup)
        c_eq.disposition.addLayout(barre)
        return c_eq

    # ============================================================== chargement
    def charger(self):
        """Recopie l'ouvrage de la session dans les champs (après Nouveau ou Ouvrir)."""
        o = self.s.ouvrage
        self._chargement = True
        for champ, w in ((self.lieu, o.lieu), (self.code, o.code_ouvrage), (self.libelle, o.libelle), (self.projet, o.nom_projet)):
            champ.setText(w)
        self.automate.setCurrentText(o.automate or "M580")
        self.localisation.setText(o.localisation)
        self.type_ouvrage.setCurrentText(o.type_ouvrage)
        self.environnement.setCurrentText(o.environnement or "Control Expert")
        self.communication.setCurrentText(o.communication)
        self.revision.setText(o.revision)
        self.statut.setCurrentText(o.statut)
        self.mode.definir(o.mode)
        self.lieu_nom.setChecked(o.lieu_dans_le_nom)
        self._chargement = False
        self.rafraichir()

    def _maj_aide_repere(self):
        from .guide import expliquer_repere
        from genvar.modele import Equipement
        o = self.s.ouvrage
        eq = self.t_eq.objet_courant() if hasattr(self, "t_eq") else None
        exemple = eq is None
        if exemple:
            eq = o.equipements[0] if o.equipements else Equipement(o.sous_ensembles[0].code if o.sous_ensembles else "11",
                                                                 "MV", "01")
        morceaux = []
        for val, role, regle, ok in expliquer_repere(o, eq):
            couleur = style.GRAVITE["OK"][0] if ok else style.GRAVITE["Erreur"][0]
            marque = "✓" if ok else "✗"
            morceaux.append(f"<span style='color:{couleur}'><b>{val or '?'}</b> {marque}</span>"
                            f"<span style='color:{style.SECONDAIRE}'> {role} ({regle})</span>")
        rep = o.repere(eq)
        self.aide_repere.setText(
            f"<b>Repère {'(exemple)' if exemple else ''} {rep}</b> = " + "  +  ".join(morceaux)
            + f"<br>Nom d'une variable : FAMILLE_REPÈRE_CODE, ex. <b>TS_{o.repere_nom(eq)}_FER</b> "
              "(TS = télésignalisation, FER = fermée).")

    def rafraichir(self):
        o = self.s.ouvrage
        self.prefixe.setText(o.prefixe() or "—")
        self.aide_mode.setText("Variables générées depuis le catalogue." if o.mode != "Existant"
                               else "Variables lues dans l'automate, jamais renommées.")
        self._anomalies = {}
        if o.mode != "Existant":
            for a in self.s.anomalies():
                if a.ident_eq:
                    niveau, n = self._anomalies.get(a.ident_eq, (a.niveau, 0))
                    self._anomalies[a.ident_eq] = ("Erreur" if a.niveau == "Erreur" else niveau, n + 1)
        self.t_se.definir(o.sous_ensembles)
        courant = self.f_se.currentData()
        self.f_se.blockSignals(True)
        self.f_se.clear()
        self.f_se.addItem("Tous", TOUS)
        for x in o.sous_ensembles:
            self.f_se.addItem(f"{x.code} — {x.libelle}" if x.libelle else x.code, x.code)
        self.f_se.setCurrentIndex(max(0, self.f_se.findData(courant)))
        self.f_se.blockSignals(False)
        courant = self.f_uf.currentData()
        self.f_uf.blockSignals(True)
        self.f_uf.clear()
        self.f_uf.addItem("Toutes", TOUS)
        self.f_uf.addItem("Communs à l'ouvrage", "")
        for u in o.unites:
            self.f_uf.addItem(f"{u.code} — {u.libelle}" if u.libelle else u.code, u.code)
        self.f_uf.setCurrentIndex(max(0, self.f_uf.findData(courant)))
        self.f_uf.blockSignals(False)
        self.t_eq.definir(self.s.equipements_tries())
        self._remplir_arbre()
        self._filtrer()
        self._maj_aide_repere()

    def _remplir_arbre(self):
        self.arbre.remplir(self.s, self._etat)

    def _deplier_tout(self):
        if self.b_deplier.text() == "Tout déplier":
            self.arbre.expandAll()
            self.b_deplier.setText("Replier")
        else:
            self.arbre.collapseAll()
            if self.arbre.topLevelItemCount():
                self.arbre.topLevelItem(0).setExpanded(True)
            self.b_deplier.setText("Tout déplier")

    def _uf_courante(self):
        items = self.arbre.selectedItems()
        return self.arbre._uf_de(items[0]) if items else (self.f_uf.currentData() if self.f_uf.currentData() not in (None, TOUS) else "")

    def _action_arbre(self, verbe, donnee):
        """Gestes de l'arborescence → opérations de la Session."""
        if verbe == "ajouter_uf":
            self._ajouter_uf()
        elif verbe == "modifier_uf":
            self._modifier_uf(donnee)
        elif verbe == "supprimer_uf":
            self._supprimer_uf(donnee)
        elif verbe == "ajouter_eq":
            self._ajouter_eq(donnee or "")
        elif verbe in ("modifier_eq", "dupliquer_eq", "choisir_eq"):
            self.recherche.clear()
            self.f_se.setCurrentIndex(0)
            if self.f_uf.currentIndex() != 0 and verbe != "choisir_eq":
                self.f_uf.setCurrentIndex(0)
            if not self.t_eq.selectionner(lambda e: e.ident == donnee):
                self.f_uf.setCurrentIndex(0)
                self.t_eq.selectionner(lambda e: e.ident == donnee)
            if verbe == "modifier_eq":
                self._modifier_eq()
            elif verbe == "dupliquer_eq":
                self._dupliquer_eq()
            else:
                self.montrer("eq")
        elif verbe == "supprimer_eq":
            self.f_uf.setCurrentIndex(0)
            self._supprimer_eq(list(donnee))
        elif verbe == "deplacer":
            idents, code = donnee
            n = self.s.affecter_uf(set(idents), code)
            if n:
                self._apres_changement()
        elif verbe == "filtrer_uf":
            self._voir_liste(donnee)
        elif verbe == "renommer_communs":
            self._renommer_communs()
        elif verbe == "ranger_communs":
            self._ranger_communs()
        elif verbe == "supprimer_communs":
            self._supprimer_communs()
        elif verbe == "choisir_ouvrage":
            self.montrer("ident")
        elif verbe == "modifier_ouvrage":
            self.montrer("ident")
            self.libelle.setFocus()

    def _arbre_active(self, item, _colonne=0):
        """Compatibilité : double-clic sur un nœud (UF, équipement)."""
        donnee = item.data(0, Qt.ItemDataRole.UserRole)
        if not donnee:
            return
        nature, valeur = donnee
        if nature == "uf":
            self.f_uf.setCurrentIndex(max(0, self.f_uf.findData(valeur)))
        elif nature in ("eq", "var", "signal"):
            self._action_arbre("modifier_eq", valeur)

    # ============================================================== unités fonctionnelles
    def _ajouter_uf(self):
        r = DialogueUF(self, self.s.ouvrage, titre="Nouvelle unité fonctionnelle",
                       code=f"UF{len(self.s.ouvrage.unites) + 1:02d}").montrer()
        if not r:
            return
        try:
            code = self.s.ajouter_uf(*r)
        except RegleMetier as ex:
            avertir(self, "Unité fonctionnelle", str(ex))
            return
        self._apres_changement()
        self.arbre.selectionner("uf", code)
        self._voir_liste(code)

    def _modifier_uf(self, code=None):
        code = code or self._uf_courante()
        u = next((x for x in self.s.ouvrage.unites if x.code == code), None)
        if u is None:
            informer(self, "Unité fonctionnelle", "Sélectionnez une unité fonctionnelle dans l'arborescence.")
            return
        r = DialogueUF(self, self.s.ouvrage, u.code, u.libelle, u.sous_ensemble,
                       titre="Modifier l'unité fonctionnelle").montrer()
        if not r:
            return
        try:
            self.s.modifier_uf(u.code, *r)
        except RegleMetier as ex:
            avertir(self, "Unité fonctionnelle", str(ex))
            return
        self._apres_changement()
        self._voir_liste(r[0])

    def _supprimer_uf(self, code=None):
        code = code or self._uf_courante()
        u = next((x for x in self.s.ouvrage.unites if x.code == code), None)
        if u is None:
            return
        n = self.s.nombre_equipements_uf(u.code)
        if not confirmer(self, "Unité fonctionnelle", f"Supprimer {u.code} ?\n"
                         + (f"Ses {n} équipement(s) sont conservés, sans UF." if n else ""), defaut_non=True):
            return
        self.s.supprimer_uf(u.code)
        self._apres_changement()
        self.montrer("ident")

    def _affecter_uf(self):
        choisis = self.t_eq.objets_selectionnes()
        if not choisis:
            return
        o = self.s.ouvrage
        if not o.unites:
            informer(self, "Unité fonctionnelle", "Créer d'abord une unité fonctionnelle (bouton « Unité fonctionnelle » au-dessus de l'arborescence).")
            return
        libelles = ["(aucune UF)"] + [f"{u.code} — {u.libelle}" if u.libelle else u.code for u in o.unites]
        choix, ok = QInputDialog.getItem(self, "Affecter à une UF",
                                         f"{len(choisis)} équipement(s) sélectionné(s) :", libelles, 0, False)
        if not ok:
            return
        code = "" if choix == libelles[0] else o.unites[libelles.index(choix) - 1].code
        self.s.affecter_uf({e.ident for e in choisis}, code)
        self._apres_changement()

    # ============================================================== affichage
    def _etat(self, e):
        return self._anomalies.get(e.ident, ("OK", 0))[0]

    def _texte_anomalies(self, e):
        n = self._anomalies.get(e.ident, ("", 0))[1]
        return n or ""

    def _infobulle(self, e):
        niv, n = self._anomalies.get(e.ident, ("OK", 0))
        if not n:
            return "Aucune anomalie"
        return f"{n} anomalie(s), la plus grave : {niv}. Détail dans l'écran Variables."

    def _filtrer(self):
        se, uf = self.f_se.currentData(), self.f_uf.currentData()
        self.t_eq.filtre.definir_condition(lambda e: (se in (None, TOUS) or e.sous_ensemble == se)
                                           and (uf in (None, TOUS) or e.uf == uf))
        self.t_eq.filtre.definir_texte(self.recherche.text())
        total = len(self.s.ouvrage.equipements)
        vus = self.t_eq.nombre_visible()
        self.compte_eq.setText(f"{total} équipement(s)" if vus == total else f"{vus} affiché(s) sur {total}")
        self._maj_contexte()
        self._maj_boutons()

    def _uf_affichee(self):
        d = self.f_uf.currentData()
        return d if d not in (None, TOUS, "") else ""

    # --- actions du groupe affiché (UF ou équipements communs)
    def _modifier_groupe(self):
        if self._uf_affichee():
            self._modifier_uf(self._uf_affichee())
        else:
            self._renommer_communs()

    def _supprimer_groupe(self):
        if self._uf_affichee():
            self._supprimer_uf(self._uf_affichee())
        else:
            self._supprimer_communs()

    def _renommer_communs(self):
        texte, ok = QInputDialog.getText(self, "Équipements communs", "Nom du groupe des équipements hors UF :",
                                         text=self.s.libelle_communs())
        if ok and texte.strip():
            self.s.renommer_communs(texte)
            self._apres_changement()

    def _ranger_communs(self):
        eqs = self.s.equipements_communs()
        o = self.s.ouvrage
        if not eqs or not o.unites:
            return
        libelles = [f"{u.code} — {u.libelle}" if u.libelle else u.code for u in o.unites]
        choix, ok = QInputDialog.getItem(self, "Ranger dans une UF",
                                         f"{len(eqs)} équipement(s) hors UF à ranger dans :", libelles, 0, False)
        if not ok or choix not in libelles:
            return
        code = o.unites[libelles.index(choix)].code
        self.s.affecter_uf({e.ident for e in eqs}, code)
        self._apres_changement()
        self.arbre.selectionner("uf", code)
        self._voir_liste(code)

    def _supprimer_communs(self):
        eqs = self.s.equipements_communs()
        if eqs:
            self._supprimer_eq([e.ident for e in eqs])
            if not self.s.equipements_communs():          # groupe vide : il disparaît de l'arbre
                self.montrer("ident")

    def _voir_liste(self, uf=TOUS):
        self.recherche.clear()
        self.f_se.setCurrentIndex(0)
        self.f_uf.setCurrentIndex(max(0, self.f_uf.findData(uf)))
        self.montrer("eqs")

    def _maj_contexte(self):
        """Titre de la liste : l'UF affichée, les équipements communs ou tout l'ouvrage."""
        o = self.s.ouvrage
        d = self.f_uf.currentData()
        u = next((x for x in o.unites if x.code == d), None) if d not in (None, TOUS) else None
        if u is not None:
            titre = f"{u.code} — {u.libelle}" if u.libelle else u.code
            info = (f"Unité fonctionnelle · sous-ensemble proposé aux nouveaux équipements : "
                    f"{u.sous_ensemble or 'aucun'}")
        elif d == "":
            titre = self.s.libelle_communs() if o.unites else "Équipements de l'ouvrage"
            info = ("Équipements hors UF (armoire, automate…). Le groupe n'existe que tant qu'il contient "
                    "des équipements." if o.unites else "")
        else:
            titre, info = "Tous les équipements", ""
        if self.ctx_titre is not None:
            self.ctx_titre.setText(titre)
        self.ctx_info.setText(info)
        self.ctx_info.setVisible(bool(info))
        communs = d == "" and bool(o.unites)
        n_communs = len(self.s.equipements_communs()) if communs else 0
        self.b_mod_uf.setText("Modifier l'UF…" if u is not None else "Renommer le groupe…")
        self.b_sup_uf.setText("Supprimer l'UF" if u is not None else "Supprimer ces équipements…")
        self.b_sup_uf.setToolTip("Les équipements sont conservés, hors UF." if u is not None
                                 else "Supprime tous les équipements hors UF (avec confirmation).")
        self.b_mod_uf.setVisible(u is not None or communs)
        self.b_sup_uf.setVisible(u is not None or (communs and n_communs > 0))
        self.b_ranger.setVisible(communs and n_communs > 0)
        self.b_tous.setText(f"Voir tous les équipements ({len(o.equipements)})")

    def _se_choisi(self):
        se = self.t_se.objet_courant()
        if se is not None:
            i = self.f_se.findData(se.code)
            if i >= 0:
                self.f_se.setCurrentIndex(i)

    # ============================================================== propriétés de l'équipement
    def _construire_panneau(self):
        from PySide6.QtWidgets import QListWidget
        self.panneau = Carte("")
        d = self.panneau.disposition
        tete = QHBoxLayout()
        textes = QVBoxLayout()
        textes.setSpacing(2)
        self.p_titre = QLabel("Sélectionner un équipement")
        self.p_titre.setObjectName("prefixe")
        self.p_titre.setWordWrap(True)
        self.p_info = QLabel("")
        self.p_info.setObjectName("legende")
        self.p_info.setWordWrap(True)
        textes.addWidget(self.p_titre)
        textes.addWidget(self.p_info)
        tete.addLayout(textes, 1)
        self.p_b_fiche = bouton("Ouvrir la fiche…", self._modifier_eq, primaire=True, icone="modifier",
                                infobulle="Signaux, propositions des règles, textes et adresses de l'équipement")
        self.p_b_es = bouton("Voir ses E/S", self._voir_es, icone="es",
                             infobulle="Ouvrir la liste des E/S filtrée sur cet équipement")
        tete.addWidget(self.p_b_es, 0, Qt.AlignmentFlag.AlignTop)
        tete.addWidget(self.p_b_fiche, 0, Qt.AlignmentFlag.AlignTop)
        d.addLayout(tete)
        self.p_resume = QLabel("")
        self.p_resume.setObjectName("aide")
        self.p_resume.setWordWrap(True)
        d.addWidget(self.p_resume)
        corps = QHBoxLayout()
        corps.setSpacing(16)
        gauche = QVBoxLayout()
        gauche.setSpacing(4)
        gauche.addWidget(caption("Options / variantes"))
        self.p_options = QVBoxLayout()
        self.p_options.setSpacing(2)
        gauche.addLayout(self.p_options)
        gauche.addStretch(1)
        corps.addLayout(gauche, 2)
        droite = QVBoxLayout()
        droite.setSpacing(4)
        droite.addWidget(caption("Entrées / sorties physiques"))
        self.p_es = QListWidget()
        self.p_es.setMinimumHeight(160)
        droite.addWidget(self.p_es, 1)
        corps.addLayout(droite, 3)
        d.addLayout(corps, 1)
        self._cases_panneau = []
        self._maj_panneau()
        return self.panneau

    def _maj_panneau(self):
        from PySide6.QtWidgets import QCheckBox, QListWidgetItem
        if not hasattr(self, "p_titre"):
            return
        eqs = self.t_eq.objets_selectionnes()
        eq = eqs[0] if len(eqs) == 1 else None
        while self.p_options.count():
            w = self.p_options.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        self.p_es.clear()
        for w in (self.p_b_fiche, self.p_b_es):
            w.setEnabled(eq is not None)
        if eq is None:
            self.p_titre.setText("Sélectionner un équipement" if not eqs else f"{len(eqs)} équipements sélectionnés")
            self.p_info.setText("Cliquer un équipement dans l'arborescence ou dans la liste : ses options, "
                                "ses E/S physiques et ses signaux s'affichent ici." if not eqs else "")
            self.p_resume.setText("")
            return
        o = self.s.ouvrage
        uf = next((f"{u.code} — {u.libelle}" for u in o.unites if u.code == eq.uf), "commun à l'ouvrage")
        self.p_titre.setText(o.repere(eq))
        self.p_info.setText(f"{self.s.catalogue.designation(eq.type)}" + (f" · {eq.libelle}" if eq.libelle else "")
                            + f"\nUF : {uf} · sous-ensemble {eq.sous_ensemble}")
        options = self.s.catalogue.options_du_type(eq.type)
        if not options:
            l = QLabel("Aucune option pour ce type.")
            l.setObjectName("aide")
            self.p_options.addWidget(l)
        for opt in options:
            c = QCheckBox(opt)
            c.setChecked(opt in eq.options)
            c.setToolTip("Cocher ou décocher : les E/S et signaux de l'équipement sont recalculés immédiatement.")
            c.toggled.connect(lambda coche, o_=opt, e=eq: self._basculer_option(e, o_, coche))
            self.p_options.addWidget(c)
        points = [p for p in self.s.points() if p.ident_eq == eq.ident]
        for p in points:
            item = QListWidgetItem(f"{p.point}  {p.nom}" + (f"   {p.adresse}" if p.adresse else ""))
            item.setToolTip(f"{p.commentaire}\n{'Validée' if p.validee else 'À valider'}"
                            + (f" · liée à {p.variable}" if p.variable else " · E/S locale"))
            item.setIcon(style.icone_gravite("OK" if p.validee else "Info"))
            self.p_es.addItem(item)
        if not points:
            self.p_es.addItem("Aucune E/S physique (équipement sans câblage déclaré).")
        variables = [v for v in self.s.variables() if v.ident_eq == eq.ident] if o.mode != "Existant" else []
        proposes = sum(1 for p in self.s.propositions(eq).values() if p.etat == "proposé")
        self.p_resume.setText(f"{len(points)} E/S · {len(variables)} signal(aux) fonctionnel(s)"
                              + (f" · {proposes} proposé(s) à examiner dans la fiche" if proposes else ""))

    def _basculer_option(self, eq, option, coche):
        if coche and option not in eq.options:
            eq.options.append(option)
        elif not coche and option in eq.options:
            eq.options.remove(option)
        else:
            return
        self.s._change()
        ident = eq.ident
        self._apres_changement()
        self.t_eq.selectionner(lambda e: e.ident == ident)

    def _voir_es(self):
        eq = self.t_eq.objet_courant()
        if eq is not None:
            self.voir_es.emit(eq.ident)

    def _maj_boutons(self):
        n = len(self.t_eq.objets_selectionnes())
        self.b_mod.setEnabled(n == 1)
        self.b_dup.setEnabled(n == 1)
        self.b_sup.setEnabled(n >= 1)
        self.b_uf.setEnabled(n >= 1)

    # ============================================================== identification
    def _champ(self, champ, valeur):
        if self._chargement:
            return
        try:
            self.s.definir(champ, valeur)
        except RegleMetier as ex:
            # En particulier, si l'utilisateur demande « Validé » alors qu'il reste des
            # adresses/E/S non confirmées, revenir à l'état précédent sans crash Qt.
            self.statut.blockSignals(True)
            self.statut.setCurrentText(self.s.ouvrage.statut)
            self.statut.blockSignals(False)
            avertir(self, "Validation refusée", str(ex))
            return
        # Après une modification technique, l'état « Validé » peut devenir « À contrôler ».
        # Rafraîchir sans émettre un deuxième changement depuis le QComboBox.
        if self.statut.currentText() != self.s.ouvrage.statut:
            self.statut.blockSignals(True)
            self.statut.setCurrentText(self.s.ouvrage.statut)
            self.statut.blockSignals(False)
        if champ in ("lieu", "code_ouvrage"):
            self.prefixe.setText(self.s.ouvrage.prefixe() or "—")
            self.t_eq.viewport().update()
            self._maj_aide_repere()
        if champ == "lieu_dans_le_nom":
            self.rafraichir()
        if champ in ("lieu", "code_ouvrage", "libelle"):
            self._remplir_arbre()                      # le nom de l'ouvrage et les repères suivent la saisie
        self.modifie.emit()

    def _changer_mode(self, valeur):
        if self._chargement or valeur == self.s.ouvrage.mode:
            return
        if self.s.ouvrage.existantes or any(e.adresses or e.adresses_es for e in self.s.ouvrage.equipements):
            avertir(self, "Mode de projet", "Le mode ne peut plus être changé lorsque des variables sources "
                    "ou des adresses sont renseignées. Créez un autre projet pour éviter de mélanger "
                    "la reprise d'existant et la génération d'un projet neuf.")
            self.mode.definir(self.s.ouvrage.mode)
            return
        self.s.definir("mode", valeur)
        self.rafraichir()
        self.modifie.emit()
        self.mode_change.emit()

    # ============================================================== sous-ensembles
    def _ajouter_se(self):
        r = DialogueSousEnsemble(self).montrer()
        if not r:
            return
        try:
            code = self.s.ajouter_sous_ensemble(*r)
        except RegleMetier as ex:
            avertir(self, "Sous-ensemble", str(ex))
            return
        self._apres_changement()
        self.t_se.selectionner(lambda s: s.code == code)

    def _modifier_se(self):
        se = self.t_se.objet_courant()
        if se is None:
            informer(self, "Sous-ensemble", "Sélectionnez un sous-ensemble.")
            return
        r = DialogueSousEnsemble(self, se.code, se.libelle).montrer()
        if not r:
            return
        try:
            self.s.modifier_sous_ensemble(se.code, *r)
        except RegleMetier as ex:
            avertir(self, "Sous-ensemble", str(ex))
            return
        self._apres_changement()

    def _supprimer_se(self):
        se = self.t_se.objet_courant()
        if se is None:
            informer(self, "Sous-ensemble", "Sélectionnez un sous-ensemble.")
            return
        if not confirmer(self, "Sous-ensemble", f"Supprimer le sous-ensemble {se.code} ?", defaut_non=True):
            return
        try:
            self.s.supprimer_sous_ensemble(se.code)
        except RegleMetier as ex:
            avertir(self, "Sous-ensemble", str(ex))
            return
        self._apres_changement()

    # ============================================================== équipements
    def _ajouter_eq(self, uf=None):
        if isinstance(uf, bool):
            uf = None
        if uf is None:
            uf = self._uf_affichee()
        se = self.f_se.currentData()
        eq = self.s.equipement_vierge(None if se in (None, TOUS) else se, uf or "")
        r = DialogueEquipement(self, self.s, eq, "Nouvel équipement").montrer()
        if r:
            self.s.ajouter_equipement(r)
            self._effacer_filtres()
            self._apres_changement()
            self.t_eq.selectionner(lambda e: e.ident == r.ident)
            self.arbre.selectionner("eq", r.ident)
            self.montrer("eq")

    def _modifier_eq(self):
        eq = self.t_eq.objet_courant()
        if eq is None:
            return
        dlg = DialogueEquipement(self, self.s, eq, f"Équipement {self.s.ouvrage.repere(eq)}", eq.ident)
        r = dlg.montrer()
        if r:
            self.s.remplacer_equipement(eq.ident, r)
        if r or dlg.catalogue_change:
            self._apres_changement()
            self.t_eq.selectionner(lambda e: e.ident == eq.ident)

    def _dupliquer_eq(self):
        eq = self.t_eq.objet_courant()
        if eq is None:
            return
        try:
            copie = self.s.copie_pour_duplication(eq.ident)
        except RegleMetier as ex:
            avertir(self, "Dupliquer", str(ex))
            return
        r = DialogueEquipement(self, self.s, copie, "Dupliquer l'équipement").montrer()
        if r:
            self.s.ajouter_equipement(r)
            self._apres_changement()
            self.t_eq.selectionner(lambda e: e.ident == r.ident)

    def _supprimer_eq(self, idents=None):
        if isinstance(idents, bool):
            idents = None
        choisis = ([e for e in self.s.ouvrage.equipements if e.ident in idents] if idents
                   else self.t_eq.objets_selectionnes())
        if not choisis:
            return
        o = self.s.ouvrage
        texte = (f"Supprimer l'équipement {o.repere(choisis[0])} ?" if len(choisis) == 1
                 else f"Supprimer les {len(choisis)} équipements sélectionnés ?")
        if not confirmer(self, "Supprimer", texte + "\nSes variables et leurs adresses seront retirées de l'ouvrage.",
                         defaut_non=True):
            return
        for e in choisis:
            self.s.supprimer_equipement(e.ident)
        self._apres_changement()

    def _effacer_filtres(self):
        self.recherche.clear()
        self.f_se.setCurrentIndex(0)
        self.f_uf.setCurrentIndex(0)

    def _apres_changement(self):
        self.rafraichir()
        self.modifie.emit()
