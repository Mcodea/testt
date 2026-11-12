"""Composants d'interface réutilisés par les écrans.

Aucun composant ne contient de règle métier : ils mettent en forme ce que la Session calcule.
"""

from PySide6.QtCore import Qt, Signal, QTimer, QSize, QPoint
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QRadioButton, QButtonGroup,
                               QMessageBox, QSpinBox, QPushButton, QSizePolicy, QLineEdit)

from . import style


# ============================================================================ structure
class Carte(QFrame):
    """Cadre blanc à bords arrondis avec un titre, un sous-titre facultatif et une zone d'actions."""

    def __init__(self, titre="", parent=None, sous_titre=""):
        super().__init__(parent)
        self.setObjectName("carte")
        self.disposition = QVBoxLayout(self)
        self.disposition.setContentsMargins(16, 14, 16, 16)
        self.disposition.setSpacing(10)
        self.entete = QHBoxLayout()
        self.entete.setSpacing(8)
        self.titre = None
        if titre or sous_titre:
            textes = QVBoxLayout()
            textes.setSpacing(1)
            self.titre = QLabel(titre)
            self.titre.setObjectName("titreCarte")
            textes.addWidget(self.titre)
            if sous_titre:
                s = QLabel(sous_titre)
                s.setObjectName("aide")
                s.setWordWrap(True)
                textes.addWidget(s)
            self.entete.addLayout(textes)
        self.entete.addStretch(1)
        self.disposition.addLayout(self.entete)

    def ajouter_action(self, widget):
        self.entete.addWidget(widget)
        return widget

    def ajouter(self, widget, etirement=0):
        self.disposition.addWidget(widget, etirement)
        return widget


class EntetePage(QWidget):
    def __init__(self, titre, sous_titre, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 2)
        lay.setSpacing(12)
        textes = QVBoxLayout()
        textes.setSpacing(2)
        self.titre = QLabel(titre)
        self.titre.setObjectName("titrePage")
        self.sous_titre = QLabel(sous_titre)
        self.sous_titre.setObjectName("sousTitre")
        self.sous_titre.setWordWrap(True)
        textes.addWidget(self.titre)
        textes.addWidget(self.sous_titre)
        lay.addLayout(textes, 1)
        self.droite = QHBoxLayout()
        self.droite.setSpacing(8)
        lay.addLayout(self.droite)


