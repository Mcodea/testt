"""Fenêtre SOREP : accueil des ouvrages, parcours guidé, navigation et garde-fous.

L'interface n'implémente aucune règle de calcul : elle orchestre Session, les vues
métier et le registre de fichiers. Les écrans travaillent sur le même ouvrage.

Ergonomie :
  * barre latérale organisée en étapes numérotées, avec avancement et compteurs ;
  * barre de contexte : ouvrage ouvert, état d'enregistrement, recherche d'actions (Ctrl+K) ;
  * confirmations non bloquantes (notifications) pour les actions réussies ;
  * Ctrl+1…Ctrl+7 : accès direct aux étapes du parcours.
"""
import os

from PySide6.QtCore import Qt, QSettings, QSize, QSignalBlocker, QTimer
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QPixmap
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel,
                               QStackedWidget, QFileDialog, QMessageBox, QPushButton, QButtonGroup,
                               QDialog, QLineEdit, QListWidget, QListWidgetItem)

from genvar import chemins, projets, NOM_OUTIL, VERSION
from . import style, parcours, guide
from .composants import Badge, BoutonNavigation, BandeauGuide, Toast, avertir, informer, repolir
from .vue_accueil import VueAccueil
from .vue_ouvrage import VueOuvrage
from .vue_variables import VueVariables
from .vues_complementaires import (VueSynthese, VueParametres, VueControles, VueExports)
from .vue_liste_es import VueES
from .vue_catalogue import VueCatalogue
from .vue_teletransmission import VueExistant

NAVIGATION = [
    # nom interne (clé des vues), libellé, icône
    ("Mes ouvrages", "Mes ouvrages", "accueil"),
    ("Synthèse", "Tableau de bord", "tableau_bord"),
    ("Ouvrage", "Ouvrage & équipements", "document"),
    ("E/S automate", "Liste des E/S", "es"),
    ("Variables", "Variables fonctionnelles", "liste"),
    ("Plan mémoire", "Plan mémoire", "memoire"),
    ("Projet existant", "Analyse & télétransmission", "analyse"),
    ("Contrôles", "Contrôles", "controle"),
    ("Exports", "Exports", "export"),
    ("Catalogue", "Référentiel", "catalogue"),
]
LIBELLES = {nom: libelle for nom, libelle, _ in NAVIGATION}


class PaletteCommandes(QDialog):
    """Recherche rapide d'un écran ou d'une action (Ctrl+K), au clavier."""

    def __init__(self, parent, commandes):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("paletteDialogue")
        self.commandes = commandes            # [(libellé, catégorie, icône, callable)]
        self.setFixedWidth(560)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.saisie = QLineEdit()
        self.saisie.setObjectName("paletteSaisie")
        self.saisie.setPlaceholderText("Aller à un écran ou lancer une action…")
        lay.addWidget(self.saisie)
        self.liste = QListWidget()
        self.liste.setObjectName("palette")
        self.liste.setIconSize(QSize(16, 16))
        self.liste.setMinimumHeight(320)
        lay.addWidget(self.liste)
        self.saisie.textChanged.connect(self._filtrer)
        self.saisie.returnPressed.connect(self._executer)
        self.liste.itemActivated.connect(lambda *_: self._executer())
        self._filtrer("")

    def _filtrer(self, texte):
        t = texte.casefold().strip()
        self.liste.clear()
        for i, (libelle, categorie, nom_icone, _) in enumerate(self.commandes):
            if t and t not in f"{libelle} {categorie}".casefold():
                continue
            item = QListWidgetItem(style.icone(nom_icone, style.SECONDAIRE, 16), f"{libelle}")
            item.setToolTip(categorie)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.liste.addItem(item)
        if self.liste.count():
            self.liste.setCurrentRow(0)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up) and self.liste.count():
            pas = 1 if e.key() == Qt.Key.Key_Down else -1
            self.liste.setCurrentRow((self.liste.currentRow() + pas) % self.liste.count())
            return
        super().keyPressEvent(e)

    def _executer(self):
        item = self.liste.currentItem()
        if item is None:
            return
        action = self.commandes[item.data(Qt.ItemDataRole.UserRole)][3]
        self.accept()
        QTimer.singleShot(0, action)


