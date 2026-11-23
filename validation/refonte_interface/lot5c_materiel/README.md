# Lot 5c — Matériel (18/11/2026)

## Ruban de l'écran

| Groupe | Commandes | Avant |
| --- | --- | --- |
| Matériel | Calculer / Recalculer le matériel, Valider le matériel (ou Repasser à valider), Ajuster les cartes | titre, bandeau, barre d'actions |
| Voies des E/S | Implanter les E/S sans voie, Libérer les voies non validées, Valider la sélection, Valider les voies affichées | onglet « Voies des E/S », menu « Autres actions » |
| Livrables | E/S par carte, Liste d'E/S, Cartes d'E/S (Excel), E/S Control Expert (XSY, TXT) | onglet « Nomenclature et livrables », menu « Autres actions » |

La barre « Autres actions » disparaît. Les exports Control Expert gardent leur trait de cible. Matériel pas encore
calculé : pas de ruban, seul le cadre de démarrage s'affiche (principe du retour de 13 h 40).

## Inspecteur

Les propriétés de l'emplacement sélectionné (carte, alimentation, processeur, communication, emplacement libre ou
rack) sont présentées dans la **grille de propriétés** du lot 3 : groupes repliables (Carte d'E/S, Occupation…),
libellé / valeur. L'onglet « Contrôles » de l'inspecteur, qui répétait le panneau de sortie, est retiré.

## Retraits volontaires

`../commandes_retirees.json` déclare chaque commande retirée du registre du lot 0, avec son motif et l'endroit où la
fonction se retrouve. L'essai `test_registre_commandes.py` refuse toute autre disparition, et tout motif vide.

## Vérification

- Tests moteur : 733 réussis ; essais navigateur : 103 réussis (dont `test_materiel_ruban_et_grille_de_proprietes`) ;
  ruff ; contrôle des scripts.
- Registre des commandes : aucune disparition non déclarée.