class Page(QWidget):
    """Fond d'un écran : marges, en-tête (titre, sous-titre, actions à droite), puis le contenu."""

    def __init__(self, titre, sous_titre, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self.disposition = QVBoxLayout(self)
        self.disposition.setContentsMargins(22, 14, 22, 14)
        self.disposition.setSpacing(10)
        self.entete = EntetePage(titre, sous_titre)
        self.disposition.addWidget(self.entete)


def separateur():
    f = QFrame()
    f.setObjectName("separateur")
    f.setFrameShape(QFrame.Shape.NoFrame)
    return f


def legende(texte="", nom="legende", retour=True):
    l = QLabel(texte)
    l.setObjectName(nom)
    l.setWordWrap(retour)
    return l


def caption(texte):
    l = QLabel(texte.upper())
    l.setObjectName("sectionCaption")
    return l


# ============================================================================ indicateurs
class Indicateur(QFrame):
    """Chiffre clé : valeur en grand, libellé dessous. La couleur suit la gravité.
    Facultativement cliquable (signal `clique`) pour aller à l'écran correspondant."""
    clique = Signal()

    def __init__(self, libelle, parent=None, icone=None, cliquable=False):
        super().__init__(parent)
        self.setObjectName("indicateur")
        self.setProperty("cliquable", cliquable)
        if cliquable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(12)
        if icone:
            tuile = QLabel()
            tuile.setObjectName("tuileIcone")
            tuile.setFixedSize(34, 34)
            tuile.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tuile.setPixmap(style.icone(icone, style.ACCENT, 18).pixmap(18, 18))
            lay.addWidget(tuile)
        textes = QVBoxLayout()
        textes.setSpacing(0)
        self.valeur = QLabel("0")
        self.valeur.setObjectName("valeurIndicateur")
        self.libelle = QLabel(libelle)
        self.libelle.setObjectName("libelleIndicateur")
        textes.addWidget(self.valeur)
        textes.addWidget(self.libelle)
        lay.addLayout(textes, 1)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def definir(self, valeur, gravite=""):
        self.valeur.setText(str(valeur))
        self.valeur.setProperty("gravite", gravite)
        self.valeur.style().unpolish(self.valeur)
        self.valeur.style().polish(self.valeur)

    def mouseReleaseEvent(self, e):
        if self.property("cliquable") and e.button() == Qt.MouseButton.LeftButton:
            self.clique.emit()
        super().mouseReleaseEvent(e)


class Badge(QLabel):
    """Pastille de texte colorée selon la gravité (Erreur, Alerte, OK, Info, Neutre, Existant)."""

    def __init__(self, texte="", gravite="", parent=None):
        super().__init__(parent)
        self.setObjectName("badge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if texte:
            self.definir(texte, gravite or "Neutre")

    def definir(self, texte, gravite):
        self.setObjectName("badge")
        self.setText(texte)
        self.setProperty("gravite", gravite)
        self.style().unpolish(self)
        self.style().polish(self)


def repolir(widget, **proprietes):
    """Met à jour des propriétés dynamiques utilisées par la feuille de style."""
    for k, v in proprietes.items():
        widget.setProperty(k, v)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


# ============================================================================ saisie
class Segment(QFrame):
    """Choix exclusif présenté comme un interrupteur à plusieurs positions."""
    change = Signal(str)

    def __init__(self, choix, parent=None):
        super().__init__(parent)
        self.setObjectName("segment")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(2)
        self.groupe = QButtonGroup(self)
        self.boutons = {}
        for valeur, texte in choix:
            b = QRadioButton(texte)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.groupe.addButton(b)
            self.boutons[valeur] = b
            lay.addWidget(b)
            b.toggled.connect(lambda coche, v=valeur: coche and self.change.emit(v))
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def definir(self, valeur):
        b = self.boutons.get(valeur)
        if b and not b.isChecked():
            b.blockSignals(True)
            b.setChecked(True)
            b.blockSignals(False)

    def valeur(self):
        for v, b in self.boutons.items():
            if b.isChecked():
                return v
        return None

    def libeller(self, valeur, texte):
        if valeur in self.boutons:
            self.boutons[valeur].setText(texte)


class Majuscules(QValidator):
    """Saisie en majuscules, lettres et chiffres seulement, sans déplacer le curseur."""

    def __init__(self, longueur=8, parent=None):
        super().__init__(parent)
        self.longueur = longueur

    def validate(self, texte, pos):
        t = texte.upper()
        if len(t) > self.longueur or not all(c.isascii() and c.isalnum() for c in t):
            return QValidator.State.Invalid, texte, pos
        return QValidator.State.Acceptable, t, pos


class Numero(QSpinBox):
    """Numéro d'équipement affiché sur deux chiffres (01 à 99)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(1, 99)

    def textFromValue(self, valeur):
        return f"{valeur:02d}"


def champ_recherche(texte):
    """Zone de recherche homogène : loupe, bouton d'effacement, texte d'aide."""
    c = QLineEdit()
    c.setObjectName("champRecherche")
    c.setPlaceholderText(texte)
    c.setClearButtonEnabled(True)
    c.addAction(style.icone("recherche", style.DISCRET, 14), QLineEdit.ActionPosition.LeadingPosition)
    return c


# ============================================================================ boutons
def bouton(texte, action=None, primaire=False, infobulle="", icone=None, nom=None):
    b = QPushButton(texte)
    if primaire:
        b.setObjectName("primaire")
    if nom:
        b.setObjectName(nom)
    if icone:
        couleur = "#FFFFFF" if primaire else (style.GRAVITE["Erreur"][0] if nom == "danger" else
                                               style.ACCENT if nom == "lien" else style.SECONDAIRE)
        b.setIcon(style.icone(icone, couleur, 16))
        b.setIconSize(QSize(15, 15))
    if infobulle:
        b.setToolTip(infobulle)
    if action:
        b.clicked.connect(action)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


class BoutonNavigation(QPushButton):
    """Entrée de la barre latérale : icône ou pastille d'étape, libellé, compteur à droite."""

    def __init__(self, nom, libelle, icone=None, parent=None):
        super().__init__(libelle.replace("&", "&&"), parent)   # « & » n'est pas un raccourci clavier
        self.nom = nom
        self.libelle = libelle
        self.nom_icone = icone
        self.numero = None
        self.setObjectName("nav")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setIconSize(QSize(20, 20))
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.addStretch(1)
        self.badge = QLabel()
        self.badge.setObjectName("navBadge")
        self.badge.hide()
        lay.addWidget(self.badge)
        self.definir_etat(None)

    def definir_etat(self, etat, numero=None):
        """etat None : icône simple ; sinon pastille d'étape (a_faire, actif, fait, erreur)."""
        self.numero = numero
        if etat is None or numero is None:
            couleur = style.ACCENT if self.isChecked() else style.SECONDAIRE
            self.setIcon(style.icone(self.nom_icone or "chevron", couleur, 18))
        else:
            self.setIcon(style.icone_etape(numero, "actif" if self.isChecked() and etat == "a_faire" else etat, 20))

    def definir_badge(self, texte="", gravite="Info"):
        self.badge.setVisible(bool(texte))
        self.badge.setText(str(texte))
        repolir(self.badge, gravite=gravite)


class CarteEtape(QFrame):
    """Bloc d'une étape de travail : pastille numérotée, titre, état et actions."""

    def __init__(self, numero, titre, description="", parent=None):
        super().__init__(parent)
        self.setObjectName("carteEtape")
        self.numero = numero
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        tete = QHBoxLayout()
        tete.setSpacing(10)
        self.pastille = QLabel()
        self.pastille.setFixedSize(24, 24)
        tete.addWidget(self.pastille)
        t = QLabel(titre)
        t.setObjectName("titreCarte")
        tete.addWidget(t, 1)
        lay.addLayout(tete)
        if description:
            lay.addWidget(legende(description, "aide"))
        self.etat = legende("", "legende")
        lay.addWidget(self.etat)
        self.actions = QVBoxLayout()
        self.actions.setSpacing(6)
        lay.addLayout(self.actions)
        lay.addStretch(1)
        self.definir("a_faire", "")

    def ajouter_bouton(self, b):
        self.actions.addWidget(b)
        return b

    def definir(self, etat, texte):
        self.pastille.setPixmap(style.icone_etape(self.numero, etat, 24).pixmap(24, 24))
        self.etat.setText(texte)
        repolir(self, etat=etat)


class EtatVide(QFrame):
    """Écran d'absence de données : icône, titre, explication et action principale facultative."""

    def __init__(self, icone, titre, texte, bouton_action=None, parent=None):
        super().__init__(parent)
        self.setObjectName("vide")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 36, 24, 36)
        lay.setSpacing(8)
        lay.addStretch(1)
        ico = QLabel()
        ico.setPixmap(style.icone(icone, style.DISCRET, 40).pixmap(40, 40))
        ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(ico)
        self.titre = QLabel(titre)
        self.titre.setObjectName("videTitre")
        self.titre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.titre)
        self.texte = legende(texte)
        self.texte.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.texte)
        if bouton_action is not None:
            r = QHBoxLayout()
            r.addStretch(1)
            r.addWidget(bouton_action)
            r.addStretch(1)
            lay.addSpacing(6)
            lay.addLayout(r)
        lay.addStretch(1)


