"""Géométrie de l'interface aux quatre résolutions de référence (refonte industrielle du 16/11/2026).

Pour chaque écran et chaque résolution (1366 × 768, 1440 × 900, 1920 × 1080, 2560 × 1440) :
- aucun défilement horizontal de la page ;
- aucun élément visible ne sort de la fenêtre (hors zones de défilement prévues) ;
- en-tête, étapes, zone de travail, navigation et barre d'état ne se chevauchent pas ;
- la barre d'étape ne masque pas le contenu : en fin de défilement le dernier bloc reste au-dessus ;
- libellés de navigation jamais coupés au milieu d'un mot ;
- panneau de détail des variables dans la fenêtre et à côté du tableau, jamais dessus ;
- arborescence des équipements ancrée sans chevaucher la fiche ;
- aucune écriture dans le projet pendant ces consultations.
"""
from pathlib import Path

from support import ServeurNavigateur

RESOLUTIONS = ((1366, 768), (1440, 900), (1920, 1080), (2560, 1440))
ECRANS = ("#/dashboard", "#/inventaire", "#/es", "#/materiel", "#/variables", "#/recette", "#/referentiel",
          "#/ouvrages")

# Éléments visibles qui sortent de la fenêtre sans être dans une zone de défilement ou de découpe prévue.
HORS_FENETRE = """() => {
  const W = innerWidth, H = innerHeight, sortie = [];
  const decoupe = el => { for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      if (/(auto|scroll|hidden|clip)/.test(getComputedStyle(p).overflowX)) return true; } return false; };
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    if (!r.width || !r.height || s.visibility === 'hidden' || s.display === 'none') continue;
    if ((r.right > W + 1 || r.left < -1) && !decoupe(el)) sortie.push((el.id ? '#' + el.id : el.tagName) + ' ' + Math.round(r.right));
  }
  return sortie.slice(0, 10);
}"""

COUPURES = """() => [...document.querySelectorAll('#v31-sidebar [data-nav] span')].filter(span => {
  const mots = span.textContent.trim().split(/\\s+/);
  const range = document.createRange(); range.selectNodeContents(span);
  const lignes = new Set([...range.getClientRects()].map(r => Math.round(r.top))).size;
  return lignes > mots.length || span.scrollWidth > span.clientWidth + 1;
}).map(s => s.textContent.trim())"""


def boite(page, selecteur):
    return page.locator(selecteur).first.bounding_box()


def separes(a, b):
    """Vrai si les rectangles a et b ne se recouvrent pas (1 px de tolérance d'arrondi)."""
    return (a['x'] + a['width'] <= b['x'] + 1 or b['x'] + b['width'] <= a['x'] + 1 or
            a['y'] + a['height'] <= b['y'] + 1 or b['y'] + b['height'] <= a['y'] + 1)


