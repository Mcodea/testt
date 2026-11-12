"""Essai facultatif : récupérer le dossier public HABILIS puis analyser le PDF.
Ne transmet aucune donnée projet. Connexion sortante limitée à l'URL publique ci-dessous.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from genvar.analyse_pdf_pl7 import analyser_pdf

URL = 'https://www.lycee-desfontaines.eu/si/sequences-ts/performance-energetique/res/dossier-technique-habilis.pdf'
SORTIE = Path(__file__).resolve().parent / 'validation' / 'pdf_pl7' / 'HABILIS_TELECHARGE'
MAX_TAILLE = 40_000_000


def telecharger():
    SORTIE.mkdir(parents=True, exist_ok=True)
    chemin = SORTIE / 'dossier-technique-habilis.pdf'
    if chemin.is_file() and chemin.read_bytes()[:4] == b'%PDF':
        print('Fichier local déjà présent :', chemin)
        return chemin
    print('Tentative de téléchargement du PDF public HABILIS...')
    requete=Request(URL,headers={'User-Agent':'Mozilla/5.0 (compatible; SOREP/PDF-reference-test)'})
    avec = 0
    contenu = bytearray()
    with urlopen(requete,timeout=45) as r:
        while True:
            bloc=r.read(65536)
            if not bloc: break
            avec += len(bloc)
            if avec>MAX_TAILLE:
                raise RuntimeError('Dossier trop volumineux (limite 40 Mo).')
            contenu.extend(bloc)
    if not contenu.startswith(b'%PDF'):
        raise RuntimeError('Le site n’a pas renvoyé un PDF valide (page HTML ou blocage réseau).')
    chemin.write_bytes(contenu)
    return chemin


def main():
    try:
        chemin=telecharger()
        bilan=analyser_pdf(chemin)
        bilan.enregistrer(SORTIE/'RAPPORT')
        print(bilan.resume())
        print('\nRapport :',SORTIE/'RAPPORT')
    except Exception as e:
        print('Essai indisponible :',e)
        print('Alternative : récupérer manuellement le dossier HABILIS, puis lancer :')
        print('  py analyser_dossier_pl7.py "chemin-vers-le-fichier.pdf"')
        raise SystemExit(1)

if __name__=='__main__':main()