# ============================================================================ notification
class Toast(QFrame):
    """Notification éphémère en bas à droite de la fenêtre (confirmation sans fenêtre modale)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 16, 10)
        lay.setSpacing(10)
        self.ico = QLabel()
        self.ico.setObjectName("toastIcone")
        self.texte = QLabel()
        self.texte.setObjectName("toastTexte")
        self.texte.setWordWrap(True)
        self.texte.setMaximumWidth(460)
        lay.addWidget(self.ico)
        lay.addWidget(self.texte, 1)
        self.minuterie = QTimer(self)
        self.minuterie.setSingleShot(True)
        self.minuterie.timeout.connect(self.hide)
        self.hide()

    def montrer(self, texte, niveau="OK", duree=4200):
        couleurs = {"OK": "#4ADE80", "Alerte": "#FBBF24", "Erreur": "#F87171", "Info": "#93C5FD"}
        glyphe = {"OK": "termine", "Alerte": "alerte", "Erreur": "alerte", "Info": "info"}.get(niveau, "info")
        self.ico.setPixmap(style.icone(glyphe, couleurs.get(niveau, "#93C5FD"), 18).pixmap(18, 18))
        self.texte.setText(texte)
        self.adjustSize()
        self.replacer()
        self.show()
        self.raise_()
        self.minuterie.start(duree)

    def replacer(self):
        p = self.parentWidget()
        if p is not None:
            self.move(QPoint(max(12, p.width() - self.width() - 24), max(12, p.height() - self.height() - 44)))

    def mousePressEvent(self, e):
        self.hide()


def notifier(widget, texte, niveau="OK"):
    """Affiche une confirmation non bloquante dans la fenêtre principale, sinon une boîte d'information."""
    fenetre = widget.window() if widget is not None else None
    toast = getattr(fenetre, "toast", None)
    if isinstance(toast, Toast):
        toast.montrer(texte, niveau)
    else:
        QMessageBox.information(widget, "Information", texte)


