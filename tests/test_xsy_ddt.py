"""Recette DDT. Fixtures de test reconstruites, sans présumer de la compatibilité des adresses OPC/Modbus."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from genvar import existant, xsy_ddt
from genvar.modele import Ouvrage, Equipement
from genvar.catalogue import Catalogue
from genvar.qualification import qualifications
from genvar import chemins

FIXTURE = Path(__file__).resolve().parents[1] / 'validation' / 'ddt' / 'exemple_DDT_reconstitue.xsy'


class TestsDDT(unittest.TestCase):
    def test_lit_parents_et_champs_reels_sans_addresse_calculee(self):
        a = xsy_ddt.analyser_xsy(FIXTURE)
        self.assertEqual(len(a.parents), 3)
        self.assertEqual(a.definitions_ddt, 4)
        self.assertEqual(len(a.champs), 7)
        self.assertFalse(a.avertissements, a.avertissements)
        v = a.index['IO_BALLUFF_A1_F0.IN.I_VERIN_1_BRIDAGE_AVANCE']
        self.assertEqual((v.type_logique, v.extract_bit), ('BOOL', '0'))
        self.assertEqual(v.parent, 'IO_BALLUFF_A1_F0')
        self.assertEqual(v.adresse_parent, '%MW500')
        self.assertEqual(v.adresse, '')
        self.assertEqual(v.commentaire, 'Vérin 1 en position avancée')
        self.assertEqual(a.index['TM_TEST'].adresse, '%MW2000')

    def test_ancien_lecteur_reste_compatible(self):
        self.assertEqual(len(existant.lire_xsy(FIXTURE)), 3)

    def test_import_et_sauvegarde_des_metadonnees(self):
        a = existant.lire_xsy_detaille(FIXTURE)
        o = Ouvrage(mode='Existant')
        nb, nouveaux = existant.importer_xsy_detaille(o, a)
        self.assertEqual((nb, nouveaux), (10, 10))
        v = next(v for v in o.existantes if v.nom.endswith('I_VERIN_1_BRIDAGE_AVANCE'))
        self.assertEqual(v.adresse, '')
        self.assertFalse(v.retenue)
        self.assertEqual(v.nature_source, 'Champ DDT')
        self.assertEqual(v.extract_bit, '0')
        self.assertEqual(v.empreinte_source_xsy, a.sha256)
        with TemporaryDirectory() as d:
            path = str(Path(d) / 'test.ouvrage.json')
            o.enregistrer(path)
            relue = Ouvrage.ouvrir(path)
            vc = next(x for x in relue.existantes if x.nom == v.nom)
            self.assertEqual((vc.parent_xsy, vc.adresse_parent_xsy, vc.chemin_symbolique),
                             ('IO_BALLUFF_A1_F0', '%MW500', v.nom))

    def test_selection_ddt_n_est_pas_validation_de_l_adresse(self):
        o = Ouvrage(mode='Existant')
        existant.importer_xsy_detaille(o, existant.lire_xsy_detaille(FIXTURE))
        v = next(v for v in o.existantes if v.nom.endswith('I_VERIN_1_BRIDAGE_AVANCE'))
        o.equipements.append(Equipement('11','MV','03',ident='eq1'))
        v.retenue = True; v.ident_eq='eq1'; v.cle='TS_OUV'; v.identification='Confirmée'
        cat = Catalogue.charger(chemins.fichier_catalogue_origine())
        self.assertEqual(qualifications(o, cat)[id(v)].niveau, 'À confirmer')

    def test_validation_ddt_requiert_mapping_et_confirmation_documentaire(self):
        o = Ouvrage(mode='Existant')
        existant.importer_xsy_detaille(o, existant.lire_xsy_detaille(FIXTURE))
        v = next(v for v in o.existantes if v.nom.endswith('I_VERIN_1_BRIDAGE_AVANCE'))
        o.equipements.append(Equipement('11', 'MV', '03', ident='eq1'))
        v.retenue = True
        v.ident_eq = 'eq1'
        v.cle = 'TS_OUV'
        v.identification = 'Confirmée'
        cat = Catalogue.charger(chemins.fichier_catalogue_origine())
        self.assertEqual(qualifications(o,cat)[id(v)].niveau, 'À confirmer')
        v.adresse_acquisition = 'IO_BALLUFF_A1_F0.IN.I_VERIN_1_BRIDAGE_AVANCE'
        v.protocole_acquisition = 'OPC / OFS'
        self.assertEqual(qualifications(o,cat)[id(v)].niveau, 'À confirmer')
        v.acces_verifie = True
        self.assertEqual(qualifications(o,cat)[id(v)].niveau, 'Validée')
        self.assertEqual(v.adresse, '')  # Aucune adresse %MW inventée

    def test_reimport_changement_adresse_parent_invalide_validation(self):
        a = existant.lire_xsy_detaille(FIXTURE)
        o = Ouvrage(mode='Existant', statut='Validé')
        existant.importer_xsy_detaille(o, a)
        v = next(v for v in o.existantes if v.nom.endswith('I_VERIN_1_BRIDAGE_AVANCE'))
        v.identification = 'Confirmée'
        v.adresse_acquisition = 'TAG_OPC_CONFIRME'
        v.protocole_acquisition = 'OPC / OFS'
        v.acces_verifie = True
        o.statut = 'Validé'
        with TemporaryDirectory() as d:
            p = Path(d) / 'modifie.xsy'
            p.write_text(FIXTURE.read_text().replace('%MW500', '%MW900'), encoding='utf-8')
            analyse = existant.lire_xsy_detaille(p)
            diffs = existant.differences_xsy_detaille(o, analyse)
            self.assertTrue(any(x[0]==v.nom and x[1]=='Adresse du parent DDT' for x in diffs))
            existant.importer_xsy_detaille(o, analyse)
        self.assertEqual(v.identification, 'À identifier')
        self.assertEqual(o.statut, 'À contrôler')
        self.assertEqual(v.adresse_parent_xsy, '%MW900')
        self.assertEqual(v.adresse, '')
        self.assertEqual(v.adresse_acquisition, 'TAG_OPC_CONFIRME')
        self.assertFalse(v.acces_verifie)

    def test_doublon_chemin_refuse_sans_mutation(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'dup.xsy'
            p.write_text(FIXTURE.read_text().replace('<variables name="TM_TEST"', '<variables name="CELL_CMD"'),encoding='utf-8')
            a = existant.lire_xsy_detaille(p)
            o=Ouvrage(mode='Existant')
            with self.assertRaisesRegex(ValueError, 'conflit|doublon'):
                existant.importer_xsy_detaille(o,a)
            self.assertEqual(o.existantes, [])

    def test_ddt_cyclique_est_signale(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'cycle.xsy'
            p.write_text('''<VariablesExchangeFile><dataBlock><variables name="A" typeName="BOUCLE"/></dataBlock>
                <DDTSource DDTName="BOUCLE"><structure><variables name="S" typeName="BOUCLE"/></structure></DDTSource>
                </VariablesExchangeFile>''')
            a = xsy_ddt.analyser_xsy(p)
            self.assertFalse(a.complet)
            self.assertTrue(any('récursif' in m for m in a.avertissements))

    def test_type_inconnu_signale_et_conserve_sans_adresse(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'opaque.xsy'
            p.write_text('''<VariablesExchangeFile><dataBlock><variables name="A" typeName="DDT_A" topologicalAddress="%MW1"/></dataBlock>
                <DDTSource DDTName="DDT_A"><structure><variables name="TAB" typeName="ARRAY[0..3] OF WORD"/></structure></DDTSource>
                </VariablesExchangeFile>''')
            a = xsy_ddt.analyser_xsy(p)
            self.assertFalse(a.complet)
            self.assertEqual(a.champs[0].adresse, '')
            self.assertEqual(a.champs[0].type_logique, 'ARRAY[0..3] OF WORD')

    def test_export_excel_conserve_origine_et_parent(self):
        from genvar import chemins
        o = Ouvrage(mode='Existant')
        existant.importer_xsy_detaille(o, existant.lire_xsy_detaille(FIXTURE))
        cat = Catalogue.charger(chemins.fichier_catalogue_origine())
        with TemporaryDirectory() as d:
            cible = str(Path(d) / 'correspondances.xlsx')
            existant.exporter_correspondance(cible, o, cat)
            from openpyxl import load_workbook
            wb = load_workbook(cible, read_only=True, data_only=True)
            try:
                ws = wb['Correspondance']
                hdr = [c.value for c in next(ws.rows)]
                i = hdr.index('Parent DDT')
                self.assertIn('Adresse parent (non transposable)', hdr)
                rows = list(ws.iter_rows(min_row=2, values_only=True))
                self.assertTrue(any(r[i]=='IO_BALLUFF_A1_F0' for r in rows))
            finally:
                wb.close()

    def test_assistant_hybride_recherche_un_champ_ddt_sans_inventer_adresse(self):
        from genvar import rapprochement
        xml = """<VariablesExchangeFile><dataBlock>
            <variables name="STRUCT_V3" typeName="DDT_V3" topologicalAddress="%MW100"/>
            </dataBlock><DDTSource DDTName="DDT_V3"><structure>
            <variables name="V3_FER" typeName="BOOL"><comment>Vanne V3 fermée</comment></variables>
            </structure></DDTSource></VariablesExchangeFile>"""
        with TemporaryDirectory() as d:
            f = Path(d)/'test.xsy'
            f.write_text(xml, encoding='utf-8')
            o = Ouvrage(mode='Existant', code_ouvrage='RV')
            eq = Equipement('11','MV','03')
            o.equipements.append(eq)
            existant.importer_xsy_detaille(o, existant.lire_xsy_detaille(f))
            catalogue = Catalogue.charger(chemins.fichier_catalogue_origine())
            propositions = rapprochement.proposer(o, catalogue, 'hybride')
            candidats = propositions.get((eq.ident, 'TS_FER'), [])
            self.assertTrue(any(p.variable_nom == 'STRUCT_V3.V3_FER' for p in candidats))
            v = next(v for v in o.existantes if v.nom == 'STRUCT_V3.V3_FER')
            self.assertEqual(v.adresse, '')
            self.assertFalse(v.retenue)

    def test_xml_dtd_refuse(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'doctype.xsy'
            p.write_text('<!DOCTYPE a [<!ENTITY x "foo">]><VariablesExchangeFile/>')
            with self.assertRaisesRegex(ValueError, 'DTD'):
                xsy_ddt.analyser_xsy(p)

if __name__ == '__main__':
    unittest.main()
