"""Retours de l'utilisateur du 16/11/2026 : en-tête de l'arborescence, rack équipé emplacement par emplacement,
sources d'acquisition classées."""
import re
from support import ServeurNavigateur


class TestRetours1611(ServeurNavigateur):
    BASE = 20

    def setUp(self):
        type(self).numero += 1
        self.api('/api/nouveau', {'mode': 'Neuf'})
        if not any(x['code'] == 'XTST' for x in self.api('/api/listes-ouvrage')['lieux']):
            self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'lieux',
                                                   'code': 'XTST', 'libelle': 'Lieu fictif'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': f'{self.BASE + self.numero:02d}',
            'libelle': 'Essai du 16/11', 'automate': 'Sch - M340', 'revision': 'A'}})
        i = self.api('/api/equipement/ajouter', {'type': 'PM', 'numero': '01', 'se': '00'})['ident']
        self.api('/api/equipement/proposition', {'ident_eq': i, 'decision': 'retenir'})
        self.api('/api/equipement/valider', {'idents': [i], 'valide': True})
        pts = self.api('/api/es')['points']
        self.api('/api/es/valider', {'niveau': 'contenu',
                                     'paires': [{'ident_eq': p['ident_eq'], 'cle': p['cle']} for p in pts]})
        self.api('/api/materiel/action', {'action': 'appliquer'})
        self.context = self.browser.new_context(viewport={'width': 1366, 'height': 768})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.erreurs = []
        self.page.on('pageerror', lambda e: self.erreurs.append(str(e)))

    def tearDown(self):
        self.assertEqual(self.erreurs, [])

    def test_en_tete_de_l_arborescence_compact_et_lisible(self):
        # Refonte, lot 5a : les commandes de l'inventaire sont au ruban de l'écran (groupe « Inventaire »).
        self.page.goto(self.url + '#/inventaire', wait_until='networkidle')
        groupe = self.page.locator('#o-ruban [role="group"][aria-label="Inventaire"]')
        groupe.wait_for()
        for s in ('#b-eq', '#b-uf', '#b-import'):
            self.assertEqual(groupe.locator(s).count(), 1, s)
            self.assertTrue(self.page.locator(s).is_visible(), s)
            self.assertLessEqual(self.page.locator(s).evaluate('e => e.scrollWidth - e.clientWidth'), 1, s)
        self.assertIn("Arborescence", self.page.locator('#vue > aside h2').inner_text())

    def test_emplacement_libre_equipe_d_une_carte_puis_d_un_module_de_communication(self):
        self.page.goto(self.url + '#/materiel', wait_until='networkidle')
        libres = self.page.locator('.emplacement.libre[data-emplacement]')
        libres.first.wait_for()
        cle = libres.first.get_attribute('data-emplacement')
        libres.first.dblclick()          # poste de travail : double-clic = fenêtre de l'emplacement
        self.page.locator('#e-ref').select_option('BMX DRA 1605')
        self.page.locator('#e-ok').click()
        self.page.wait_for_function('c => !!document.querySelector(`[data-carte="${c}"]`)', arg=cle)
        module = next(m for m in self.api('/api/es')['modules'] if m['module'] == cle)
        self.assertEqual((module['reference'], module['nature'], module['voies']), ('BMX DRA 1605', 'ST', 16))
        # Un autre emplacement libre reçoit un module de communication
        cle2 = self.page.locator('.emplacement.libre[data-emplacement]').first.get_attribute('data-emplacement')
        self.page.locator('.emplacement.libre[data-emplacement]').first.dblclick()
        self.page.locator('input[name="e-type"][value="com"]').check()
        self.page.locator('#e-com-ref').select_option('BMX NOM 0200')
        self.page.locator('#e-ok').click()
        self.page.wait_for_function('c => document.querySelector(`[data-emplacement="${c}"]`)?.dataset.role === "communication"',
                                    arg=cle2)
        # L'emplacement de communication refuse une carte (réservé) et peut être libéré
        rack, pos = cle2.split('.')
        with self.assertRaisesRegex(RuntimeError, 'réservé'):
            self.api('/api/modules', {'action': 'ajouter', 'rack': rack, 'position': pos, 'nature': 'ET',
                                      'voies': 16, 'reference': 'BMX DDI 1602'})
        self.page.locator(f'[data-emplacement="{cle2}"]').dblclick()
        self.page.locator('#e-liberer').click()
        self.page.wait_for_function('c => document.querySelector(`[data-emplacement="${c}"]`)?.dataset.role === "libre"', arg=cle2)

    def test_emplacements_reserves_proposent_seulement_leur_module(self):
        self.page.goto(self.url + '#/materiel', wait_until='networkidle')
        self.page.locator('.emplacement.alim[data-emplacement]').dblclick()
        options = self.page.locator('#e-ref option').all_text_contents()
        self.assertTrue(all(o.startswith('BMX CPS') or o.startswith('—') for o in options))
        self.page.locator('#e-ref').select_option('BMX CPS 2010')
        self.page.locator('#e-ok').click()
        self.page.wait_for_function('() => document.querySelector(".emplacement.alim b")?.textContent === "BMX CPS 2010"')
        self.page.locator('.emplacement.cpu[data-emplacement]').first.dblclick()
        options = self.page.locator('#e-ref option').all_text_contents()
        self.assertTrue(all(o.startswith('BMX P34') or o.startswith('—') for o in options))
        self.page.locator('#modale [data-fermer]').click()

    def test_source_d_acquisition_classee(self):
        self.page.goto(self.url + '#/inventaire', wait_until='networkidle')
        self.page.locator('#fiche-ouvrage > summary h2').click()
        groupes = self.page.locator('#automate optgroup').evaluate_all('g => g.map(x => x.label)')
        self.assertEqual(groupes[:3], ['Automate', 'Télégestion', 'E/S déportées'])
        self.assertEqual(self.page.locator('label[for="automate"]').inner_text(), "Source d'acquisition")
        self.assertEqual(self.page.locator('#automate').input_value(), 'Sch - M340')


