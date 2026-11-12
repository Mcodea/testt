"""Adoption explicite d'un projet fictif historique, navigateur et serveur réels."""
import copy
import os
from pathlib import Path
from unittest.mock import patch

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.session import Session
from support import ServeurNavigateur


class TestAdoptionNavigateur(ServeurNavigateur):
    def setUp(self):
        type(self).numero += 1
        self.projet = self.data / f"adoption-fictive-{self.numero}.json"
        with patch.dict(os.environ, {"SOREP_DATA_DIR": str(self.data)}):
            s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
            s.nouveau(False)
            s.definir("lieu", "XTST")
            s.definir("code_ouvrage", "RV")
            s.ouvrage.numero_ouvrage = "01"
            s.ajouter_sous_ensemble("00")
            for numero in ("01", "02"):
                e = s.ajouter_equipement(Equipement("00", "EV", numero))
                s.decider_propositions(e.ident, "retenir")
                s.valider_equipements([e.ident])
            plan, _ = s.plan()
            s.appliquer(plan)  # Adresses d'essai calculées par le moteur, aucune voie industrielle inventée.
            s.catalogue = copy.deepcopy(s.catalogue)
            for signal in s.catalogue.signaux:
                if signal["type"] == "EV" and signal["code"] in ("OUV", "FER"):
                    signal["organe"] = "FDC"
            s.enregistrer(str(self.projet))
        self.original = self.projet.read_bytes()
        self.api("/api/ouvrir", {"chemin": str(self.projet)})
        self.adresses = {v["nom"]: v["adresse"] for v in self.api("/api/variables")["lignes"]}
        self.context = self.browser.new_context(viewport={"width": 1366, "height": 768}, accept_downloads=True)
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.erreurs = []
        self.page.on("pageerror", lambda e: self.erreurs.append(str(e)))
        self.page.goto(self.url + "#/inventaire", wait_until="networkidle")
        self.page.wait_for_selector("#ref-adopter")

    def tearDown(self):
        self.assertEqual(self.erreurs, [])

    def ouvrir(self):
        self.page.locator("#ref-adopter").click()
        self.page.wait_for_selector(".adoption-equipement")

    def confirmer(self):
        self.page.locator('[data-type="EV"]').check()
        for ligne in self.page.locator("[data-confirmation]").all():
            ligne.check()

    def adopter(self):
        self.ouvrir()
        self.confirmer()
        self.page.locator("#m-ok").click()
        self.page.wait_for_selector("#ref-annuler-adoption")

    def test_apercu_par_equipement_decoches_annulable_sans_ecriture(self):
        self.ouvrir()
        self.assertEqual(self.page.locator("[data-adoption-eq]").count(), 2)
        self.assertEqual(self.page.locator("[data-confirmation]").count(), 4)
        self.assertEqual(self.page.locator("[data-confirmation]:checked").count(), 0)
        texte = self.page.locator(".boite-corps").inner_text()
        for numero in ("01", "02"):
            self.assertIn(f"XTSTRV01EV{numero}", texte)
            self.assertIn(f"ET_RV01EV{numero}_FDC_OUV", texte)
            self.assertIn(f"ET_RV01EV{numero}_OUV", texte)
        self.assertNotIn("<repère>", texte)
        self.page.locator("#m-ok").focus()
        self.page.keyboard.press("Tab")
        self.assertTrue(self.page.locator('[data-type="EV"]').evaluate("el => el === document.activeElement"))
        self.page.keyboard.press("Shift+Tab")
        self.assertTrue(self.page.locator("#m-ok").evaluate("el => el === document.activeElement"))
        self.page.locator('[data-type="EV"]').press("Escape")
        self.assertTrue(self.page.locator("#ref-adopter").evaluate("el => el === document.activeElement"))
        self.assertEqual(self.projet.read_bytes(), self.original)

    def test_chaque_renommage_requiert_confirmation(self):
        self.ouvrir()
        self.page.locator('[data-type="EV"]').check()
        self.page.locator("#m-ok").click()
        self.assertIn("chaque renommage", self.page.locator("#m-err").inner_text())
        self.assertEqual(self.projet.read_bytes(), self.original)
        self.page.locator("[data-confirmation]").first.check()
        self.page.locator("#m-ok").click()
        self.assertIn("chaque renommage", self.page.locator("#m-err").inner_text())
        self.assertEqual(self.projet.read_bytes(), self.original)

    def test_adoption_sauvegarde_telechargee_et_annulation_identique(self):
        self.adopter()
        captures = Path(os.environ.get("OGIAS_CAPTURE_DIR", "artifacts/ci/captures"))
        captures.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(captures / "adoption-retour-1366.png"), full_page=True)
        apres = self.projet.read_bytes()
        self.assertNotEqual(apres, self.original)
        self.assertEqual({v["nom"]: v["adresse"] for v in self.api("/api/variables")["lignes"]}, self.adresses)
        self.assertTrue(all(not e["valide"] for e in self.api("/api/ouvrage")["equipements"]))
        with self.page.expect_download() as attente:
            self.page.locator("#ref-sauvegarde").click()
        self.assertEqual(Path(attente.value.path()).read_bytes(), self.original)
        self.page.locator("#ref-annuler-adoption").click()
        self.page.locator("#m-ok").press("Escape")
        self.assertEqual(self.projet.read_bytes(), apres)
        self.page.locator("#ref-annuler-adoption").click()
        self.page.locator("#m-ok").click()
        self.page.wait_for_selector("#ref-adopter")
        self.assertEqual(self.page.locator("#ref-annuler-adoption").count(), 0)
        self.assertEqual(self.projet.read_bytes(), self.original)

    def test_apercu_perime_refuse_et_choix_conserves(self):
        self.ouvrir()
        self.confirmer()
        self.api("/api/definir", {"champ": "libelle", "valeur": "Modification fictive après aperçu"})
        actuel = self.projet.read_bytes()
        self.page.locator("#m-ok").click()
        self.page.wait_for_function("document.querySelector('#m-err').textContent.includes('a changé')")
        self.assertEqual(self.projet.read_bytes(), actuel)
        self.assertTrue(self.page.locator('[data-type="EV"]').is_checked())
        self.assertTrue(self.page.locator("#m-ok").is_enabled())

    def test_echec_annulation_affiche_le_motif_et_conserve_le_fichier(self):
        self.adopter()
        adopte = self.projet.read_bytes()
        nom = self.api("/api/ouvrage")["referentiel"]["sauvegarde_adoption"]
        (self.projet.parent / nom).unlink()
        self.page.locator("#ref-annuler-adoption").click()
        self.page.locator("#m-ok").click()
        self.page.wait_for_selector(".toast.err", timeout=3000)
        self.assertIn("introuvable", self.page.locator(".toast.err").inner_text())
        self.assertEqual(self.projet.read_bytes(), adopte)
        self.assertTrue(self.page.locator("#ref-annuler-adoption").is_visible())

    def test_capture_et_resolutions_sans_debordement(self):
        self.ouvrir()
        for largeur, hauteur in ((1366, 768), (1920, 1080), (2560, 1440)):
            with self.subTest(largeur=largeur):
                self.page.set_viewport_size({"width": largeur, "height": hauteur})
                self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                pied = self.page.locator("#modale .boite-pied").bounding_box()
                self.assertLessEqual(pied["y"] + pied["height"], hauteur)
                self.assertTrue(self.page.locator("#m-ok").is_visible())
        self.page.set_viewport_size({"width": 1366, "height": 768})
        captures = Path(os.environ.get("OGIAS_CAPTURE_DIR", "artifacts/ci/captures"))
        captures.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(captures / "adoption-detail-1366.png"), full_page=True)
