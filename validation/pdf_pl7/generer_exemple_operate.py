"""Fabrique un dossier PL7 fictif pour vérifier des parsings, pas un programme réel."""
from pathlib import Path
import fitz
base = Path(__file__).resolve().parent
out = base/'EXEMPLE_FICTIF_OPERATE_PL7.pdf'
doc=fitz.open()
for lines in [
    ['SOMMAIRE','4 Programme........................................5p','5 Références croisées.............................2p','6 Variables.........................................2p'],
    ['MAST-PRL','OPERATE','%MW10:=%IW0.2/10','Liste de Variables utilisées dans le rung :','REPERE','SYMBOLE','COMMENTAIRE','%IW0.2','Pt_100','Sonde fictive','Folio : 4.2.1 - 1'],
    ['MAST-POST','OPERATE','%MW11:=%MW10*100','OPERATE','%MW11:=%MW10*100','Folio : 4.2.3 - 1'],
    ['REFERENCES CROISEES','%IW0.2 MAST-PRL R','%MW10 MAST-POST R','%MW11 MAST-POST W','Folio : 5 - 1'],
    ['VARIABLES','%IW0.2 Pt_100 Mesure entrante','%MW10 TEMP_C Valeur calculee','%MW11 TEMP_X100 Mise a echelle','Folio : 6 - 1'],
]:
    page=doc.new_page()
    for j,line in enumerate(lines):
        page.insert_text((45,50+21*j),line,fontsize=10)
doc.save(out)
doc.close()
print(out)