class TestRetours1611Parcours(ServeurNavigateur):
    """Retour du 16/11 (11 h 03) : fiche équipement et écran matériel guidés, colonne « Source » des variables
    remplacée par le libellé."""
    BASE = 40
    setUp = TestRetours1611.setUp
    tearDown = TestRetours1611.tearDown

    def visibles(self, selecteurs):
        return [s for s in selecteurs if self.page.locator(s).is_visible()]

    def test_fiche_equipement_guidee_par_onglets(self):
        self.api('/api/equipement/ajouter', {'type': 'PM', 'numero': '02', 'se': '00'})
        self.page.goto(self.url + '#/inventaire', wait_until='networkidle')
        self.page.locator('#vue > aside :text("PM02")').first.click()
        self.page.locator('.parcours-eq').wait_for()
        blocs = ('#configuration-es', '#infos-fonctionnelles', '#lignes-supervision')
        self.assertTrue(self.page.locator('.parcours-eq .prochaine-action').is_visible())
        # Trois onglets de paramétrage, plus la vue d'ensemble « Fil des informations » (refonte, lot 5a)
        self.assertEqual(self.page.locator('.onglets-eq [role=tab]').count(), 4)
        blocs = blocs + ('#fil-informations',)
        self.assertEqual(len(self.visibles(blocs)), 1, 'Un seul onglet affiché à la fois')
        for onglet, bloc in (('fonc', '#infos-fonctionnelles'), ('lignes', '#lignes-supervision'), ('es', '#configuration-es')):
            self.page.locator(f'[data-onglet-eq="{onglet}"]').click()
            self.assertEqual(self.visibles(blocs), [bloc])
            self.assertEqual(self.page.locator(f'[data-onglet-eq="{onglet}"]').get_attribute('aria-selected'), 'true')
        # Clavier : flèche droite passe à l'onglet suivant
        self.page.locator('[data-onglet-eq="es"]').focus()
        self.page.keyboard.press('ArrowRight')
        self.assertEqual(self.visibles(blocs), ['#infos-fonctionnelles'])
        self.page.locator('[data-onglet-eq="es"]').click()
        # Options compactes (une ligne) et aide repliée
        options = self.page.locator('.option-eq').all()
        if options:
            self.assertEqual(len({round(o.bounding_box()['y']) for o in options}), 1)
        self.assertIsNone(self.page.locator('#configuration-es details.aide-pliable').get_attribute('open'))
        # Le choix d'onglet est conservé quand on revient sur l'équipement
        self.page.locator('[data-onglet-eq="lignes"]').click()
        self.page.locator('#vue > aside :text("PM01")').first.click()
        self.page.wait_for_function('() => !document.querySelector("#contenu h1")?.textContent.includes("PM02")')
        self.page.locator('#vue > aside :text("PM02")').first.click()
        self.page.wait_for_function('() => document.querySelector("#contenu h1")?.textContent.includes("PM02")')
        self.assertEqual(self.visibles(blocs), ['#lignes-supervision'])

    def test_ecran_materiel_rack_puis_onglets(self):
        self.page.goto(self.url + '#/materiel', wait_until='networkidle')
        self.page.locator('#onglets-mat').wait_for()
        action = self.page.locator('#pa-materiel')
        self.assertTrue(action.is_visible())
        self.assertLess(self.page.locator('.rack').first.bounding_box()['y'],
                        self.page.locator('#onglets-mat').bounding_box()['y'], 'Le rack avant les onglets')
        panneaux = ['#panneau-mat-voies', '#panneau-mat-reglages', '#panneau-mat-livrables']
        self.assertEqual(self.visibles(panneaux), ['#panneau-mat-voies'], 'Cartes posées : onglet des voies')
        self.page.locator('[data-onglet-mat="reglages"]').click()
        self.assertEqual(self.visibles(panneaux), ['#panneau-mat-reglages'])
        self.assertTrue(self.page.locator('[data-cfg="alimentation"]').is_visible())
        self.page.locator('[data-onglet-mat="livrables"]').click()
        self.assertTrue(self.page.locator('#m-nomenclature').is_visible())
        # Toutes les commandes restent dans la page
        for s in ('#m-impl', '#m-lib', '#x-q', '#m-livrables', '#m-calc'):
            self.assertEqual(self.page.locator(s).count(), 1, s)
        # La prochaine action déclenche la commande existante (ici : implanter les E/S sans voie)
        if self.page.locator('#pa-bouton').inner_text() == 'Implanter les E/S':
            self.page.locator('#pa-bouton').click()
            self.page.locator('#modale').get_by_text('Implanter', exact=True).wait_for()
            self.page.locator('#modale [data-fermer]').first.click()

    def test_variables_libelle_a_la_place_de_la_source(self):
        self.page.goto(self.url + '#/variables', wait_until='networkidle')
        self.page.locator('.v31-variable-row').first.wait_for()
        entetes = self.page.locator('.v31-table thead th').all_text_contents()
        self.assertNotIn('Source', [e.strip() for e in entetes])
        self.assertIn('Libellé', [e.strip() for e in entetes])
        v = self.api('/api/variables')['lignes'][0]
        attendu = v.get('libelle') or v.get('commentaire') or '—'
        ligne = self.page.locator(f'.v31-variable-row[data-variable="{v["nom"]}"] .v31-libelle')
        self.assertEqual(ligne.inner_text().strip(), attendu.strip())


