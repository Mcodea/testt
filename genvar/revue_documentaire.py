"""Revue d'une documentation PL7 : pistes explicables et JAMAIS validées.

Ce module ne déclare aucune variable acquise par TOPKAPI. Il prépare une liste
révisable de variables rencontrées dans les programmes imprimés. Les chaînes
proviennent seulement d'affectations textuelles reconnues, pas de Ladder/FBD.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import csv
import json
import re
from collections import defaultdict
from types import SimpleNamespace


@dataclass
class LigneRevue:
    adresse: str
    symbole: str
    commentaire: str
    categorie: str
    origine_potentielle: str
    preuves_pages: str
    explication: str
    statut: str = 'À examiner — non validé'
    adresse_acquisition_topkapi: str = ''
    verification_a_realiser: str = 'Vérifier le programme, le protocole et l’accès réel depuis la supervision'


def _entree_physique(adr: str) -> bool:
    return bool(re.match(r'^%I(?:W|F|D)?\d', adr.upper()))


def _sortie_physique(adr: str) -> bool:
    return bool(re.match(r'^%Q(?:W|F|D)?\d', adr.upper()))


def _index_affectations(bilan):
    out = defaultdict(list)
    for a in bilan.affectations_documentaires:
        out[a.destination.upper()].append(a)
    for lien in bilan.liens_il_simples:
        # Dépendance IL strictement textuelle LD/ST, toujours "à examiner".
        out[lien.destination.upper()].append(SimpleNamespace(
            destination=lien.destination.upper(), dependances=[lien.origine.upper()], page=lien.page
        ))
    return out


def _ancetres(adresse: str, index: dict, max_profondeur: int = 8):
    """Origines textuellement documentées, boucles bornées, plusieurs écrivains gardés."""
    entrees = set()
    preuves_pages = set()
    piles = [(adresse.upper(), frozenset({adresse.upper()}), 0)]
    while piles:
        cible, visites, profondeur = piles.pop()
        if profondeur >= max_profondeur:
            continue
        for a in index.get(cible, []):
            preuves_pages.add(int(a.page))
            for origine in a.dependances:
                origine = origine.upper()
                if _entree_physique(origine):
                    entrees.add(origine)
                elif origine not in visites:
                    piles.append((origine, visites | {origine}, profondeur + 1))
    return sorted(entrees), sorted(preuves_pages)


def preparer_revue(bilan) -> list[LigneRevue]:
    """Inventaire de pistes, non tri sur la base d'une vérité de référence.

    Les commentaires XBT/afficheur sont des indices de dialogue local ; ils ne
    suffisent pas à conclure à une zone d'échange TOPKAPI.
    """
    symboles = defaultdict(list)
    for indice in bilan.indices_symboles:
        symboles[indice.adresse.upper()].append(indice)
    occurrences = defaultdict(list)
    for occ in bilan.occurrences:
        occurrences[occ.adresse.upper()].append(occ)
    index = _index_affectations(bilan)
    adresses = sorted(set(occurrences) | set(index) | set(symboles))
    lignes = []
    for adr in adresses:
        assoc = symboles.get(adr, [])
        # Si une même adresse a plusieurs symboles différents dans le PDF,
        # ne pas masquer ce conflit derrière le premier trouvé.
        etiquettes = sorted(set(i.symbole for i in assoc if i.symbole))
        descriptions = sorted(set(i.commentaire for i in assoc if i.commentaire))
        symbole = ' | '.join(etiquettes)
        commentaire = ' | '.join(descriptions)
        origine, pages_affect = _ancetres(adr, index)
        pages = sorted(set(o.page for o in occurrences.get(adr, [])) | {i.page for i in assoc} | set(pages_affect))
        evidence = []
        if etiquettes:
            evidence.append('symbole relevé dans un tableau PDF')
        if index.get(adr):
            evidence.append(f'{len(index[adr])} relation(s) syntaxique(s) OPERATE ou IL documentée(s)')
        if origine:
            evidence.append('dépendance(s) syntaxique(s) vers E/S documentée(s)')
        if len(etiquettes) > 1:
            evidence.append('plusieurs symboles : ambiguïté à examiner')
        if len(index.get(adr, [])) > 1:
            evidence.append('plusieurs écritures : conditions d’exécution à vérifier')
        if not evidence:
            evidence.append('adresse mentionnée, fonction non établie')
        hmi = bool(re.search(r'(?:^|[^A-Za-z0-9])(?:XBT|IHM|PUPITRE|AFFICH(?:AGE|EUR)|HMI)(?=$|[^A-Za-z0-9])', f'{symbole} {commentaire}', re.I))
        if _entree_physique(adr):
            categorie = 'Entrée physique documentée'
        elif _sortie_physique(adr):
            categorie = 'Sortie physique documentée'
        elif hmi:
            categorie = 'Lien éventuel avec un pupitre/IHM (pas une preuve TOPKAPI)'
        elif origine:
            categorie = 'Valeur issue d’E/S selon affectations textuelles'
        elif index.get(adr):
            categorie = 'Variable écrite selon le code imprimé (rôle à qualifier)'
        else:
            categorie = 'Autre adresse — rôle non déterminé'
        # Priorités de revue, AUCUNE catégorie ne signifie "à superviser".
        lignes.append(LigneRevue(
            adresse=adr, symbole=symbole, commentaire=commentaire,
            categorie=categorie,
            origine_potentielle=' | '.join(origine),
            preuves_pages=' | '.join(map(str,pages)),
            explication=' ; '.join(evidence),
        ))
    return lignes


def _cellule_csv_texte(valeur):
    """Empêche Excel d'interpréter comme formule un commentaire issu d'un PDF.

    La version JSON conserve les valeurs originales pour permettre les audits.
    """
    valeur = str(valeur)
    return "'" + valeur if valeur.lstrip().startswith(('=', '+', '-', '@')) else valeur


def enregistrer_revue(bilan, dossier: str | Path):
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    lignes = preparer_revue(bilan)
    champs = list(LigneRevue.__dataclass_fields__)
    with (dossier / 'revue_variables_pdf.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=champs, delimiter=';')
        writer.writeheader()
        writer.writerows({k: _cellule_csv_texte(v) for k, v in asdict(x).items()} for x in lignes)
    (dossier / 'revue_variables_pdf.json').write_text(
        json.dumps([asdict(x) for x in lignes], ensure_ascii=False, indent=2), encoding='utf8'
    )
    return lignes
