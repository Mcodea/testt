"""Analyse hors production d'un dossier PDF d'application PLC.

Usage : py analyser_dossier_pl7.py C:\\Dossiers\\Habilis.pdf --sortie C:\\Dossiers\\Rapport
"""
import argparse
from pathlib import Path
from genvar.analyse_pdf_pl7 import analyser_pdf


def main():
    parser=argparse.ArgumentParser(description='SOREP - diagnostic de dossier PDF PL7')
    parser.add_argument('pdf',type=Path,help='PDF documentaire fourni par l’utilisateur')
    parser.add_argument('--sortie',type=Path,default=Path('Rapport_PDF_PL7'))
    parser.add_argument('--cible', help='Adresse dont on veut remonter les dépendances OPERATE (ex: %MW5)')
    args=parser.parse_args()
    bilan=analyser_pdf(args.pdf)
    bilan.enregistrer(args.sortie)
    print(bilan.resume())
    if args.cible:
        import json
        from genvar.analyse_pdf_pl7 import tracer_origines
        traces = tracer_origines(bilan, args.cible)
        (args.sortie/'traces_cible.json').write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding='utf8')
        print(f'\nDépendances syntaxiques de {args.cible}: {len(traces)} chemins (voir traces_cible.json)')
    print(f'\nRapport enregistré dans {args.sortie.resolve()}')


if __name__=='__main__': main()
