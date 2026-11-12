"""Écrans métier Qt complétant les écrans Ouvrage / Variables de la V0.5.

Tous les changements passent par Session ou par les fonctions du moteur. Les données
issues d'un XSY existant restent inchangées (nom, type, adresse, commentaire).
"""
import os
from collections import Counter
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
                               QTableWidget, QTableWidgetItem, QAbstractItemView, QFileDialog, QDialog, QDialogButtonBox, QCheckBox, QSpinBox, QGridLayout, QTextEdit, QProgressBar, QScrollArea)

from genvar import chemins, import_sources
from genvar.modele import ORDRE_ZONES, zone, TAILLE_MOTS
from .composants import (Page, Carte, Indicateur, Badge, Segment, bouton, avertir, informer,
                         confirmer, notifier, legende, caption, separateur, champ_recherche, repolir)
from .tableaux import Tableau, Colonne
from . import style, parcours


def simple_table(headers):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(32)
    t.horizontalHeader().setStretchLastSection(True)
    t.horizontalHeader().setHighlightSections(False)
    t.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    t.setShowGrid(False)
    t.setWordWrap(False)
    return t


def remplir_table(table, lignes, data_col=0):
    table.setSortingEnabled(False)
    table.setRowCount(len(lignes))
    for i, champs in enumerate(lignes):
        for j, valeur in enumerate(champs):
            item = QTableWidgetItem(str(valeur))
            if j == data_col:
                item.setData(Qt.ItemDataRole.UserRole, i)
            table.setItem(i, j, item)
    table.setSortingEnabled(True)


def choix(parent, titre, texte, items, actuel=None):
    d = QDialog(parent)
    d.setWindowTitle(titre)
    l = QVBoxLayout(d)
    l.addWidget(QLabel(texte))
    c = QComboBox()
    c.addItems(items)
    if actuel in items:
        c.setCurrentText(actuel)
    l.addWidget(c)
    boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    boutons.accepted.connect(d.accept); boutons.rejected.connect(d.reject)
    l.addWidget(boutons)
    return c.currentText() if d.exec() else None


class LigneEtape(QFrame):
    """Ligne de la liste d'avancement : pastille, titre, détail, bouton d'accès."""

    def __init__(self, etape, action, parent=None):
        super().__init__(parent)
        self.setObjectName("ligneEtape")
        self.setProperty("recommande", etape.recommande)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(14)
        pastille = QLabel()
        pastille.setPixmap(style.icone_etape(etape.numero,
                           "actif" if etape.recommande and etape.etat == "a_faire" else etape.etat, 26).pixmap(26, 26))
        lay.addWidget(pastille)
        textes = QVBoxLayout()
        textes.setSpacing(1)
        t = QLabel(etape.titre)
        t.setObjectName("titreLigne")
        textes.addWidget(t)
        d = legende(etape.detail or etape.description)
        textes.addWidget(d)
        lay.addLayout(textes, 1)
        if etape.badge:
            lay.addWidget(Badge(etape.badge, etape.gravite))
        b = bouton("Continuer" if etape.recommande else "Ouvrir", action,
                   primaire=etape.recommande, nom=None if etape.recommande else "discret")
        b.setMinimumWidth(96)
        lay.addWidget(b)


