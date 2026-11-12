# OGIAS — Module 2 « Référentiel métier » : conception proposée, non codée

## Objectif

Constituer l'unique source des **modèles d'équipements** et de leurs comportements, sans modifier silencieusement les ouvrages existants. Ce module utilisera le module 1 (Inbound/Validation) pour les importations, mais n'utilisera aucun adressage physique/protocolaire directement : ces fonctions appartiennent au module 3.

## Architecture réelle V0.26 constatée

- `genvar/modeles.py` : modèles, types et lignes documentaires historiques, stockés dans `referentiel_modeles.json`.
- `genvar/catalogue.py` : signaux génériques de type et règles associées.
- `genvar/regles.py` : règles métier de génération d'informations calculées.
- `genvar/session.py` : création, modification, validation et publication des modèles et copies figées par ouvrage.
- `genvar/modele.py` : `Ouvrage.modeles_snapshot` et `Ouvrage.catalogue_snapshot`.
- `genvar/audit_referentiel.py` : contrôles de conception. Exemples d'alertes encore à arbitrer : option de totalisateur FT sans effet, seuils activés par défaut et défauts de mesures analogiques absents selon les modèles.

Ces structures se recoupent partiellement : il faut les consolider *sans supprimer les lecteurs historiques* avant d'avoir vérifié toutes leurs dépendances.

## Proposition de modèle de données v2

Une **identité technique stable**, distincte du libellé, pour chaque modèle et chaque signal. Les clés anciennes fondées sur le nom restent lisibles par adaptateur ; les nouveaux identifiants ne seront pas attribués à un ouvrage existant sans acte de migration.

Chaque modèle porte :

1. Métadonnées : identifiant stable, code de type, nom, statut (`brouillon`, `à valider`, `validé`), révision et empreinte.
2. E/S physiques possibles : `ET`, `ST`, `EA`, `SA`, présence obligatoire/par défaut/optionnelle, caractéristiques de principe (sans adresses ni échelles de site).
3. Informations fonctionnelles : états, défauts, calculs internes, source(s) requise(s), conditions d'activation.
4. Points de télétransmission : `TS`, `TM`, `TC`, `TR`, `RTR`, `CP` et leur correspondance avec source physique ou fonction calculée.
5. Règles fonctionnelles **déclaratives** : identifiant de règle Python préenregistrée, paramètres typés, préconditions et variables résultantes. Aucune exécution arbitraire de code contenu dans un Excel.
6. Dépendances et décisions : si un signal optionnel manque, ses variables dépendantes ne peuvent être implicitement générées.

## Cycle de vie proposé

- Édition d'un modèle = création d'une **révision brouillon** ; le modèle publié reste stable.
- Validation technique : unicité des identifiants, existence des sources, compatibilité des familles, cycles de dépendances, types et conditions.
- Publication : acte explicite qui enregistre la nouvelle révision immuable.
- Ouvrage existant : reste attaché à sa copie figée du modèle ; l'application d'une nouvelle révision est une action contrôlée avec rapport d'écart.
- Modifications de signaux : invalidation ciblée des validations d'équipements et des correspondances concernées, sans réadressage automatique.

## Export/import du référentiel

- Export Excel `.xlsx` pour modification humaine (modèles, E/S, fonctions, télétransmission, correspondances, règles, statuts), plus une représentation JSON canonique versionnée.
- Relecture par le pipeline de validation sans modifier le référentiel maître.
- Prévisualisation détaillée des ajouts, suppressions, modifications et conflits ; validation explicite avant publication.
- Aller-retour export / réimport sans modification : même contenu métier et mêmes identifiants techniques.
- Interdiction de faire disparaître des liens métier lors d'une suppression de signal.

## Scénarios de validation métier

- Vanne HV : deux FDC ET, TS ouvert/fermé, information de discordance calculée proposée selon règles, pas d'ordre de marche inventé.
- Vanne commandée : défaut de non-atteinte de position dépendant de l'ordre et du délai configurés.
- Débitmètre : EA débit, ET impulsions facultative, CP volume **unique**, sans ST artificielle et sans min/max dans le référentiel.
- Pompe : commande/retour/défauts suivant le modèle choisi, sans signaux non justifiés.
- SOFREL S4W et Schneider : mêmes modèles fonctionnels, E/S et adresses affectées ultérieurement par les adaptateurs matériels du module 3.
- Réouverture d'un projet ancien : aucun changement de variables, d'identifiants, d'adresses ou de validations sans action explicite.

## Décision demandée avant de coder

**Valider le cycle « brouillon → validation → publication » par révision immuable**, avec les ouvrages existants attachés à leur version figée. L'éditeur graphique ne sera pas redessiné avant validation de ses maquettes par l'utilisateur.

Après validation : commencer par les schémas et validateurs du référentiel, puis leurs tests, puis l'export/import et enfin le raccordement de l'interface actuelle. Les modifications seront livrées avec comparaison de résultats et tests de non-régression.
