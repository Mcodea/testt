"""Recette reproductible du Générateur SOREP, sans données réelles ni équipement.

Exécuter : py verifier_sorep.py --qt-obligatoire
Sans --qt-obligatoire, les tests métier tournent et l'absence de Qt reste signalée.
"""
from __future__ import annotations
import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent


def executer(titre, commande):
    print('\n' + '=' * 70)
    print(titre)
    print('=' * 70, flush=True)
    code = subprocess.call(commande, cwd=RACINE)
    print(f'[{"OK" if code == 0 else "ÉCHEC"}] {titre}', flush=True)
    return code


def main():
    parser = argparse.ArgumentParser(description='Tests et recette SOREP')
    parser.add_argument('--qt-obligatoire', action='store_true',
                        help='Exiger la présence de PySide6 pour une recette complète')
    args = parser.parse_args()
    print('SOREP — vérification sur une copie fictive, sans communication automate')
    print(f'Python : {sys.version.split()[0]} ; Projet : {RACINE}')
    if executer('Tests du moteur (unittest)',
                [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']):
        return 1
    if executer('Parcours fonctionnels fictifs (neuf et existant)',
                [sys.executable, str(RACINE / 'recette_parcours.py')]):
        return 1
    if executer('Comparaison reproductible des stratégies d’identification',
                [sys.executable, str(RACINE / 'comparer_les_methodes.py')]):
        return 1
    executer('Évaluation à l’aveugle du rapprochement (informative, corrigé séparé)',
             [sys.executable, str(RACINE / 'validation' / 'aveugle' / 'evaluer.py')])
    if not importlib.util.find_spec('PySide6'):
        print('\n[NON TESTÉ] Interface PySide6 absente : les tests Qt NE SONT PAS validés.')
        print('Installation Windows : py -m pip install -r requirements-qt.txt')
        return 2 if args.qt_obligatoire else 0
    if executer('Tests de l’interface PySide6 (Qt offscreen)',
                [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests_qt', '-v']):
        return 1
    print('\nTests automatisés terminés. La recette visuelle et les logiciels industriels'
          '\n(Control Expert, PL7, S4W-Tools, TOPKAPI) restent à valider sur leurs environnements.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