class VueSynthese(Page):
    naviguer = Signal(str)

    def __init__(self, session, parent=None):
        super().__init__("Tableau de bord", "Où en est l'ouvrage, et quelle est la prochaine étape.", parent)
        self.s = session
        self.entete.droite.addWidget(bouton("Fiche ouvrage", lambda: self.naviguer.emit("Ouvrage"),
                                            icone="modifier"))

        # ---------------------------------------------------------- identité
        self.c = Carte()
        ident = QHBoxLayout()
        ident.setSpacing(14)
        col = QVBoxLayout()
        col.setSpacing(3)
        self.titre = QLabel()
        self.titre.setObjectName("prefixe")
        col.addWidget(self.titre)
        self.infos = legende("")
        col.addWidget(self.infos)
        ident.addLayout(col, 1)
        self.b_mode = Badge()
        self.b_statut = Badge()
        ident.addWidget(self.b_mode, 0, Qt.AlignmentFlag.AlignTop)
        ident.addWidget(self.b_statut, 0, Qt.AlignmentFlag.AlignTop)
        self.c.disposition.addLayout(ident)
        self.disposition.addWidget(self.c)

        # ---------------------------------------------------------- chiffres clés (cliquables)
        chiffres = QHBoxLayout()
        chiffres.setSpacing(12)
        self.k_eq = Indicateur("équipements", icone="document", cliquable=True)
        self.k_var = Indicateur("variables", icone="liste", cliquable=True)
        self.k_er = Indicateur("erreurs bloquantes", icone="alerte", cliquable=True)
        self.k_al = Indicateur("alertes", icone="info", cliquable=True)
        for widget in (self.k_eq, self.k_var, self.k_er, self.k_al):
            chiffres.addWidget(widget, 1)
        self.k_eq.clique.connect(lambda: self.naviguer.emit("Ouvrage"))
        self.k_var.clique.connect(lambda: self.naviguer.emit(
            "Projet existant" if self.s.ouvrage.mode == "Existant" else "Variables"))
        self.k_er.clique.connect(lambda: self.naviguer.emit("Contrôles"))
        self.k_al.clique.connect(lambda: self.naviguer.emit("Contrôles"))
        self.disposition.addLayout(chiffres)

        # ---------------------------------------------------------- parcours guidé
        self.a = Carte("Parcours de travail", sous_titre="Les étapes se cochent lorsque l'outil n'a plus rien à signaler. "
                       "Ce n'est pas une validation industrielle.")
        self.progression = QProgressBar()
        self.progression.setTextVisible(False)
        self.a.ajouter_action(self.progression)
        self.progression.setFixedWidth(160)
        self.guide = legende("", "aide")
        self.a.ajouter(self.guide)
        self.liste_etapes = QVBoxLayout()
        self.liste_etapes.setSpacing(4)
        self.a.disposition.addLayout(self.liste_etapes)
        r = QHBoxLayout()
        self.action_principale = bouton("Commencer", self._principal, primaire=True)
        self.action_principale.hide()             # l'étape recommandée porte son propre bouton
        r.addWidget(self.action_principale)
        r.addStretch(1)
        self.a.disposition.addLayout(r)
        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setFrameShape(QFrame.Shape.NoFrame)
        conteneur = QWidget()
        cl = QVBoxLayout(conteneur)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(self.a)
        cl.addStretch(1)
        zone.setWidget(conteneur)
        self.disposition.addWidget(zone, 1)

    def _principal(self):
        av = parcours.calculer(self.s)
        e = av.prochaine()
        self.naviguer.emit(e.nom if e else "Contrôles")

    def charger(self):
        o = self.s.ouvrage
        av = parcours.calculer(self.s)
        existant = o.mode == "Existant"
        self.titre.setText(f"{o.prefixe() or 'Nouvel ouvrage'}   ·   {o.libelle or 'À renseigner'}")
        self.infos.setText(f"Automate {o.automate or '—'}   ·   Révision {o.revision or '—'}   ·   "
                           f"{len(o.sous_ensembles)} sous-ensemble(s)"
                           + (f"   ·   Projet Control Expert : {o.nom_projet}" if o.nom_projet else ""))
        self.b_mode.definir("Projet existant" if existant else "Projet neuf", "Existant" if existant else "Info")
        self.b_statut.definir(o.statut, "OK" if o.statut == "Validé" else "Neutre")
        self.k_eq.definir(len(o.equipements))
        self.k_var.definir(av.variables)
        self.k_er.definir(av.erreurs, "Erreur" if av.erreurs else "OK")
        self.k_al.definir(av.alertes, "Alerte" if av.alertes else "OK")
        self.progression.setRange(0, len(av.etapes))
        self.progression.setValue(av.faites)
        prochaine = av.prochaine()
        self.guide.setText(
            (f"Prochaine étape recommandée : {prochaine.titre}." if prochaine else
             "Toutes les étapes sont terminées. Vérifier les livrables dans les outils industriels.")
            + ("  Les noms et adresses du programme existant ne sont jamais réattribués." if existant else
               "  Les adresses confirmées restent stables lors d'un ajout d'équipement."))
        while self.liste_etapes.count():
            w = self.liste_etapes.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        for e in av.etapes:
            self.liste_etapes.addWidget(LigneEtape(e, lambda _=False, n=e.nom: self.naviguer.emit(n)))
        self.action_principale.setText(f"Continuer : {prochaine.titre}" if prochaine else "Voir les contrôles")


