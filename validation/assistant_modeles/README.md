# Assistant « créer un modèle depuis un export » (lot 7, 19/11/2026)

But : réduire le travail de préparation chez un client qui a son propre standard (supervision, automate…).
Au lieu d'écrire un modèle `<#…#>` à la main, on part du fichier que l'outil du client exporte pour **un seul
équipement** déjà décrit dans l'ouvrage ouvert (ex. la pompe PM01).

## Où

Standards d'ingénierie > Modèles de livrables > **Créer depuis un export…** (un ouvrage doit être ouvert).

## Ce que fait OGIAS

1. Il cherche dans le fichier les valeurs qu'il connaît pour l'équipement de référence : repère, noms de variables,
   libellés, adresses, registres, noms d'E/S, données de l'ouvrage. Ce sont exactement les valeurs que le moteur de
   remplissage écrit : reconnaissance et génération ne peuvent pas diverger.
2. Il range le fichier : en-tête et pied recopiés tels quels ; le corps devient un bloc répété pour chaque équipement
   **du même type** (`DEBUT_EQUIPEMENTS_PM`, nouveau filtre du moteur) ; une suite de lignes « une par variable » de
   même forme devient un bloc VARIABLES (filtré par famille si chaque famille a sa forme), idem pour les E/S.
3. Chaque substitution peut être refusée (case à décocher) : la valeur reste écrite telle quelle.
4. **Contrôle** : le modèle est rempli pour l'équipement de référence et comparé au fichier d'origine
   (identique / mêmes lignes dans un autre ordre / reproduit avec des lignes en plus / différences à examiner).
5. Enregistrement seulement à la demande, et refusé si le modèle est en erreur. L'encodage du fichier d'origine
   (UTF-8 ou Windows-1252) est conservé.

## Ce qui est signalé, jamais caché

- ligne citant plusieurs variables ou E/S, ou lignes de formes différentes : recopiées telles quelles, à reprendre ;
- adresses de l'équipement de référence non attribuées : une colonne d'adresses ne peut pas être reconnue ;
- type d'équipement inutilisable comme filtre : le modèle se répéterait pour tous les équipements.

## Limites

- Fichiers texte seulement (CSV, TXT, XML, SCL…). Pas de binaire.
- Aucun format d'outil réel n'a encore été essayé : les essais utilisent des exports **fictifs**. Il faut un vrai
  export de la supervision d'un client (données anonymisées) pour confirmer, puis l'import du fichier généré dans
  l'outil cible pour le qualifier.
- Le placement graphique sur un synoptique n'est pas concerné : OGIAS produit le fichier d'import, rien de plus.

## Vérifications

- `tests/test_assistant_modele.py` (8) : reproduction identique et généralisation (PM02 générée, vanne exclue),
  refus d'une substitution, export partiel et familles, XML détecté, refus motivés, ligne ambiguë, analyse sans
  enregistrement puis enregistrement (encodage conservé), filtre de type du moteur.
- `tests_web/test_coque_bureau.py::test_assistant_modele_depuis_export`.
- Suites complètes : 820 tests moteur, 116 navigateur ; audits données, CSS, accessibilité à zéro.

## Captures (données fictives XTST)

`etape1_choix.png`, `etape2_proposition.png`, `etape2_modele.png`, `etape2_sombre.png`, `bibliotheque.png`.