class TestPosteDeTravailMateriel(ServeurNavigateur):
    """16/11, 12 h : écran Matériel en poste de travail (éditeur, catalogue à droite, inspecteur en bas)."""
    BASE = 60
    setUp = TestRetours1611.setUp
    tearDown = TestRetours1611.tearDown

    def ouvrir(self, largeur=1366, hauteur=768):
        self.page.set_viewport_size({'width': largeur, 'height': hauteur})
        self.page.goto(self.url + '#/materiel', wait_until='networkidle')
        self.page.locator('#pt-catalogue .cat-item').first.wait_for()

    def test_panneaux_sans_chevauchement_ni_defilement_de_page(self):
        for largeur, hauteur in ((1366, 768), (1440, 900), (1920, 1080), (2560, 1440)):
            with self.subTest(resolution=f'{largeur}x{hauteur}'):
                self.ouvrir(largeur, hauteur)
                b = {k: self.page.locator(s).bounding_box() for k, s in
                     (('ed', '#pt-editeur'), ('cat', '#pt-catalogue'), ('ins', '#pt-inspecteur'), ('pied', '.pied-etape'))}
                self.assertLessEqual(b['ed']['x'] + b['ed']['width'], b['cat']['x'] + 1)
                self.assertLessEqual(b['ed']['y'] + b['ed']['height'], b['ins']['y'] + 1)
                self.assertLessEqual(b['ins']['y'] + b['ins']['height'], b['pied']['y'] + 1)
                self.assertLessEqual(b['cat']['y'] + b['cat']['height'], b['pied']['y'] + 1)
                self.assertGreaterEqual(b['ins']['height'], 150)
                self.assertGreaterEqual(b['cat']['width'], 239)
                self.assertEqual(self.page.evaluate("(() => { const v = document.querySelector('#vue'); return v.scrollHeight - v.clientHeight })()"), 0)
                self.assertLess(self.page.locator('.rack').first.bounding_box()['y'], b['ins']['y'], 'Rack visible au-dessus de l\'inspecteur')

    def test_installer_depuis_le_catalogue_par_clic_et_par_glisser(self):
        self.ouvrir()
        avant = len(self.api('/api/es')['modules'])
        self.page.locator('.cat-item[data-ref="BMX DDO 1602"]').click()
        self.assertEqual(self.page.locator('.cat-item[data-ref="BMX DDO 1602"]').get_attribute('aria-pressed'), 'true')
        cibles = self.page.locator('.rack .emplacement.cible')
        self.assertGreaterEqual(cibles.count(), 1)
        self.assertEqual(self.page.locator('.rack .emplacement.cible:not(.libre)').count(), 0, 'Une carte ne vise que les emplacements libres')
        self.page.keyboard.press('Escape')
        self.assertEqual(self.page.locator('.rack .emplacement.cible').count(), 0)
        self.page.locator('.cat-item[data-ref="BMX DDO 1602"]').click()
        cle = cibles.first.get_attribute('data-emplacement')
        cibles.first.click()
        self.page.wait_for_function('c => !!document.querySelector(`[data-carte="${c}"]`)', arg=cle)
        self.assertEqual(len(self.api('/api/es')['modules']), avant + 1)
        self.assertIn('BMX DDO 1602', self.page.locator('#pt-inspecteur .pt-titre').inner_text())
        # Glisser-déposer d'une alimentation sur l'emplacement CPS
        self.page.locator('.cat-item[data-ref="BMX CPS 2010"]').drag_to(self.page.locator('.emplacement.alim[data-emplacement]'))
        self.page.wait_for_function('() => document.querySelector(".emplacement.alim b")?.textContent === "BMX CPS 2010"')

    def test_inspecteur_proprietes_voies_et_controles(self):
        self.ouvrir()
        self.assertIn('Rack', self.page.locator('#pt-inspecteur .pt-titre').inner_text())
        carte = self.page.locator('.rack [data-carte]').first
        carte.click()
        self.assertIn('selection', carte.get_attribute('class'))
        self.assertTrue(self.page.locator('#pt-inspecteur .voies-carte').is_visible())
        self.page.locator('[data-pt-onglet="props"]').click()
        self.assertIn('Référence', self.page.locator('#pt-inspecteur .pt-props').inner_text())
        self.page.locator('.emplacement.cpu[data-emplacement]').first.click()
        self.assertIn('Processeur', self.page.locator('#pt-inspecteur .pt-props').inner_text())
        self.assertEqual(self.page.locator('#modale').is_visible(), False, 'Un clic ne doit pas ouvrir de fenêtre')
        # Refonte, lot 5c : plus d'onglet « Contrôles » dans l'inspecteur ; les contrôles sont au panneau de sortie.
        self.assertEqual(self.page.locator('[data-pt-onglet="controles"]').count(), 0)
        self.page.locator('#o-sortie [data-o-sortie="controles"]').click()
        self.assertTrue(self.page.locator('#o-sortie .parcours-points').is_visible())
        # Filtre du catalogue
        self.page.locator('#pt-cat-q').fill('NOE')
        visibles = [t for t in self.page.locator('.cat-item:visible b').all_text_contents()]
        self.assertTrue(visibles and all('NOE' in t for t in visibles))


