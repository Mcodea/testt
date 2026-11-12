import tempfile
import unittest
from pathlib import Path
from genvar import import_sources, existant
from genvar.modele import Ouvrage


class ImportSourcesTests(unittest.TestCase):
    def test_scy_textuel_pl7(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'table.scy'
            p.write_bytes('Adresse;Symbole;Commentaire\n%M120;V3_FER;Vanne fermée\n%MW200;PRES;Pression aval\n'.encode('cp1252'))
            h,r=import_sources.charger_table(p)
            data,warnings=import_sources.preparer_lignes(h,r,import_sources._colonnes(h))
            self.assertEqual(data[0],('V3_FER','','%M120','Vanne fermée'))
            self.assertEqual(len(data),2)

    def test_scy_sans_entete(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'table.scy'
            p.write_text('%M120;V3_FER;Retour fermé\n%M121;V3_OUV;Retour ouvert\n')
            h,r=import_sources.charger_table(p)
            data,_=import_sources.preparer_lignes(h,r,import_sources._colonnes(h))
            self.assertEqual(len(data),2)

    def test_scy_inconnu_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'table.scy';p.write_bytes(b'\x00\x01\x02')
            with self.assertRaises(ValueError): import_sources.charger_table(p)

    def test_csv_garder_adresse_et_commentaire(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'table.csv';p.write_text('variable;address;datatype;description\nTS_A;%M15;BOOL;Etat\n',encoding='utf-8')
            h,r=import_sources.charger_table(p)
            donnees,_=import_sources.preparer_lignes(h,r,import_sources._colonnes(h))
            self.assertEqual(donnees,[('TS_A','BOOL','%M15','Etat')])

    def test_xlsx(self):
        from openpyxl import Workbook
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'table.xlsx';w=Workbook();w.active.append(['Nom','Adresse','Type','Commentaire']);w.active.append(['P01','%MW100','INT','Compteur']);w.save(p)
            h,r=import_sources.charger_table(p)
            donnees,_=import_sources.preparer_lignes(h,r,import_sources._colonnes(h))
            self.assertEqual(donnees[0][2],'%MW100')

    def test_reimport_preserve_confirmation(self):
        o=Ouvrage(mode='Existant')
        existant.importer_lignes(o,[('V3_FER','BOOL','%M120','Ancien')])
        o.existantes[0].identification='Confirmée';o.existantes[0].cle='TS_FER'
        existant.importer_lignes(o,[('V3_FER','BOOL','%XT25','Nouveau')])
        self.assertEqual(o.existantes[0].identification,'À identifier')
        self.assertEqual(o.existantes[0].cle,'TS_FER')
        self.assertIn('nouvelle validation', o.existantes[0].remarque)
        self.assertEqual(o.existantes[0].adresse,'%XT25')

    def test_doublon_contradictoire_bloque(self):
        h=['Nom','Adresse'];rows=[['A','%M1'],['A','%M2']]
        with self.assertRaisesRegex(ValueError, 'conflit'):
            import_sources.preparer_lignes(h, rows, import_sources._colonnes(h))

if __name__=='__main__': unittest.main()
