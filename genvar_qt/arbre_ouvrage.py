"""Arborescence de l'ouvrage : Ouvrage → UF → équipements → E/S et signaux.

C'est l'outil principal pour organiser l'ouvrage : clic droit pour ajouter, renommer, déplacer ou
supprimer ; glisser un équipement sur une UF pour l'y ranger ; double-clic pour ouvrir sa fiche.
Les lignes « ＋ … » sont des raccourcis cliquables. Aucune règle métier ici : chaque geste
devient une demande (signal `action`) traitée par la Session dans l'écran Ouvrage.
"""
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QAbstractItemView, QHeaderView

from . import style

ROLE = Qt.ItemDataRole.UserRole


class ArbreOuvrage(QTreeWidget):
    action = Signal(str, object)          # (verbe, donnée)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.header().setStretchLastSection(False)
        self.setIconSize(QSize(16, 16))
        self.setIndentation(18)
        self.setAnimated(True)
        self.setUniformRowHeights(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.itemDoubleClicked.connect(self._double_clic)
        self.itemSelectionChanged.connect(self._selection)
        self._ouverts = None

    # ================================================================== construction
    @staticmethod
    def _cle(item):
        d = item.data(0, ROLE)
        return (d[0], str(d[1])) if d else None

    def _noeud(self, parent, textes, nature, valeur, icone=None, couleur=None, italique=False, gras=False,
               infobulle=""):
        principal, detail = (list(textes) + ["", ""])[:2]
        it = QTreeWidgetItem([f"{principal}   {detail}" if detail else principal])
        it.setData(0, ROLE, (nature, valeur))
        if icone is not None:
            it.setIcon(0, icone)
        if couleur:
            it.setForeground(0, QBrush(QColor(couleur)))
        if italique or gras:
            f = QFont()
            f.setItalic(italique)
            f.setBold(gras)
            it.setFont(0, f)
        if infobulle:
            it.setToolTip(0, infobulle)
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if nature == "eq":
            flags |= Qt.ItemFlag.ItemIsDragEnabled
        if nature in ("uf", "commun", "eq"):
            flags |= Qt.ItemFlag.ItemIsDropEnabled
        it.setFlags(flags)
        if parent is None:
            self.addTopLevelItem(it)
        else:
            parent.addChild(it)
        return it

    def _memoriser_ouverts(self):
        ouverts = set()

        def parcourir(item):
            if item.isExpanded() and self._cle(item):
                ouverts.add(self._cle(item))
            for i in range(item.childCount()):
                parcourir(item.child(i))
        for i in range(self.topLevelItemCount()):
            parcourir(self.topLevelItem(i))
        return ouverts

    def remplir(self, session, etat_eq=lambda e: "OK"):
        """(Re)construit l'arbre en conservant les nœuds dépliés et la sélection."""
        o = session.ouvrage
        ouverts = self._memoriser_ouverts() if self.topLevelItemCount() else None
        selection = {self._cle(i) for i in self.selectedItems()}
        self.blockSignals(True)
        self.clear()
        neuf = o.mode != "Existant"
        variables, points = {}, {}
        if neuf:
            for v in session.variables():
                variables.setdefault(v.ident_eq, []).append(v)
            for p in session.points():
                points.setdefault(p.ident_eq, []).append(p)
        titre = " — ".join(x for x in (o.prefixe(), o.libelle) if x) or "Nouvel ouvrage (identification à compléter)"
        racine = self._noeud(None, [titre], "ouvrage", "", style.icone("document", style.ACCENT, 16), gras=True,
                             infobulle=f"{'Projet neuf' if neuf else 'Projet existant'} · {len(o.equipements)} "
                                       "équipement(s)\nClic : identification de l'ouvrage · clic droit : ajouter")
        tries = session.equipements_tries()
        for u in o.unites:
            eqs = [e for e in tries if e.uf == u.code]
            se = f" · SE {u.sous_ensemble}" if u.sous_ensemble else ""
            n_uf = self._noeud(racine, [f"{u.code} — {u.libelle or 'sans libellé'}", f"({len(eqs)}{se})"],
                               "uf", u.code, style.icone("dossier", style.ACCENT, 16), gras=True,
                               infobulle="Unité fonctionnelle. Clic : ses équipements · glisser un équipement "
                                         "ici pour l'y ranger")
            for e in eqs:
                self._equipement(n_uf, session, e, variables.get(e.ident, []), points.get(e.ident, []), etat_eq)
            self._noeud(n_uf, ["＋  Ajouter un équipement"], "ajout_eq", u.code, couleur=style.ACCENT,
                        italique=True, infobulle="Double-clic : ajouter un équipement dans cette UF")
        communs = [e for e in tries if not e.uf or e.uf not in {u.code for u in o.unites}]
        if o.unites and communs:
            # groupe affiché seulement s'il contient des équipements ; vide, il disparaît
            parent = self._noeud(racine, [session.libelle_communs(), f"({len(communs)})"], "commun", "",
                                 style.icone("dossier", style.SECONDAIRE, 16), gras=True,
                                 infobulle="Équipements hors UF (armoire, automate…). Clic droit : renommer, "
                                           "ranger dans une UF, supprimer.")
        else:
            parent = racine                       # ouvrage sans UF : les équipements sont directement dessous
        for e in communs:
            self._equipement(parent, session, e, variables.get(e.ident, []), points.get(e.ident, []), etat_eq)
        self._noeud(racine, ["＋  Ajouter un équipement commun (hors UF)" if o.unites else "＋  Ajouter un équipement"],
                    "ajout_eq", "", couleur=style.ACCENT, italique=True,
                    infobulle="Double-clic : ajouter un équipement" + (" hors UF" if o.unites else ""))
        self._noeud(racine, ["＋  Ajouter une unité fonctionnelle"], "ajout_uf", "", couleur=style.ACCENT,
                    italique=True, infobulle="Double-clic : créer une UF (ex. UF01 Stockage, sous-ensemble 11)")
        # dépliage : tout l'ouvrage et ses UF par défaut ; les équipements restent repliés
        def deplier(item):
            cle = self._cle(item)
            if ouverts is None:
                item.setExpanded(cle is not None and cle[0] in ("ouvrage", "uf", "commun"))
            else:
                item.setExpanded(cle in ouverts or (cle is not None and cle[0] == "ouvrage"))
            if cle in selection:
                item.setSelected(True)
            for i in range(item.childCount()):
                deplier(item.child(i))
        deplier(racine)
        self.blockSignals(False)

    def _equipement(self, parent, session, e, variables, points, etat_eq):
        o = session.ouvrage
        etat = etat_eq(e)
        props = session.propositions(e) if o.mode != "Existant" else {}
        en_attente = [p for p in props.values() if p.etat == "proposé"]
        detail = e.libelle or session.catalogue.designation(e.type)
        if en_attente:
            detail += f"  ⋯ {len(en_attente)} à examiner"
        n_eq = self._noeud(parent, [o.repere(e), detail], "eq", e.ident, style.icone_gravite(etat),
                           infobulle="Double-clic : fiche de l'équipement · glisser sur une UF pour le déplacer")
        for p in points:
            adr = p.adresse or "adresse physique à saisir"
            self._noeud(n_eq, [f"⇄  {p.nom}", f"{p.point} · {adr}"], "signal", e.ident,
                        couleur=None if p.adresse else style.GRAVITE["Alerte"][0],
                        infobulle=f"E/S physique : {p.information}" + (f" → {p.variable}" if p.variable else " (locale)"))
        for v in variables:
            adr = (v.adresse + (" ✓" if v.adresse_validee else " proposée")) if v.adresse else "sans adresse"
            self._noeud(n_eq, [v.nom, f"{adr} · {v.information}" + (" · ⚙" if v.logique else "")], "signal", e.ident,
                        couleur=None if v.adresse else style.DISCRET,
                        infobulle=f"{v.commentaire}\nOrigine : {v.origine}" + (f"\n⚙ {v.logique}" if v.logique else ""))
        for p in en_attente:
            ids = ", ".join(r.get("id", "?") for r in p.regles)
            fam, code = p.cle.split("_", 1)
            self._noeud(n_eq, [f"⋯  {fam}_{o.repere_nom(e)}_{code}", f"proposé ({ids}) · {p.signal['information']}"],
                        "proposition",
                        e.ident, couleur=style.GRAVITE["Alerte"][0], italique=True,
                        infobulle=f"{p.raison}\n{p.logique}\nDouble-clic : ouvrir la fiche pour accepter ou refuser.")

    def selectionner(self, nature, valeur):
        """Sélectionne un nœud sans déclencher d'action (après un ajout, par exemple)."""
        def chercher(item):
            if self._donnee(item) == (nature, valeur):
                return item
            for i in range(item.childCount()):
                r = chercher(item.child(i))
                if r is not None:
                    return r
            return None
        racine = self.topLevelItem(0)
        trouve = chercher(racine) if racine is not None else None
        if trouve is None:
            return False
        self.blockSignals(True)
        self.clearSelection()
        trouve.setSelected(True)
        self.setCurrentItem(trouve)
        self.blockSignals(False)
        self.scrollToItem(trouve)
        return True

    # ================================================================== interactions
    def _donnee(self, item):
        return item.data(0, ROLE) if item is not None else None

    def _uf_de(self, item):
        while item is not None:
            d = self._donnee(item)
            if d and d[0] in ("uf", "commun"):
                return d[1]
            item = item.parent()
        return ""

    def _double_clic(self, item, _col=0):
        d = self._donnee(item)
        if not d:
            return
        nature, valeur = d
        if nature == "ajout_eq":
            self.action.emit("ajouter_eq", valeur)
        elif nature == "ajout_uf":
            self.action.emit("ajouter_uf", None)
        elif nature in ("eq", "signal", "proposition"):
            self.action.emit("modifier_eq", valeur)
        elif nature == "uf":
            self.action.emit("modifier_uf", valeur)
        elif nature == "commun":
            self.action.emit("renommer_communs", None)
        elif nature == "ouvrage":
            self.action.emit("modifier_ouvrage", None)

    def _selection(self):
        items = self.selectedItems()
        d = self._donnee(items[0]) if items else None
        if not d:
            return
        if d[0] == "ouvrage":
            self.action.emit("choisir_ouvrage", None)
        elif d[0] in ("uf", "commun"):
            self.action.emit("filtrer_uf", d[1])
        elif d[0] in ("eq", "signal", "proposition"):
            self.action.emit("choisir_eq", d[1])

    def _menu(self, pos):
        item = self.itemAt(pos)
        d = self._donnee(item)
        menu = QMenu(self)
        ico = lambda n: style.icone(n, style.SECONDAIRE, 16)
        if d is None or d[0] in ("ouvrage", "ajout_uf"):
            menu.addAction(ico("ajouter"), "Ajouter une unité fonctionnelle…", lambda: self.action.emit("ajouter_uf", None))
            menu.addAction(ico("ajouter"), "Ajouter un équipement…", lambda: self.action.emit("ajouter_eq", ""))
            menu.addSeparator()
            menu.addAction(ico("modifier"), "Modifier l'identification de l'ouvrage", lambda: self.action.emit("modifier_ouvrage", None))
        elif d[0] in ("uf", "commun", "ajout_eq"):
            code = d[1]
            menu.addAction(ico("ajouter"), "Ajouter un équipement ici…", lambda: self.action.emit("ajouter_eq", code))
            if d[0] == "commun":
                menu.addAction(ico("modifier"), "Renommer le groupe…", lambda: self.action.emit("renommer_communs", None))
                menu.addAction(ico("dossier"), "Ranger ces équipements dans une UF…",
                               lambda: self.action.emit("ranger_communs", None))
                menu.addSeparator()
                menu.addAction(ico("supprimer"), "Supprimer ces équipements…",
                               lambda: self.action.emit("supprimer_communs", None))
            if d[0] == "uf":
                menu.addAction(ico("modifier"), "Renommer / modifier l'UF…", lambda: self.action.emit("modifier_uf", code))
                menu.addAction(ico("supprimer"), "Supprimer l'UF (les équipements sont conservés)",
                               lambda: self.action.emit("supprimer_uf", code))
        elif d[0] in ("eq", "signal", "proposition"):
            idents = [self._donnee(i)[1] for i in self.selectedItems() if self._donnee(i) and self._donnee(i)[0] == "eq"]
            if d[1] not in idents:
                idents = [d[1]]
            menu.addAction(ico("modifier"), "Ouvrir la fiche de l'équipement…", lambda: self.action.emit("modifier_eq", d[1]))
            menu.addAction(ico("copier"), "Dupliquer…", lambda: self.action.emit("dupliquer_eq", d[1]))
            parent = self.topLevelItem(0)
            cibles = []
            for i in range(parent.childCount() if parent else 0):
                cible = self._donnee(parent.child(i))
                if cible and cible[0] in ("uf", "commun"):
                    cibles.append((parent.child(i).text(0), cible[1]))
            if cibles:
                deplacer = menu.addMenu(ico("dossier"), "Ranger dans l'UF")
                for texte, code in cibles:
                    deplacer.addAction(texte, lambda c=code: self.action.emit("deplacer", (idents, c)))
            menu.addSeparator()
            menu.addAction(ico("supprimer"), "Supprimer…", lambda: self.action.emit("supprimer_eq", idents))
        menu.exec(self.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------ glisser-déposer
    def _cible(self, event):
        item = self.itemAt(event.position().toPoint())
        d = self._donnee(item)
        if not d:
            return None
        if d[0] in ("uf", "commun", "ajout_eq"):
            return d[1]
        if d[0] == "ouvrage":                  # déposer sur l'ouvrage : retirer de l'UF
            return ""
        if d[0] in ("eq", "signal", "proposition"):
            return self._uf_de(item)
        return None

    def dragMoveEvent(self, event):
        if self._cible(event) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        cible = self._cible(event)
        idents = [self._donnee(i)[1] for i in self.selectedItems() if self._donnee(i) and self._donnee(i)[0] == "eq"]
        event.setDropAction(Qt.DropAction.IgnoreAction)
        event.ignore()                      # l'arbre est reconstruit à partir de la Session
        if cible is not None and idents:
            self.action.emit("deplacer", (idents, cible))