class TestPosteDeTravailEquipementsEtES(ServeurNavigateur):
    """16/11, 13 h : catalogue des modèles sur l'écran Équipements ; liste des E/S sur une ligne par E/S."""
    BASE = 80
    setUp = TestRetours1611.setUp
    tearDown = TestRetours1611.tearDown

    def test_ajout_en_deux_temps_modele_puis_libelle(self):
        self.page.goto(self.url + '#/inventaire', wait_until='networkidle')
        self.page.locator('#b-eq').click()
        choix = self.page.locator('.choix-modele')
        choix.first.wait_for()
        self.page.locator('#cm-q').fill('pompage')
        visibles = self.page.locator('.choix-modele:visible')
        self.assertGreaterEqual(visibles.count(), 1)
        self.assertTrue(all('pompage' in (b.get_attribute('data-filtre') or '') for b in visibles.all()))
        item = self.page.locator('.choix-modele:visible[data-eq-type="PM"]').first
        modele = item.get_attribute('data-eq-modele')
        item.click()
        self.page.locator('.cm-choisi').wait_for()
        self.assertFalse(self.page.locator('#q-type').is_visible(), 'Type déjà choisi : liste masquée')
        self.assertEqual(self.page.locator('#q-type').input_value(), 'PM')
        if modele:
            self.assertEqual(self.page.locator('#q-modele').input_value(), modele)
        self.page.wait_for_function('() => /^\\d{2}$/.test(document.querySelector("#q-num").value)')
        self.assertTrue(self.page.locator('#q-lib').evaluate('e => e === document.activeElement'))
        self.page.locator('#q-lib').fill('Pompe essai')
        self.page.locator('#m-ok').click()
        self.page.wait_for_function('() => document.querySelector("#contenu .entete-eq .sous")?.textContent.includes("Pompe essai")')
        # Saisie libre toujours disponible
        self.page.locator('#b-eq').click()
        self.page.locator('#cm-libre').click()
        self.assertTrue(self.page.locator('#q-type').is_visible())
        self.page.locator('#modale [data-fermer]').first.click()

    def test_fiche_une_seule_ligne_d_action_et_menu_des_commandes(self):
        self.api('/api/equipement/ajouter', {'type': 'HV', 'numero': '07', 'se': '00'})
        self.page.goto(self.url + '#/inventaire', wait_until='networkidle')
        self.page.locator('#vue > aside :text("HV07")').first.click()
        self.page.locator('.parcours-eq').wait_for()
        self.assertEqual(self.page.locator('#contenu .avert').count(), 0, 'Plus de bandeaux redondants')
        self.assertEqual(self.page.locator('#contenu .prochaine-action').count(), 1)
        # Refonte, lot 5a : les commandes de l'équipement quittent le menu « ⋯ » pour le ruban de l'écran.
        groupe = self.page.locator('#o-ruban [role="group"][aria-label="Équipement sélectionné"]')
        for s in ('#e-mod', '#e-dep', '#e-sup', '#e-val'):
            self.assertEqual(groupe.locator(s).count(), 1, s)
            self.assertTrue(self.page.locator(s).is_visible(), s)
            self.assertEqual(self.page.locator(s).count(), 1, 'Identifiant unique : ' + s)
        self.assertFalse(self.page.locator('.menu-eq').is_visible(), 'Plus de menu « ⋯ » vide')

    def test_liste_des_es_une_ligne_par_es_sans_debordement(self):
        self.page.goto(self.url + '#/es', wait_until='networkidle')
        lignes = self.page.locator('.es-ligne')
        lignes.first.wait_for()
        defile = "(() => { const s = document.querySelector('.es-scroll'); return s.scrollWidth - s.clientWidth })()"
        self.assertLessEqual(lignes.first.bounding_box()['height'], 46)
        self.assertEqual(self.page.evaluate(defile), 0)
        lignes.nth(1).click()
        self.page.locator('.es-panneau').wait_for()
        self.assertEqual(self.page.evaluate(defile), 0)
        self.page.locator('.pied-etape').wait_for()                # reconstruit à l'image suivante (rendu complet)
        self.assertEqual(self.page.locator('.pied-etape').count(), 1, 'Le pied d\'étape reste après la sélection')
        vue = "(() => { const v = document.querySelector('#vue'); return v.scrollHeight - v.clientHeight })()"
        self.assertEqual(self.page.evaluate(vue), 0)


