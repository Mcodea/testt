"""Tableaux : modèle générique, filtre, et composant « tableau filtrable » réutilisable.

Un tableau se décrit par une liste de colonnes :
    Colonne("nom", "Nom de variable", lambda v: v.nom, largeur=220)
et reçoit une liste d'objets (variables, équipements, anomalies…).
"""

import re

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QSettings, Signal
from PySide6.QtGui import QColor, QFont, QAction, QPainter
from PySide6.QtWidgets import QTableView, QHeaderView, QAbstractItemView, QMenu

ROLE_OBJET = Qt.ItemDataRole.UserRole + 1
ROLE_TRI = Qt.ItemDataRole.UserRole + 2


def cle_tri_adresse(adresse):
    """%MW1000.12 -> « 0001000.12 » : tri numérique des adresses."""
    m = re.match(r"^%[A-Z]+(\d+)(?:\.(\d+))?", adresse or "")
    if not m:
        return adresse or ""
    return f"{int(m.group(1)):07d}.{int(m.group(2) or 0):02d}"


class Colonne:
    def __init__(self, cle, titre, valeur, largeur=100, alignement=None, tri=None, icone=None, infobulle=None,
                 visible=True, etirable=False):
        self.cle, self.titre, self.valeur, self.largeur = cle, titre, valeur, largeur
        self.alignement = alignement
        self.tri = tri                  # fonction objet -> clé de tri (texte ou nombre)
        self.icone = icone              # fonction objet -> QIcon ou None
        self.infobulle = infobulle      # fonction objet -> texte
        self.visible, self.etirable = visible, etirable