class TestGeometrieResolutions(ServeurNavigateur):
    def setUp(self):
        type(self).numero += 1
        self.api('/api/nouveau', {'mode': 'Neuf'})
        if not any(x['code'] == 'XTST' for x in self.api('/api/listes-ouvrage')['lieux']):
            self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'lieux',
                                                   'code': 'XTST', 'libelle': 'Lieu fictif'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': f'{50 + self.numero:02d}',
            'libelle': "Réservoir fictif au libellé volontairement long pour l'essai de mise en page",
            'automate': 'M340', 'revision': 'A'}})
        idents = []
        for k, t in enumerate(['PM', 'MV', 'HV'] * 8):                 # 24 équipements : beaucoup de lignes
            i = self.api('/api/equipement/ajouter', {'type': t, 'numero': f'{k + 1:02d}', 'se': '00'})['ident']
            self.api('/api/equipement/proposition', {'ident_eq': i, 'decision': 'retenir'})
            idents.append(i)
        self.api('/api/equipement/valider', {'idents': idents, 'valide': True})
        pts = self.api('/api/es')['points']
        self.api('/api/es/valider', {'niveau': 'contenu',
                                     'paires': [{'ident_eq': p['ident_eq'], 'cle': p['cle']} for p in pts]})
        self.api('/api/materiel/action', {'action': 'config', 'alimentation': 'BMX CPS 3500',
                                          'processeur': 'BMX P34 2020', 'communication': ['BMX NOE 0100']})
        self.api('/api/materiel/action', {'action': 'appliquer'})
        self.api('/api/modules', {'action': 'implanter'})
        self.projet = Path(self.api('/api/ouvrage')['chemin'])
        self.avant = self.projet.read_bytes()
        self.context = self.browser.new_context(viewport={'width': 1366, 'height': 768})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.erreurs = []
        self.page.on('pageerror', lambda e: self.erreurs.append(str(e)))

    def tearDown(self):
        self.assertEqual(self.erreurs, [])
        self.assertEqual(self.projet.read_bytes(), self.avant, 'Une consultation ne doit rien écrire')

    def ouvrir(self, route):
        self.page.goto(self.url + route, wait_until='networkidle')
        self.page.evaluate('document.fonts.ready')
        self.page.wait_for_timeout(150)

    def test_structure_sans_debordement_ni_chevauchement(self):
        for largeur, hauteur in RESOLUTIONS:
            self.page.set_viewport_size({'width': largeur, 'height': hauteur})
            for route in ECRANS:
                with self.subTest(resolution=f'{largeur}x{hauteur}', ecran=route):
                    self.ouvrir(route)
                    self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), largeur)
                    self.assertEqual(self.page.evaluate(HORS_FENETRE), [])
                    nav, top, vue = boite(self.page, '#v31-sidebar'), boite(self.page, '#v31-top'), boite(self.page, '#vue')
                    etat = boite(self.page, '#v30-status')
                    self.assertTrue(separes(nav, vue) and separes(nav, top) and separes(top, vue))
                    # Barre d'état en bas, pleine largeur de la zone de travail, sans recouvrir #vue
                    self.assertTrue(separes(etat, vue))
                    self.assertAlmostEqual(etat['y'] + etat['height'], hauteur, delta=1)
                    self.assertGreater(len(self.page.locator('#v30-status').inner_text().strip()), 10)
                    self.assertEqual(self.page.evaluate(COUPURES), [], 'Libellé de navigation coupé dans un mot')

    def test_barre_d_etape_ne_masque_pas_le_contenu(self):
        for largeur, hauteur in RESOLUTIONS:
            self.page.set_viewport_size({'width': largeur, 'height': hauteur})
            for route in ('#/inventaire', '#/es', '#/materiel', '#/recette'):
                with self.subTest(resolution=f'{largeur}x{hauteur}', ecran=route):
                    self.ouvrir(route)
                    mesure = self.page.evaluate("""() => {
                      const p = document.querySelector('.pied-etape'); let sc = p.parentElement;
                      while (sc && !/(auto|scroll)/.test(getComputedStyle(sc).overflowY)) sc = sc.parentElement;
                      const bas = sc.getBoundingClientRect().bottom, collee = p.getBoundingClientRect().bottom;
                      sc.scrollTop = sc.scrollHeight;
                      return {bas, collee, dernier: p.previousElementSibling.getBoundingClientRect().bottom,
                              haut: p.getBoundingClientRect().top}; }""")
                    self.assertAlmostEqual(mesure['collee'], mesure['bas'], delta=1, msg='Barre collée en bas')
                    self.assertLessEqual(mesure['dernier'], mesure['haut'] + 1, 'Dernier bloc sous la barre')

    def test_detail_des_variables_a_cote_du_tableau(self):
        for largeur, hauteur in RESOLUTIONS:
            self.page.set_viewport_size({'width': largeur, 'height': hauteur})
            with self.subTest(resolution=f'{largeur}x{hauteur}'):
                self.ouvrir('#/variables')
                sans = boite(self.page, '.v31-main-table')
                ecran = boite(self.page, '.v31-variable-screen')
                self.assertAlmostEqual(sans['width'], ecran['width'], delta=1, msg='Pas de colonne vide sans détail')
                self.page.locator('.v31-variable-row').first.click()
                detail, table = boite(self.page, '.v31-variable-detail'), boite(self.page, '.v31-main-table')
                self.assertGreaterEqual(detail['x'], 0)
                self.assertLessEqual(detail['x'] + detail['width'], largeur + 1)
                self.assertGreaterEqual(detail['width'], 249)
                self.assertTrue(separes(detail, table), 'Le détail ne doit pas recouvrir le tableau')
                self.assertGreaterEqual(table['width'], 600, 'Tableau comprimé par le panneau')
                self.page.locator('#v31-close-detail').click()

    def test_arborescence_ancree_et_fiche_repliable(self):
        for largeur, hauteur in RESOLUTIONS:
            self.page.set_viewport_size({'width': largeur, 'height': hauteur})
            with self.subTest(resolution=f'{largeur}x{hauteur}'):
                self.ouvrir('#/inventaire')
                arbre, fiche = boite(self.page, '#vue > aside'), boite(self.page, '#contenu')
                self.assertTrue(self.page.locator('#vue > aside').is_visible())
                self.assertTrue(separes(arbre, fiche))
                self.assertGreaterEqual(fiche['width'], 600)
                self.assertTrue(self.page.locator('#b-eq').is_visible(), 'Ajout d\'équipement accessible')
                # Fiche enregistrée : repliée sur une ligne, dépliable sans perdre de champ
                self.assertIsNone(self.page.locator('#fiche-ouvrage').get_attribute('open'))
                self.page.locator('#fiche-ouvrage > summary h2').click()
                self.assertTrue(self.page.locator('#lieu').is_visible())
                self.assertTrue(self.page.locator('#fiche-modifier').is_visible())
                self.page.locator('#fiche-ouvrage > summary h2').click()        # replier pour la résolution suivante
                self.assertIsNone(self.page.locator('#fiche-ouvrage').get_attribute('open'))
                # Le bouton de structure masque puis réaffiche l'arborescence
                bouton = self.page.locator('#v31-tree-trigger')
                self.assertEqual(bouton.get_attribute('aria-pressed'), 'true')
                bouton.click()
                self.assertFalse(self.page.locator('#vue > aside').is_visible())
                bouton.click()
                self.assertTrue(self.page.locator('#vue > aside').is_visible())

    def test_rack_lisible_en_tete_de_l_ecran_materiel(self):
        for largeur, hauteur in RESOLUTIONS:
            self.page.set_viewport_size({'width': largeur, 'height': hauteur})
            with self.subTest(resolution=f'{largeur}x{hauteur}'):
                self.ouvrir('#/materiel')
                rack = boite(self.page, '.rack')
                self.assertLess(rack['y'], hauteur, 'Le rack doit être visible sans défiler')
                for classe in ('alim', 'cpu', 'com', 'carte', 'libre'):
                    self.assertGreaterEqual(self.page.locator(f'.rack .emplacement.{classe}').count(), 1, classe)
                cases = self.page.locator('.rack .emplacement').all()
                for a, b in zip(cases, cases[1:]):
                    self.assertTrue(separes(a.bounding_box(), b.bounding_box()), 'Emplacements superposés')
