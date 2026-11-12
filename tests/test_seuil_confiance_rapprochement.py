"""Cahier § 6 : seuil de confiance du rapprochement hybride, mesures publiées, confirmations tracées et annulables.

- Aucune proposition fausse connue (jeux de validation/hybride, toutes méthodes, tous candidats, signaux absents
  compris) n'atteint le seuil ; au-dessus, la précision est de 100 %.
- Chaque proposition porte sa confiance et sa raison ; sous le seuil ou ambiguë : « à rapprocher manuellement ».
- Le compte rendu publié (validation/hybride/SEUIL_CONFIANCE.md) est exactement celui que le code produit.
- Confirmation une par une ou en lot (confiance élevée seulement) : tracée, annulable, sans vérifier l'accès.
"""
import unittest
from pathlib import Path

from genvar.rapprochement import A_RAPPROCHER, CONFIANCE_ELEVEE, METHODES, SEUIL_CONFIANCE, Proposition
from genvar.session import RegleMetier, Session
from validation.hybride.evaluer import BASE, JEUX, mesures_seuil, rapport_seuil, scenario


class TestSeuil(unittest.TestCase):
    def test_aucune_proposition_fausse_connue_au_dessus_du_seuil(self):
        for nom, rep in JEUX:
            for methode, r in mesures_seuil(rep).items():
                with self.subTest(jeu=nom, methode=methode):
                    self.assertLess(r["score_max_faux"], SEUIL_CONFIANCE)
                    self.assertEqual((r["eleves_faux"], r["faux_sur_absents"]), (0, 0))
                    if r["eleves_corrects"]:
                        self.assertEqual(r["precision_pct"], 100.0)

    def test_le_seuil_n_est_pas_trivial(self):
        # au moins une vraie correspondance est confirmable en lot, et un faux connu existe juste en dessous
        hybride = [mesures_seuil(rep)["hybride"] for _, rep in JEUX]
        self.assertGreater(sum(r["eleves_corrects"] for r in hybride), 0)
        self.assertEqual(max(r["score_max_faux"] for r in hybride), SEUIL_CONFIANCE - 1)

    def test_confiance_et_raison(self):
        haute = Proposition("V", "e", "TS_OUV", "hybride", SEUIL_CONFIANCE, ("Nom normalisé", "Repère"))
        self.assertEqual(haute.confiance, CONFIANCE_ELEVEE)
        self.assertEqual(haute.raison, "Nom normalisé ; Repère")
        self.assertEqual(Proposition("V", "e", "TS_OUV", "hybride", SEUIL_CONFIANCE - 1, ()).confiance, A_RAPPROCHER)
        ambigue = Proposition("V", "e", "TS_OUV", "hybride", 100, (), ambiguite=True)
        self.assertEqual(ambigue.confiance, A_RAPPROCHER)

    def test_compte_rendu_publie_identique_au_calcul(self):
        # fins de ligne normalisées : la conversion CRLF de Git sous Windows ne change pas le contenu publié
        publie = (BASE / "SEUIL_CONFIANCE.md").read_text(encoding="utf-8").replace("\r\n", "\n")
        self.assertEqual(publie, rapport_seuil())
        self.assertIn(f"{SEUIL_CONFIANCE}/100", publie)
        for m in METHODES:
            self.assertIn(f"| {m} |", publie)


