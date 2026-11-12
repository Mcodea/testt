"""Polices et icônes réellement chargées depuis le serveur local, sans CDN."""
import hashlib
from urllib.parse import urlsplit

from support import ServeurNavigateur


class TestRessourcesEmbarquees(ServeurNavigateur):
    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1366, "height": 768})
        self.addCleanup(self.context.close)
        self.sorties = []
        origine = urlsplit(self.url).netloc

        def garder_local(route):
            if urlsplit(route.request.url).netloc != origine:
                self.sorties.append(route.request.url)
                route.abort()
            else:
                route.continue_()

        self.context.route("**/*", garder_local)
        self.page = self.context.new_page()
        self.erreurs = []
        self.page.on("pageerror", lambda e: self.erreurs.append(str(e)))
        self.reponses = []
        self.page.on("response", lambda r: self.reponses.append((r.url, r.status)))
        self.page.goto(self.url + "#/referentiel", wait_until="networkidle")

    def tearDown(self):
        self.assertEqual(self.erreurs, [])
        self.assertEqual(self.sorties, [], "Une ressource de l'interface dépend d'un serveur extérieur")

    def test_polices_et_licences_servies_localement(self):
        familles = self.page.evaluate("""async () => {
          await document.fonts.load('14px OGIAS-Inter');
          await document.fonts.load('13px OGIAS-Mono');
          await document.fonts.ready;
          return [...document.fonts].map(f => ({famille:f.family, etat:f.status}));
        }""")
        for famille in ("OGIAS-Inter", "OGIAS-Mono"):
            self.assertTrue(any(f["famille"] == famille and f["etat"] == "loaded" for f in familles))
        for police in ("InterVariable.woff2", "JetBrainsMono-Regular.woff2"):
            self.assertIn((self.url + "assets/fonts/" + police, 200), self.reponses)
        mesure = self.page.evaluate("""() => {
          const c=document.createElement('canvas').getContext('2d'); c.font='13px OGIAS-Mono';
          return [c.measureText('iiii').width,c.measureText('WWWW').width];
        }""")
        self.assertAlmostEqual(*mesure, places=5)
        for fichier, auteur in (("LICENSE-Inter.txt", "Inter Project Authors"),
                                ("LICENSE-JetBrainsMono.txt", "JetBrains Mono Project Authors")):
            reponse = self.context.request.get(self.url + "assets/fonts/" + fichier)
            self.assertEqual(reponse.status, 200)
            self.assertIn("SIL OPEN FONT LICENSE Version 1.1", reponse.text())
            self.assertIn(auteur, reponse.text())

    def test_icones_lucide_rendues_et_licence_disponible(self):
        icones = self.page.locator(".v31-sidebar svg.v31-icon")
        self.assertGreaterEqual(icones.count(), 5)
        self.assertEqual(icones.locator("use").count(), icones.count())
        self.page.wait_for_function("""() => [...document.querySelectorAll('.v31-sidebar svg.v31-icon')]
          .every(e => e.querySelector('use') && e.getBBox().width > 0 && e.getBBox().height > 0)""")
        for icone in icones.all():
            self.assertTrue(icone.get_attribute("data-lucide"))
            self.assertIn("assets/lucide/sprite.svg#", icone.locator("use").get_attribute("href"))
        licence = self.context.request.get(self.url + "assets/lucide/LICENSE.txt")
        self.assertEqual(licence.status, 200)
        self.assertIn("ISC License", licence.text())
        self.assertIn("Lucide Contributors", licence.text())

    def test_ressources_du_manifeste_intactes_et_licences_accessibles_depuis_a_propos(self):
        manifeste = self.context.request.get(self.url + "assets/tiers/manifest.json")
        self.assertEqual(manifeste.status, 200)
        for nom, digest in manifeste.json()["files"].items():
            with self.subTest(nom=nom):
                ressource = self.context.request.get(self.url + "assets/" + nom)
                self.assertEqual(ressource.status, 200)
                self.assertEqual(hashlib.sha256(ressource.body()).hexdigest(), digest)
        self.page.locator("#v31-about").click()
        self.page.wait_for_selector("#modale a[data-licence]", timeout=3000)
        self.assertEqual(self.page.locator("#modale a[data-licence]").count(), 3)
        for lien in self.page.locator("#modale a[data-licence]").all():
            self.assertEqual(self.context.request.get(self.url + lien.get_attribute("href")).status, 200)
