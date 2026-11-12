"""Charte visuelle SOREP — système de design de l'interface Qt.

Principes :
  * une seule couleur d'accent (bleu), le reste en neutres ardoise ;
  * les couleurs de gravité (rouge / orange / vert / bleu) ne servent qu'à représenter
    les statuts calculés par le moteur, jamais à décorer ;
  * espacements sur une grille de 4 px, rayons 6 / 8 / 12 px ;
  * icônes vectorielles natives Windows (Segoe Fluent Icons / Segoe MDL2 Assets),
    sans fichier image à distribuer ; repli silencieux sur une pastille si la police manque.

Aucune décision métier n'est prise dans cette couche.
"""

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPalette, QPixmap, QPen, QPolygonF

# ----------------------------------------------------------------------------- jetons
FOND = "#F4F6F9"            # fond d'application
SURFACE = "#FFFFFF"         # cartes, tableaux, champs
SURFACE_2 = "#F8FAFC"       # en-têtes de tableau, zones secondaires
BORD = "#E3E8EF"
BORD_FORT = "#CDD5DF"
TEXTE = "#0F172A"
SECONDAIRE = "#475569"
DISCRET = "#8A97A8"
ACCENT = "#2563EB"
ACCENT_SURVOL = "#1D4ED8"
ACCENT_PRESSE = "#1E40AF"
ACCENT_CLAIR = "#EFF4FF"
ACCENT_BORD = "#C7D7FE"
LATERAL = "#FFFFFF"
LATERAL_SURVOL = "#F1F5F9"
LATERAL_ACTIF = "#EAF1FF"

GRAVITE = {
    "Erreur": ("#C0262D", "#FDEDED"),
    "Alerte": ("#B45309", "#FEF4E2"),
    "Info": ("#2563EB", "#EFF4FF"),
    "OK": ("#15803D", "#EAF7EE"),
    "Neutre": ("#475569", "#F1F5F9"),
}
NEUF = "#2563EB"
EXISTANT = "#7C3AED"
PROPRE = "#1F5DA8"
ALARME = "#C0262D"


# ----------------------------------------------------------------------------- icônes
# Points de code communs à Segoe Fluent Icons (Windows 11) et Segoe MDL2 Assets (Windows 10).
GLYPHES = {
    "accueil": "", "dossier": "", "ouvrir": "", "tableau_bord": "",
    "document": "", "liste": "", "es": "", "memoire": "",
    "analyse": "", "controle": "", "export": "", "import": "",
    "catalogue": "", "enregistrer": "", "ajouter": "", "modifier": "",
    "supprimer": "", "copier": "", "archive": "", "recherche": "",
    "filtre": "", "alerte": "", "info": "", "termine": "",
    "chevron": "", "reglages": "", "lien": "", "pdf": "",
    "valider": "", "assistant": "", "parcours": "",
}

_POLICE_ICONES = None
_CACHE: dict[tuple, QIcon] = {}


def police_icones():
    """Nom de la police d'icônes Windows disponible, ou chaîne vide."""
    global _POLICE_ICONES
    if _POLICE_ICONES is None:
        try:
            familles = set(QFontDatabase.families())
        except Exception:
            familles = set()
        _POLICE_ICONES = next((f for f in ("Segoe Fluent Icons", "Segoe MDL2 Assets") if f in familles), "")
    return _POLICE_ICONES


def icone(nom, couleur=SECONDAIRE, taille=16):
    """Icône vectorielle nommée (voir GLYPHES). Toujours un QIcon valide."""
    cle = ("g", nom, couleur, taille)
    if cle in _CACHE:
        return _CACHE[cle]
    pm = QPixmap(taille * 2, taille * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    famille = police_icones()
    glyphe = GLYPHES.get(nom, "")
    if famille and glyphe:
        f = QFont(famille)
        f.setPixelSize(int(taille * 0.92))
        p.setFont(f)
        p.setPen(QColor(couleur))
        p.drawText(QRectF(0, 0, taille, taille), Qt.AlignmentFlag.AlignCenter.value, glyphe)
    else:                                    # repli : petite pastille discrète
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(couleur))
        r = taille * 0.22
        p.drawEllipse(QRectF(taille / 2 - r, taille / 2 - r, 2 * r, 2 * r))
    p.end()
    _CACHE[cle] = QIcon(pm)
    return _CACHE[cle]