class TestDemarrageMateriel(ServeurNavigateur):
    """Retour du 16/11 (13 h 40) : sans matériel calculé, l'écran n'affiche qu'un cadre de démarrage."""
    BASE = 90

    def setUp(self):
        type(self).numero += 1
        self.api('/api/nouveau', {'mode': 'Neuf'})
        if not any(x['code'] == 'XTST' for x in self.api('/api/listes-ouvrage')['lieux']):
            self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'lieux', 'code': 'XTST', 'libelle': 'Lieu fictif'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': f'{self.BASE + self.numero:02d}',
            'libelle': 'Démarrage', 'automate': '', 'revision': 'A'}})
        i = self.api('/api/equipement/ajouter', {'type': 'PM', 'numero': '01', 'se': '00'})['ident']
        self.api('/api/equipement/proposition', {'ident_eq': i, 'decision': 'retenir'})
        self.api('/api/equipement/valider', {'idents': [i], 'valide': True})
        pts = self.api('/api/es')['points']
        self.api('/api/es/valider', {'niveau': 'contenu', 'paires': [{'ident_eq': p['ident_eq'], 'cle': p['cle']} for p in pts]})
        self.context = self.browser.new_context(viewport={'width': 1366, 'height': 768})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.erreurs = []
        self.page.on('pageerror', lambda e: self.erreurs.append(str(e)))

    def tearDown(self):
        self.assertEqual(self.erreurs, [])

    def test_cadre_de_demarrage_seul_puis_poste_de_travail(self):
        self.page.goto(self.url + '#/materiel', wait_until='networkidle')
        carte = self.page.locator('.demarrage-materiel')
        carte.wait_for()
        for s in ('#pt-catalogue', '#pt-inspecteur', '#onglets-mat', '.rack', '.v31-page-actions', '#o-ruban'):
            self.assertFalse(self.page.locator(s).first.is_visible(), s)
        self.assertIn('non renseignée', carte.inner_text())
        # Audit du 16/11 : sans source d'acquisition, aucune gamme n'est supposée et le calcul est impossible.
        self.assertTrue(self.page.locator('#m-demarrer').is_disabled())
        self.assertEqual(self.api('/api/definir', {'champ': 'automate', 'valeur': 'Sch - M340'}), {})
        self.page.reload(wait_until='networkidle')
        carte.wait_for()
        self.assertIn('Sch - M340', carte.inner_text())
        self.assertEqual(self.page.locator('[data-cfg="alimentation"]').count(), 1)
        self.assertTrue(carte.locator('[data-cfg="alimentation"]').is_visible())
        carte.locator('[data-cfg="alimentation"]').select_option('BMX CPS 2010')
        self.page.wait_for_function('() => document.querySelector(\'[data-cfg="alimentation"]\')?.value === "BMX CPS 2010"')
        self.page.locator('#m-demarrer').click()
        self.page.locator('#pt-catalogue .cat-item').first.wait_for()
        self.assertEqual(self.page.locator('.demarrage-materiel').count(), 0)
        self.assertTrue(self.page.locator('.rack').first.is_visible())
        self.assertTrue(self.api('/api/es')['modules'])


