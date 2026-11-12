"""Projet existant : import des sources, équipements, table de télétransmission.

Écran central du parcours « existant ». Une ligne = une information attendue. Le panneau
de droite montre, pour la ligne choisie, sa source, ses preuves, les candidats proposés et
les deux validations (fonction / accès TOPKAPI). Aucune donnée source n'est modifiée.
"""
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
                               QFileDialog, QDialog, QDialogButtonBox, QCheckBox, QTabWidget, QSplitter,
                               QListWidget, QListWidgetItem, QInputDialog, QScrollArea, QFormLayout,
                               QAbstractItemView)

from genvar import existant, import_sources, liste_es
from genvar.teletransmission import STATUTS, COULEUR, PROTOCOLES, verifier_cloture
from genvar.session import RegleMetier
from . import style
from .composants import (Page, Carte, Badge, Segment, CarteEtape, bouton, avertir, informer, confirmer,
                         notifier, legende, caption, separateur, champ_recherche)
from .tableaux import Tableau, Colonne
from .vues_complementaires import DialogueColonnesImport, rapport_detaille

TOUS = "__tous__"


class DialogueDetectes(QDialog):
    """Équipements trouvés dans les noms : l'automaticien coche ceux qui existent réellement."""

    def __init__(self, parent, detectes):
        super().__init__(parent)
        self.setWindowTitle("Équipements détectés dans le programme")
        self.resize(720, 460)
        lay = QVBoxLayout(self)
        lay.addWidget(legende("Ces équipements apparaissent dans des noms normalisés du programme mais ne sont "
                              "pas encore déclarés. Cocher uniquement ceux qui existent réellement sur l'ouvrage."))
        self.liste = QListWidget()
        for d in detectes:
            item = QListWidgetItem(f"{d.code}  —  {d.designation}   ({len(d.variables)} variable(s) : "
                                   f"{', '.join(d.variables[:3])}{'…' if len(d.variables) > 3 else ''})")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, d)
            self.liste.addItem(item)
        lay.addWidget(self.liste, 1)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        b.button(QDialogButtonBox.StandardButton.Ok).setText("Ajouter les équipements cochés")
        b.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primaire")
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        lay.addWidget(b)

    def choisis(self):
        return [self.liste.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.liste.count())
                if self.liste.item(i).checkState() == Qt.CheckState.Checked]


class DialogueChoixVariable(QDialog):
    """Choix manuel d'une variable du programme, avec recherche."""

    def __init__(self, parent, variables, utilisees):
        super().__init__(parent)
        self.setWindowTitle("Choisir la variable source")
        self.resize(820, 520)
        lay = QVBoxLayout(self)
        self.recherche = champ_recherche("Rechercher un nom, une adresse, un commentaire…")
        lay.addWidget(self.recherche)
        self.t = Tableau([
            Colonne("nom", "Variable", lambda v: v.nom, 230),
            Colonne("type", "Type", lambda v: v.type_logique, 70),
            Colonne("adr", "Adresse", lambda v: v.adresse, 110),
            Colonne("util", "Déjà utilisée", lambda v: utilisees.get(v.nom, ""), 150),
            Colonne("com", "Commentaire", lambda v: v.commentaire, 300, etirable=True),
        ], "choix_variable_source")
        self.t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.t.definir(variables)
        self.t.objet_active.connect(lambda _: self.accept())
        self.recherche.textChanged.connect(self.t.filtre.definir_texte)
        lay.addWidget(self.t, 1)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        b.button(QDialogButtonBox.StandardButton.Ok).setText("Associer")
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        lay.addWidget(b)

    def choix(self):
        return self.t.objet_courant()


