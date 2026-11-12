"""Qualification prudente des correspondances issues d'un automate existant.

Un nom reconnu automatiquement n'est jamais synonyme de validation métier.
Les anomalies sont calculées à partir de l'état réel du référentiel, sans modifier
les variables ni les adresses importées.
"""
import re
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class Qualification:
    niveau: str  # Validée, À confirmer, Incohérence, Hors supervision
    motif: str


def qualifications(ouvrage, catalogue):
    """Retourne des qualifications par identité d'objet (id(v))."""
    cles = Counter((v.ident_eq, v.cle) for v in ouvrage.existantes
                   if v.retenue and v.ident_eq and v.cle)
    resultat = {}
    for v in ouvrage.existantes:
        if not v.retenue:
            resultat[id(v)] = Qualification('Hors supervision', 'Variable explicitement exclue de la supervision.')
            continue
        motifs = []
        if v.ident_eq and v.cle and cles[(v.ident_eq, v.cle)] > 1:
            motifs.append('Plusieurs variables sont rattachées au même signal de cet équipement.')
        eq = ouvrage.equipement(v.ident_eq) if v.ident_eq else None
        if v.ident_eq and not eq:
            motifs.append('Équipement associé introuvable.')
        if eq and v.cle:
            signaux = [s for s in catalogue.signaux_du_type(eq.type, avec_ecartes=True)
                       if f"{s['famille']}_{s['code']}" == v.cle]
            if not signaux:
                motifs.append('Signal absent du catalogue de cet équipement.')
            else:
                attendu = (signaux[0].get('type_logique') or '').upper()
                reel = (v.type_logique or '').upper()
                bools = {'BOOL', 'EBOOL'}
                if attendu and reel and not (attendu == reel or {attendu, reel} <= bools):
                    # REAL/INT, INT/DINT, signé/non signé : aucune conversion
                    # automatique n'est garantie par une correspondance de noms.
                    motifs.append(f'Types incompatibles sans conversion définie : automate {reel} / catalogue {attendu}.')
        if motifs:
            resultat[id(v)] = Qualification('Incohérence', ' '.join(motifs))
        elif not v.ident_eq or not v.cle:
            resultat[id(v)] = Qualification('À confirmer', 'Fonction ou équipement non identifié.')
        elif v.nature_source == 'Champ DDT' and not v.adresse_acquisition:
            resultat[id(v)] = Qualification('À confirmer',
                'Champ DDT : adresse/tag d’acquisition non établi ; adresse parent non transposable.')
        elif v.nature_source == 'Champ DDT' and not v.protocole_acquisition:
            resultat[id(v)] = Qualification('À confirmer',
                'Champ DDT : protocole d’acquisition non renseigné.')
        elif v.nature_source == 'Champ DDT' and not v.acces_verifie:
            resultat[id(v)] = Qualification('À confirmer',
                'Champ DDT : le mapping d’acquisition n’a pas été vérifié manuellement.')
        elif v.nature_source == 'Champ DDT' and not (v.type_logique or '').strip():
            resultat[id(v)] = Qualification('À confirmer', 'Type de donnée du champ DDT absent.')
        elif v.nature_source == 'Champ DDT' and v.identification == 'Confirmée':
            resultat[id(v)] = Qualification('Validée',
                'Correspondance métier confirmée et accès documenté ; communication réelle non testée.')
        elif v.nature_source == 'Champ DDT':
            resultat[id(v)] = Qualification('À confirmer', 'Correspondance DDT non confirmée par l’automaticien.')
        elif not v.adresse:
            resultat[id(v)] = Qualification('À confirmer', 'Adresse source absente : accessibilité non démontrée.')
        elif re.match(r'^%(?:I|Q)(?:W|D|F|X)?\d', v.adresse, re.I):
            resultat[id(v)] = Qualification('À confirmer',
                "Adresse E/S physique : accessibilité directe depuis TOPKAPI non démontrée.")
        elif not (v.type_logique or '').strip():
            resultat[id(v)] = Qualification('À confirmer', 'Type de donnée source absent : compatibilité non vérifiable.')
        elif not v.adresse.strip().startswith('%'):
            resultat[id(v)] = Qualification('À confirmer',
                'Source symbolique / OPC : accès effectif et méthode de communication à vérifier.')
        elif v.identification == 'Confirmée':
            resultat[id(v)] = Qualification('Validée', 'Correspondance vérifiée manuellement ; accès TOPKAPI à tester séparément.')
        else:
            resultat[id(v)] = Qualification('À confirmer', 'Correspondance automatique non confirmée par un automaticien.')
    return resultat


def bilan_qualification(ouvrage, catalogue):
    from collections import Counter
    return dict(Counter(q.niveau for q in qualifications(ouvrage, catalogue).values()))