def rapport_detaille(parent, titre, contenu, validation=True):
    """Affiche tous les avertissements dans une fenêtre défilante avant application."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(titre)
    dlg.resize(800, 540)
    layout = QVBoxLayout(dlg)
    texte = QTextEdit()
    texte.setObjectName("rapport")
    texte.setReadOnly(True)
    texte.setPlainText(contenu)
    layout.addWidget(texte)
    if validation:
        boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        boutons.button(QDialogButtonBox.StandardButton.Ok).setText('Confirmer l’import')
    else:
        boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    boutons.accepted.connect(dlg.accept)
    boutons.rejected.connect(dlg.reject)
    layout.addWidget(boutons)
    return dlg.exec() == QDialog.DialogCode.Accepted


class DialogueColonnesImport(QDialog):
    """Prévisualisation et association explicite des colonnes avant tout import."""
    def __init__(self, parent, headers, rows, nom):
        super().__init__(parent)
        self.setWindowTitle('Préparer l’import — ' + nom)
        self.resize(950, 575)
        self.headers, self.rows, self.donnees = headers, rows, None
        racine = QVBoxLayout(self)
        racine.addWidget(QLabel(f'{len(rows)} lignes lues — choisir les colonnes, vérifier l’aperçu, puis confirmer.'))
        forms = QGridLayout()
        self.combos = {}
        auto = import_sources._colonnes(headers)
        for i, (champ, titre) in enumerate([
            ('nom','Nom / Symbole *'), ('adresse','Adresse automate *'),
            ('type','Type'), ('commentaire','Commentaire')]):
            cb = QComboBox()
            cb.addItem('(non renseigné)', -1)
            for j, h in enumerate(headers):
                cb.addItem(f'{j+1} — {h}', j)
            cb.setCurrentIndex(auto.get(champ, -1) + 1)
            forms.addWidget(QLabel(titre), i//2, (i%2)*2)
            forms.addWidget(cb, i//2, (i%2)*2+1)
            self.combos[champ] = cb
        racine.addLayout(forms)
        self.table = simple_table(headers)
        self.table.setRowCount(min(len(rows), 30))
        for i, row in enumerate(rows[:30]):
            for j in range(min(len(row),len(headers))):
                self.table.setItem(i,j,QTableWidgetItem(str(row[j])))
        racine.addWidget(self.table, 1)
        self.message = QLabel('Aperçu limité aux 30 premières lignes. Les valeurs sources seront conservées.')
        racine.addWidget(self.message)
        boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        boutons.button(QDialogButtonBox.StandardButton.Ok).setText('Importer les variables')
        boutons.accepted.connect(self.valider)
        boutons.rejected.connect(self.reject)
        racine.addWidget(boutons)

    def valider(self):
        mapping = {k:c.currentData() for k,c in self.combos.items() if c.currentData() >= 0}
        try:
            donnees, avertissements = import_sources.preparer_lignes(self.headers,self.rows,mapping)
        except ValueError as ex:
            avertir(self, 'Colonnes incorrectes', str(ex))
            return
        apercu = '\n'.join(f'{n} | {t} | {a}' for n,t,a,c in donnees[:25])
        rapport = import_sources.rapport_import(len(self.rows), donnees, avertissements)
        texte = (rapport + '\n\nAperçu (25 premières) :\n' + apercu
                 + '\n\nTous les avertissements :\n' + ('\n'.join(avertissements) or 'Aucun')
                 + '\n\nLes adresses importées ne seront pas réattribuées.')
        if rapport_detaille(self,'Contrôle des données avant import',texte):
            self.donnees = (donnees, avertissements)
            self.accept()


class VueParametres(Page):
    modifie = Signal()
    def __init__(self, session, parent=None):
        super().__init__("Plan mémoire", "Plages %MW réservées à chaque famille pour l'adressage des projets neufs.", parent)
        self.s = session
        self._mots = {}
        self.b_appliquer = bouton("Appliquer les paramètres", self.appliquer, primaire=True, icone="valider")
        self.entete.droite.addWidget(self.b_appliquer)
        self.c = Carte("Plages d'adressage de la table d'échange",
                       sous_titre="Les plages proposées sont à adapter au parc automate. Une plage ne peut pas "
                                  "exclure une adresse déjà attribuée.")
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(8)
        for j, t in enumerate(("FAMILLE", "DÉBUT %MW", "FIN %MW", "CAPACITÉ", "OCCUPATION ESTIMÉE", "")):
            self.grid.addWidget(caption(t) if t else QLabel(""), 0, j)
        self.debuts, self.fins, self.occupations, self.barres, self.capacites = {}, {}, {}, {}, {}
        for i, fam in enumerate(ORDRE_ZONES, start=1):
            nom = QLabel(fam)
            nom.setObjectName("titreLigne")
            self.grid.addWidget(nom, i, 0)
            a, b = QSpinBox(), QSpinBox()
            for w in (a, b):
                w.setRange(0, 65535)
                w.setMinimumWidth(110)
                w.valueChanged.connect(self._maj_occupation)
            self.debuts[fam], self.fins[fam] = a, b
            self.grid.addWidget(a, i, 1)
            self.grid.addWidget(b, i, 2)
            cap = legende("", retour=False)
            self.capacites[fam] = cap
            self.grid.addWidget(cap, i, 3)
            barre = QProgressBar()
            barre.setTextVisible(False)
            barre.setMinimumWidth(160)
            self.barres[fam] = barre
            self.grid.addWidget(barre, i, 4)
            lab = legende("", retour=False)
            self.occupations[fam] = lab
            self.grid.addWidget(lab, i, 5)
        self.grid.setColumnStretch(4, 1)
        self.c.disposition.addLayout(self.grid)
        self.c.ajouter(separateur())
        r = QHBoxLayout()
        r.setSpacing(10)
        r.addWidget(QLabel("Décalage Modbus"))
        self.modbus = QComboBox(); self.modbus.addItems(['0', '1'])
        self.modbus.setToolTip("Écart entre le numéro de mot %MW et le registre Modbus affiché.")
        r.addWidget(self.modbus)
        r.addSpacing(18)
        r.addWidget(QLabel("Produit XSY"))
        self.produit = QLineEdit(); self.produit.setMinimumWidth(220); r.addWidget(self.produit)
        r.addStretch(1)
        self.c.disposition.addLayout(r)
        self.note = legende("TR/RTR : mêmes indices logiques, plages différentes. Les REAL et DINT occupent "
                            "deux mots ; les BOOL occupent des bits (16 par mot). L'occupation est une estimation "
                            "indicative calculée sur les variables actuelles.", "aide")
        self.c.ajouter(self.note)
        self.disposition.addWidget(self.c)
        self.disposition.addStretch(1)
        self._mots = {}

    def charger(self):
        o = self.s.ouvrage
        for fam in ORDRE_ZONES:
            a, b = zone(o, fam)
            for w, val in ((self.debuts[fam], a), (self.fins[fam], b)):
                w.blockSignals(True); w.setValue(val); w.blockSignals(False)
        self.modbus.setCurrentText(str(o.decalage_modbus))
        self.produit.setText(o.produit_xsy)
        variables = self.s.variables() if o.mode == 'Neuf' else []
        counts = Counter(v.famille for v in variables)
        bools = Counter(v.famille for v in variables if (v.type_logique or '').upper() in ('BOOL', 'EBOOL'))
        mots = Counter()
        for v in variables:
            if (v.type_logique or '').upper() not in ('BOOL', 'EBOOL'):
                mots[v.famille] += max(1, TAILLE_MOTS.get(v.type_logique, 1))
        self._mots = {fam: mots[fam] + -(-bools[fam] // 16) for fam in ORDRE_ZONES}
        for fam in ORDRE_ZONES:
            self.occupations[fam].setText(f"{counts[fam]} variable(s)")
        self._maj_occupation()
        self.c.setEnabled(o.mode == 'Neuf')
        self.b_appliquer.setEnabled(o.mode == 'Neuf')

    def _maj_occupation(self, *_):
        for fam in ORDRE_ZONES:
            capacite = max(0, self.fins[fam].value() - self.debuts[fam].value() + 1)
            utilises = self._mots.get(fam, 0)
            self.capacites[fam].setText(f"{capacite} mots" if capacite else "plage invalide")
            barre = self.barres[fam]
            barre.setRange(0, max(1, capacite))
            barre.setValue(min(utilises, max(1, capacite)))
            taux = utilises / capacite if capacite else 1
            repolir(barre, gravite="Erreur" if taux > 1 or not capacite else "Alerte" if taux > .85 else "")
            barre.setToolTip(f"≈ {utilises} mot(s) utilisé(s) sur {capacite}")

    def appliquer(self):
        zones = {f:(self.debuts[f].value(), self.fins[f].value()) for f in ORDRE_ZONES}
        for f,(a,b) in zones.items():
            if b < a:
                avertir(self,'Plan mémoire',f'{f}: la fin doit être supérieure au début.'); return
        familles = list(ORDRE_ZONES)
        for i,f in enumerate(familles):
            for g in familles[i+1:]:
                a,b=zones[f]; c,d=zones[g]
                if max(a,c)<=min(b,d):
                    avertir(self,'Plan mémoire',f'Chevauchement des plages {f} / {g}.'); return
        # Une modification des plages ne doit pas déplacer ni invalider silencieusement une adresse confirmée.
        from genvar.modele import _mot
        for v in self.s.variables():
            if not v.adresse:
                continue
            position = _mot(v.adresse)
            if position is None:
                avertir(self,'Plan mémoire',f'Adresse non reconnue : {v.nom} = {v.adresse}'); return
            mot = position[0]; largeur = max(1, TAILLE_MOTS.get(v.type_logique, 1))
            a,b = zones[v.famille]
            if mot<a or mot+largeur-1>b:
                avertir(self,'Plan mémoire', f'La nouvelle plage {v.famille} exclurait {v.nom} ({v.adresse}).'); return
        o = self.s.ouvrage
        o.zones = {f:x[0] for f,x in zones.items()}
        o.zones_fin = {f:x[1] for f,x in zones.items()}
        o.decalage_modbus = int(self.modbus.currentText())
        o.produit_xsy = self.produit.text().strip()
        self.s._change(); self.modifie.emit()
        notifier(self, 'Plan mémoire enregistré. Aucune adresse existante n’a été réattribuée.')


class VueControles(Page):
    naviguer = Signal(object)          # anomalie à montrer dans l'écran de travail
    commande = Signal(str)             # action de correction d'un groupe (attribuer, fiche, es…)

    def __init__(self, session, parent=None):
        super().__init__("Contrôles", "Erreurs bloquantes et alertes calculées par le moteur. "
                         "Double-clic sur une ligne pour aller à l'élément concerné.", parent)
        self.s = session
        self.anomalies = []
        chiffres = QHBoxLayout()
        chiffres.setSpacing(12)
        self.k_er = Indicateur("erreurs bloquantes", icone="alerte", cliquable=True)
        self.k_al = Indicateur("alertes à examiner", icone="info", cliquable=True)
        self.k_er.clique.connect(lambda: (self.niveau.definir("Erreur"), self._filtrer()))
        self.k_al.clique.connect(lambda: (self.niveau.definir("Alerte"), self._filtrer()))
        chiffres.addWidget(self.k_er, 1)
        chiffres.addWidget(self.k_al, 1)
        chiffres.addStretch(2)
        self.disposition.addLayout(chiffres)

        # constats regroupés par nature, chacun avec sa correction
        self.c_groupes = Carte("Par nature de constat", sous_titre="Traiter les groupes dans l'ordre ; chaque "
                               "bouton mène à la correction.")
        self.groupes = QVBoxLayout()
        self.groupes.setSpacing(4)
        self.c_groupes.disposition.addLayout(self.groupes)
        self.disposition.addWidget(self.c_groupes)

        self.c = Carte("Détail des constats")
        filtres = QHBoxLayout()
        filtres.setSpacing(8)
        self.recherche = champ_recherche("Rechercher un repère, une variable, un message…")
        self.niveau = Segment([("Tous", "Tous"), ("Erreur", "Erreurs"), ("Alerte", "Alertes")])
        self.niveau.definir("Tous")
        filtres.addWidget(self.recherche, 1)
        filtres.addWidget(self.niveau)
        self.c.disposition.addLayout(filtres)
        self.t = Tableau([
            Colonne("niv", "Gravité", lambda x: x.niveau, 110, icone=lambda x: style.icone_gravite(x.niveau),
                    tri=lambda x: {"Erreur": 0, "Alerte": 1}.get(x.niveau, 2)),
            Colonne("rep", "Équipement / variable", lambda x: x.repere, 200),
            Colonne("msg", "Constat", lambda x: x.message, 600, etirable=True),
        ], "controles_v09")
        self.t.texte_vide = "Aucune anomalie détectée.\nLes contrôles sont recalculés à chaque modification."
        self.t.objet_active.connect(lambda a: a is not None and self.naviguer.emit(a))
        self.c.ajouter(self.t, 1)
        self.compte = legende("", retour=False)
        self.c.ajouter(self.compte)
        # compatibilité avec les anciens appels : self.table désigne le tableau des résultats
        self.table = self.t
        self.disposition.addWidget(self.c, 1)
        self.recherche.textChanged.connect(self._filtrer)
        self.niveau.change.connect(self._filtrer)

    def charger(self):
        an = self.s.anomalies_existant() if self.s.ouvrage.mode == 'Existant' else self.s.anomalies()
        self.anomalies = sorted(an, key=lambda x: (x.niveau != 'Erreur', x.repere))
        self.t.definir(self.anomalies)
        ne = sum(a.niveau == 'Erreur' for a in an)
        na = sum(a.niveau == 'Alerte' for a in an)
        self.k_er.definir(ne, "Erreur" if ne else "OK")
        self.k_al.definir(na, "Alerte" if na else "OK")
        from .guide import grouper
        while self.groupes.count():
            w = self.groupes.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        groupes = grouper(an)
        for g in groupes:
            ligne = QFrame()
            ligne.setObjectName("ligneEtape")
            r = QHBoxLayout(ligne)
            r.setContentsMargins(10, 8, 10, 8)
            r.setSpacing(12)
            r.addWidget(Badge(str(len(g.anomalies)), g.niveau))
            textes = QVBoxLayout()
            textes.setSpacing(1)
            t = QLabel(g.titre)
            t.setObjectName("titreLigne")
            textes.addWidget(t)
            textes.addWidget(legende(g.explication))
            r.addLayout(textes, 1)
            if g.commande != "controles":
                r.addWidget(bouton(g.bouton, lambda _=False, c=g.commande: self.commande.emit(c),
                                   primaire=(g is groupes[0])))
            self.groupes.addWidget(ligne)
        self.c_groupes.setVisible(bool(groupes))
        self._filtrer()

    def _filtrer(self, *_):
        n = self.niveau.valeur()
        self.t.filtre.definir_condition(None if n in (None, "Tous") else (lambda x, n=n: x.niveau == n))
        self.t.filtre.definir_texte(self.recherche.text())
        total, vus = len(self.anomalies), self.t.nombre_visible()
        self.compte.setText(f"{total} constat(s)" if vus == total else f"{vus} affiché(s) sur {total}")


class CarteLivrable(QFrame):
    def __init__(self, nom_icone, titre, description, b, parent=None):
        super().__init__(parent)
        self.setObjectName("carteLivrable")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(14)
        tuile = QLabel()
        tuile.setObjectName("tuileIcone")
        tuile.setFixedSize(44, 44)
        tuile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tuile.setPixmap(style.icone(nom_icone, style.ACCENT, 22).pixmap(22, 22))
        lay.addWidget(tuile, 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(3)
        t = QLabel(titre)
        t.setObjectName("titreCarte")
        col.addWidget(t)
        self.description = legende(description)
        col.addWidget(self.description)
        col.addSpacing(6)
        r = QHBoxLayout()
        r.addWidget(b)
        r.addStretch(1)
        col.addLayout(r)
        lay.addLayout(col, 1)


class VueExports(Page):
    naviguer = Signal(str)

    def __init__(self, session, parent=None):
        super().__init__("Exports", "Produire les livrables. Un export contrôlé exige zéro erreur bloquante.", parent)
        self.s = session

        # ---------------------------------------------------------- état de préparation
        self.c = Carte("Avant d'exporter")
        self.resume = legende("")
        self.c.ajouter(self.resume)
        self.verifs = QVBoxLayout()
        self.verifs.setSpacing(6)
        self.c.disposition.addLayout(self.verifs)
        self.disposition.addWidget(self.c)

        # ---------------------------------------------------------- livrables
        livrables = QHBoxLayout()
        livrables.setSpacing(12)
        self.xsy = bouton('Exporter XSY — projet neuf', lambda: self._exporter('xsy'), primaire=True, icone="export")
        self.xlsx = bouton('Exporter tableau Excel', lambda: self._exporter('xlsx'), icone="export")
        self.l_xsy = CarteLivrable("liste", "Fichier XSY — Control Expert",
                                   "Variables de la table d'échange à importer dans Control Expert "
                                   "(Données › Variables › Importer) ou dans Softlink.", self.xsy)
        self.l_xlsx = CarteLivrable("document", "Tableau Excel",
                                    "Table d'échange ou table de correspondance, pour relecture, diffusion "
                                    "et intégration TOPKAPI.", self.xlsx)
        livrables.addWidget(self.l_xsy, 1)
        livrables.addWidget(self.l_xlsx, 1)
        self.disposition.addLayout(livrables)

        # ---------------------------------------------------------- brouillon explicite
        encart = QFrame()
        encart.setObjectName("encartBrouillon")
        el = QVBoxLayout(encart)
        el.setContentsMargins(14, 10, 14, 10)
        el.setSpacing(4)
        self.brouillon = QCheckBox('Exporter en brouillon malgré des erreurs de contrôle')
        el.addWidget(self.brouillon)
        el.addWidget(legende("Le fichier sera suffixé _BROUILLON. Un brouillon ne doit jamais être importé comme "
                             "une configuration validée. Les imports TOPKAPI / Control Expert sont à vérifier "
                             "en environnement de test.", "aide"))
        self.disposition.addWidget(encart)
        self.disposition.addStretch(1)

    def _ligne_verif(self, ok, texte, cible=None, gravite="Erreur"):
        r = QHBoxLayout()
        r.setSpacing(8)
        ico = QLabel()
        niveau = "OK" if ok else gravite
        ico.setPixmap(style.icone("termine" if ok else "alerte", style.GRAVITE[niveau][0], 16).pixmap(16, 16))
        r.addWidget(ico)
        l = QLabel(texte)
        if not ok:
            l.setProperty("gravite", niveau)
        r.addWidget(l, 1)
        if cible and not ok:
            r.addWidget(bouton("Corriger", lambda _=False, c=cible: self.naviguer.emit(c), nom="lien"))
        w = QWidget()
        w.setLayout(r)
        r.setContentsMargins(0, 0, 0, 0)
        self.verifs.addWidget(w)

    def charger(self):
        b = self.s.bilan()
        neuf = self.s.ouvrage.mode == 'Neuf'
        self.xsy.setEnabled(neuf)
        self.l_xsy.setEnabled(neuf)
        self.l_xsy.setToolTip("" if neuf else "En projet existant, TOPKAPI reprend directement le XSY de l'automate.")
        self.resume.setText(f"{b['variables']} variables · {b['points']} E/S · "
                            f"{b['erreurs']} erreur(s) et {b['alertes']} alerte(s).")
        while self.verifs.count():
            w = self.verifs.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        self._ligne_verif(b['variables'] > 0, "L'ouvrage contient des variables" if b['variables'] else
                          "Aucune variable : rien à exporter", "Ouvrage" if neuf else "Projet existant")
        self._ligne_verif(not b['erreurs'], "Aucune erreur bloquante" if not b['erreurs'] else
                          f"{b['erreurs']} erreur(s) bloquante(s) : export contrôlé impossible", "Contrôles")
        if neuf:
            sans = sum(1 for v in self.s.variables() if not v.adresse)
            self._ligne_verif(not sans, "Toutes les variables ont une adresse" if not sans else
                              f"{sans} variable(s) sans adresse", "Variables", "Alerte")
            recap = self.s.recap_export()
            self._ligne_verif(not recap.sans_adresse, "Toutes les E/S sont adressées" if not recap.sans_adresse else
                              f"{len(recap.sans_adresse)} E/S sans adresse seront exclues du XSY", "E/S automate", "Alerte")
        self._ligne_verif(not b['alertes'], "Aucune alerte" if not b['alertes'] else
                          f"{b['alertes']} alerte(s) à examiner (non bloquant)", "Contrôles", "Alerte")
        self.brouillon.setChecked(False)

    def _exporter(self, extension):
        b=self.s.bilan()
        brouillon=self.brouillon.isChecked()
        if b['erreurs'] and not brouillon:
            avertir(self,'Export bloqué',f"{b['erreurs']} erreur(s) bloquante(s) : corrigez-les, "
                   'ou choisissez explicitement un export brouillon.'); return
        suffixe='_BROUILLON' if brouillon else ''
        nom=f"{self.s.nom_fichier_propose() or 'ouvrage'}{suffixe}.{extension}"
        p,_=QFileDialog.getSaveFileName(self,'Enregistrer le livrable',os.path.join(chemins.dossier_exports(),nom),
                                        'Fichier XSY (*.xsy)' if extension=='xsy' else 'Excel (*.xlsx)')
        if not p:
            return
        if not p.lower().endswith('.'+extension):p+='.'+extension
        if extension=='xsy':
            recap=self.s.recap_export()
            exclusion='\n'.join(recap.sans_adresse[:10])
            texte=f"{recap.variables} variables · {recap.points} E/S · {recap.avec_adresse} E/S adressées\n"
            if recap.sans_adresse:
                texte+=f"{len(recap.sans_adresse)} E/S sans adresse seront exclues :\n{exclusion}\n"
            texte+='Confirmer la génération du livrable ?'
            if not confirmer(self,'Contrôle avant XSY',texte,defaut_non=True):return
        elif not confirmer(self,'Contrôle avant Excel',f"Exporter {b['variables']} variables ?",defaut_non=True):
            return
        try:
            if extension=='xsy':self.s.exporter_xsy(p)
            else:self.s.exporter_excel(p)
        except Exception as exc:
            avertir(self,'Échec de l’export',str(exc));return
        informer(self,'Export créé',f"Fichier créé :\n{p}\nStatut : {'BROUILLON' if brouillon else 'Contrôlé (logiciels industriels à vérifier)'}")
