# Lot 2a — Coque de bureau (18/11/2026)

Réalisation de la maquette du lot 2 (`../lot2_maquette/`), première partie. Fichier : `sorep_web/static/ogias-coque.js`,
styles dans `ogias.css` (jetons uniquement).

| Avant | Après |
| --- | --- |
| Barre latérale bleu nuit de 9 liens (avec doublons) | **Barre de titre** : menus Fichier, Édition, Affichage, Ouvrage, Outils, Aide ; recherche ; ouvrage courant ; thème ; à propos |
| En-tête (fil d'Ariane + titre) et frise des 5 étapes | **Explorateur** : Mes ouvrages, Référentiel, Tableau de bord, et le **parcours** des 5 étapes avec leur état |
| Un seul écran visible | **Onglets de documents** : les écrans ouverts restent accessibles ; fermer l'onglet actif ramène au précédent |

Clavier : menus au clavier (flèches, Entrée, Échap), Ctrl K (recherche), Ctrl B (explorateur, choix mémorisé), F1 (aide).

Le ruban et les commandes de chaque écran arrivent écran par écran au lot 5 : aucune commande n'est déplacée ni
masquée dans ce lot.

## Défaut corrigé en chemin

Abandonner la création d'un ouvrage (bouton « Annuler » de la fiche, ou navigation vers un autre écran) appelait
`/api/fermer` en GET alors que la route n'existe qu'en POST : erreur 404, l'utilisateur restait bloqué sur la création
sans message. Correction dans `app.js` (deux appels) ; essai `test_quitter_une_creation_d_ouvrage_ferme_le_brouillon`.

## Vérification

- Tests moteur : 729 réussis ; essais navigateur : 92 réussis (dont 4 nouveaux dans `test_coque_bureau.py`) ; ruff ;
  contrôle des scripts.
- Les essais qui visaient l'ancienne barre latérale et la frise visent maintenant l'explorateur et la barre de titre.
- Registre des commandes comparé au lot 0 : **aucune commande disparue**.
- Captures : `captures/`.
