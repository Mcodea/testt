"""Crée un document de contrôle entièrement FICTIF, non issu d'un ouvrage réel."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

out=Path(__file__).resolve().parent/'EXEMPLE_FICTIF_PL7.pdf'
c=canvas.Canvas(str(out),pagesize=A4)
W,H=A4

def page(titre, lines):
    c.setFont('Helvetica-Bold',16)
    c.drawString(48,H-70,titre)
    c.line(48,H-78,W-48,H-78)
    c.setFont('Courier',10)
    for k,line in enumerate(lines):
        c.drawString(52,H-110-19*k,line)
    c.setFont('Helvetica',8)
    c.drawString(48,40,'SOREP - EXEMPLE FICTIF - AUCUNE INSTALLATION REELLE')
    c.showPage()

page('SOMMAIRE', ['Application : EXEMPLE FICTIF PL7 / TSX', 'Programme .... 2', 'References croisees .... 3', 'Variables .... 4'])
page('PROGRAMME MAST-POST', ['(* Illustration de variables dans le programme *)',
      'LD  %I0.3.2', 'ST  %M120', 'LD  %M120', 'ST  %MW1200:X3',
      'REMARQUE : une liste imprimée ne demontre pas toujours une causalite'])
page('REFERENCES CROISEES', ['ADRESSE          SYMBOLE             SECTION       USAGE',
      '%I0.3.2          FC_V3_FER           MAST-PRL         R',
      '%M120            V3_FER              MAST-POST        W',
      '%MW1200:X3       TS_V3_FER           MAST-POST        W'])
page('VARIABLES', ['ADRESSE          SYMBOLE           COMMENTAIRE',
      '%I0.3.2          FC_V3_FER         Fin de course ferme',
      '%M120            V3_FER            Etat interieur',
      '%MW1200:X3       TS_V3_FER         Bit accessible dans un mot',
      '%MW100           A                 Reserve 1',
      '%MW101           B                 Reserve 2',
      '%MW102           C                 Reserve 3'])
c.save()
print(out)