class Fenetre(QMainWindow):
    def __init__(self, session=None):
        super().__init__()
        from genvar.session import Session
        self.s = session or Session()
        self.avancement = None
        self.setMinimumSize(QSize(1180, 720))
        self.pile = QStackedWidget()
        self.pile.setObjectName("pile")
        self.v_accueil = VueAccueil()
        self.v_synthese = VueSynthese(self.s)
        self.v_ouvrage = VueOuvrage(self.s)
        self.v_variables = VueVariables(self.s)
        self.v_es = VueES(self.s)
        self.v_existant = VueExistant(self.s)
        self.v_catalogue = VueCatalogue(self.s)
        self.v_parametres = VueParametres(self.s)
        self.v_controles = VueControles(self.s)
        self.v_exports = VueExports(self.s)
        self.vues = {
            "Mes ouvrages": self.v_accueil,
            "Synthèse": self.v_synthese,
            "Ouvrage": self.v_ouvrage,
            "Variables": self.v_variables,
            "E/S automate": self.v_es,
            "Projet existant": self.v_existant,
            "Plan mémoire": self.v_parametres,
            "Contrôles": self.v_controles,
            "Exports": self.v_exports,
            "Catalogue": self.v_catalogue,
        }
        for vue in self.vues.values():
            self.pile.addWidget(vue)
        # « À faire maintenant » : un bandeau de guidage en tête des écrans du projet neuf
        self.guides = {}
        for nom in ("Ouvrage", "Variables", "E/S automate", "Plan mémoire", "Contrôles"):
            bandeau = BandeauGuide()
            bandeau.commande.connect(self.executer)
            self.vues[nom].disposition.insertWidget(1, bandeau)
            self.guides[nom] = bandeau

        self.setCentralWidget(self._construire_espace())
        self._construire_actions()
        self.toast = Toast(self)

        # Accueil : pilotage des projets sans mélange avec l'ouvrage en cours.
        self.v_accueil.nouveau_demande.connect(self.nouveau)
        self.v_accueil.nouveau_neuf_demande.connect(lambda: self.nouveau_mode("Neuf"))
        self.v_accueil.nouveau_existant_demande.connect(lambda: self.nouveau_mode("Existant"))
        self.v_accueil.ouvrir_demande.connect(self.ouvrir)
        self.v_accueil.fichier_demande.connect(self.ouvrir)
        self.v_accueil.importer_demande.connect(self.importer_anciens_projets)
        self.v_accueil.dupliquer_demande.connect(self.dupliquer)
        self.v_accueil.archiver_demande.connect(self.archiver)
        self.v_accueil.supprimer_demande.connect(self.supprimer_ouvrage)
        self.v_accueil.corbeille_demande.connect(self.restaurer_ouvrage)
        self.v_synthese.naviguer.connect(self.aller)
        self.v_controles.naviguer.connect(self._aller_anomalie)
        self.v_exports.naviguer.connect(self.aller)
        self.v_controles.commande.connect(self.executer)
        self.v_ouvrage.voir_es.connect(self._voir_es_equipement)
        for v in (self.v_ouvrage, self.v_variables, self.v_es, self.v_existant,
                  self.v_catalogue, self.v_parametres):
            v.modifie.connect(self._ouvrage_modifie)
        self.v_ouvrage.mode_change.connect(self._ouvrage_modifie)
        self.v_variables.message.connect(lambda t: self.toast.montrer(t, "OK"))
        self.v_variables.export_demande.connect(self._aller_exports)

        self._restaurer()
        self.charger()
        # Écran initial toujours dédié aux ouvrages, et non à une fiche vide.
        self.accueil()

    # ================================================================== construction
    def _construire_espace(self):
        espace = QWidget()
        centre = QHBoxLayout(espace)
        centre.setContentsMargins(0, 0, 0, 0)
        centre.setSpacing(0)
        centre.addWidget(self._construire_lateral())
        travail = QWidget()
        droite = QVBoxLayout(travail)
        droite.setContentsMargins(0, 0, 0, 0)
        droite.setSpacing(0)
        droite.addWidget(self._construire_contexte())
        droite.addWidget(self.pile, 1)
        centre.addWidget(travail, 1)
        return espace

    def _construire_lateral(self):
        lateral = QFrame()
        lateral.setObjectName("lateral")
        lateral.setFixedWidth(256)
        lay = QVBoxLayout(lateral)
        lay.setContentsMargins(12, 16, 12, 0)
        lay.setSpacing(2)

        marque = QHBoxLayout()
        marque.setContentsMargins(6, 0, 0, 10)
        marque.setSpacing(10)
        logo = QLabel()
        logo.setObjectName("logoOGIAS")
        logo.setFixedSize(38, 38)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chemin_logo = os.path.join(os.path.dirname(__file__), "assets", "ogias-icone-512.png")
        if os.path.isfile(chemin_logo):
            logo.setPixmap(QPixmap(chemin_logo).scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            logo.setText("OG")
        marque.addWidget(logo)
        textes = QVBoxLayout()
        textes.setSpacing(0)
        nom = QLabel("OGIAS")
        nom.setObjectName("marque")
        sous = QLabel("Ingénierie · Automatisme · Supervision")
        sous.setObjectName("marqueSous")
        textes.addWidget(nom)
        textes.addWidget(sous)
        marque.addLayout(textes, 1)
        lay.addLayout(marque)

        self.groupe_nav = QButtonGroup(self)
        self.groupe_nav.setExclusive(True)
        self.items = {}
        for nom, libelle, nom_icone in NAVIGATION:
            b = BoutonNavigation(nom, libelle, nom_icone)
            b.clicked.connect(lambda _=False, n=nom: self.aller(n))
            self.groupe_nav.addButton(b)
            self.items[nom] = b

        lay.addWidget(self.items["Mes ouvrages"])

        # Carte du dossier ouvert : on sait toujours sur quoi on travaille.
        self.carte_dossier = QFrame()
        self.carte_dossier.setObjectName("carteDossier")
        cd = QVBoxLayout(self.carte_dossier)
        cd.setContentsMargins(12, 10, 12, 10)
        cd.setSpacing(3)
        ligne = QHBoxLayout()
        self.dossier_repere = QLabel("—")
        self.dossier_repere.setObjectName("dossierRepere")
        self.dossier_mode = Badge()
        ligne.addWidget(self.dossier_repere, 1)
        ligne.addWidget(self.dossier_mode)
        cd.addLayout(ligne)
        self.dossier_libelle = QLabel("")
        self.dossier_libelle.setObjectName("dossierLibelle")
        self.dossier_libelle.setWordWrap(True)
        cd.addWidget(self.dossier_libelle)
        self.dossier_avancement = QLabel("")
        self.dossier_avancement.setObjectName("aide")
        cd.addWidget(self.dossier_avancement)
        lay.addSpacing(10)
        lay.addWidget(self.carte_dossier)
        lay.addSpacing(6)
        lay.addWidget(self.items["Synthèse"])

        self.titre_parcours = QLabel("PARCOURS")
        self.titre_parcours.setObjectName("sectionNav")
        lay.addWidget(self.titre_parcours)
        for nom in ("Ouvrage", "E/S automate", "Variables", "Plan mémoire", "Projet existant",
                    "Contrôles", "Exports"):
            lay.addWidget(self.items[nom])

        lay.addStretch(1)
        ref = QLabel("RÉFÉRENTIEL")
        ref.setObjectName("sectionNav")
        lay.addWidget(ref)
        lay.addWidget(self.items["Catalogue"])
        version = QLabel(f"Version {VERSION}")
        version.setObjectName("versionLaterale")
        lay.addWidget(version)
        # Compatibilité : anciens titres de sections (masqués/affichés avec le parcours).
        self._titres_sections = {"parcours": self.titre_parcours, "commun": self.carte_dossier}
        return lateral

    def _construire_contexte(self):
        contexte = QFrame()
        contexte.setObjectName("barreSuperieure")
        bande = QHBoxLayout(contexte)
        bande.setContentsMargins(28, 10, 20, 10)
        bande.setSpacing(10)
        labels = QVBoxLayout()
        labels.setSpacing(1)
        self.fil_ariane = QLabel("SOREP  /  Espace de travail")
        self.fil_ariane.setObjectName("filAriane")
        self.titre_contexte = QLabel("Mes ouvrages")
        self.titre_contexte.setObjectName("titreContexte")
        labels.addWidget(self.fil_ariane)
        labels.addWidget(self.titre_contexte)
        bande.addLayout(labels)
        bande.addStretch(1)
        self.b_recherche = QPushButton("  Rechercher une action…        Ctrl+K")
        self.b_recherche.setObjectName("recherche")
        self.b_recherche.setIcon(style.icone("recherche", style.DISCRET, 14))
        self.b_recherche.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_recherche.clicked.connect(self.palette)
        bande.addWidget(self.b_recherche)
        self.etat_enregistrement = QLabel("")
        self.etat_enregistrement.setObjectName("etatEnregistrement")
        bande.addWidget(self.etat_enregistrement)
        self.b_enregistrer_entete = QPushButton("Enregistrer")
        self.b_enregistrer_entete.setIcon(style.icone("enregistrer", "#FFFFFF", 16))
        self.b_enregistrer_entete.setObjectName("primaire")
        self.b_enregistrer_entete.setToolTip("Enregistrer l'ouvrage (Ctrl+S)")
        self.b_enregistrer_entete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_enregistrer_entete.clicked.connect(self.enregistrer)
        bande.addWidget(self.b_enregistrer_entete)
        return contexte

    def _construire_actions(self):
        self.a_accueil = self._action("Mes ouvrages", self.accueil, "Ctrl+H", "accueil")
        self.a_nouveau = self._action("Nouvel ouvrage…", self.nouveau, QKeySequence.StandardKey.New, "ajouter")
        self.a_ouvrir = self._action("Ouvrir un fichier…", self.ouvrir, QKeySequence.StandardKey.Open, "ouvrir")
        self.a_enregistrer = self._action("Enregistrer", self.enregistrer, QKeySequence.StandardKey.Save, "enregistrer")
        self.a_enregistrer_sous = self._action("Enregistrer sous…", self.enregistrer_sous,
                                               QKeySequence.StandardKey.SaveAs)
        self.a_quitter = self._action("Quitter", self.close, QKeySequence.StandardKey.Quit)
        self.a_attribuer = self._action("Attribuer les adresses…", self._attribuer, None, "memoire")
        self.a_xsy = self._action("Exporter XSY…", lambda: self._aller_exports("xsy"), "Ctrl+E", "export")
        self.a_xlsx = self._action("Exporter Excel…", lambda: self._aller_exports("xlsx"), None, "export")
        self.a_palette = self._action("Rechercher une action…", self.palette, "Ctrl+K", "recherche")

        fichier = self.menuBar().addMenu("&Fichier")
        for a in (self.a_accueil, self.a_nouveau, self.a_ouvrir, None, self.a_enregistrer,
                  self.a_enregistrer_sous, None, self.a_quitter):
            fichier.addSeparator() if a is None else fichier.addAction(a)
        outils = self.menuBar().addMenu("&Outils")
        for a in (self.a_attribuer, self.a_xsy, self.a_xlsx, None, self.a_palette):
            outils.addSeparator() if a is None else outils.addAction(a)
        self.menu_affichage = self.menuBar().addMenu("&Affichage")
        for nom, libelle, nom_icone in NAVIGATION:
            self.menu_affichage.addAction(style.icone(nom_icone, style.SECONDAIRE, 16), libelle.replace("&", "&&"),
                                          lambda checked=False, n=nom: self.aller(n))
        aide = self.menuBar().addMenu("&Aide")
        aide.addAction("Raccourcis clavier", self.raccourcis)
        aide.addAction("À propos", self.a_propos)

        # Ctrl+1…Ctrl+7 : étapes visibles du parcours, dans l'ordre affiché.
        for i in range(1, 8):
            QShortcut(QKeySequence(f"Ctrl+{i}"), self, activated=lambda i=i: self._aller_etape(i))

        self.b_mode = Badge()
        self.b_var = Badge()
        self.b_err = Badge()
        self.b_al = Badge()
        self.chemin_label = QLabel("")
        self.statusBar().addWidget(self.chemin_label, 1)
        for b in (self.b_mode, self.b_var, self.b_err, self.b_al):
            self.statusBar().addPermanentWidget(b)

    def _action(self, libelle, callback, raccourci=None, nom_icone=None):
        action = QAction(libelle, self)
        action.triggered.connect(callback)
        if raccourci:
            action.setShortcut(QKeySequence(raccourci))
        if nom_icone:
            action.setIcon(style.icone(nom_icone, style.SECONDAIRE, 16))
        return action

    # ================================================================== navigation
    def aller(self, nom):
        vue = self.vues.get(nom)
        if vue is None:
            return
        self.pile.setCurrentWidget(vue)
        bouton = self.items.get(nom)
        if bouton is not None:
            bouton.setChecked(True)
        if nom == "Variables":
            self.v_variables.rafraichir()
        elif nom == "Ouvrage":
            self.v_ouvrage.rafraichir()
        elif hasattr(vue, "charger"):
            vue.charger()
        self._maj_etat()

    def _aller_etape(self, rang):
        if self.pile.currentWidget() is self.v_accueil or self.avancement is None:
            return
        etapes = self.avancement.etapes
        if 1 <= rang <= len(etapes):
            self.aller(etapes[rang - 1].nom)

    def _aller_anomalie(self, anomalie):
        """Double-clic sur un contrôle : montrer l'élément concerné dans l'écran de travail."""
        if self.s.ouvrage.mode == "Existant":
            self.aller("Projet existant")
            return
        self.aller("Variables")
        self.v_variables._aller_a(anomalie)

    def accueil(self):
        self.v_accueil.charger()
        self.aller("Mes ouvrages")

    def palette(self):
        projet = self.pile.currentWidget() is not self.v_accueil
        neuf = self.s.ouvrage.mode == "Neuf"
        commandes = []
        for nom, libelle, nom_icone in NAVIGATION:
            b = self.items[nom]
            if nom == "Mes ouvrages" or nom == "Catalogue" or (projet and not b.isHidden()):
                commandes.append((f"Aller à : {libelle}", "Navigation", nom_icone, lambda n=nom: self.aller(n)))
        commandes += [
            ("Créer un projet neuf", "Ouvrage", "ajouter", lambda: self.nouveau_mode("Neuf")),
            ("Analyser un ouvrage existant", "Ouvrage", "analyse", lambda: self.nouveau_mode("Existant")),
            ("Ouvrir un fichier d'ouvrage…", "Ouvrage", "ouvrir", self.ouvrir),
        ]
        if projet:
            commandes.append(("Enregistrer l'ouvrage", "Ouvrage", "enregistrer", self.enregistrer))
            if neuf:
                commandes += [
                    ("Ajouter un équipement…", "Fiche ouvrage", "ajouter",
                     lambda: (self.aller("Ouvrage"), self.v_ouvrage._ajouter_eq())),
                    ("Attribuer les adresses…", "Variables", "memoire", self._attribuer),
                    ("Exporter le fichier XSY…", "Exports", "export", lambda: self._aller_exports("xsy")),
                ]
            else:
                commandes += [
                    ("Importer des variables (XSY / SCY / Excel / CSV)…", "Analyse", "import",
                     lambda: (self.aller("Projet existant"), self.v_existant.importer())),
                    ("Importer une liste d'E/S…", "Analyse", "import",
                     lambda: (self.aller("Projet existant"), self.v_existant.importer_es())),
                    ("Équipements détectés dans le programme…", "Analyse", "analyse",
                     lambda: (self.aller("Projet existant"), self.v_existant.equipements_detectes())),
                    ("Construire / mettre à jour la table de télétransmission", "Analyse", "liste",
                     lambda: (self.aller("Projet existant"), self.v_existant.construire())),
                    ("Proposer les associations", "Analyse", "assistant",
                     lambda: (self.aller("Projet existant"), self.v_existant.proposer())),
                ]
            commandes.append(("Exporter le tableau Excel…", "Exports", "export", lambda: self._aller_exports("xlsx")))
        d = PaletteCommandes(self, commandes)
        centre = self.mapToGlobal(self.rect().center())
        d.move(centre.x() - d.width() // 2, self.mapToGlobal(self.rect().topLeft()).y() + 90)
        d.saisie.setFocus()
        d.exec()

    # ================================================================== état
    def _ouvrage_modifie(self):
        # Une modification après validation invalide l'ancien statut ; refléter
        # immédiatement cet état dans la fiche même si un autre écran est actif.
        statut = self.s.ouvrage.statut
        if self.v_ouvrage.statut.currentText() != statut:
            with QSignalBlocker(self.v_ouvrage.statut):
                self.v_ouvrage.statut.setCurrentText(statut)
        self.v_variables.invalider()
        if self.sender() is self.v_variables:
            self.v_ouvrage.rafraichir()
        if self.pile.currentWidget() is self.v_synthese:
            self.v_synthese.charger()
        self._maj_etat()

    def charger(self):
        self.v_ouvrage.charger()
        self.v_variables.invalider()
        self._maj_etat()

    def _maj_etat(self):
        o = self.s.ouvrage
        av = self.avancement = parcours.calculer(self.s)
        titre = o.libelle or o.prefixe() or "Nouvel ouvrage"
        self.setWindowTitle(f"{'* ' if self.s.modifie else ''}{titre} — {NOM_OUTIL}")
        actif = self.pile.currentWidget() is not self.v_accueil
        neuf = o.mode == "Neuf"
        courant = next((n for n, v in self.vues.items() if v is self.pile.currentWidget()), "Mes ouvrages")

        # ---------------------------------------------------------- barre de contexte
        mode_txt = "Projet neuf" if neuf else "Projet existant"
        self.fil_ariane.setText("SOREP  /  " + ("Mes ouvrages" if not actif else
                                f"{mode_txt}  /  {LIBELLES.get(courant, courant)}"))
        self.titre_contexte.setText("Mes ouvrages" if not actif else
                                    f"{o.prefixe() or 'Nouvel ouvrage'}  ·  {o.libelle or 'Identification à compléter'}")
        self.b_enregistrer_entete.setVisible(actif)
        self.etat_enregistrement.setVisible(actif)
        if self.s.modifie:
            self.etat_enregistrement.setText("●  Modifications non enregistrées")
            repolir(self.etat_enregistrement, etat="modifie")
        elif self.s.chemin:
            self.etat_enregistrement.setText("✓  Enregistré")
            repolir(self.etat_enregistrement, etat="ok")
        else:
            self.etat_enregistrement.setText("Non enregistré")
            repolir(self.etat_enregistrement, etat="modifie")
        self.chemin_label.setText(str(self.s.chemin) if (actif and self.s.chemin) else
                                  ("" if actif else f"Dossier des ouvrages : {chemins.dossier_projets()}"))

        # ---------------------------------------------------------- barre latérale
        self.carte_dossier.setVisible(actif)
        self.titre_parcours.setVisible(actif)
        self.dossier_repere.setText(o.prefixe() or "Nouvel ouvrage")
        self.dossier_libelle.setText(o.libelle or "Libellé à renseigner")
        self.dossier_mode.definir("Neuf" if neuf else "Existant", "Info" if neuf else "Existant")
        self.dossier_avancement.setText(f"{av.faites} / {len(av.etapes)} étapes terminées")
        visibles = {e.nom: e for e in av.etapes}
        for nom, b in self.items.items():
            if nom in ("Mes ouvrages", "Catalogue"):
                b.setHidden(False)
                b.definir_etat(None)
                continue
            if nom == "Synthèse":
                b.setHidden(not actif)
                b.definir_etat(None)
                continue
            etape = visibles.get(nom)
            b.setHidden(not (actif and etape is not None))
            if etape is not None:
                b.definir_etat(etape.etat, etape.numero)
                b.definir_badge(etape.badge, etape.gravite)
                b.setToolTip(f"{etape.titre} — {etape.detail}\nRaccourci : Ctrl+{etape.numero}")
        bouton_courant = self.items.get(courant)
        if bouton_courant is not None and not bouton_courant.isChecked():
            bouton_courant.setChecked(True)
        if bouton_courant is not None and courant in visibles:
            e = visibles[courant]
            bouton_courant.definir_etat(e.etat, e.numero)
        elif bouton_courant is not None:
            bouton_courant.definir_etat(None)

        self.a_attribuer.setEnabled(actif and neuf)
        self.a_xsy.setEnabled(actif and neuf)
        self.a_xlsx.setEnabled(actif)
        self.a_enregistrer.setEnabled(actif)
        self.a_enregistrer_sous.setEnabled(actif)

        # ---------------------------------------------------------- guidage
        bandeau = self.guides.get(courant)
        for nom, b in self.guides.items():
            if b is not bandeau:
                b.hide()
        if bandeau is not None:
            actions = guide.a_faire(self.s) if actif and neuf else []
            bandeau.afficher(guide.pour_ecran(actions, courant, maximum=2), total=len(actions))

        # ---------------------------------------------------------- barre d'état
        for b in (self.b_mode, self.b_var, self.b_err, self.b_al):
            b.setVisible(actif)
        self.b_mode.definir(mode_txt, "Info" if neuf else "Existant")
        self.b_var.definir(f"{av.variables} variables", "Neutre")
        self.b_err.definir(f"{av.erreurs} erreur(s)", "Erreur" if av.erreurs else "OK")
        self.b_al.definir(f"{av.alertes} alerte(s)", "Alerte" if av.alertes else "OK")

    # ================================================================== fichiers
    def _confirmer_abandon(self):
        if not self.s.modifie:
            return True
        boite = QMessageBox(QMessageBox.Icon.Question, "Modifications non enregistrées",
                            "Enregistrer les modifications de l'ouvrage avant de poursuivre ?",
                            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                            QMessageBox.StandardButton.Cancel, self)
        boite.button(QMessageBox.StandardButton.Save).setText("Enregistrer")
        boite.button(QMessageBox.StandardButton.Discard).setText("Ne pas enregistrer")
        boite.button(QMessageBox.StandardButton.Cancel).setText("Annuler")
        boite.setDefaultButton(QMessageBox.StandardButton.Save)
        boite.exec()
        clic = boite.clickedButton()
        if clic is None or clic is boite.button(QMessageBox.StandardButton.Cancel):
            return False
        if clic is boite.button(QMessageBox.StandardButton.Save):
            return self.enregistrer()
        return True

    def nouveau(self):
        """Depuis le menu : l'accueil présente les deux parcours côte à côte."""
        if self.pile.currentWidget() is not self.v_accueil:
            self.accueil()
        self.toast.montrer("Choisissez le parcours : projet neuf ou ouvrage existant.", "Info")

    def nouveau_mode(self, mode):
        """Création directe depuis les deux cartes de l'accueil."""
        if mode not in ("Neuf", "Existant"):
            raise ValueError("Mode de projet inconnu")
        if not self._confirmer_abandon():
            return
        self.s.nouveau(lieu_dans_le_nom=(mode != "Neuf"))     # règle R2 : pas de lieu dans les noms (projet neuf)
        self.s.definir("mode", mode)
        self.charger()
        self.aller("Ouvrage")
        self.toast.montrer(
            "Projet existant créé : renseignez l'ouvrage, puis importez les fichiers sources."
            if mode == "Existant" else
            "Projet neuf créé : renseignez l'ouvrage, puis ajoutez les équipements.", "Info")

    def ouvrir(self, chemin=None):
        if isinstance(chemin, bool):
            chemin = None
        if not chemin:
            chemin, _ = QFileDialog.getOpenFileName(self, "Ouvrir un ouvrage", chemins.dossier_projets(),
                                                    "Ouvrage (*.ouvrage.json);;Tous les fichiers (*.*)")
        if not chemin:
            return
        if not self._confirmer_abandon():
            return
        try:
            self.s.ouvrir(chemin)
        except Exception as exc:
            avertir(self, "Ouvrage illisible", f"Le fichier n'a pas été modifié.\n{exc}")
            return
        self.charger()
        self.aller("Synthèse")
        if self.s.avertissement_ouverture:
            avertir(self, "Ouvrage existant à contrôler", self.s.avertissement_ouverture)
        else:
            self.toast.montrer(f"Ouvrage ouvert : {os.path.basename(chemin)}", "OK")

    def enregistrer(self):
        if self.pile.currentWidget() is self.v_accueil and not self.s.chemin:
            return False
        if not self.s.chemin:
            # Un nouveau projet est classé par défaut dans le registre des ouvrages.
            if not self.s.ouvrage.code_ouvrage:
                return self.enregistrer_sous()
            cible = projets.nom_libre(self.s.nom_fichier_propose())
        else:
            cible = self.s.chemin
        try:
            self.s.enregistrer(str(cible))
        except Exception as exc:
            avertir(self, "Enregistrement impossible", str(exc))
            return False
        self.v_accueil.charger()
        self._maj_etat()
        self.toast.montrer(f"Ouvrage enregistré · {os.path.basename(str(cible))}", "OK")
        return True

    def enregistrer_sous(self):
        suggestion = os.path.join(chemins.dossier_projets(), self.s.nom_fichier_propose() + ".ouvrage.json")
        cible, _ = QFileDialog.getSaveFileName(self, "Enregistrer l'ouvrage", suggestion,
                                               "Ouvrage SOREP (*.ouvrage.json)")
        if not cible:
            return False
        if not cible.lower().endswith(".ouvrage.json"):
            cible += ".ouvrage.json"
        if os.path.exists(cible):
            boite = QMessageBox(QMessageBox.Icon.Question, "Fichier existant",
                                "Écraser le fichier choisi ? Une sauvegarde .bak sera conservée.",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
            boite.setDefaultButton(QMessageBox.StandardButton.No)
            boite.exec()
            if boite.clickedButton() is not boite.button(QMessageBox.StandardButton.Yes):
                return False
        try:
            self.s.enregistrer(cible)
        except Exception as exc:
            avertir(self, "Enregistrement impossible", str(exc))
            return False
        self.v_accueil.charger()
        self._maj_etat()
        self.toast.montrer(f"Ouvrage enregistré · {os.path.basename(cible)}", "OK")
        return True

    def importer_anciens_projets(self):
        dossier = QFileDialog.getExistingDirectory(self, "Dossier d'une ancienne version ou dossier Projets")
        if not dossier:
            return
        try:
            copies = projets.importer_dossier(dossier)
        except Exception as exc:
            avertir(self, "Import des ouvrages", str(exc))
            return
        self.v_accueil.charger()
        informer(self, "Import terminé", f"{len(copies)} fichier(s) copié(s) sans écraser les originaux.")

    def dupliquer(self, chemin):
        try:
            destination = projets.dupliquer(chemin)
        except Exception as exc:
            avertir(self, "Duplication", str(exc))
            return
        self.accueil()
        self.toast.montrer(f"Copie indépendante créée : {os.path.basename(str(destination))}", "OK")

    def archiver(self, chemin, archive):
        if self.s.chemin == chemin and self.s.modifie:
            if not self._confirmer_abandon():
                return
            if self.s.modifie:  # « Ne pas enregistrer » : repartir du fichier enregistré.
                self.s.ouvrir(chemin)
                self.charger()
        try:
            projets.archiver(chemin, archive)
            if self.s.chemin == chemin:
                self.s.ouvrage.archive = archive
        except Exception as exc:
            avertir(self, "Archivage", str(exc))
            return
        self.accueil()
        self.toast.montrer("Ouvrage archivé." if archive else "Ouvrage restauré.", "OK")

    def supprimer_ouvrage(self, chemin):
        """Ouvrage retiré de « Mes ouvrages » : déplacé dans la corbeille, jamais effacé."""
        ouvert = bool(self.s.chemin) and os.path.abspath(self.s.chemin) == os.path.abspath(chemin)
        try:
            destination = projets.supprimer(chemin)
        except Exception as exc:
            avertir(self, "Suppression", str(exc))
            return
        if ouvert:                                   # l'ouvrage affiché n'a plus de fichier : on le referme
            self.s.nouveau()
            self.s.modifie = False
            self.charger()
        self.accueil()
        self.toast.montrer(f"Ouvrage supprimé · restaurable depuis « Corbeille… » "
                           f"({os.path.basename(destination)})", "OK")

    def restaurer_ouvrage(self):
        from PySide6.QtWidgets import QInputDialog
        fiches = projets.lister_corbeille()
        if not fiches:
            informer(self, "Corbeille", "La corbeille est vide.")
            return
        libelles = [f"{f.repere} — {f.libelle}   ({os.path.basename(f.chemin)})" for f in fiches]
        choix, ok = QInputDialog.getItem(self, "Corbeille", "Ouvrage à restaurer dans « Mes ouvrages » :",
                                         libelles, 0, False)
        if not ok or choix not in libelles:
            return
        try:
            remis = projets.restaurer(fiches[libelles.index(choix)].chemin)
        except Exception as exc:
            avertir(self, "Corbeille", str(exc))
            return
        self.accueil()
        self.toast.montrer(f"Ouvrage restauré : {os.path.basename(remis)}", "OK")

    def _voir_es_equipement(self, ident):
        self.aller("E/S automate")
        self.v_es.f_eq.setCurrentIndex(max(0, self.v_es.f_eq.findData(ident)))

    def executer(self, commande):
        """Exécute l'action proposée par un bandeau de guidage ou un groupe de contrôles."""
        if commande == "fiche":
            self.aller("Ouvrage")
            self.v_ouvrage.montrer("ident")
            self.v_ouvrage.lieu.setFocus()
        elif commande == "ajouter_uf":
            self.aller("Ouvrage")
            self.v_ouvrage._ajouter_uf()
        elif commande == "ajouter_se":
            self.aller("Ouvrage")
            self.v_ouvrage._ajouter_se()
        elif commande == "ajouter_eq":
            self.aller("Ouvrage")
            self.v_ouvrage._ajouter_eq()
        elif commande == "propositions":
            self.aller("Ouvrage")
            eq = next((e for e in self.s.equipements_tries()
                       if any(p.etat == "proposé" for p in self.s.propositions(e).values())), None)
            if eq is not None:
                self.v_ouvrage._effacer_filtres()
                if self.v_ouvrage.t_eq.selectionner(lambda e: e.ident == eq.ident):
                    self.v_ouvrage._modifier_eq()
        elif commande == "attribuer":
            self._attribuer()
        elif commande == "valider":
            self.aller("Variables")
            self.v_variables._effacer_filtres()
            self.v_variables.valider_affichees()
        elif commande == "es":
            self.aller("E/S automate")
        elif commande == "variables":
            self.aller("Variables")
        elif commande == "controles":
            self.aller("Contrôles")
        elif commande == "exports":
            self.aller("Exports")
        elif commande == "tableau":
            self.aller("Synthèse")
        self._maj_etat()

    def _attribuer(self):
        if self.s.ouvrage.mode != "Neuf":
            avertir(self, "Adresses", "Un projet existant conserve les adresses de l'automate.")
            return
        self.aller("Variables")
        self.v_variables.attribuer()

    def _aller_exports(self, format):
        self.aller("Exports")
        self.v_exports._exporter(format)

    # ================================================================== aide
    def raccourcis(self):
        informer(self, "Raccourcis clavier",
                 "Ctrl+K\tRechercher un écran ou une action\n"
                 "Ctrl+1 … Ctrl+7\tÉtapes du parcours, dans l'ordre affiché\n"
                 "Ctrl+H\tMes ouvrages\n"
                 "Ctrl+S\tEnregistrer\n"
                 "Ctrl+O\tOuvrir un fichier d'ouvrage\n"
                 "Ctrl+E\tExporter le fichier XSY (projet neuf)\n"
                 "Entrée / double-clic\tModifier la ligne sélectionnée\n"
                 "Clic droit sur un en-tête\tChoisir les colonnes affichées")

    def a_propos(self):
        QMessageBox.about(self, "À propos", f"<b>{NOM_OUTIL}</b><br>Version {VERSION}<br><br>"
                          "Interface PySide6 : accueil, gestion de projets, équipements, variables, "
                          "E/S, reprise d'existant, catalogue, plan mémoire, contrôles et exports.<br>"
                          "Les fichiers d'import/export doivent être vérifiés dans les outils industriels.")

    # ================================================================== fenêtre
    def _restaurer(self):
        ancien = QSettings().value("fenetre/geometrie")
        if ancien is not None:
            self.restoreGeometry(ancien)
        else:
            self.resize(1440, 860)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if getattr(self, "toast", None) is not None and self.toast.isVisible():
            self.toast.replacer()

    def closeEvent(self, evenement):
        if not self._confirmer_abandon():
            evenement.ignore()
            return
        QSettings().setValue("fenetre/geometrie", self.saveGeometry())
        evenement.accept()