class ModeleTable(QAbstractTableModel):
    def __init__(self, colonnes, parent=None):
        super().__init__(parent)
        self.colonnes = colonnes
        self.lignes = []
        self.couleur = None             # fonction objet -> QColor du texte, ou None
        self.fond = None                # fonction objet -> QColor de fond, ou None
        self.italique = None            # fonction objet -> bool

    def definir(self, lignes):
        self.beginResetModel()
        self.lignes = list(lignes)
        self.endResetModel()

    def objet(self, ligne):
        return self.lignes[ligne] if 0 <= ligne < len(self.lignes) else None

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.lignes)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.colonnes)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.colonnes[section].titre
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        obj = self.lignes[index.row()]
        col = self.colonnes[index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            v = col.valeur(obj)
            return "" if v is None else str(v)
        if role == ROLE_TRI:
            if col.tri:
                return col.tri(obj)
            v = col.valeur(obj)
            return "" if v is None else (v if isinstance(v, (int, float)) else str(v).lower())
        if role == ROLE_OBJET:
            return obj
        if role == Qt.ItemDataRole.DecorationRole and col.icone:
            return col.icone(obj)
        if role == Qt.ItemDataRole.ToolTipRole:
            if col.infobulle:
                return col.infobulle(obj)
            v = col.valeur(obj)
            return str(v) if v and len(str(v)) > 30 else None
        if role == Qt.ItemDataRole.TextAlignmentRole and col.alignement is not None:
            return col.alignement
        if role == Qt.ItemDataRole.ForegroundRole and self.couleur:
            c = self.couleur(obj)
            return QColor(c) if c else None
        if role == Qt.ItemDataRole.BackgroundRole and self.fond:
            c = self.fond(obj)
            return QColor(c) if c else None
        if role == Qt.ItemDataRole.FontRole and self.italique and self.italique(obj):
            f = QFont()
            f.setItalic(True)
            return f
        return None


class Filtre(QSortFilterProxyModel):
    """Recherche plein texte sur toutes les colonnes + condition libre sur l'objet."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.texte = ""
        self.condition = None          # fonction objet -> bool
        self.setSortRole(ROLE_TRI)
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def definir_texte(self, texte):
        self.texte = (texte or "").strip().lower()
        self.invalidateFilter()

    def definir_condition(self, condition):
        self.condition = condition
        self.invalidateFilter()

    def filterAcceptsRow(self, ligne, parent):
        m = self.sourceModel()
        obj = m.objet(ligne)
        if obj is None:
            return False
        if self.condition and not self.condition(obj):
            return False
        if not self.texte:
            return True
        for c in range(m.columnCount()):
            v = m.data(m.index(ligne, c), Qt.ItemDataRole.DisplayRole)
            if v and self.texte in v.lower():
                return True
        return False


class Tableau(QTableView):
    """Tableau trié, filtrable, colonnes redimensionnables et masquables (clic droit sur l'en-tête).
    La disposition des colonnes est mémorisée d'une session à l'autre."""

    objet_active = Signal(object)          # double-clic ou Entrée
    selection_changee = Signal()

    def __init__(self, colonnes, cle_reglages, parent=None):
        super().__init__(parent)
        self.cle_reglages = cle_reglages
        self.modele = ModeleTable(colonnes, self)
        self.filtre = Filtre(self)
        self.filtre.setSourceModel(self.modele)
        self.setModel(self.filtre)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setWordWrap(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(30)
        self.setShowGrid(False)
        self.texte_vide = "Aucune ligne à afficher"
        self.texte_filtre_vide = "Aucun résultat pour ces filtres"
        en_tete = self.horizontalHeader()
        en_tete.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        en_tete.setHighlightSections(False)
        en_tete.setSectionsMovable(True)
        en_tete.setStretchLastSection(False)
        en_tete.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        en_tete.customContextMenuRequested.connect(self._menu_colonnes)
        for i, c in enumerate(colonnes):
            self.setColumnWidth(i, c.largeur)
            if c.etirable:
                en_tete.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            if not c.visible:
                self.setColumnHidden(i, True)
        self._restaurer()
        self.doubleClicked.connect(lambda idx: self.objet_active.emit(self.filtre.data(idx, ROLE_OBJET)))
        self.selectionModel().selectionChanged.connect(lambda *a: self.selection_changee.emit())
        en_tete.sectionResized.connect(lambda *a: self._memoriser())
        en_tete.sectionMoved.connect(lambda *a: self._memoriser())

    # --- données
    def definir(self, objets, garder_selection=True):
        choisis = {id(o) for o in self.objets_selectionnes()} if garder_selection else set()
        cles = [self._cle(o) for o in self.objets_selectionnes()] if garder_selection else []
        self.modele.definir(objets)
        if cles:
            self.selectionner(lambda o: self._cle(o) in cles)
        return choisis

    @staticmethod
    def _cle(o):
        for attr in ("ident", "nom", "code", "message"):
            if hasattr(o, attr):
                return (attr, getattr(o, attr), getattr(o, "repere", ""))
        return id(o)

    def objets_selectionnes(self):
        lignes = sorted({i.row() for i in self.selectionModel().selectedRows()}) if self.selectionModel() else []
        return [self.filtre.data(self.filtre.index(r, 0), ROLE_OBJET) for r in lignes]

    def objet_courant(self):
        sel = self.objets_selectionnes()
        return sel[0] if sel else None

    def selectionner(self, condition):
        """Sélectionne la première ligne visible qui vérifie la condition, et la rend visible."""
        for r in range(self.filtre.rowCount()):
            idx = self.filtre.index(r, 0)
            if condition(self.filtre.data(idx, ROLE_OBJET)):
                self.selectRow(r)
                self.scrollTo(idx, QAbstractItemView.ScrollHint.PositionAtCenter)
                return True
        return False

    def nombre_visible(self):
        return self.filtre.rowCount()

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.filtre.rowCount() == 0:
            # État vide explicite : un tableau blanc sans explication déroute l'utilisateur.
            texte = self.texte_vide if self.modele.rowCount() == 0 else self.texte_filtre_vide
            p = QPainter(self.viewport())
            p.setPen(QColor("#8A97A8"))
            p.drawText(self.viewport().rect().adjusted(20, 20, -20, -20),
                       Qt.AlignmentFlag.AlignCenter.value | Qt.TextFlag.TextWordWrap.value, texte)
            p.end()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.objet_courant() is not None:
            self.objet_active.emit(self.objet_courant())
            return
        super().keyPressEvent(e)

    # --- colonnes
    def _menu_colonnes(self, pos):
        menu = QMenu(self)
        for i, c in enumerate(self.modele.colonnes):
            a = QAction(c.titre or c.cle, menu, checkable=True)
            a.setChecked(not self.isColumnHidden(i))
            a.toggled.connect(lambda etat, i=i: (self.setColumnHidden(i, not etat), self._memoriser()))
            menu.addAction(a)
        menu.addSeparator()
        menu.addAction("Disposition d'origine", self._reinitialiser)
        menu.exec(self.horizontalHeader().mapToGlobal(pos))

    def _memoriser(self):
        QSettings().setValue(f"tableaux/{self.cle_reglages}", self.horizontalHeader().saveState())

    def _restaurer(self):
        etat = QSettings().value(f"tableaux/{self.cle_reglages}")
        if etat is not None:
            self.horizontalHeader().restoreState(etat)

    def _reinitialiser(self):
        QSettings().remove(f"tableaux/{self.cle_reglages}")
        en_tete = self.horizontalHeader()
        for i, c in enumerate(self.modele.colonnes):
            en_tete.moveSection(en_tete.visualIndex(i), i)
            self.setColumnHidden(i, not c.visible)
            self.setColumnWidth(i, c.largeur)
