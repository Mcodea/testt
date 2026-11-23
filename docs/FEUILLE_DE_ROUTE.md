# OGIAS — Feuille de route d'ingénierie (22/11/2026)

Rédigée par Claude, ingénieur en chef du développement, à la demande de l'utilisateur : viser des objectifs
professionnels et fiables, en s'inspirant des logiciels d'ingénierie industrielle du marché. Elle complète le cahier
des charges V1 (`docs/CAHIER_DES_CHARGES_V1.md`), qui reste la référence d'acceptation.

## Positionnement

OGIAS est un **logiciel d'ingénierie de données d'automatisme** : une seule base de l'ouvrage (équipements, E/S,
matériel, variables, télétransmission) d'où sortent tous les livrables, sans ressaisie. C'est la famille des outils
d'ingénierie de données (EPLAN Preplanning, Aucotec Engineering Base, Siemens COMOS) et des générateurs à partir de
« typicals » (Typical Manager), appliquée à l'eau, la télégestion et la supervision.

Principes retenus de ces outils, et ce qu'OGIAS en fait :

| Principe du marché | Dans OGIAS |
| --- | --- |
| Source unique, aucune ressaisie | L'ouvrage est la seule source ; chaque livrable est calculé, jamais retapé. |
| Typicals / macros réutilisables | Modèles d'équipements du référentiel, modèles de livrables (lots 1, 7, 8). |
| Ouverture aux outils de chaque client | **Formats d'export appris** : le format du constructeur s'apprend, il n'est pas codé. |
| Standards par client | Standards d'ingénierie : charte de nommage, plan d'adressage, chaîne d'outils. |
| Contrôles de cohérence nommés | Règles R-xxx, recette consolidée, aucun export s'il reste une erreur bloquante. |
| Gestion des révisions | Copies horodatées, adoption contrôlée du référentiel, indices de livraison figés et liste des modifications entre indices. |
| Traçabilité de la qualification | Formats qualifiés par un essai réel tracé, puis contrôlés automatiquement. |

## Règles d'ingénierie (non négociables)

1. **Rien n'est deviné.** Ce qu'OGIAS ne sait pas est signalé, jamais inventé (format, adresse, matériel).
2. **Rien ne change en silence.** Toute opération lourde passe par un aperçu et une confirmation ; un ouvrage
   existant garde ses noms et adresses.
3. **Un livrable se relit.** Un fichier produit est contrôlé avant d'être livré ; un fichier qui ne se relit pas
   n'est pas livré.
4. **Qualifié veut dire essayé.** Un format n'est « qualifié » qu'après un essai réel dans le logiciel cible.
5. **Chaque lot est prouvé** : tests moteur et navigateur, contrôles statiques, audit des données, notice dans
   `validation/`, CI verte avant fusion.
6. **Aucune donnée réelle** dans le dépôt (audit `outils/verifier_donnees.py`).

## Objectifs, par ordre de priorité

### 1. Ouverture à tout constructeur (en cours)
- [x] Formats appris, lot 1 : liste des E/S physiques (texte à colonnes).
- [x] Formats appris, lot 2 : télétransmission (chaque supervision) et IHM.
- [x] Formats appris : classeurs Excel (tables de variables TIA Portal).
- [x] Gamme livrée Siemens S7-1500 (références vérifiées). Schneider et Siemens couverts (décision du 22/11).
- [ ] S7-1200 / S7-1200 G2 : quand des références commandables seront vérifiées.
- [ ] Formats appris : fichiers XML, si un outil des clients l'exige.
- [x] Gammes de matériel déclarées par l'atelier : tout automate est calculé comme une gamme livrée.

### 2. Révisions des livrables (niveau professionnel)
- [x] Indices de livraison et **liste des modifications** entre deux indices (équipements, E/S, variables,
      adresses, cartes ; ajoutés, supprimés, modifiés champ par champ), Excel et « Tous les livrables ».

### 3. Mesure honnête de l'avancement
- [ ] Réévaluer le tableau de conformité de `ETAT_TRAVAIL.md` ligne par ligne avec les preuves des lots du 16 au
      22/11, et publier un taux fondé sur les preuves.

### 4. Vers la version 1.0 vendable
- [ ] Décisions utilisateur sur le référentiel (A1, R1, D5-b) puis application.
- [ ] Qualification des formats par l'utilisateur (section 8), facilitée par les formats appris.
- [ ] Processus de livraison : les 16 exigences absentes de la section 10.
- [ ] Installation et documentation utilisateur (section 9).

## Décisions attendues de l'utilisateur

- Automates : Schneider et Siemens pour l'instant (22/11). Supervisions employées : à préciser.
- A1 / R1 / D5-b (référentiel).
