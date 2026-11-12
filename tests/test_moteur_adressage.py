"""Qualification du moteur d'adressage centralisé (scénarios A à F du cahier des charges du 9 novembre 2026).

Les résultats attendus sont écrits ici à partir des règles d'adressage documentées (cartes par rack puis
position, première voie libre, E/S d'un équipement groupées ; plages %MW par famille ; BOOL sur un bit,
INT sur un mot, DINT/REAL sur deux mots alignés), pas relus dans le générateur. Lieu fictif XTST.
Un test réussi ne vaut PAS qualification dans Control Expert, S4W-Tools ou TOPKAPI.
"""
import os
import tempfile
import unittest

from genvar import adressage, chemins, existant
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, _mot, TAILLE_MOTS
from genvar.session import Session, RegleMetier


def nouvelle(automate="M340"):
    s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
    s.nouveau(lieu_dans_le_nom=False)
    s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
    s.definir("automate", automate)
    s.ajouter_sous_ensemble("00")
    return s


def equiper(s, *specs):
    eqs = []
    for t, num, opts in specs:
        e = s.ajouter_equipement(Equipement("00", t, num, options=list(opts)))
        s.decider_propositions(e.ident, "retenir")
        eqs.append(e)
    s.valider_contenu_es([(p.ident_eq, p.cle) for p in s.points()])
    return eqs


def par_niveau(plan, niveau):
    return {(a.ident_eq, a.cle): a for a in plan.affectations if a.niveau == niveau}


def mots_occupes(adresse, type_logique):
    m, b = _mot(adresse)
    if b is not None:
        return {(m, b)}
    return {(m + i, None) for i in range(max(1, TAILLE_MOTS[type_logique]))}


