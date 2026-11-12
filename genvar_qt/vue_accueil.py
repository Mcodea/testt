"""Page d'accueil : lancement direct des deux parcours et registre des ouvrages.

L'interface ne génère aucun exemple fictif ; les comptes viennent du registre réel.
"""
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QTableWidget,
                               QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QMenu,
                               QStackedWidget)

from genvar import projets
from . import style
from .composants import Page, Carte, Indicateur, Segment, EtatVide, bouton, champ_recherche, legende


class CarteParcours(QFrame):
    """Grande carte cliquable présentant un parcours de travail."""
    activee = Signal()

    def __init__(self, numero, titre, description, etapes, libelle, teinte, nom_icone, parent=None):
        super().__init__(parent)
        self.setObjectName("carteParcours")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(16)
        tuile = QLabel()
        tuile.setObjectName("tuileIcone")
        tuile.setProperty("teinte", teinte)
        tuile.setFixedSize(48, 48)
        tuile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        couleur = style.EXISTANT if teinte == "existant" else style.ACCENT
        tuile.setPixmap(style.icone(nom_icone, couleur, 24).pixmap(24, 24))
        lay.addWidget(tuile, 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(4)
        cap = QLabel(numero)
        cap.setObjectName("sectionCaption")
        t = QLabel(titre)
        t.setObjectName("titreParcours")
        d = legende(description, "descParcours")
        e = legende(etapes, "aide")
        col.addWidget(cap)
        col.addWidget(t)
        col.addWidget(d)
        col.addWidget(e)
        col.addSpacing(8)
        r = QHBoxLayout()
        self.cta = bouton(libelle, lambda: self.activee.emit(),
                          nom="ctaExistant" if teinte == "existant" else "ctaParcours")
        r.addWidget(self.cta)
        r.addStretch(1)
        col.addLayout(r)
        lay.addLayout(col, 1)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.activee.emit()
        super().mouseReleaseEvent(e)


class VueAccueil(Page):
    ouvrir_demande = Signal(str)
    nouveau_demande = Signal()
    nouveau_neuf_demande = Signal()
    nouveau_existant_demande = Signal()
    fichier_demande = Signal()
    importer_demande = Signal()
    dupliquer_demande = Signal(str)
    archiver_demande = Signal(str, bool)
    supprimer_demande = Signal(str)
    corbeille_demande = Signal()

    def __init__(self, parent=None):
        super().__init__("Mes ouvrages", "Démarrer un nouveau dossier ou reprendre un ouvrage enregistré.", parent)
        self.fiches = []
        self.entete.droite.addWidget(bouton("Importer d'anciens projets…", lambda: self.importer_demande.emit(),
                                            icone="import", nom="discret",
                                            infobulle="Copier les ouvrages d'une version précédente, sans modifier les originaux."))
        self.entete.droite.addWidget(bouton("Ouvrir un fichier…", lambda: self.fichier_demande.emit(), icone="ouvrir"))

        # ---------------------------------------------------------- deux parcours
        parcours = QHBoxLayout()
        parcours.setSpacing(16)
        self.carte_neuf = CarteParcours(
            "PARCOURS 1  ·  PROJET NEUF", "Créer un ouvrage depuis le catalogue",
            "Générer la table d'échange d'un nouvel automate à partir des équipements.",
            "Fiche ouvrage  →  Variables  →  E/S  →  Plan mémoire  →  Contrôles  →  Exports",
            "Créer un projet neuf", "neuf", "ajouter")
        self.carte_existant = CarteParcours(
            "PARCOURS 2  ·  PROJET EXISTANT", "Reprendre un programme automate",
            "Lire le programme existant sans le modifier et préparer la télétransmission.",
            "Fiche ouvrage  →  Import & analyse  →  Correspondances  →  Contrôles  →  Exports",
            "Analyser un ouvrage existant", "existant", "analyse")
        self.carte_neuf.activee.connect(lambda: self.nouveau_neuf_demande.emit())
        self.carte_existant.activee.connect(lambda: self.nouveau_existant_demande.emit())
        parcours.addWidget(self.carte_neuf, 1)
        parcours.addWidget(self.carte_existant, 1)
        self.disposition.addLayout(parcours)

        # ---------------------------------------------------------- chiffres clés
        resume = QHBoxLayout()
        resume.setSpacing(12)
        self.i_total = Indicateur("ouvrages actifs", icone="dossier", cliquable=True)
        self.i_neufs = Indicateur("projets neufs", icone="ajouter", cliquable=True)
        self.i_existants = Indicateur("projets existants", icone="analyse", cliquable=True)
        self.i_a_verifier = Indicateur("non validés", icone="alerte")
        self.i_a_verifier.setToolTip("Ouvrages actifs dont l'état n'est pas « Validé ».")
        for w in (self.i_total, self.i_neufs, self.i_existants, self.i_a_verifier):
            resume.addWidget(w, 1)
        self.i_total.clique.connect(lambda: self.f_mode.definir("Tous") or self._filtrer())
        self.i_neufs.clique.connect(lambda: self.f_mode.definir("Neuf") or self._filtrer())
        self.i_existants.clique.connect(lambda: self.f_mode.definir("Existant") or self._filtrer())
        self.disposition.addLayout(resume)

        # ---------------------------------------------------------- registre
        haut = Carte("Ouvrages enregistrés", sous_titre="Double-clic pour ouvrir · clic droit pour plus d'actions")
        ligne = QHBoxLayout()
        ligne.setSpacing(8)
        self.recherche = champ_recherche("Rechercher un repère, un libellé, un automate…")
        self.f_mode = Segment([("Tous", "Tous"), ("Neuf", "Neufs"), ("Existant", "Existants")])
        self.f_mode.definir("Tous")
        self.f_archive = QComboBox()
        self.f_archive.addItems(["Actifs", "Archivés", "Tous"])
        self.f_archive.setToolTip("Afficher les ouvrages actifs, archivés ou tous")
        ligne.addWidget(self.recherche, 1)
        ligne.addWidget(self.f_mode)
        ligne.addWidget(self.f_archive)
        haut.disposition.addLayout(ligne)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["Repère", "Libellé", "Parcours", "Automate", "État",
                                              "Rév.", "Équip.", "Modifié le"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        en_tete = self.table.horizontalHeader()
        en_tete.setStretchLastSection(False)
        en_tete.setHighlightSections(False)
        en_tete.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        for c, largeur in enumerate([150, 260, 140, 90, 130, 60, 70, 150]):
            self.table.setColumnWidth(c, largeur)
        en_tete.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setIconSize(QSize(10, 10))
        self.table.doubleClicked.connect(lambda *_: self.ouvrir())
        self.table.itemSelectionChanged.connect(self._maj_boutons)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu)

        self.vide = EtatVide("dossier", "Aucun ouvrage enregistré pour l'instant",
                             "Créez votre premier projet avec l'un des deux parcours ci-dessus, "
                             "ou importez les ouvrages d'une version précédente.",
                             bouton("Importer d'anciens projets…", lambda: self.importer_demande.emit(),
                                    icone="import"))
        self.pile = QStackedWidget()
        self.pile.addWidget(self.table)
        self.pile.addWidget(self.vide)
        haut.ajouter(self.pile, 1)

        barre = QHBoxLayout()
        barre.setSpacing(8)
        self.b_ouvrir = bouton("Ouvrir", self.ouvrir, primaire=True, icone="ouvrir")
        self.b_dupliquer = bouton("Dupliquer", self.dupliquer, icone="copier",
                                  infobulle="Créer une copie indépendante de l'ouvrage sélectionné.")
        self.b_archiver = bouton("Archiver", self.archiver, icone="archive",
                                 infobulle="Retirer de la liste active, sans supprimer le fichier.")
        self.b_supprimer = bouton("Supprimer", self.supprimer, icone="supprimer", nom="danger",
                                  infobulle="Retirer l'ouvrage de la liste : le fichier part dans la corbeille "
                                            "du dossier Projets, d'où il peut être restauré.")
        for b in (self.b_ouvrir, self.b_dupliquer, self.b_archiver, self.b_supprimer):
            barre.addWidget(b)
        barre.addStretch(1)
        self.b_corbeille = bouton("Corbeille…", self.corbeille_demande.emit, icone="supprimer", nom="lien",
                                  infobulle="Restaurer un ouvrage supprimé.")
        barre.addWidget(self.b_corbeille)
        self.info = legende("", retour=False)
        barre.addWidget(self.info)
        haut.disposition.addLayout(barre)
        self.disposition.addWidget(haut, 1)

        self.recherche.textChanged.connect(self._filtrer)
        self.f_mode.change.connect(self._filtrer)
        self.f_archive.currentIndexChanged.connect(self._filtrer)
        self.charger()

    # ================================================================== données
    def charger(self):
        self.fiches = projets.lister()
        actifs = [f for f in self.fiches if not f.archive and not f.erreur]
        self.i_total.definir(len(actifs))
        self.i_neufs.definir(sum(f.mode == "Neuf" for f in actifs))
        self.i_existants.definir(sum(f.mode == "Existant" for f in actifs))
        a_controler = sum(f.statut not in ("Validé",) for f in actifs)
        self.i_a_verifier.definir(a_controler, "Alerte" if a_controler else "OK")
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.fiches))
        gras = QFont()
        gras.setBold(True)
        for i, v in enumerate(self.fiches):
            parcours = ("Projet neuf" if v.mode == "Neuf" else
                        "Projet existant" if v.mode == "Existant" else "Fichier illisible")
            etat = "Archivé" if v.archive else v.statut
            valeurs = [v.repere, v.libelle, parcours, v.automate, etat, v.revision, str(v.equipements), v.date]
            for j, valeur in enumerate(valeurs):
                item = QTableWidgetItem(valeur)
                if j == 0:
                    item.setData(Qt.ItemDataRole.UserRole, v.chemin)
                    item.setFont(gras)
                if j == 2 and not v.erreur:
                    item.setForeground(QColor(style.NEUF if v.mode == "Neuf" else style.EXISTANT))
                if j == 4 and not v.erreur:
                    niveau = "Neutre" if v.archive else ("OK" if v.statut == "Validé" else "Alerte")
                    item.setIcon(style.pastille(style.DISCRET) if v.archive else style.icone_gravite(niveau))
                    item.setForeground(QColor(style.GRAVITE[niveau][0]))
                if j in (5, 6):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if v.erreur:
                    item.setToolTip(v.erreur)
                    item.setForeground(QColor(style.GRAVITE["Erreur"][0]))
                if v.archive:
                    item.setForeground(QColor(style.DISCRET))
                self.table.setItem(i, j, item)
        self.table.setSortingEnabled(True)
        self.pile.setCurrentWidget(self.vide if not self.fiches else self.table)
        self._filtrer()

    def _filtrer(self, *_):
        texte = self.recherche.text().casefold()
        mode = self.f_mode.valeur() or "Tous"
        arch = self.f_archive.currentText()
        vus = 0
        for r in range(self.table.rowCount()):
            p = self._fiche(r)
            if not p:
                continue
            montrer = (not texte or texte in f"{p.repere} {p.libelle} {p.automate} {p.statut}".casefold())
            montrer &= mode == "Tous" or mode == p.mode
            montrer &= arch == "Tous" or (arch == "Archivés") == p.archive
            self.table.setRowHidden(r, not montrer)
            vus += bool(montrer)
        total = len(self.fiches)
        self.info.setText("" if not total else
                          f"{vus} affiché(s) sur {total}" if vus != total else f"{total} ouvrage(s)")
        self._maj_boutons()

    def _fiche(self, row):
        item = self.table.item(row, 0)
        chemin = item.data(Qt.ItemDataRole.UserRole) if item else None
        return next((v for v in self.fiches if v.chemin == chemin), None)

    def _courante(self):
        r = self.table.currentRow()
        if r < 0 or self.table.isRowHidden(r) or not self.table.selectionModel().hasSelection():
            return None
        return self._fiche(r)

    def _maj_boutons(self):
        p = self._courante()
        for b in (self.b_ouvrir, self.b_dupliquer, self.b_archiver):
            b.setEnabled(p is not None and not p.erreur)
        self.b_supprimer.setEnabled(p is not None)          # un fichier illisible peut aussi être écarté
        self.b_archiver.setText("Restaurer" if p is not None and p.archive else "Archiver")

    def _menu(self, pos):
        item = self.table.itemAt(pos)
        if item is None:
            return
        self.table.selectRow(item.row())
        p = self._courante()
        if p is None:
            return
        menu = QMenu(self)
        menu.addAction(style.icone("ouvrir", style.SECONDAIRE), "Ouvrir", self.ouvrir).setEnabled(not p.erreur)
        menu.addAction(style.icone("copier", style.SECONDAIRE), "Dupliquer…", self.dupliquer).setEnabled(not p.erreur)
        menu.addSeparator()
        menu.addAction(style.icone("archive", style.SECONDAIRE),
                       "Restaurer…" if p.archive else "Archiver…", self.archiver).setEnabled(not p.erreur)
        menu.addSeparator()
        menu.addAction(style.icone("supprimer", style.GRAVITE["Erreur"][0]), "Supprimer l'ouvrage…", self.supprimer)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    # ================================================================== actions
    def selection(self):
        p = self._courante()
        if not p:
            QMessageBox.information(self, "Ouvrages", "Sélectionnez un ouvrage dans la liste.")
            return None
        if p.erreur:
            QMessageBox.warning(self, "Fichier illisible", p.erreur)
            return None
        return p

    def ouvrir(self):
        p = self.selection()
        if p:
            self.ouvrir_demande.emit(p.chemin)

    def dupliquer(self):
        from .composants import confirmer
        p = self.selection()
        if p and confirmer(self, "Dupliquer", f"Créer une copie indépendante de {p.repere} ?"):
            self.dupliquer_demande.emit(p.chemin)

    def archiver(self):
        from .composants import confirmer
        p = self.selection()
        if not p:
            return
        intention = "restaurer" if p.archive else "archiver"
        if confirmer(self, "Archiver" if not p.archive else "Restaurer",
                     f"Voulez-vous {intention} {p.repere} ?\nAucun fichier ne sera supprimé."):
            self.archiver_demande.emit(p.chemin, not p.archive)

    def supprimer(self):
        from .composants import confirmer
        p = self._courante()
        if not p:
            QMessageBox.information(self, "Ouvrages", "Sélectionnez un ouvrage dans la liste.")
            return
        if confirmer(self, "Supprimer l'ouvrage",
                     f"Supprimer {p.repere} — {p.libelle} ?\n\n"
                     "Il disparaît de « Mes ouvrages ». Le fichier n'est pas effacé : il est rangé dans "
                     "la corbeille du dossier Projets et peut être restauré (bouton « Corbeille… »).",
                     defaut_non=True):
            self.supprimer_demande.emit(p.chemin)