class VueExistant(Page):
    modifie = Signal()

    def __init__(self, session, parent=None):
        super().__init__("Analyse & télétransmission",
                         "Une ligne par information attendue : associer la variable du programme, confirmer sa "
                         "fonction, vérifier son accès TOPKAPI. Le programme existant n'est jamais modifié.", parent)
        self.s = session
        self.lignes = []
        self._candidats = {}
        self._courante = None

        # ---------------------------------------------------------- trois étapes
        etapes = QHBoxLayout()
        etapes.setSpacing(12)
        self.e_import = CarteEtape(1, "Importer les sources")
        self.e_import.ajouter_bouton(bouton("Variables XSY / SCY / Excel…", self.importer, primaire=True, icone="import",
                                            infobulle="Control Expert (.xsy), PL7 (.scy), Excel ou CSV. Aperçu avant import."))
        self.e_import.ajouter_bouton(bouton("Importer liste E/S…", self.importer_es, icone="es",
                                            infobulle="Liste des E/S du schéma électrique : indices de rapprochement."))
        self.e_import.ajouter_bouton(bouton("Programme PDF (PL7)…", self.analyser_dossier_pdf, icone="pdf",
                                            infobulle="Lecture documentaire en lecture seule : rapport d'indices séparé."))
        self.e_table = CarteEtape(2, "Équipements et table")
        self.b_detectes = bouton("Équipements détectés…", self.equipements_detectes, icone="analyse",
                                 infobulle="Équipements trouvés dans les noms du programme : à accepter un par un.")
        self.e_table.ajouter_bouton(self.b_detectes)
        self.e_table.ajouter_bouton(bouton("Construire / mettre à jour la table", self.construire, icone="liste",
                                           infobulle="Une ligne par information attendue des équipements déclarés. "
                                                     "Les décisions déjà prises sont conservées."))
        self.e_table.ajouter_bouton(bouton("Proposer les associations", self.proposer, icone="assistant",
                                           infobulle="Moteur de rapprochement unique (programme + catalogue + liste E/S). "
                                                     "Remplit les lignes sans source, sans rien valider."))
        self.e_valid = CarteEtape(3, "Valider ligne par ligne")
        self.b_confirmer = bouton("Confirmer la fonction (sélection)", self.confirmer_selection, primaire=True,
                                  icone="valider", infobulle="Confirme la fonction des lignes sélectionnées qui ont une source.")
        self.e_valid.ajouter_bouton(self.b_confirmer)
        self.e_valid.ajouter_bouton(legende("L'accès TOPKAPI se vérifie dans le panneau de droite, ligne par ligne.", "aide"))
        for c in (self.e_import, self.e_table, self.e_valid):
            etapes.addWidget(c, 1)
        self.disposition.addLayout(etapes)

        # ---------------------------------------------------------- onglets
        self.onglets = QTabWidget()
        self.onglets.setDocumentMode(True)
        self.onglets.addTab(self._construire_table(), "Table de télétransmission")
        self.onglets.addTab(self._construire_inventaire(), "Inventaire du programme")
        self.disposition.addWidget(self.onglets, 1)

    # ================================================================== construction
    def _construire_table(self):
        page = QSplitter(Qt.Orientation.Horizontal)
        page.setChildrenCollapsible(False)
        gauche = Carte()
        filtres = QHBoxLayout()
        filtres.setSpacing(8)
        self.recherche = champ_recherche("Rechercher un repère, une information, une variable…")
        self.f = Segment([("Tous", "Toutes")] + [(s, s) for s in STATUTS])
        self.f.definir("Tous")
        self.f_uf = QComboBox()
        self.f_uf.setToolTip("Filtrer par unité fonctionnelle")
        filtres.addWidget(self.recherche, 1)
        filtres.addWidget(self.f_uf)
        gauche.disposition.addLayout(filtres)
        gauche.disposition.addWidget(self.f)
        self.t = Tableau([
            Colonne("statut", "Statut", lambda x: x.statut, 120, icone=lambda x: style.icone_gravite(
                COULEUR.get(x.statut, "Info") if x.statut != "Non accessible" else "Info"),
                tri=lambda x: STATUTS.index(x.statut), infobulle=lambda x: x.motif),
            Colonne("uf", "UF", lambda x: x.uf.split(" ")[0] if x.uf else "", 55),
            Colonne("rep", "Repère", lambda x: x.repere, 130),
            Colonne("info", "Information", lambda x: f"{x.famille} {x.information}", 190),
            Colonne("nom", "Nom standardisé", lambda x: x.nom_standard, 200),
            Colonne("src", "Variable source", lambda x: x.variable_source or ("—" if x.statut != "Non accessible"
                                                                           else "non accessible"), 190),
            Colonne("adr", "Adresse", lambda x: x.adresse_acquisition or x.adresse_source, 105),
            Colonne("fct", "Fonction", lambda x: "✓" if x.ligne.fonction_validee else "", 70,
                    alignement=Qt.AlignmentFlag.AlignCenter),
            Colonne("acc", "Accès", lambda x: "✓" if x.ligne.acces_verifie else "", 60,
                    alignement=Qt.AlignmentFlag.AlignCenter),
            Colonne("sens", "Sens", lambda x: x.sens, 80, visible=False),
            Colonne("proto", "Protocole", lambda x: x.protocole, 100, visible=False),
            Colonne("motif", "Reste à faire", lambda x: x.motif, 300, etirable=True),
        ], "teletransmission_v09")
        self.t.texte_vide = ("Table vide.\n1) Importer les variables du programme  2) Déclarer ou accepter les "
                             "équipements  3) « Construire / mettre à jour la table ».")
        self.t.selection_changee.connect(self._ligne_choisie)
        gauche.ajouter(self.t, 1)
        self.stats = legende("", retour=False)
        gauche.ajouter(self.stats)
        page.addWidget(gauche)

        # ---------------------------------------------------------- panneau de détail
        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setFrameShape(QFrame.Shape.NoFrame)
        zone.setMinimumWidth(380)
        self.detail = Carte()
        d = self.detail.disposition
        self.d_titre = QLabel("Sélectionner une ligne")
        self.d_titre.setObjectName("titreCarte")
        self.d_titre.setWordWrap(True)
        d.addWidget(self.d_titre)
        self.d_sous = legende("")
        d.addWidget(self.d_sous)
        ligne_statut = QHBoxLayout()
        self.d_statut = Badge()
        ligne_statut.addWidget(self.d_statut)
        ligne_statut.addStretch(1)
        d.addLayout(ligne_statut)
        self.d_motif = legende("")
        d.addWidget(self.d_motif)
        d.addWidget(separateur())

        d.addWidget(caption("Variable source"))
        self.d_source = legende("")
        self.d_source.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        d.addWidget(self.d_source)
        d.addWidget(caption("Preuves"))
        self.d_preuves = legende("", "aide")
        d.addWidget(self.d_preuves)
        r = QHBoxLayout()
        self.b_choisir = bouton("Choisir une variable…", self.choisir_variable, icone="recherche")
        self.b_dissocier = bouton("Dissocier", self.dissocier, icone="supprimer", nom="danger")
        r.addWidget(self.b_choisir)
        r.addWidget(self.b_dissocier)
        r.addStretch(1)
        d.addLayout(r)
        d.addWidget(caption("Candidats proposés"))
        self.d_candidats = QListWidget()
        self.d_candidats.setMinimumHeight(110)
        self.d_candidats.setWordWrap(True)
        self.d_candidats.itemDoubleClicked.connect(lambda *_: self.associer_candidat())
        d.addWidget(self.d_candidats)
        self.b_associer = bouton("Associer le candidat sélectionné", self.associer_candidat, icone="lien")
        d.addWidget(self.b_associer)
        d.addWidget(separateur())

        d.addWidget(caption("Validation 1 · fonction"))
        self.c_fonction = QCheckBox("La variable porte bien cette information (vérifié dans le programme)")
        self.c_fonction.clicked.connect(self._fonction_cochee)
        d.addWidget(self.c_fonction)
        d.addWidget(caption("Validation 2 · accès TOPKAPI"))
        form = QFormLayout()
        self.d_adresse = QLineEdit()
        self.d_adresse.setPlaceholderText("vide = adresse source")
        self.d_protocole = QComboBox()
        self.d_protocole.setEditable(True)
        self.d_protocole.addItems(list(PROTOCOLES))
        form.addRow("Adresse / tag", self.d_adresse)
        form.addRow("Protocole", self.d_protocole)
        d.addLayout(form)
        self.c_acces = QCheckBox("Adresse et protocole contrôlés (documentation ou essai)")
        d.addWidget(self.c_acces)
        self.b_acces = bouton("Enregistrer l'accès", self.enregistrer_acces, icone="enregistrer")
        d.addWidget(self.b_acces)
        d.addWidget(separateur())
        d.addWidget(caption("Décision"))
        r2 = QHBoxLayout()
        self.b_non_accessible = bouton("Non accessible…", self.non_accessible, icone="alerte",
                                       infobulle="L'information existe sur l'équipement mais n'est pas disponible.")
        self.b_non_applicable = bouton("Non applicable", self.non_applicable, icone="supprimer",
                                       infobulle="Le signal n'existe pas sur cet équipement : la ligne est retirée.")
        r2.addWidget(self.b_non_accessible)
        r2.addWidget(self.b_non_applicable)
        r2.addStretch(1)
        d.addLayout(r2)
        d.addStretch(1)
        zone.setWidget(self.detail)
        page.addWidget(zone)
        page.setStretchFactor(0, 3)
        page.setStretchFactor(1, 1)
        page.setSizes([900, 420])

        self.recherche.textChanged.connect(self.filtrer)
        self.f.change.connect(self.filtrer)
        self.f_uf.currentIndexChanged.connect(self.filtrer)
        self._ligne_choisie()
        return page

    def _construire_inventaire(self):
        c = Carte(sous_titre="Toutes les variables lues dans le programme, telles quelles. Celles qui ne sont "
                             "associées à aucune ligne restent consultables ici.")
        r = QHBoxLayout()
        self.recherche_inv = champ_recherche("Rechercher dans l'inventaire…")
        self.f_inv = Segment([("Toutes", "Toutes"), ("Non", "Non utilisées"), ("Oui", "Utilisées")])
        self.f_inv.definir("Toutes")
        r.addWidget(self.recherche_inv, 1)
        r.addWidget(self.f_inv)
        c.disposition.addLayout(r)
        self.t_inv = Tableau([
            Colonne("nom", "Variable", lambda v: v.nom, 260),
            Colonne("type", "Type", lambda v: v.type_logique, 70),
            Colonne("adr", "Adresse", lambda v: v.adresse or "Non établie", 115),
            Colonne("orig", "Origine", lambda v: v.nature_source, 95),
            Colonne("util", "Utilisée pour", lambda v: self._utilisee.get(v.nom, ""), 220),
            Colonne("com", "Commentaire", lambda v: v.commentaire, 320, etirable=True),
        ], "inventaire_programme_v09")
        self.t_inv.texte_vide = "Aucune variable importée."
        c.ajouter(self.t_inv, 1)
        self._utilisee = {}
        self.recherche_inv.textChanged.connect(self.t_inv.filtre.definir_texte)
        self.f_inv.change.connect(self._filtrer_inventaire)
        # compatibilité : l'ancien tableau principal s'appelait `t` ; l'inventaire garde ce rôle de consultation
        return c

    # ================================================================== chargement
    def charger(self):
        o = self.s.ouvrage
        actif = o.mode == "Existant"
        for w in (self.e_import, self.e_table, self.e_valid, self.onglets):
            w.setEnabled(actif)
        self.lignes = self.s.table() if actif and o.table_tt else []
        self._candidats = self.s.candidats() if actif and o.table_tt else {}
        courant = self.f_uf.currentData()
        self.f_uf.blockSignals(True)
        self.f_uf.clear()
        self.f_uf.addItem("Toutes les UF", TOUS)
        for u in o.unites:
            self.f_uf.addItem(f"{u.code} — {u.libelle}" if u.libelle else u.code, u.code)
        self.f_uf.setCurrentIndex(max(0, self.f_uf.findData(courant)))
        self.f_uf.blockSignals(False)
        self.t.definir(self.lignes)
        compte = {s: sum(x.statut == s for x in self.lignes) for s in STATUTS}
        self.f.libeller("Tous", f"Toutes  {len(self.lignes)}")
        for s in STATUTS:
            self.f.libeller(s, f"{s}  {compte[s]}")
        self.onglets.setTabText(0, f"Table de télétransmission ({len(self.lignes)})")
        eqs = {e.ident: o.repere(e) for e in o.equipements}
        self._utilisee = {l.variable_source: f"{eqs.get(l.ident_eq, '?')} {l.cle}"
                          for l in o.table_tt if l.variable_source}
        self.t_inv.definir(o.existantes if actif else [])
        self.onglets.setTabText(1, f"Inventaire du programme ({len(o.existantes) if actif else 0})")
        self._filtrer_inventaire()
        self.filtrer()
        self._maj_etapes(compte)
        self._ligne_choisie()

    def _maj_etapes(self, compte):
        o = self.s.ouvrage
        n_var, n_es = len(o.existantes), len(o.entrees_physiques_importees)
        detectes = self.s.equipements_detectes() if o.existantes else []
        self.b_detectes.setText(f"Équipements détectés ({len(detectes)})…" if detectes else "Équipements détectés…")
        if not n_var:
            self.e_import.definir("actif", "Aucune source importée.")
        else:
            self.e_import.definir("fait", f"{n_var} variables · {n_es} E/S documentaires.")
        if not o.equipements:
            self.e_table.definir("actif" if n_var else "a_faire",
                                 "Déclarer les équipements (fiche ouvrage) ou accepter ceux détectés.")
        elif not o.table_tt:
            self.e_table.definir("actif", f"{len(o.equipements)} équipement(s) : construire la table.")
        else:
            avec_source = sum(1 for l in o.table_tt if l.variable_source)
            self.e_table.definir("fait", f"{len(o.table_tt)} lignes · {avec_source} avec une source.")
        if not self.lignes:
            self.e_valid.definir("a_faire", "Disponible quand la table existe.")
        elif compte["Incohérence"]:
            self.e_valid.definir("erreur", f"{compte['Incohérence']} incohérence(s) · {compte['Validée']} validée(s).")
        elif compte["À compléter"] or compte["Sans source"]:
            self.e_valid.definir("actif", f"{compte['Validée']} validée(s) · "
                                 f"{compte['À compléter'] + compte['Sans source']} à traiter.")
        else:
            cloture = verifier_cloture(o, self.s.catalogue)
            if cloture:
                self.e_valid.definir("actif", cloture[0])
            else:
                self.e_valid.definir("fait", f"{compte['Validée']} validée(s) · {compte['Non accessible']} non accessible(s).")
        self.stats.setText(f"{compte['Validée']} validées · {compte['À compléter']} à compléter · "
                           f"{compte['Sans source']} sans source · {compte['Incohérence']} incohérences · "
                           f"{compte['Non accessible']} non accessibles")

    def filtrer(self, *_):
        statut = self.f.valeur() or "Tous"
        uf = self.f_uf.currentData()
        self.t.filtre.definir_condition(lambda x: (statut == "Tous" or x.statut == statut)
                                        and (uf in (None, TOUS) or x.uf.split(" ")[0] == uf))
        self.t.filtre.definir_texte(self.recherche.text())

    def _filtrer_inventaire(self, *_):
        choix = self.f_inv.valeur() or "Toutes"
        self.t_inv.filtre.definir_condition(None if choix == "Toutes" else
                                            (lambda v: (v.nom in self._utilisee) == (choix == "Oui")))

    # ================================================================== détail d'une ligne
    def _ligne_choisie(self, *_):
        x = self.t.objet_courant()
        self._courante = x
        actif = x is not None
        for w in (self.b_choisir, self.b_dissocier, self.b_associer, self.c_fonction, self.d_adresse,
                  self.d_protocole, self.c_acces, self.b_acces, self.b_non_accessible, self.b_non_applicable):
            w.setEnabled(actif)
        self.d_candidats.clear()
        if not actif:
            self.d_titre.setText("Sélectionner une ligne de la table")
            self.d_sous.setText("Le détail, les preuves et les deux validations s'affichent ici.")
            self.d_statut.definir("—", "Neutre")
            for w in (self.d_motif, self.d_source, self.d_preuves):
                w.setText("")
            return
        l = x.ligne
        self.d_titre.setText(f"{x.nom_standard}")
        self.d_sous.setText(f"{x.repere} · {x.designation} · {x.famille} {x.information} · {x.sens}"
                            + (f" · {x.uf}" if x.uf else ""))
        self.d_statut.definir(x.statut, COULEUR.get(x.statut, "Neutre"))
        self.d_motif.setText(x.motif)
        if x.variable_source:
            self.d_source.setText(f"{x.variable_source}  ·  {x.type_source or 'type ?'}  ·  "
                                  f"{x.adresse_source or 'adresse non établie'}\n« {x.commentaire_source} »"
                                  + (f"\n{l.origine_association}" if l.origine_association else ""))
        else:
            self.d_source.setText("Aucune variable associée.")
        self.d_preuves.setText("\n".join(f"• {p}" for p in l.preuves) or "—")
        cands = self._candidats.get((l.ident_eq, l.cle), [])
        for p in cands:
            item = QListWidgetItem(f"{p.variable_nom}   {p.score}/100{'   (ambigu)' if p.ambiguite else ''}\n"
                                   + "; ".join(p.indices))
            item.setData(Qt.ItemDataRole.UserRole, p)
            if p.variable_nom == l.variable_source:
                item.setIcon(style.icone("termine", style.GRAVITE["OK"][0], 14))
            self.d_candidats.addItem(item)
        if not cands:
            self.d_candidats.addItem("Aucun candidat : choisir une variable à la main ou déclarer non accessible.")
        self.c_fonction.setChecked(l.fonction_validee)
        self.c_fonction.setEnabled(bool(l.variable_source))
        self.d_adresse.setText(l.adresse_acquisition)
        self.d_adresse.setPlaceholderText(f"vide = {x.adresse_source}" if x.adresse_source else "adresse ou tag à établir")
        self.d_protocole.setCurrentText(l.protocole)
        self.d_protocole.lineEdit().setPlaceholderText(self.s.ouvrage.communication or "protocole")
        self.c_acces.setChecked(l.acces_verifie)
        self.b_dissocier.setEnabled(bool(l.variable_source))
        self.b_non_accessible.setText("Rouvrir la ligne" if l.non_accessible else "Non accessible…")

    def _apres(self, garder=None):
        self.charger()
        self.modifie.emit()
        if garder is not None:
            self.t.selectionner(lambda x: (x.ligne.ident_eq, x.ligne.cle) == garder)

    def _cle(self):
        x = self._courante
        return (x.ligne.ident_eq, x.ligne.cle) if x is not None else None

    def _faire(self, action, *args):
        cle = self._cle()
        if cle is None:
            return False
        try:
            action(*cle, *args)
        except RegleMetier as ex:
            avertir(self, "Table de télétransmission", str(ex))
            return False
        self._apres(cle)
        return True

    def associer_candidat(self):
        item = self.d_candidats.currentItem()
        p = item.data(Qt.ItemDataRole.UserRole) if item else None
        if p is None:
            informer(self, "Candidat", "Sélectionner un candidat dans la liste.")
            return
        preuves = list(p.indices) + [f"Score de classement {p.score}/100 (pas une probabilité)"]
        self._faire(lambda i, c: self.s.associer(i, c, p.variable_nom, preuves, "Proposition acceptée"))

    def choisir_variable(self):
        if self._courante is None:
            return
        d = DialogueChoixVariable(self, self.s.ouvrage.existantes, self._utilisee)
        if d.exec() and d.choix() is not None:
            nom = d.choix().nom
            self._faire(lambda i, c: self.s.associer(i, c, nom))

    def dissocier(self):
        if confirmer(self, "Dissocier", "Retirer la variable source de cette ligne ?\n"
                     "Les deux validations seront remises à zéro.", defaut_non=True):
            self._faire(self.s.dissocier)

    def _fonction_cochee(self, coche):
        self._faire(lambda i, c: self.s.valider_fonction(i, c, coche))

    def enregistrer_acces(self):
        if self._faire(lambda i, c: self.s.definir_acces(i, c, self.d_adresse.text(),
                                                         self.d_protocole.currentText(), self.c_acces.isChecked())):
            notifier(self, "Accès enregistré.")

    def non_accessible(self):
        x = self._courante
        if x is None:
            return
        if x.ligne.non_accessible:
            self._faire(self.s.reouvrir)
            return
        motif, ok = QInputDialog.getText(self, "Information non accessible",
                                         f"{x.nom_standard}\nPourquoi cette information n'est-elle pas accessible ?\n"
                                         "(ex. absente du programme, non câblée, à créer lors des travaux)")
        if ok:
            self._faire(lambda i, c: self.s.declarer_non_accessible(i, c, motif))

    def non_applicable(self):
        x = self._courante
        if x is not None and confirmer(self, "Non applicable",
                                       f"{x.famille} {x.information} n'existe pas sur {x.repere} ?\n"
                                       "La ligne sort de la table (réversible depuis la fiche de l'équipement).",
                                       defaut_non=True):
            self._faire(self.s.signal_non_applicable)

    def confirmer_selection(self):
        choisies = [x for x in self.t.objets_selectionnes() if x.variable_source and not x.ligne.fonction_validee]
        if not choisies:
            informer(self, "Confirmer la fonction", "Sélectionner des lignes qui ont une variable source.")
            return
        if not confirmer(self, "Confirmer la fonction",
                         f"Confirmer la fonction de {len(choisies)} ligne(s) ?\n"
                         "Vous attestez avoir vérifié dans le programme que chaque variable porte l'information. "
                         "L'accès TOPKAPI reste à vérifier séparément."):
            return
        for x in choisies:
            self.s.valider_fonction(x.ligne.ident_eq, x.ligne.cle, True)
        self._apres()
        notifier(self, f"{len(choisies)} fonction(s) confirmée(s).")

    # ================================================================== table et équipements
    def equipements_detectes(self):
        detectes = self.s.equipements_detectes()
        if not detectes:
            informer(self, "Équipements détectés", "Aucun équipement non déclaré n'a été trouvé dans les noms "
                     "normalisés du programme. Déclarer les équipements dans la fiche ouvrage.")
            return
        d = DialogueDetectes(self, detectes)
        if d.exec():
            n = self.s.ajouter_detectes(d.choisis())
            self._apres()
            notifier(self, f"{n} équipement(s) ajouté(s). Construire ensuite la table.")

    def construire(self):
        if not self.s.ouvrage.equipements:
            informer(self, "Table de télétransmission", "Déclarer d'abord les équipements réellement présents "
                     "(fiche ouvrage) ou accepter les équipements détectés.")
            return
        ajoutees, retirees = self.s.construire_table()
        self._apres()
        notifier(self, f"Table à jour : {ajoutees} ligne(s) ajoutée(s), {retirees} retirée(s) ou hors périmètre.")

    def proposer(self):
        if not self.s.ouvrage.table_tt:
            self.construire()
            if not self.s.ouvrage.table_tt:
                return
        n = self.s.proposer_associations()
        self._apres()
        informer(self, "Propositions", f"{n} ligne(s) remplie(s) avec la meilleure proposition.\n\n"
                 "Rien n'est validé : chaque ligne reste orange tant que la fonction et l'accès TOPKAPI "
                 "n'ont pas été confirmés. Les lignes ambiguës ne sont pas remplies : voir leurs candidats.")

    # ================================================================== imports (inchangés)
    def analyser_dossier_pdf(self):
        """Diagnostic en lecture seule : ne touche pas à l'ouvrage, ni aux adresses sources."""
        if self.s.ouvrage.mode != 'Existant':
            return
        fichier, _ = QFileDialog.getOpenFileName(self, "Dossier de programme PL7 (PDF)", "", "PDF (*.pdf)")
        if not fichier:
            return
        try:
            from genvar.analyse_pdf_pl7 import analyser_pdf
            rapport = analyser_pdf(fichier)
        except (ValueError, RuntimeError, OSError, ImportError) as ex:
            avertir(self, 'Lecture documentaire PDF', str(ex))
            return
        rapport_detaille(self, 'Rapport documentaire (aucun rattachement automatique)',
                         rapport.resume(), validation=False)
        if confirmer(self, 'Enregistrer le diagnostic',
                     'Exporter les indices PDF et la revue des variables (CSV/JSON/TXT) dans un dossier séparé ?\n'
                     'Les données de l’ouvrage restent inchangées.', defaut_non=True):
            dossier = QFileDialog.getExistingDirectory(self, 'Choisir le dossier pour le rapport PDF')
            if dossier:
                try:
                    rapport.enregistrer(dossier)
                    informer(self, 'Rapport enregistré',
                             f'Dossier : {dossier}\n\nOuvrir revue_variables_pdf.csv pour examiner les pistes.\nAucune variable n’est validée pour TOPKAPI.')
                except OSError as ex:
                    avertir(self, 'Export du diagnostic', str(ex))

    def importer(self):
        if self.s.ouvrage.mode != "Existant":
            return
        nom, _ = QFileDialog.getOpenFileName(
            self, "Importer une table de variables", "",
            "Variables automate (*.xsy *.scy *.csv *.txt *.xlsx);;Control Expert (*.xsy);;"
            "PL7 symboles (*.scy);;Excel (*.xlsx);;CSV / texte (*.csv *.txt);;Tous (*.*)")
        if not nom:
            return
        try:
            analyse_xsy = None
            if os.path.splitext(nom)[1].lower() == '.xsy':
                analyse_xsy = existant.lire_xsy_detaille(nom)
                donnees, avertissements = import_sources.verifier_lignes_import(analyse_xsy.lignes)
                apercu = '\n'.join(f'{n} | {t} | {a or "adresse à vérifier"}'
                                    for n,t,a,c in donnees[:25])
                rapport = import_sources.rapport_import(len(analyse_xsy.lignes), donnees, avertissements)
                bilan_ddt = (f"\n\n{len(analyse_xsy.parents)} variables principales · "
                             f"{len(analyse_xsy.champs)} champs DDT développés · "
                             f"{analyse_xsy.definitions_ddt} définitions DDT.\n"
                             "Les champs DDT sont des chemins symboliques, PAS des adresses Modbus. "
                             "Leurs adresses d'acquisition restent non vérifiées.\n"
                             f"Empreinte SHA256 source : {analyse_xsy.sha256}\n")
                if analyse_xsy.avertissements:
                    bilan_ddt += ("\nATTENTION : développement DDT incomplet sur "
                                  f"{len(analyse_xsy.avertissements)} point(s) :\n" +
                                  "\n".join(analyse_xsy.avertissements[:30]) +
                                  "\nLe programme ne doit pas considérer cet inventaire comme exhaustif.\n")
                if not rapport_detaille(self, 'Vérifier le XSY et ses structures DDT',
                       rapport + bilan_ddt + '\nAperçu des variables :\n' + apercu +
                       '\n\nAutres avertissements :\n' +
                       ('\n'.join(avertissements) or 'Aucun') +
                       '\n\nAucun fichier automate ne sera modifié.'):
                    return
            else:
                headers, rows = import_sources.charger_table(nom)
                dlg = DialogueColonnesImport(self, headers, rows, os.path.basename(nom))
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    return
                donnees, avertissements = dlg.donnees
            changements = (existant.differences_xsy_detaille(self.s.ouvrage, analyse_xsy)
                           if analyse_xsy else existant.differences_reimport(self.s.ouvrage, donnees))
            modifications = [x for x in changements if x[1] != "Nouvelle variable"]
            absentes = existant.absentes_reimport(self.s.ouvrage, donnees)
            if modifications or absentes:
                extrait = "\n".join(f"{n} — {champ}: {avant or '(vide)'} → {apres or '(vide)'}"
                                    for n, champ, avant, apres in modifications[:12])
                if not confirmer(self, "Écarts au réimport",
                    f"{len(modifications)} propriété(s) source modifiée(s).\n"
                    f"{len(absentes)} variable(s) du référentiel absente(s) de ce fichier "
                    "(elles peuvent venir d'une autre source).\n\n"
                    f"{extrait}\n\n"
                    + ("Non retrouvées, premières lignes : " + ', '.join(absentes[:10]) + "\n\n" if absentes else "")
                    + "Aucune variable absente ne sera supprimée. Les types, adresses ou commentaires "
                      "changés dans le référentiel imposeront une nouvelle validation métier.\nContinuer ?",
                    defaut_non=True):
                    return
            total, nouveaux = (existant.importer_xsy_detaille(self.s.ouvrage, analyse_xsy)
                               if analyse_xsy else existant.importer_lignes(self.s.ouvrage, donnees))
            self.s._change()
            if self.s.ouvrage.table_tt:
                self.s.construire_table()       # les lignes dont la source a changé passent en incohérence
            self.charger(); self.modifie.emit()
            detectes = self.s.equipements_detectes()
            fin = (f'{total} variables importées, dont {nouveaux} nouvelles.\n'
                   'Noms, types, adresses et commentaires sources conservés.\n'
                   + (f'{len(detectes)} équipement(s) détecté(s) dans les noms : les examiner '
                      '(« Équipements détectés… »).\n' if detectes else '')
                   + 'Étape suivante : construire la table de télétransmission.')
            if avertissements:
                fin += ('\n\n' + str(len(avertissements)) + ' avertissement(s) :\n'
                        + '\n'.join(avertissements[:10]))
            informer(self, 'Import terminé', fin)
        except Exception as ex:
            avertir(self, 'Import impossible', f'Aucun fichier source n’a été modifié.\n{ex}')

    def importer_es(self):
        if self.s.ouvrage.mode != "Existant":
            return
        nom, _ = QFileDialog.getOpenFileName(
            self, "Liste E/S d'un ouvrage existant", "",
            "Liste E/S (*.xlsx *.csv *.txt);;Excel (*.xlsx);;CSV (*.csv);;Texte (*.txt)")
        if not nom:
            return
        try:
            es = liste_es.charger_liste_es(nom)
            apercu = "\n".join(f"{e.nom} | {e.adresse} | {e.equipement} | {e.fonction}" for e in es[:15])
            texte = (f"{len(es)} E/S lues. La liste précédente ({len(self.s.ouvrage.entrees_physiques_importees)} E/S) "
                     "sera remplacée pour cet ouvrage.\nAucune variable automate ne sera modifiée.\n\n"
                     "Aperçu :\n" + apercu + "\n\nValider cet import ?")
            if not rapport_detaille(self, "Vérifier la liste des E/S", texte):
                return
            self.s.ouvrage.entrees_physiques_importees = [x.__dict__.copy() for x in es]
            self.s._change()
            self.charger(); self.modifie.emit()
            informer(self, "Liste E/S importée", f"{len(es)} points documentaires enregistrés. "
                    "Ils apportent des indices de rapprochement, sans valider une liaison logique automate.")
        except Exception as exc:
            avertir(self, "Import E/S refusé", str(exc))