class Base(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def sans_chevauchement(self, s):
        vus = {}
        for v in s.variables():
            if not v.adresse:
                continue
            m, b = _mot(v.adresse)
            for cle in mots_occupes(v.adresse, v.type_logique):
                autre = vus.get(cle) or (vus.get((cle[0], None)) if cle[1] is not None else None)
                self.assertIsNone(autre, f"{v.nom} {v.adresse} chevauche {autre}")
                vus[cle] = v.nom
            if b is None:
                self.assertFalse(any(k[0] == m and k[1] is not None for k in vus if vus[k] != v.nom),
                                 f"{v.nom} : mot entier sur un mot déjà utilisé bit à bit")
        voies = [p.adresse for p in s.points() if p.adresse]
        self.assertEqual(len(voies), len(set(voies)), "deux E/S sur la même voie")


class ScenarioA_M340(Base):
    """Pompe commandée, vanne motorisée à deux fins de course, débitmètre analogique ; cartes 16/4."""

    def test_affectation_complete_et_attendus(self):
        s = nouvelle("M340")
        pm, mv, ft = equiper(s, ("PM", "01", ["Télécommandée"]), ("MV", "01", ["Télécommandée"]), ("FT", "01", []))
        s.appliquer_materiel("16_4"); s.valider_materiel()
        plan = s.plan_adressage()
        self.assertEqual(plan.conflits, [])
        phys = par_niveau(plan, "physique")
        # attendu indépendant : ordre de l'arbre (type puis numéro : FT, MV, PM) ; première carte ET (rack 0,
        # position 1) ; la vanne a 4 ET (2 FDC, défaut, local), la pompe 3 ET (marche, thermique, local)
        et = sorted((a for a in phys.values() if a.nature == "ET"), key=lambda a: int(a.voie))
        self.assertEqual([a.proposee for a in et], [f"%I0.1.{i}" for i in range(7)])
        self.assertEqual([a.ident_eq for a in et], [mv.ident] * 4 + [pm.ident] * 3)   # E/S groupées par équipement
        st = sorted((a for a in phys.values() if a.nature == "ST"), key=lambda a: int(a.voie))
        self.assertEqual([a.proposee for a in st], [f"%Q0.2.{i}" for i in range(4)])
        ea = [a for a in phys.values() if a.nature == "EA"]
        self.assertEqual([a.ident_eq for a in ea], [ft.ident])
        self.assertTrue(ea[0].proposee.startswith("%IW0."))
        auto = par_niveau(plan, "automate")
        self.assertTrue(all(a.etat == "proposée" for a in auto.values()))
        # variables internes / calculées : aucune voie physique consommée
        self.assertNotIn((mv.ident, "TS_DISC"), phys)
        self.assertIn((mv.ident, "TS_DISC"), auto)
        for a in auto.values():
            self.assertTrue(a.regle, a.nom)                                        # justification toujours fournie
        r = s.appliquer_adressage(plan.empreinte)
        self.assertEqual(r, {"physique": len(phys), "automate": len(auto)})
        self.sans_chevauchement(s)
        apres = s.plan_adressage()
        self.assertEqual(sum(a.etat == "proposée" for a in apres.affectations if a.niveau != "teletransmission"), 0)
        self.assertEqual(s.plan_adressage().empreinte, apres.empreinte)           # déterministe
        # traçabilité : règle, origine, auteur
        t = pm.traces["automate:TS_MA"]
        self.assertEqual(t["origine"], "proposée"); self.assertTrue(t["regle"]); self.assertIn("le", t)


class ScenarioB_M580(Base):
    def test_types_alignement_et_emplacements(self):
        s = nouvelle("M580")
        equiper(s, ("PM", "01", ["Télécommandée", "Variateur"]), ("FT", "01", ["Seuils réglables"]))
        s.appliquer_materiel(); s.valider_materiel()
        self.assertEqual(s.ouvrage.racks[0]["cpu"], [0, 1])                          # M580 : CPU sur 2 positions
        plan = s.plan_adressage()
        phys = par_niveau(plan, "physique")
        self.assertTrue(all(int(a.module.split(".")[1]) >= 2 for a in phys.values()))   # jamais sur la CPU
        s.appliquer_adressage(plan.empreinte)
        for v in s.variables():
            m, b = _mot(v.adresse)
            if v.type_logique in ("BOOL", "EBOOL"):
                self.assertIsNotNone(b, v.nom)
            else:
                self.assertIsNone(b, v.nom)
            if TAILLE_MOTS.get(v.type_logique) == 2:
                self.assertEqual(m % 2, 0, f"{v.nom} 32 bits sur adresse impaire")
        # TR et RTR : correspondance explicite (miroir de plage), contrôlée
        tr = {v.code: v for v in s.variables() if v.famille == "TR"}
        rtr = {v.code: v for v in s.variables() if v.famille == "RTR"}
        self.assertEqual(set(tr), set(rtr))
        self.assertFalse([a for a in s.anomalies() if "miroir" in a.message])
        self.sans_chevauchement(s)


class ScenarioC_S4W(Base):
    def test_rien_d_invente(self):
        s = nouvelle("SOFREL S4W")
        equiper(s, ("HV", "01", []), ("LT", "01", []))
        prop = s.proposer_materiel()
        self.assertEqual((prop.plateforme, prop.applicable), ("S4W", False))
        plan = s.plan_adressage()
        for niveau in ("physique", "automate", "teletransmission"):
            a = par_niveau(plan, niveau).values()
            self.assertTrue(a)
            self.assertTrue(all(x.etat == "non résolue" and "S4W" in x.motif for x in a), niveau)
        self.assertTrue(all(not x.proposee for x in plan.affectations))
        self.assertEqual(s.appliquer_adressage(plan.empreinte), {"physique": 0, "automate": 0})


class ScenarioD_Existant(Base):
    def projet_historique(self):
        neuf = nouvelle("M580")
        equiper(neuf, ("PM", "01", []), ("HV", "01", []))
        props, _ = neuf.plan(); neuf.appliquer(props)
        xsy = os.path.join(self.dossier, "historique.xsy")
        neuf.exporter_xsy(xsy)
        s = nouvelle("M580")
        s.definir("mode", "Existant")
        existant.importer_xsy_detaille(s.ouvrage, existant.lire_xsy_detaille(xsy))
        return s, {v.nom: v.adresse for v in s.ouvrage.existantes}

    def test_historique_intact_et_disponibilite(self):
        s, historique = self.projet_historique()
        s.ajouter_detectes(s.equipements_detectes())
        s.ajouter_equipement(Equipement("00", "LT", "01"))              # nouvel équipement
        plan = s.plan_adressage()
        auto = [a for a in plan.affectations if a.niveau == "automate"]
        self.assertTrue(auto)
        self.assertTrue(all(not a.proposee for a in auto))              # disponibilité non vérifiée : rien
        self.assertTrue(any("disponibilité non vérifiée" in a.motif for a in auto))
        s.declarer_disponibilite(True)
        plan = s.plan_adressage()
        occupes = {_mot(a)[0] for a in historique.values() if _mot(a)}
        for a in plan.affectations:
            if a.niveau == "automate" and a.proposee:
                self.assertNotIn(_mot(a.proposee)[0], occupes, a.nom)   # jamais sur un mot historique
        self.assertEqual({v.nom: v.adresse for v in s.ouvrage.existantes}, historique)

    def test_conflit_introduit_detecte(self):
        s, historique = self.projet_historique()
        a, b = s.ouvrage.existantes[0], s.ouvrage.existantes[1]
        b.adresse = a.adresse                                           # conflit volontaire
        msgs = [x.message for x in s.anomalies_existant()]
        self.assertTrue(any(a.adresse in m for m in msgs), msgs[:5])


class ScenarioE_Modifications(Base):
    def test_reservations_ajout_retrait_et_stabilite(self):
        s = nouvelle("M340")
        hv, = equiper(s, ("HV", "01", []))
        s.appliquer_materiel("16_4"); s.valider_materiel()
        s.ajouter_reservation("voie", "0.1:0-1", "réserve câblage armoire")
        s.ajouter_reservation("memoire", "%MW1000-%MW1001", "réserve exploitant")
        plan = s.plan_adressage()
        phys = par_niveau(plan, "physique")
        self.assertNotIn("%I0.1.0", {a.proposee for a in phys.values()})
        self.assertNotIn("%I0.1.1", {a.proposee for a in phys.values()})
        auto = [a.proposee for a in plan.affectations if a.niveau == "automate"]
        self.assertFalse([x for x in auto if _mot(x)[0] in (1000, 1001)])
        s.appliquer_adressage(plan.empreinte)
        s.valider_affectations("automate", [(v.ident_eq, v.cle) for v in s.variables()])
        figees = {v.nom: v.adresse for v in s.variables()}
        voies = {p.nom: p.adresse for p in s.points()}
        # ajout puis retrait d'un équipement : les adresses validées ne bougent pas
        pm, = equiper(s, ("PM", "01", []))
        plan = s.plan_adressage()
        self.assertTrue(all(a.etat != "proposée" for a in plan.affectations
                            if a.niveau == "automate" and a.ident_eq == hv.ident))
        s.appliquer_adressage(plan.empreinte)
        s.supprimer_equipement(pm.ident)
        p2 = s.plan_adressage(); s.appliquer_adressage(p2.empreinte)
        self.assertEqual({v.nom: v.adresse for v in s.variables()}, figees)
        self.assertEqual({p.nom: p.adresse for p in s.points()}, voies)
        # réexécution : rien de nouveau, même empreinte
        e1 = s.plan_adressage().empreinte
        self.assertEqual(s.appliquer_adressage(e1), {"physique": 0, "automate": 0})
        self.assertEqual(s.plan_adressage().empreinte, e1)

    def test_adresse_validee_jamais_ecrasee(self):
        s = nouvelle("M340")
        hv, = equiper(s, ("HV", "01", []))
        p = s.plan_adressage(); s.appliquer_adressage(p.empreinte)
        v = next(x for x in s.variables() if x.cle == "TS_OUV")
        s.valider_affectations("automate", [(v.ident_eq, v.cle)])
        with self.assertRaises(RegleMetier):
            s.definir_adresses(v.ident_eq, v.cle, adresse="%MW1010.5")        # changement non confirmé
        self.assertEqual(next(x for x in s.variables() if x.cle == "TS_OUV").adresse, v.adresse)


class ScenarioF_Robustesse(Base):
    def test_saturation_et_simulation_des_besoins(self):
        s = nouvelle("M340")
        equiper(s, *[("PM", f"{i:02d}", []) for i in range(1, 9)], ("FT", "01", []), ("LT", "01", []))
        s.ajouter_module(0, 1, "ET", 16)                                # 16 voies pour 24 ET ; aucune EA
        plan = s.plan_adressage()
        phys = list(par_niveau(plan, "physique").values())
        # politique documentée : les 3 ET d'une pompe restent sur la même carte ; la 16e voie reste libre
        # plutôt que de couper la pompe 06 en deux cartes
        self.assertEqual(sum(a.etat == "proposée" for a in phys), 15)
        nr = [a for a in phys if a.etat == "non résolue"]
        self.assertEqual(len(nr), 11)                                   # 9 ET (pompes 06 à 08) + 2 EA
        self.assertTrue(all(a.motif for a in nr))
        self.assertTrue(any("réserve" in x for x in plan.alertes))     # réserve de 20 % entamée : signalée
        besoins = {b["nature"]: b for b in plan.besoins}
        self.assertEqual((besoins["ET"]["manquantes"], besoins["EA"]["manquantes"]), (9, 2))
        self.assertEqual(len(s.ouvrage.modules), 1)                     # simulation : rien ajouté

    def test_conflit_adresse_et_application_refusee(self):
        s = nouvelle("M340")
        hv, = equiper(s, ("HV", "01", []))
        p = s.plan_adressage(); s.appliquer_adressage(p.empreinte)
        a, b = [x for x in s.variables() if x.famille == "TS"][:2]
        hv.adresses[b.cle] = a.adresse                                  # adresse déjà utilisée (donnée incohérente)
        plan = s.plan_adressage()
        self.assertTrue(plan.conflits)
        self.assertTrue(any("chevauche" in m.message or "déjà" in m.message for m in s.anomalies()))
        hv2 = s.ajouter_equipement(Equipement("00", "LT", "01"))
        plan = s.plan_adressage()
        with self.assertRaises(RegleMetier):
            s.appliquer_adressage(plan.empreinte)                      # conflit : rien n'est appliqué
        self.assertFalse(hv2.adresses)

    def test_plan_perime_et_interruption_sans_modification_partielle(self):
        s = nouvelle("M340")
        hv, = equiper(s, ("HV", "01", []))
        plan = s.plan_adressage()
        s.ajouter_equipement(Equipement("00", "LT", "01"))
        with self.assertRaises(RegleMetier):
            s.appliquer_adressage(plan.empreinte)                      # données modifiées depuis l'aperçu
        plan = s.plan_adressage()
        avant = s.ouvrage
        original = adressage.calculer
        appels = {"n": 0}

        def defaillant(session):
            appels["n"] += 1
            if appels["n"] == 2:                                        # contrôle après écriture
                raise RuntimeError("coupure simulée")
            return original(session)
        adressage.calculer = defaillant
        try:
            with self.assertRaises(RuntimeError):
                s.appliquer_adressage(plan.empreinte)
        finally:
            adressage.calculer = original
        self.assertTrue(all(not e.adresses for e in s.ouvrage.equipements))   # rien de partiel
        self.assertIsNot(s.ouvrage, avant)

    def test_valeurs_manquantes_et_reservations_illisibles(self):
        s = nouvelle("")
        equiper(s, ("HV", "01", []))
        plan = s.plan_adressage()
        self.assertTrue(any("non renseigné" in x for x in plan.alertes))
        self.assertTrue(all(a.etat == "non résolue" for a in plan.affectations if a.niveau == "physique"))
        for niveau, cible in (("voie", "carte 3"), ("memoire", "%MW20-%MW10"), ("xx", "a")):
            with self.assertRaises(RegleMetier):
                s.ajouter_reservation(niveau, cible, "motif")
        with self.assertRaises(RegleMetier):
            s.ajouter_reservation("memoire", "%MW1200", "")             # motif obligatoire

    def test_teletransmission_convention_declaree_seulement(self):
        s = nouvelle("M340")
        equiper(s, ("FT", "01", ["Seuils réglables"]))
        p = s.plan_adressage(); s.appliquer_adressage(p.empreinte)
        tt = par_niveau(s.plan_adressage(), "teletransmission")
        self.assertTrue(all(a.etat == "non résolue" and not a.proposee for a in tt.values()))
        s.declarer_protocole(True, 0)
        tt = par_niveau(s.plan_adressage(), "teletransmission")
        noms = [a.nom for a in tt.values()]
        self.assertEqual(len(noms), len(set(noms)))                     # aucun point en double
        variables = {(v.ident_eq, v.cle): v for v in s.variables()}
        for k, a in tt.items():
            self.assertEqual(_mot("%MW" + a.proposee)[0], _mot(variables[k].adresse)[0])
        self.assertTrue(any("Retour" in a.regle for a in tt.values() if a.nature == "TR"))

    def test_persistance_des_affectations_et_traces(self):
        s = nouvelle("M340")
        equiper(s, ("HV", "01", []), ("PM", "01", []))
        s.appliquer_materiel("16_4"); s.valider_materiel()
        p = s.plan_adressage(); s.appliquer_adressage(p.empreinte)
        s.valider_affectations("physique", [(x.ident_eq, x.cle) for x in s.points()])
        chemin = os.path.join(self.dossier, "o.ouvrage.json")
        s.enregistrer(chemin)
        s2 = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s2.ouvrir(chemin)
        a1 = [(a.niveau, a.ident_eq, a.cle, a.adresse, a.etat, a.origine, a.regle, a.validee_par)
              for a in s.plan_adressage().affectations]
        a2 = [(a.niveau, a.ident_eq, a.cle, a.adresse, a.etat, a.origine, a.regle, a.validee_par)
              for a in s2.plan_adressage().affectations]
        self.assertEqual(a1, a2)
        self.assertTrue(any(x[4] == "validée" and x[0] == "physique" for x in a2))


if __name__ == "__main__":
    unittest.main()
