"""Recette Chromium de la vue Variables, avec serveur et API réels.

Exécution : python -m unittest discover -s tests_web -v
Dépendances : requirements-qt.txt et Playwright (voir tests_web/README.md).
Tous les ouvrages sont fictifs et stockés dans un dossier temporaire.
"""
from pathlib import Path
import json
import os
import unittest

from support import ServeurNavigateur


class TestVariablesV031(ServeurNavigateur):
    def setUp(self):
        type(self).numero += 1
        self.api("/api/nouveau", {"mode": "Neuf"})
        if not any(lieu["code"] == "XTST" for lieu in self.api("/api/listes-ouvrage")["lieux"]):
            self.api("/api/listes-ouvrage/action", {
                "action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif",
            })
        self.api("/api/fiche-ouvrage", {"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": f"{self.numero:02d}",
            "libelle": "Recette navigateur fictive", "automate": "M340", "revision": "A",
        }})
        equipment = self.api("/api/equipement/ajouter", {
            "type": "HV", "numero": "01", "se": "00", "libelle": "Vanne fictive",
        })
        ident = equipment["ident"]
        self.api("/api/equipement/proposition", {"ident_eq": ident, "decision": "retenir"})
        self.api("/api/equipement/valider", {"idents": [ident], "valide": True})
        points = self.api("/api/es")["points"]
        self.api("/api/es/valider", {"niveau": "contenu", "paires": [
            {"ident_eq": point["ident_eq"], "cle": point["cle"]} for point in points
        ]})
        self.api("/api/materiel/action", {"action": "appliquer"})
        self.api("/api/materiel/action", {"action": "valider"})

        self.context = self.browser.new_context(viewport={"width": 1366, "height": 768})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(self.url + "#/variables", wait_until="networkidle")
        self.page.wait_for_selector(".v31-variable-row")

    def tearDown(self):
        self.assertEqual(self.errors, [], "Exception JavaScript pendant la recette")

    def test_keyboard_opens_detail_without_applying_addresses(self):
        before = self.api("/api/variables")["lignes"]
        self.assertTrue(before)
        for key in ("Enter", "Space"):
            with self.subTest(key=key):
                row = self.page.locator(".v31-variable-row").first
                name = row.get_attribute("data-variable")
                row.focus()
                row.press(key)
                self.assertEqual(self.page.locator("#v31-close-detail").count(), 1)
                self.assertEqual(self.page.locator(".v31-variable-detail h2").inner_text(), name)
                self.assertEqual(self.api("/api/variables")["lignes"], before)
                self.page.locator("#v31-close-detail").click()

    def test_checkbox_space_keeps_native_selection(self):
        checkbox = self.page.locator(".v31-choose").first
        checkbox.focus()
        checkbox.press("Space")
        self.assertTrue(checkbox.is_checked())
        self.assertEqual(self.page.locator("#v31-close-detail").count(), 0)

    def test_presets_describe_columns_without_changing_variables(self):
        fichier = Path(self.api('/api/ouvrage')['chemin'])
        avant = fichier.read_bytes()
        noms = self.page.locator('.v31-variable-row').evaluate_all("els => els.map(e => e.dataset.variable)")
        for vue, libelle in (('all', 'Toutes'), ('exchange', 'Adresses automate'), ('tele', 'Télétransmission')):
            with self.subTest(vue=vue):
                bouton = self.page.locator(f'[data-var-view="{vue}"]')
                self.assertEqual(bouton.inner_text(), libelle)
                bouton.click()
                self.assertEqual(self.page.locator('.v31-variable-row').evaluate_all(
                    "els => els.map(e => e.dataset.variable)"), noms)
        self.assertEqual(fichier.read_bytes(), avant)

    def test_rows_match_mockup_density_and_keep_accessible_selection(self):
        fichier = Path(self.api('/api/ouvrage')['chemin'])
        avant = fichier.read_bytes()
        for largeur, hauteur in ((1366, 768), (1920, 1080), (2560, 1440)):
            with self.subTest(largeur=largeur):
                self.page.set_viewport_size({'width': largeur, 'height': hauteur})
                ligne = self.page.locator('.v31-variable-row').first
                self.assertAlmostEqual(ligne.bounding_box()['height'], 44, delta=1)
                case = ligne.locator('.v31-choose')
                self.assertGreaterEqual(case.bounding_box()['width'], 24)
                self.assertGreaterEqual(case.bounding_box()['height'], 24)
                case.uncheck()
                case.focus()
                case.press('Space')
                self.assertTrue(case.is_checked())
                self.assertEqual(self.page.locator('#v31-close-detail').count(), 0)
                self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        self.assertEqual(fichier.read_bytes(), avant)

    def test_empty_filter_uses_empty_state_without_zero_counter(self):
        fichier = Path(self.api('/api/ouvrage')['chemin'])
        avant = fichier.read_bytes()
        self.page.locator('#v31-var-search').fill('aucune-variable-fictive-correspondante')
        compteur = self.page.locator('.v31-table-footer > span').inner_text()
        self.assertIn('Aucun résultat', compteur)
        self.assertNotRegex(compteur, r'\b0\b')
        self.assertEqual(self.page.locator('.v31-variable-row').count(), 0)
        self.assertEqual(fichier.read_bytes(), avant)

    def test_empty_filter_with_detail_spans_visible_columns_after_resize(self):
        fichier = Path(self.api('/api/ouvrage')['chemin'])
        avant = fichier.read_bytes()
        self.page.locator('.v31-variable-row').first.click()
        for vue in ('all', 'exchange', 'tele'):
            self.page.locator(f'[data-var-view="{vue}"]').click()
            self.page.locator('#v31-var-search').fill('aucune-variable-fictive-correspondante')
            for largeur in (1366, 1920, 2560):
                with self.subTest(vue=vue, largeur=largeur):
                    self.page.set_viewport_size({'width': largeur, 'height': 1080})
                    self.page.wait_for_function("""() => {
                      const table=document.querySelector('.v31-table'), vide=table.querySelector('td[colspan]');
                      return vide.colSpan === [...table.tHead.rows[0].cells].filter(e => getComputedStyle(e).display !== 'none').length;
                    }""", timeout=3000)
                    self.assertTrue(self.page.locator('#v31-close-detail').is_visible())
            self.page.locator('#v31-var-search').fill('')
        self.assertEqual(fichier.read_bytes(), avant)

    def test_escape_closes_detail_and_restores_row_focus_without_write(self):
        fichier = Path(self.api('/api/ouvrage')['chemin'])
        avant = fichier.read_bytes()
        ligne = self.page.locator('.v31-variable-row').first
        nom = ligne.get_attribute('data-variable')
        ligne.focus()
        ligne.press('Enter')
        self.page.wait_for_selector('#v31-close-detail')
        self.page.keyboard.press('Escape')
        self.page.wait_for_selector('#v31-close-detail', state='detached', timeout=3000)
        self.assertTrue(self.page.locator(f'[data-variable="{nom}"]').evaluate('e => e === document.activeElement'))
        self.assertEqual(fichier.read_bytes(), avant)

    def test_escape_closes_foreground_before_variable_detail(self):
        fichier = Path(self.api('/api/ouvrage')['chemin'])
        avant = fichier.read_bytes()
        self.page.locator('.v31-variable-row').first.click()
        self.page.locator('#v31-edit-single').click()
        self.page.wait_for_selector('#modale:not([hidden])')
        self.page.keyboard.press('Escape')
        self.assertFalse(self.page.locator('#modale').is_visible())
        self.assertTrue(self.page.locator('#v31-close-detail').is_visible())
        self.page.keyboard.press('Control+k')
        self.page.wait_for_selector('#v31-search-dialog')
        self.page.keyboard.press('Escape')
        self.assertEqual(self.page.locator('#v31-search-dialog').count(), 0)
        self.assertTrue(self.page.locator('#v31-close-detail').is_visible())
        self.page.keyboard.press('Escape')
        self.assertEqual(self.page.locator('#v31-close-detail').count(), 0)
        self.assertEqual(fichier.read_bytes(), avant)

    def test_captures_aux_dimensions_des_maquettes(self):
        dossier = Path(os.environ.get("OGIAS_CAPTURE_DIR", "artifacts/ci/captures"))
        dossier.mkdir(parents=True, exist_ok=True)
        mesures = {}
        self.page.set_viewport_size({"width": 1920, "height": 1080})
        for route, fichier in (("#/dashboard", "maquette-1-tableau-de-bord-1920.png"),
                               ("#/variables", "maquette-2-variables-1920.png")):
            self.page.goto(self.url + route, wait_until="networkidle")
            self.page.evaluate("document.fonts.ready")
            self.assertEqual(self.page.locator("#v31-sidebar").bounding_box()["width"], 80)
            self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            self.page.screenshot(path=str(dossier / fichier), full_page=True)
            mesures[route] = {"navigation": self.page.locator("#v31-sidebar").bounding_box(),
                              "contenu": self.page.locator(".v31-dashboard, .v31-main-table").bounding_box()}
        premiere = self.page.locator(".v31-variable-row").first
        nom = premiere.get_attribute("data-variable")
        premiere.click()
        self.page.wait_for_selector(".v31-variable-detail")
        self.assertEqual(self.page.locator(".v31-variable-detail h2").inner_text(), nom)
        self.page.screenshot(path=str(dossier / "maquette-3-variables-detail-1920.png"), full_page=True)
        mesures["detail"] = self.page.locator(".v31-variable-detail").bounding_box()
        (dossier / "maquettes-mesures.json").write_text(json.dumps(mesures, indent=2) + "\n", encoding="utf-8")

    def test_detail_garde_les_entetes_alignes_aux_cellules(self):
        self.page.locator(".v31-variable-row").first.click()
        for largeur in (1366, 1920, 2560):
            self.page.set_viewport_size({"width": largeur, "height": 1080})
            for vue in ("all", "exchange", "tele"):
                with self.subTest(largeur=largeur, vue=vue):
                    self.page.locator(f'[data-var-view="{vue}"]').click()
                    entetes = self.page.locator(".v31-table thead th").evaluate_all(
                        "els => els.filter(e => getComputedStyle(e).display !== 'none').map(e => ({texte:e.textContent.trim(),x:e.getBoundingClientRect().x}))")
                    cellules = self.page.locator(".v31-variable-row").first.locator("td").evaluate_all(
                        "els => els.filter(e => getComputedStyle(e).display !== 'none').map(e => ({texte:e.textContent.trim(),x:e.getBoundingClientRect().x}))")
                    self.assertEqual(len(entetes), len(cellules))
                    noms = [e["texte"] for e in entetes]
                    self.assertIn("Source", noms)
                    self.assertNotIn("Règle", noms)
                    self.assertEqual("Télétransmission" in noms, largeur > 1400 and vue != "exchange")
                    for h, c in zip(entetes, cellules):
                        self.assertAlmostEqual(h["x"], c["x"], delta=1)
                    self.assertIn("%MW", cellules[noms.index("Adresse automate")]["texte"])

    def test_view_headers_match_visible_cells(self):
        for view, excluded, count in [("all", None, 8), ("exchange", "Télétransmission", 7),
                                      ("tele", "Règle", 7)]:
            with self.subTest(view=view):
                self.page.locator(f'[data-var-view="{view}"]').click()
                headers = self.page.locator(".v31-table thead th").evaluate_all(
                    "els => els.filter(e => getComputedStyle(e).display !== 'none').map(e => e.textContent.trim())"
                )
                cells = self.page.locator(".v31-variable-row").first.locator("td").evaluate_all(
                    "els => els.filter(e => getComputedStyle(e).display !== 'none').length"
                )
                self.assertEqual(len(headers), cells)
                self.assertEqual(cells, count)
                if excluded:
                    self.assertNotIn(excluded, headers)
                self.page.locator("#v31-var-search").fill("aucune-variable-correspondante")
                self.assertEqual(self.page.locator(".v31-table tbody td[colspan]").get_attribute("colspan"), str(count))
                self.page.locator("#v31-var-search").fill("")

    def test_cancel_preview_does_not_write_project(self):
        project = Path(self.api("/api/ouvrage")["chemin"])
        self.assertTrue(project.resolve().is_relative_to(self.data.resolve()))
        before = project.read_bytes()
        variables = self.api("/api/variables")["lignes"]
        self.page.locator("#v31-validate-proposed").click()
        self.page.wait_for_selector("#m-ok")
        self.assertEqual(project.read_bytes(), before)
        self.page.get_by_role("button", name="Annuler", exact=True).click()
        self.assertEqual(project.read_bytes(), before)
        self.assertEqual(self.api("/api/variables")["lignes"], variables)

    def test_confirm_applies_engine_proposals_then_validates(self):
        plan = self.api("/api/adressage")
        expected = {(a["ident_eq"], a["cle"]): a["proposee"] for a in plan["affectations"]
                    if a["niveau"] == "automate" and a["etat"] == "proposée"}
        self.assertTrue(expected)
        self.page.locator("#v31-validate-proposed").click()
        self.page.locator("#m-ok").click()
        self.page.wait_for_function(
            "[...document.querySelectorAll('.v31-variable-row')].every(r => r.textContent.includes('validée'))"
        )
        actual = self.api("/api/variables")["lignes"]
        self.assertEqual({(v["ident_eq"], v["cle"]): v["adresse"] for v in actual}, expected)
        self.assertTrue(all(v["validee"] for v in actual))
        self.assertTrue(all(v["validee_le"] for v in actual))

    def test_stale_preview_is_refused_without_partial_application(self):
        self.page.locator("#v31-validate-proposed").click()
        self.page.wait_for_selector("#m-ok")
        # Modifier le projet APRÈS l'aperçu rend son empreinte périmée.
        self.api("/api/equipement/ajouter", {
            "type": "HV", "numero": "02", "se": "00", "libelle": "Autre vanne fictive",
        })
        project = Path(self.api("/api/ouvrage")["chemin"])
        self.assertTrue(project.resolve().is_relative_to(self.data.resolve()))
        before = project.read_bytes()
        with self.page.expect_response(
            lambda response: response.request.method == "POST" and response.url.endswith("/api/adressage/action")
        ) as pending:
            self.page.locator("#m-ok").click()
        self.assertEqual(pending.value.status, 400)
        self.assertIn("Le plan a changé", pending.value.json()["erreur"])
        self.page.wait_for_load_state("networkidle")
        self.assertEqual(project.read_bytes(), before)
        self.assertTrue(all(not v["adresse"] and not v["validee"]
                            for v in self.api("/api/variables")["lignes"]))


if __name__ == "__main__":
    unittest.main()
