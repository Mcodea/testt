"""Recette technique non industrielle de SOREP, avec données fictives.
Aucune donnée de production, aucun automate ni logiciel constructeur n'est contacté.
Usage : py recette_parcours.py
"""
import os, sys, tempfile, time, xml.etree.ElementTree as ET
from pathlib import Path

APP=Path(__file__).resolve().parent
sys.path.insert(0,str(APP))
from genvar.catalogue import Catalogue
from genvar import chemins, existant, projets, import_sources
from genvar.modele import Ouvrage, Equipement, SousEnsemble
from genvar.session import Session, RegleMetier
from genvar.qualification import qualifications
from openpyxl import load_workbook

stats=[]
def test(name,fn):
    start=time.perf_counter()
    try:
        info=fn()
        stats.append((name,'RÉUSSI',round(time.perf_counter()-start,3),info))
    except Exception as exc:
        stats.append((name,'ÉCHEC',round(time.perf_counter()-start,3),f'{type(exc).__name__}: {exc}'))

with tempfile.TemporaryDirectory(prefix='sorep_recette_') as data:
    os.environ['SOREP_DATA_DIR']=data
    cat=Catalogue.charger(chemins.fichier_catalogue_origine())
    root=Path(data)
    new=Ouvrage(mode='Neuf',lieu='F999',code_ouvrage='RV',libelle='Réservoir fictif — test',automate='M580')
    new.sous_ensembles=[SousEnsemble('11','Réservoir')]
    new.equipements=[Equipement('11','MV','01','Vanne',options=['Télécommandée']),Equipement('11','PM','01','Pompe',options=['Variateur']),Equipement('11','LT','01','Niveau')]
    s=Session(cat,new)
    def nouveau():
        vars_=s.variables(); assert len(vars_)>=8, len(vars_)
        propositions,erreurs=s.plan(); assert not erreurs,erreurs
        assert len(propositions)==len(vars_)
        s.appliquer(propositions)
        assert not [a for a in s.anomalies() if a.niveau=='Erreur']
        tr=[v for v in s.variables() if v.famille=='TR']
        rtr=[v for v in s.variables() if v.famille=='RTR']
        assert tr and rtr
        for x in tr:
            same=next((y for y in rtr if y.ident_eq==x.ident_eq and y.code==x.code),None)
            if same: assert int(same.adresse[3:])-4000==int(x.adresse[3:])-100
        return f'{len(vars_)} variables, {len(s.points())} E/S, TR/RTR cohérents'
    test('Neuf : génération + plan mémoire + contrôle',nouveau)
    def enregistrement():
        f=root/'essai.ouvrage.json'; s.enregistrer(str(f)); assert f.exists()
        copie=Session(cat); copie.ouvrir(str(f))
        assert [(v.nom,v.adresse) for v in copie.variables()]==[(v.nom,v.adresse) for v in s.variables()]
        copie.enregistrer();assert Path(str(f)+'.bak').exists()
        assert projets.fiche(f).repere=='F999RV'
        return 'sauvegarde, réouverture, catalogue figé, sauvegarde .bak'
    test('Neuf : enregistrer / rouvrir',enregistrement)
    def exporter():
        px=root/'neuf.xsy'; pe=root/'neuf.xlsx'
        s.exporter_xsy(str(px));s.exporter_excel(str(pe))
        tree=ET.parse(px);elems=tree.findall('.//variables')
        assert len(elems)==len(s.variables()) # E/S sans adresse omises
        wb=load_workbook(pe,read_only=True)
        assert wb.sheetnames
        wb.close()
        return f'{len(elems)} variables XSY XML, Excel lisible'
    test('Neuf : exports XSY et Excel analysables',exporter)
    def extension():
        before={v.nom:v.adresse for v in s.variables()}
        s.ajouter_equipement(Equipement('11','PM','02','Nouvelle pompe',options=['Variateur']))
        propositions,erreurs=s.plan();assert not erreurs
        s.appliquer(propositions)
        after={v.nom:v.adresse for v in s.variables()}
        assert all(after[k]==value for k,value in before.items())
        return f'{len(after)-len(before)} variables ajoutées, {len(before)} adresses préservées'
    test('Neuf : ajout équipement sans décaler',extension)
    def blocage_collision():
        trs=[v for v in s.variables() if v.famille=='TR']
        assert len(trs)>=2
        a,b=trs[0],trs[1]
        try:
            s.definir_adresses(b.ident_eq,b.cle,adresse=a.adresse)
        except RegleMetier:
            assert next(v for v in s.variables() if v.nom==b.nom).adresse==b.adresse
            return 'collision refusée sans altération'
        raise AssertionError('Une collision a été acceptée')
    test('Neuf : collision bloquée et données conservées',blocage_collision)
    exist=Ouvrage(mode='Existant',lieu='F999',code_ouvrage='RV',automate='TSX57',libelle='TSX fictif')
    exist.sous_ensembles=[SousEnsemble('11','Vannes')]
    eq=Equipement('11','MV','03','Vanne existante');exist.equipements=[eq]
    se=Session(cat,exist)
    def import_csv():
        csvf=root/'source.csv'
        csvf.write_text('Nom;Adresse;Type;Commentaire\nTS_RV11MV03_FER;%M120;BOOL;Retour vanne fermée\nTC_RV11MV03_OUV;%M130;BOOL;Commande ouvrir\n',encoding='utf-8')
        h,rows=import_sources.charger_table(str(csvf))
        assert rows and h
        mapping={'nom':0,'adresse':1,'type':2,'commentaire':3}
        lignes,w=import_sources.preparer_lignes(h,rows,mapping)
        assert not w,w
        lus,nouveaux=existant.importer_lignes(exist,lignes)
        assert (lus,nouveaux)==(2,2)
        existant.identifier(exist,cat)
        assert [v.adresse for v in exist.existantes]==['%M120','%M130']
        assert all(qualifications(exist,cat)[id(v)].niveau!='Validée' for v in exist.existantes)
        return '2 variables reprises, adresses préservées, non validées automatiquement'
    test('Existant : CSV → correspondances',import_csv)
    def invalide():
        exist.statut='Validé'
        try: se.enregistrer(str(root/'tsx.ouvrage.json'))
        except RegleMetier:
            return 'statut « Validé » refusé tant que les correspondances sont orange'
        raise AssertionError('Validation automatique acceptée')
    test('Existant : validation métier bloquante',invalide)
    def reimport():
        v=exist.existantes[0]
        original=v.adresse
        v.ident_eq=eq.ident;v.cle='TS_FER';v.identification='Confirmée'
        assert qualifications(exist,cat)[id(v)].niveau=='Validée'
        changements=existant.differences_reimport(exist, [('TS_RV11MV03_FER','BOOL','%M220','Retour vanne fermée')])
        assert changements
        existant.importer_lignes(exist,[('TS_RV11MV03_FER','BOOL','%M220','Retour vanne fermée')])
        assert v.adresse=='%M220' and v.identification!='Confirmée'
        assert qualifications(exist,cat)[id(v)].niveau!='Validée'
        assert original=='%M120'
        return 'écart détecté, adresse source actualisée et confirmation révoquée'
    test('Existant : réimport adresse modifiée',reimport)
    def export_exist():
        p=root/'correspondances.xlsx'
        se.exporter_excel(str(p))
        wb=load_workbook(p,read_only=True);assert wb.sheetnames; wb.close()
        return 'table de correspondance Excel générée'
    test('Existant : export correspondances Excel',export_exist)
    def doublon():
        data_before=[(v.nom,v.adresse) for v in exist.existantes]
        try:
            existant.importer_lignes(exist,[('TS_DUP','BOOL','%M101',''),('TS_DUP','BOOL','%M102','')])
        except ValueError:
            assert [(v.nom,v.adresse) for v in exist.existantes]==data_before
            return 'import contradictoire refusé sans modification'
        raise AssertionError('Doublon contradictoire accepté')
    test('Existant : import contradictoire atomique',doublon)
    def charge():
        o=Ouvrage(mode='Neuf',lieu='F999',code_ouvrage='SP',automate='M580')
        o.sous_ensembles=[SousEnsemble('11','Station')]
        for i in range(1,41):
            o.equipements.extend([Equipement('11','MV',f'{i:02d}',options=['Télécommandée']),Equipement('11','PM',f'{i:02d}',options=['Variateur']),Equipement('11','LT',f'{i:02d}')])
        x=Session(cat,o)
        props,errs=x.plan(); assert not errs,errs[:5]
        x.appliquer(props)
        assert not [a for a in x.anomalies() if a.niveau=='Erreur']
        return f'120 équipements, {len(x.variables())} variables, {len(x.points())} E/S, aucun conflit mémoire'
    test('Charge fictive : plusieurs centaines de variables',charge)

for name,status,duration,detail in stats:
    print(f'[{status}] {name} ({duration:.3f}s) : {detail}')
print(f'BILAN : {sum(s=="RÉUSSI" for _,s,_,_ in stats)}/{len(stats)} parcours réussis')
if any(s!='RÉUSSI' for _,s,_,_ in stats):sys.exit(1)