def icone_etape(numero, etat="a_faire", taille=22):
    """Pastille d'étape numérotée : a_faire (contour gris), actif (bleu), fait (vert, coche), erreur (rouge)."""
    cle = ("e", numero, etat, taille)
    if cle in _CACHE:
        return _CACHE[cle]
    pm = QPixmap(taille * 2, taille * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    cadre = QRectF(1.5, 1.5, taille - 3, taille - 3)
    couleurs = {"fait": GRAVITE["OK"][0], "actif": ACCENT, "erreur": GRAVITE["Erreur"][0]}
    if etat in couleurs:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(couleurs[etat]))
        p.drawEllipse(cadre)
        texte_couleur = QColor("#FFFFFF")
    else:
        p.setPen(QPen(QColor(BORD_FORT), 1.4))
        p.setBrush(QColor(SURFACE))
        p.drawEllipse(cadre)
        texte_couleur = QColor(SECONDAIRE)
    if etat == "fait":
        stylo = QPen(texte_couleur, 2.0)
        stylo.setCapStyle(Qt.PenCapStyle.RoundCap)
        stylo.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(stylo)
        t = taille
        p.drawPolyline(QPolygonF([QPointF(t * .30, t * .52), QPointF(t * .44, t * .66), QPointF(t * .71, t * .37)]))
    else:
        f = QFont("Segoe UI")
        f.setPixelSize(int(taille * 0.5))
        f.setBold(True)
        p.setFont(f)
        p.setPen(texte_couleur)
        p.drawText(cadre, Qt.AlignmentFlag.AlignCenter.value, str(numero))
    p.end()
    _CACHE[cle] = QIcon(pm)
    return _CACHE[cle]


def pastille(couleur, taille=10):
    cle = ("p", couleur, taille)
    if cle in _CACHE:
        return _CACHE[cle]
    pm = QPixmap(taille * 2, taille * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(couleur))
    p.drawEllipse(QRectF(1.5, 1.5, taille - 3, taille - 3))
    p.end()
    _CACHE[cle] = QIcon(pm)
    return _CACHE[cle]


def icone_gravite(niveau):
    return pastille(GRAVITE.get(niveau, GRAVITE["Info"])[0])


