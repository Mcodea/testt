"""Recette indépendante de l'interface pour un XSY réel Control Expert.

Peut analyser un fichier téléchargé manuellement, ou tenter le téléchargement du
fichier public de tonycab. Aucun projet existant de l'utilisateur n'est modifié.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from genvar import existant
from genvar.modele import Ouvrage

URL = 'https://raw.githubusercontent.com/tonycab/XSY_To_CSV_XML/main/InputFile.XSY'


def main():
    ap = argparse.ArgumentParser(description='Tester le XSY public ou tout XSY fourni en lecture seule.')
    ap.add_argument('fichier', nargs='?', help='Chemin vers un XSY téléchargé (sinon, essai de téléchargement public)')
    ap.add_argument('--sortie', help='Répertoire du rapport (par défaut sous validation/ddt/resultats)')
    args = ap.parse_args()
    output = Path(args.sortie) if args.sortie else Path(__file__).parent / 'resultats'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        if args.fichier:
            p = Path(args.fichier)
        else:
            local = Path(__file__).parent / 'InputFile.XSY'
            if local.exists():
                p = local
            else:
                p = Path(tmp) / 'InputFile.XSY'
                try:
                    with urllib.request.urlopen(urllib.request.Request(
                        URL, headers={'User-Agent': 'SOREP-DDT-Test/1.0'}), timeout=20) as rep:
                        data = rep.read(15 * 1024 * 1024 + 1)
                    p.write_bytes(data)
                except Exception as exc:
                    raise SystemExit('Téléchargement impossible. Enregistrer le fichier InputFile.XSY '
                         f'à côté de ce script puis relancer. Détail : {exc}')
        analyse = existant.lire_xsy_detaille(p)
        o = Ouvrage(mode='Existant', automate='M580')
        effectifs = existant.importer_xsy_detaille(o, analyse)
        assert effectifs[0] == len(analyse.parents) + len(analyse.champs)
        assert all(x.adresse == '' for x in o.existantes if x.nature_source == 'Champ DDT')
        with tempfile.TemporaryDirectory() as d:
            sauvegarde = str(Path(d) / 'essai.ouvrage.json')
            o.enregistrer(sauvegarde)
            v = Ouvrage.ouvrir(sauvegarde)
            assert len(v.existantes) == len(o.existantes)
            assert all(x.adresse == '' for x in v.existantes if x.nature_source == 'Champ DDT')
        with (output/'champs_ddt.csv').open('w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f, delimiter=';')
            w.writerow(['Chemin symbolique','Type','Commentaire','Parent','Adresse parent (indicative)', 'ExtractBit','Adresse champ'])
            for x in analyse.champs:
                w.writerow([x.nom,x.type_logique,x.commentaire,x.parent,x.adresse_parent,x.extract_bit,x.adresse])
        report = {
            'fichier_analysé':p.name,
            'sha256_source':analyse.sha256,
            'variables_principales':len(analyse.parents),
            'ddt_definis':analyse.definitions_ddt,
            'champs_ddt_developpes':len(analyse.champs),
            'lignes_importees_ouvrages_test':effectifs[0],
            'lignes_nouvelles':effectifs[1],
            'champs_ddt_avec_adresse_calculee':sum(bool(x.adresse) for x in analyse.champs),
            'exhaustivite_developpement_ddt': 'complète selon le lecteur' if analyse.complet else 'INCOMPLÈTE / À ANALYSER',
            'avertissements':analyse.avertissements,
            'limites':[
                'Une adresse %MW d’un DDT parent ne donne pas automatiquement une adresse Modbus de ses champs.',
                'ExtractBit est conservé mais ne fournit pas à lui seul un offset valide.',
                'L’existence d’un chemin symbolique ne garantit pas son exposition via OPC/OFS.',
                'Aucune correspondance métier TOPKAPI ni compatibilité industrielle validée.',
            ],
        }
        (output/'rapport_lecture_xsy.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Fichier:',p.name)
        print('SHA256:',analyse.sha256)
        print('Principales:',len(analyse.parents),' | DDT:',analyse.definitions_ddt,
              ' | Champs développés:',len(analyse.champs))
        print('Avertissements:',len(analyse.avertissements))
        print('Rapport:',output/'rapport_lecture_xsy.json')
        if analyse.avertissements:
            print('Attention : données partiellement développées. Voir le rapport.')


if __name__ == '__main__':
    main()
