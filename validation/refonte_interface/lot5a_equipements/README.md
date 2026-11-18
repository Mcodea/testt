# Lot 5a — Écran Équipements (18/11/2026)

Premier écran refait dans la coque de bureau.

## Ruban de l'écran

Les commandes sont rangées par tâche dans un ruban, sous les onglets de documents :

| Groupe | Commandes | Avant |
| --- | --- | --- |
| Inventaire | Nouvel équipement, Unité fonctionnelle, Importer une liste | en tête de l'arborescence |
| Équipement sélectionné | Valider le paramétrage (ou Repasser à contrôler), Modifier, Ranger dans une UF, Supprimer | menu « ⋯ » de la fiche |
| Unité fonctionnelle | Modifier l'UF, Renommer le groupe, Supprimer l'UF | boutons de la fiche de l'UF |

Les boutons sont **déplacés, jamais recréés** : mêmes identifiants, mêmes écouteurs, mêmes états. Les commandes de la
sélection précédente quittent le ruban avant chaque nouvelle fiche, pour que chaque commande agisse toujours sur
l'élément sélectionné (essai : Modifier sur HV01, MV02 puis HV01 ouvre bien la fiche de chacun). Le ruban se vide en
quittant l'écran ; il arrivera sur les autres écrans un par un.

## Vue « Fil des informations » de la fiche

Quatrième onglet de la fiche, en lecture seule : une ligne par information de l'équipement avec toute sa chaîne —
information, famille, E/S physique (ou « calculée »), voie, variable automate, type, adresse posée, libellé de
supervision, état. Tableau dense du lot 3 : tri, filtres, copie vers Excel. Données : `/api/fil?detail=1`.

## Allègement

Le fil d'Ariane de la fiche (répété par la barre du fil de l'information) et l'en-tête vide de l'arborescence sont
masqués ; le menu « ⋯ », vidé, disparaît.

## Vérification

- Tests moteur : 733 réussis ; essais navigateur : 100 réussis (dont
  `test_ruban_equipements_et_fil_des_informations`) ; ruff ; mypy ; contrôle des scripts.
- Registre des commandes comparé au lot 0 : aucune commande disparue (le ruban est relevé).