# ----------------------------------------------------------------------------- feuille de style
FEUILLE = f"""
* {{ outline: none; }}
QWidget {{ color: {TEXTE}; font-size: 10pt; }}
QMainWindow, QWidget#page, QDialog, QStackedWidget#pile {{ background: {FOND}; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}

/* ---------- barre latérale */
QFrame#lateral {{ background: {LATERAL}; border: none; border-right: 1px solid {BORD}; }}
QLabel#logo {{ background: {ACCENT}; color: white; border-radius: 8px; font-size: 13pt; font-weight: 800; }}
QLabel#marque {{ color: {TEXTE}; font-size: 12.5pt; font-weight: 800; }}
QLabel#marqueSous {{ color: {DISCRET}; font-size: 8.5pt; }}
QLabel#sectionNav {{ color: {DISCRET}; font-size: 8pt; font-weight: 700; padding: 14px 12px 4px 12px; }}
QPushButton#nav {{ background: transparent; border: none; border-radius: 7px; text-align: left;
                   padding: 7px 10px; min-height: 22px; font-weight: 500; color: #334155; }}
QPushButton#nav:hover {{ background: {LATERAL_SURVOL}; }}
QPushButton#nav:checked {{ background: {LATERAL_ACTIF}; color: {ACCENT_PRESSE}; font-weight: 700; }}
QLabel#navBadge {{ border-radius: 8px; padding: 1px 7px; font-size: 8pt; font-weight: 700; }}
QLabel#navBadge[gravite="Erreur"] {{ background: {GRAVITE['Erreur'][1]}; color: {GRAVITE['Erreur'][0]}; }}
QLabel#navBadge[gravite="Alerte"] {{ background: {GRAVITE['Alerte'][1]}; color: {GRAVITE['Alerte'][0]}; }}
QLabel#navBadge[gravite="Info"] {{ background: {GRAVITE['Neutre'][1]}; color: {GRAVITE['Neutre'][0]}; }}
QFrame#carteDossier {{ background: {SURFACE_2}; border: 1px solid {BORD}; border-radius: 9px; }}
QLabel#dossierRepere {{ font-size: 10.5pt; font-weight: 800; color: {TEXTE}; }}
QLabel#dossierLibelle {{ font-size: 9pt; color: {SECONDAIRE}; }}
QLabel#versionLaterale {{ color: {DISCRET}; font-size: 8.5pt; padding: 10px 16px 12px 16px; }}

/* ---------- barre de contexte */
QFrame#barreSuperieure {{ background: {SURFACE}; border: none; border-bottom: 1px solid {BORD}; }}
QLabel#filAriane {{ color: {DISCRET}; font-size: 8.5pt; font-weight: 600; }}
QLabel#titreContexte {{ color: {TEXTE}; font-size: 11.5pt; font-weight: 700; }}
QLabel#etatEnregistrement {{ font-size: 9pt; font-weight: 600; padding: 3px 9px; border-radius: 10px; }}
QLabel#etatEnregistrement[etat="modifie"] {{ color: {GRAVITE['Alerte'][0]}; background: {GRAVITE['Alerte'][1]}; }}
QLabel#etatEnregistrement[etat="ok"] {{ color: {GRAVITE['OK'][0]}; background: {GRAVITE['OK'][1]}; }}
QPushButton#recherche {{ background: {SURFACE_2}; border: 1px solid {BORD}; border-radius: 8px; color: {DISCRET};
                        text-align: left; padding: 6px 12px; min-width: 230px; font-weight: 500; }}
QPushButton#recherche:hover {{ border-color: {BORD_FORT}; color: {SECONDAIRE}; }}

/* ---------- en-têtes de page */
QLabel#titrePage {{ font-size: 17pt; font-weight: 700; color: {TEXTE}; }}
QLabel#sousTitre {{ font-size: 10pt; color: {SECONDAIRE}; }}
QLabel#prefixe {{ font-size: 17pt; font-weight: 800; color: {ACCENT}; }}
QLabel#legende {{ color: {SECONDAIRE}; font-size: 9pt; }}
QLabel#aide {{ color: {DISCRET}; font-size: 9pt; }}
QLabel#bandeau {{ background: {ACCENT_CLAIR}; color: #1E3A8A; border: 1px solid {ACCENT_BORD}; border-radius: 8px; padding: 10px 14px; }}
QLabel#bandeauAlerte {{ background: {GRAVITE['Alerte'][1]}; color: #7C2D12; border: 1px solid #F8D9A8; border-radius: 8px; padding: 10px 14px; }}
QLabel#sectionCaption {{ color: {DISCRET}; font-size: 8pt; font-weight: 700; }}

/* ---------- cartes */
QFrame#carte, QFrame#carteParcours, QFrame#carteEtape, QFrame#carteLivrable {{
    background: {SURFACE}; border: 1px solid {BORD}; border-radius: 12px; }}
QFrame#carteParcours:hover, QFrame#indicateur[cliquable="true"]:hover {{ border-color: {ACCENT_BORD}; background: #FBFCFF; }}
QFrame#carteEtape[etat="actif"] {{ border: 1px solid {ACCENT_BORD}; background: #FBFCFF; }}
QFrame#carteEtape[etat="fait"] {{ border-color: #BFE3CB; }}
QLabel#titreCarte {{ font-size: 10.5pt; font-weight: 700; color: {TEXTE}; }}
QLabel#titreParcours {{ font-size: 13pt; font-weight: 700; color: {TEXTE}; }}
QLabel#descParcours {{ color: {SECONDAIRE}; font-size: 9.5pt; }}
QLabel#tuileIcone {{ background: {ACCENT_CLAIR}; border-radius: 10px; }}
QLabel#tuileIcone[teinte="existant"] {{ background: #F3EEFF; }}
QFrame#separateur {{ background: {BORD}; max-height: 1px; min-height: 1px; border: none; }}
QFrame#ligneEtape {{ background: transparent; border: none; border-bottom: 1px solid {BORD}; }}
QFrame#ligneEtape[recommande="true"] {{ background: {ACCENT_CLAIR}; border-radius: 8px; border-bottom: none; }}
QLabel#titreLigne {{ font-weight: 600; font-size: 10pt; }}
QFrame#bandeauGuide {{ background: {ACCENT_CLAIR}; border: 1px solid {ACCENT_BORD}; border-radius: 10px; }}
QFrame#bandeauGuide QLabel#legende {{ color: #334155; }}
QFrame#encartBrouillon {{ background: {GRAVITE['Alerte'][1]}; border: 1px solid #F8D9A8; border-radius: 8px; }}
QFrame#vide {{ background: transparent; border: none; }}
QLabel#videTitre {{ font-size: 12pt; font-weight: 700; color: {TEXTE}; }}

/* ---------- indicateurs et badges */
QFrame#indicateur {{ background: {SURFACE}; border: 1px solid {BORD}; border-radius: 10px; }}
QLabel#valeurIndicateur {{ font-size: 18pt; font-weight: 700; color: {TEXTE}; }}
QLabel#libelleIndicateur {{ color: {SECONDAIRE}; font-size: 9pt; }}
QLabel[gravite="Erreur"] {{ color: {GRAVITE['Erreur'][0]}; }}
QLabel[gravite="Alerte"] {{ color: {GRAVITE['Alerte'][0]}; }}
QLabel[gravite="OK"] {{ color: {GRAVITE['OK'][0]}; }}
QLabel#badge {{ border-radius: 9px; padding: 2px 9px; font-weight: 600; font-size: 8.5pt; }}
QLabel#badge[gravite="Erreur"] {{ background: {GRAVITE['Erreur'][1]}; color: {GRAVITE['Erreur'][0]}; }}
QLabel#badge[gravite="Alerte"] {{ background: {GRAVITE['Alerte'][1]}; color: {GRAVITE['Alerte'][0]}; }}
QLabel#badge[gravite="OK"] {{ background: {GRAVITE['OK'][1]}; color: {GRAVITE['OK'][0]}; }}
QLabel#badge[gravite="Info"] {{ background: {ACCENT_CLAIR}; color: {ACCENT}; }}
QLabel#badge[gravite="Neutre"] {{ background: {GRAVITE['Neutre'][1]}; color: {GRAVITE['Neutre'][0]}; }}
QLabel#badge[gravite="Existant"] {{ background: #F3EEFF; color: {EXISTANT}; }}

/* ---------- boutons */
QPushButton, QToolButton#bouton {{ background: {SURFACE}; border: 1px solid {BORD_FORT}; border-radius: 7px;
                                 padding: 6px 13px; min-height: 20px; font-weight: 600; color: #1E293B; }}
QPushButton:hover, QToolButton#bouton:hover {{ background: {SURFACE_2}; border-color: #AEB9C7; }}
QPushButton:pressed, QToolButton#bouton:pressed {{ background: #EEF2F6; }}
QPushButton:focus {{ border-color: {ACCENT}; }}
QPushButton:disabled, QToolButton#bouton:disabled {{ color: {DISCRET}; border-color: {BORD}; background: {SURFACE_2}; }}
QPushButton#primaire {{ background: {ACCENT}; border: 1px solid {ACCENT}; color: white; }}
QPushButton#primaire:hover {{ background: {ACCENT_SURVOL}; border-color: {ACCENT_SURVOL}; }}
QPushButton#primaire:pressed {{ background: {ACCENT_PRESSE}; }}
QPushButton#primaire:disabled {{ background: #A9C0F5; border-color: #A9C0F5; color: #F5F8FF; }}
QPushButton#danger {{ color: {GRAVITE['Erreur'][0]}; }}
QPushButton#danger:hover {{ background: {GRAVITE['Erreur'][1]}; border-color: #F0B4B4; }}
QPushButton#discret, QPushButton#lien {{ background: transparent; border: 1px solid transparent; color: {SECONDAIRE}; }}
QPushButton#discret:hover {{ background: #EEF2F6; }}
QPushButton#lien {{ color: {ACCENT}; padding: 4px 6px; }}
QPushButton#lien:hover {{ background: {ACCENT_CLAIR}; }}
QPushButton#ctaParcours {{ background: {ACCENT}; border: 1px solid {ACCENT}; color: white; padding: 8px 16px; }}
QPushButton#ctaParcours:hover {{ background: {ACCENT_SURVOL}; }}
QPushButton#ctaExistant {{ background: {EXISTANT}; border: 1px solid {EXISTANT}; color: white; padding: 8px 16px; }}
QPushButton#ctaExistant:hover {{ background: #6D28D9; }}
QToolButton#bouton::menu-indicator {{ subcontrol-position: right center; right: 6px; }}
QToolButton#bouton {{ padding-right: 22px; }}

/* ---------- champs */
QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit {{ background: {SURFACE}; border: 1px solid {BORD_FORT};
        border-radius: 7px; padding: 5px 8px; min-height: 20px; selection-background-color: {ACCENT}; }}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{ border-color: #AEB9C7; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {ACCENT}; }}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{ background: {SURFACE_2}; color: {DISCRET}; }}
QLineEdit[invalide="true"] {{ border-color: {GRAVITE['Erreur'][0]}; background: {GRAVITE['Erreur'][1]}; }}
QLineEdit#champRecherche {{ padding-left: 8px; background: {SURFACE}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {SURFACE}; border: 1px solid {BORD_FORT}; border-radius: 6px; padding: 4px;
                              selection-background-color: {ACCENT_CLAIR}; selection-color: {TEXTE}; }}
QTextEdit#rapport {{ font-family: "Cascadia Mono", Consolas, monospace; font-size: 9.5pt; background: {SURFACE_2}; }}

/* ---------- segments (filtres exclusifs) */
QFrame#segment {{ border: 1px solid {BORD_FORT}; border-radius: 8px; background: {SURFACE_2}; }}
QFrame#segment QRadioButton {{ padding: 4px 11px; border-radius: 6px; color: {SECONDAIRE}; font-weight: 600; }}
QFrame#segment QRadioButton {{ spacing: 0px; }}
QFrame#segment QRadioButton::indicator {{ width: 0px; height: 0px; margin: 0px; border: none; image: none; background: transparent; }}
QFrame#segment QRadioButton:hover {{ color: {TEXTE}; }}
QFrame#segment QRadioButton:checked {{ background: {SURFACE}; color: {ACCENT_PRESSE}; border: 1px solid {BORD}; }}
QCheckBox, QRadioButton {{ spacing: 8px; }}

/* ---------- arborescence */
QTreeView, QTreeWidget {{ background: {SURFACE}; border: 1px solid {BORD}; border-radius: 8px; padding: 4px;
        selection-background-color: #E3ECFF; selection-color: {TEXTE}; outline: 0; }}
QTreeView::item {{ padding: 3px 4px; border-radius: 4px; }}
QTreeView::item:hover {{ background: #F3F7FF; }}
QTreeView::item:selected {{ background: #E3ECFF; color: {TEXTE}; }}

/* ---------- tableaux */
QTableView, QTableWidget, QListWidget {{ background: {SURFACE}; alternate-background-color: #FAFBFD;
        border: 1px solid {BORD}; border-radius: 8px; gridline-color: #EEF1F5;
        selection-background-color: #E3ECFF; selection-color: {TEXTE}; }}
QTableView::item, QTableWidget::item {{ padding: 0 6px; border: none; }}
QTableView::item:hover, QTableWidget::item:hover {{ background: #F3F7FF; }}
QHeaderView {{ background: {SURFACE_2}; border: none; }}
QHeaderView::section {{ background: {SURFACE_2}; color: {SECONDAIRE}; font-weight: 700; font-size: 9pt;
        padding: 7px 8px; border: none; border-right: 1px solid #EEF1F5; border-bottom: 1px solid {BORD}; }}
QHeaderView::section:hover {{ background: #EEF2F6; color: {TEXTE}; }}
QTableCornerButton::section {{ background: {SURFACE_2}; border: none; }}
QListWidget#palette {{ border: none; border-top: 1px solid {BORD}; border-radius: 0; padding: 6px; }}
QListWidget#palette::item {{ padding: 8px 10px; border-radius: 6px; }}
QListWidget#palette::item:selected {{ background: {ACCENT_CLAIR}; color: {ACCENT_PRESSE}; }}
QLineEdit#paletteSaisie {{ border: none; font-size: 12pt; padding: 12px 14px; background: {SURFACE}; }}
QDialog#paletteDialogue {{ background: {SURFACE}; border: 1px solid {BORD_FORT}; border-radius: 12px; }}

/* ---------- onglets */
QTabWidget::pane {{ border: none; background: transparent; top: -1px; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{ background: transparent; color: {SECONDAIRE}; padding: 8px 14px; margin-right: 4px;
               border: none; border-bottom: 2px solid transparent; font-weight: 600; }}
QTabBar::tab:hover {{ color: {TEXTE}; }}
QTabBar::tab:selected {{ color: {ACCENT_PRESSE}; border-bottom: 2px solid {ACCENT}; }}

/* ---------- barres de défilement fines */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #CBD3DE; border-radius: 3px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: #A9B4C2; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #CBD3DE; border-radius: 3px; min-width: 28px; }}
QScrollBar::handle:horizontal:hover {{ background: #A9B4C2; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------- barres de progression (occupation mémoire) */
QProgressBar {{ background: #EEF2F6; border: none; border-radius: 4px; max-height: 8px; min-height: 8px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}
QProgressBar[gravite="Alerte"]::chunk {{ background: #F59E0B; }}
QProgressBar[gravite="Erreur"]::chunk {{ background: {GRAVITE['Erreur'][0]}; }}

/* ---------- menus, barres système */
QMenuBar {{ background: {SURFACE}; border-bottom: 1px solid {BORD}; padding: 1px 6px; }}
QMenuBar::item {{ padding: 5px 10px; border-radius: 6px; color: {SECONDAIRE}; }}
QMenuBar::item:selected {{ background: {LATERAL_SURVOL}; color: {TEXTE}; }}
QMenu {{ background: {SURFACE}; border: 1px solid {BORD_FORT}; border-radius: 8px; padding: 5px; }}
QMenu::item {{ padding: 6px 26px 6px 12px; border-radius: 5px; }}
QMenu::item:selected {{ background: {ACCENT_CLAIR}; color: {ACCENT_PRESSE}; }}
QMenu::item:disabled {{ color: {DISCRET}; }}
QMenu::separator {{ height: 1px; background: {BORD}; margin: 5px 8px; }}
QStatusBar {{ background: {SURFACE}; border-top: 1px solid {BORD}; color: {SECONDAIRE}; font-size: 9pt; }}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ padding: 0 4px; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 10px; }}
QSplitter::handle:vertical {{ height: 10px; }}
QToolTip {{ background: #1E293B; color: white; border: none; border-radius: 6px; padding: 6px 8px; font-size: 9pt; }}
QMessageBox QLabel {{ font-size: 10pt; }}
QDialogButtonBox QPushButton {{ min-width: 86px; }}

/* ---------- notification éphémère */
QFrame#toast {{ background: #1E293B; border-radius: 10px; }}
QLabel#toastTexte {{ color: white; font-size: 10pt; font-weight: 500; }}
QLabel#toastIcone {{ background: transparent; }}
"""


def appliquer(app):
    app.setStyle("Fusion")
    familles = set(QFontDatabase.families())
    police = QFont("Segoe UI Variable Text" if "Segoe UI Variable Text" in familles else "Segoe UI")
    police.setPointSizeF(10)
    police.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(police)
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor(FOND))
    pal.setColor(QPalette.ColorRole.Base, QColor(SURFACE))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#FAFBFD"))
    pal.setColor(QPalette.ColorRole.Text, QColor(TEXTE))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXTE))
    pal.setColor(QPalette.ColorRole.Button, QColor(SURFACE))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(TEXTE))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(DISCRET))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1E293B"))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor("white"))
    app.setPalette(pal)
    app.setStyleSheet(FEUILLE)