# ============================================================================ boîtes de dialogue
def avertir(parent, titre, texte):
    QMessageBox.warning(parent, titre, texte)


def informer(parent, titre, texte):
    QMessageBox.information(parent, titre, texte)


def confirmer(parent, titre, texte, defaut_non=False):
    boite = QMessageBox(QMessageBox.Icon.Question, titre, texte,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, parent)
    boite.button(QMessageBox.StandardButton.Yes).setText("Oui")
    boite.button(QMessageBox.StandardButton.No).setText("Non")
    boite.setDefaultButton(QMessageBox.StandardButton.No if defaut_non else QMessageBox.StandardButton.Yes)
    boite.exec()
    return boite.clickedButton() is boite.button(QMessageBox.StandardButton.Yes)


# ============================================================================ guidage
class BandeauGuide(QFrame):
    """« À faire » compact : une ligne par action (deux au plus), chacune avec son bouton.

    Le détail complet reste dans l'infobulle ; la liste entière est sur le tableau de bord.
    """
    commande = Signal(str)
    ICONES = {"erreur": ("alerte", "Erreur"), "alerte": ("alerte", "Alerte"), "faire": ("chevron", "Info"),
              "ok": ("termine", "OK")}
    LONGUEUR_DETAIL = 110

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bandeauGuide")
        self.lay = QHBoxLayout(self)
        self.lay.setContentsMargins(12, 6, 12, 6)
        self.lay.setSpacing(10)
        tete = QLabel("À FAIRE")
        tete.setObjectName("sectionCaption")
        self.lay.addWidget(tete, 0, Qt.AlignmentFlag.AlignTop)
        self.lignes = QVBoxLayout()
        self.lignes.setSpacing(2)
        self.lay.addLayout(self.lignes, 1)
        self.b_tout = bouton("Tout voir", lambda _=False: self.commande.emit("tableau"), nom="lien",
                             infobulle="Toutes les actions restantes, sur le tableau de bord.")
        self.lay.addWidget(self.b_tout, 0, Qt.AlignmentFlag.AlignTop)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.hide()

    def afficher(self, actions, total=None):
        while self.lignes.count():
            item = self.lignes.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for i, a in enumerate(actions):
            ligne = QWidget()
            r = QHBoxLayout(ligne)
            r.setContentsMargins(0, 0, 0, 0)
            r.setSpacing(8)
            nom_icone, gravite = self.ICONES.get(a.niveau, ("chevron", "Info"))
            ico = QLabel()
            ico.setPixmap(style.icone(nom_icone, style.GRAVITE[gravite][0], 16).pixmap(16, 16))
            r.addWidget(ico)
            detail = a.detail if len(a.detail) <= self.LONGUEUR_DETAIL else a.detail[:self.LONGUEUR_DETAIL - 1] + "…"
            t = QLabel(f"<b>{a.titre}</b>&nbsp;&nbsp;<span style='color:{style.SECONDAIRE}'>{detail}</span>")
            t.setTextFormat(Qt.TextFormat.RichText)
            t.setToolTip(a.detail)
            t.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            r.addWidget(t, 1)
            b = bouton(a.bouton, lambda _=False, c=a.commande: self.commande.emit(c),
                       primaire=(i == 0))
            r.addWidget(b)
            self.lignes.addWidget(ligne)
        reste = (total or len(actions)) - len(actions)
        self.b_tout.setText(f"+{reste} autre(s)" if reste > 0 else "Tableau de bord")
        self.setVisible(bool(actions))