class TestConfirmationEnLot(unittest.TestCase):
    def setUp(self):
        o, cat, truth, self.eqs = scenario(BASE)
        self.s = Session(cat)
        self.s.ouvrage = o
        self.s.construire_table()
        self.s.proposer_associations()
        self.attendus = {(self.eqs[n].ident, sig): att for n, sig, att in truth["liens"]}

    def _etat(self):
        return [(l.ident_eq, l.cle, l.variable_source, l.fonction_validee, l.acces_verifie)
                for l in self.s.ouvrage.table_tt]

    def test_lot_limite_a_la_confiance_elevee_et_juste(self):
        lot = self.s.confirmables_en_lot()
        self.assertTrue(lot)
        for l, p in lot:
            self.assertEqual(p.confiance, CONFIANCE_ELEVEE)
            self.assertGreaterEqual(p.score, SEUIL_CONFIANCE)
            self.assertEqual(self.attendus.get((l.ident_eq, l.cle)), l.variable_source)   # aucune fausse
        # les autres associations proposées restent à confirmer une par une
        restantes = [l for l in self.s.ouvrage.table_tt if l.variable_source and l not in [x for x, _ in lot]]
        self.assertTrue(restantes)

    def test_lot_trace_puis_annule_a_l_identique(self):
        avant = self._etat()
        entree = self.s.confirmer_en_lot()
        self.assertEqual(entree["action"], "confirmation en lot")
        self.assertTrue(entree["lignes"] and all("score" in x and x["raison"] for x in entree["lignes"]))
        confirmees = {(x["ident_eq"], x["cle"]) for x in entree["lignes"]}
        for l in self.s.ouvrage.table_tt:
            self.assertEqual(l.fonction_validee, (l.ident_eq, l.cle) in confirmees)
            self.assertFalse(l.acces_verifie)                     # l'accès TOPKAPI n'est jamais vérifié ici
        self.assertEqual(self.s.confirmables_en_lot(), [])
        self.assertIsNone(self.s.confirmer_en_lot())               # rien de plus à confirmer
        annulation = self.s.annuler_lot(entree["id"])
        self.assertEqual((annulation["action"], annulation["lot"], annulation["laissees"]),
                         ("annulation de lot", entree["id"], []))
        self.assertEqual(self._etat(), avant)
        with self.assertRaises(RegleMetier):
            self.s.annuler_lot(entree["id"])                      # une seule annulation
        with self.assertRaises(RegleMetier):
            self.s.annuler_lot(999)

    def test_annulation_respecte_une_decision_posterieure(self):
        entree = self.s.confirmer_en_lot()
        x = entree["lignes"][0]
        self.s.dissocier(x["ident_eq"], x["cle"])                  # décision prise après le lot
        annulation = self.s.annuler_lot(entree["id"])
        self.assertEqual(annulation["laissees"], [x])
        self.assertNotIn(x, annulation["lignes"])

    def test_confirmation_unitaire_tracee_et_annulable(self):
        l = next(l for l in self.s.ouvrage.table_tt if l.variable_source)
        self.s.valider_fonction(l.ident_eq, l.cle)
        self.s.valider_fonction(l.ident_eq, l.cle)                 # déjà confirmée : pas de doublon de trace
        self.s.valider_fonction(l.ident_eq, l.cle, False)
        actions = [e["action"] for e in self.s.ouvrage.journal_rapprochement]
        self.assertEqual(actions, ["confirmation", "annulation de confirmation"])
        self.assertFalse(l.fonction_validee)

    def test_rien_n_est_confirme_sans_geste(self):
        self.assertFalse(any(l.fonction_validee for l in self.s.ouvrage.table_tt))
        self.assertEqual(self.s.ouvrage.journal_rapprochement, [])


class TestJournalPersistant(unittest.TestCase):
    def test_journal_enregistre_et_relu(self):
        import os
        import tempfile
        o, cat, _, _ = scenario(Path(BASE))
        s = Session(cat)
        s.ouvrage = o
        s.construire_table(); s.proposer_associations()
        entree = s.confirmer_en_lot()
        with tempfile.TemporaryDirectory() as d:
            chemin = os.path.join(d, "o.ouvrage.json")
            s.enregistrer(chemin)
            s2 = Session(cat)
            s2.ouvrir(chemin)
        self.assertEqual(s2.ouvrage.journal_rapprochement, s.ouvrage.journal_rapprochement)
        s2.annuler_lot(entree["id"])
        self.assertFalse(any(l.fonction_validee for l in s2.ouvrage.table_tt))


if __name__ == "__main__":
    unittest.main()