class TestRetours1611Apres15h(ServeurNavigateur):
    """Retours du 16/11 (15 h 08) : réserve réglable (20 % au moins), processeur M580 double largeur affiché
    comme un seul module, pied d'étape des Variables vers la Recette, exports regroupés dans la Recette."""
    BASE = 10

    def setUp(self):
        type(self).numero += 1
        self.api('/api/nouveau', {'mode': 'Neuf'})
        if not any(x['code'] == 'XTST' for x in self.api('/api/listes-ouvrage')['lieux']):
            self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'lieux', 'code': 'XTST', 'libelle': 'Lieu fictif'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RP', 'numero_ouvrage': f'{self.BASE + self.numero:02d}',
            'libelle': 'Essai M580', 'automate': 'Sch - M580', 'revision': 'A'}})
        ids = []
        for t, n in (('PM', '01'), ('MV', '02')):
            i = self.api('/api/equipement/ajouter', {'type': t, 'numero': n, 'se': '00'})['ident']
            self.api('/api/equipement/proposition', {'ident_eq': i, 'decision': 'retenir'})
            ids.append(i)
        self.api('/api/equipement/valider', {'idents': ids, 'valide': True})
        pts = self.api('/api/es')['points']
        self.api('/api/es/valider', {'niveau': 'contenu', 'paires': [{'ident_eq': p['ident_eq'], 'cle': p['cle']} for p in pts]})
        self.api('/api/materiel/action', {'action': 'config', 'processeur': 'BME P58 2020'})
        self.api('/api/materiel/action', {'action': 'appliquer'})
        self.context = self.browser.new_context(viewport={'width': 1366, 'height': 768})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.erreurs = []
        self.page.on('pageerror', lambda e: self.erreurs.append(str(e)))

    def tearDown(self):
        self.assertEqual(self.erreurs, [])

    def test_processeur_m580_un_seul_module_sur_deux_emplacements(self):
        self.page.goto(self.url + '#/materiel', wait_until='networkidle')
        cpu = self.page.locator('.rack .emplacement.cpu')
        cpu.first.wait_for()
        self.assertEqual(cpu.count(), 1, 'Un processeur M580, pas deux')
        self.assertEqual(cpu.get_attribute('data-double'), '1')
        self.assertEqual(cpu.locator('.pos').inner_text(), '0–1')
        voisin = self.page.locator('.rack .emplacement').nth(2).bounding_box()
        self.assertGreater(cpu.bounding_box()['width'], 1.8 * voisin['width'])

    def test_reserve_reglable_vingt_pour_cent_au_moins(self):
        self.page.goto(self.url + '#/materiel', wait_until='networkidle')
        champ = self.page.locator('#m-reserve')
        champ.wait_for(state='attached')
        if not champ.is_visible():
            self.page.locator('[data-onglet-mat]').first.scroll_into_view_if_needed()
        self.assertEqual(champ.get_attribute('min'), '20')
        champ.fill('15'); champ.dispatch_event('change')
        self.page.locator('.toast.err').first.wait_for()
        self.assertEqual(self.api('/api/materiel')['reserve_min'], 0.2)
        self.page.locator('#m-reserve').fill('30'); self.page.locator('#m-reserve').dispatch_event('change')
        self.page.wait_for_function('() => document.querySelector("#m-reserve")?.value === "30"')
        self.assertEqual(self.api('/api/materiel')['reserve_min'], 0.3)

    def test_variables_menent_a_la_recette(self):
        self.page.goto(self.url + '#/variables', wait_until='networkidle')
        bouton = self.page.locator('.pied-etape button.prim')
        bouton.wait_for()
        self.assertIn('Recette', bouton.inner_text())
        self.page.locator('.v31-variable-row').first.click()           # rendu partiel : le pied reste
        self.page.wait_for_timeout(200)
        self.assertEqual(self.page.locator('.pied-etape').count(), 1)
        bouton.click()
        self.page.wait_for_function("() => location.hash === '#/recette'")

    def test_exports_regroupes_dans_la_recette(self):
        # Retour du 16/11 (16 h 32) : livrables par destination, état et raison, formats non décrits nommés
        self.page.goto(self.url + '#/recette', wait_until='networkidle')
        self.page.locator('.rc-hero').wait_for()
        groupes = self.page.locator('.rc-groupe h2').all_text_contents()
        self.assertEqual(groupes, ['Automate', 'Télégestion SOFREL', 'Supervision / IHM', 'Documents'])
        texte = self.page.locator('.recette-lux').inner_text()
        for attendu in ('Table de télétransmission TOPKAPI', 'IHM Vijeo', 'Liste des entrées / sorties SOFREL',
                        'Nomenclature', 'Aucun poste SOFREL configuré'):
            self.assertIn(attendu, texte)
        vijeo = self.page.locator('.rc-carte', has_text='IHM Vijeo')
        self.assertIn('Non disponible', vijeo.inner_text())
        self.assertEqual(vijeo.locator('button').count(), 0, 'Format non décrit : aucun bouton, jamais simulé')
        quoi = set(self.page.locator('.rc-groupe [data-export]').evaluate_all('b => b.map(x => x.dataset.export)'))
        self.assertTrue({'es_xsy', 'es_txt', 'xsy', 'topkapi', 'es_cartes', 'liste_es', 'tele_etudes', 'nomenclature'} <= quoi)
        # Retour du 18/11 : plus de convention à déclarer, la télétransmission lit l'adresse automate
        topkapi = self.page.locator('[data-export="topkapi"]')
        self.assertNotIn('convention', topkapi.get_attribute('title') or '')
        for code, suffixe in (('es_cartes', '_ES_par_carte.xlsx'), ('tele_etudes', '_teletransmission_etudes.xlsx')):
            with self.page.expect_download() as dl:
                self.page.locator(f'[data-export="{code}"]').click()
            self.assertTrue(dl.value.suggested_filename.endswith(suffixe), code)
        # Dossier complet et actualisation dans l'en-tête, sans barre en double
        # 18/11 : chaque constat porte sa règle nommée (R-…) et la façon de corriger
        self.page.evaluate("document.querySelector('details.rc-controles').open = true")
        codes = self.page.locator('.rc-controles td.rc-regle').all_inner_texts()
        self.assertTrue(codes and all(re.fullmatch(r'R-[A-Z]{2,3}-\d{2}', c.strip()) for c in codes), codes[:5])
        self.assertTrue(self.page.locator('.rc-controles .rc-corriger').count() > 0)
        # Vue « Par règle » par défaut : une ligne par règle, son nombre de constats ; « Voir » ouvre le détail filtré
        groupes = self.api('/api/recette')['par_regle']
        self.assertEqual(sum(g['nombre'] for g in groupes), self.api('/api/recette')['erreurs'] + self.api('/api/recette')['alertes'])
        self.assertEqual(self.page.locator('table.rc-par-regle tbody tr').count(), len(groupes))
        premier = groupes[0]
        self.page.locator(f'table.rc-par-regle [data-rc-regle="{premier["regle"]}"]').click()
        self.page.evaluate("document.querySelector('details.rc-controles').open = true")
        self.assertEqual(self.page.locator('table[data-o-cle="recette-controles"] tbody tr').count(), min(premier['nombre'], 500))
        self.assertEqual(set(self.page.locator('table[data-o-cle="recette-controles"] td.rc-regle').all_inner_texts()), {premier['regle']})
        self.page.locator('[data-rc-vue="regles"]').click()
        regles = self.api('/api/regles')['regles']
        self.assertTrue(all(r['corriger'] for r in regles))
        # Lot 5e : commandes de la livraison au ruban, une seule fois
        self.assertEqual(self.page.locator('#o-ruban [aria-label="Livraison"] #r-dossier').count(), 1)
        self.assertEqual(self.page.locator('#o-ruban [aria-label="Livraison"] #r-actualiser').count(), 1)
        self.assertEqual(self.page.locator('#vue #r-dossier, #vue #r-actualiser').count(), 0)
