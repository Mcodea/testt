# Refonte de l'interface OGIAS

Plan validé le 18/11/2026 : faire d'OGIAS un logiciel d'ingénierie de bureau, avec une identité propre, sans toucher
au moteur ni aux règles métier. Huit lots, appliqués dans l'ordre, chacun vérifié avant le suivant.

| Lot | Contenu | État |
| --- | --- | --- |
| 0. Socle | Branche à jour, inventaire des styles, captures et registre des commandes « avant » | Fait |
| 1. Système de design | Jetons, thèmes clair et sombre, une feuille `ogias.css` | Fait |
| 2. Coque de bureau | Menus, explorateur et parcours, onglets de documents, panneau de sortie, barre d'état | Fait |
| 3. Composants de bureau | Tableau dense, grille de propriétés, menu contextuel, raccourcis | Fait |
| 4. Identité | Fil de l'information, symboles propres | Fait |
| 5. Écrans | Un sous-lot par écran : 5a Équipements, 5b Liste des E/S, 5c Matériel (téléchargements regroupés dans Recette), 5d Variables, 5e Recette, 5f Référentiel, 5g Mes ouvrages et Tableau de bord faits | Fait |
| 6. Fenêtre Windows | Fenêtre native et installateur | À faire |
| 7. Finition | Retrait des anciennes couches, accessibilité, performances : 7a règles mortes retirées | En cours |

## Règles

- Branche `claude/refonte-interface`, créée depuis la dernière version (`claude/refonte-ui-industrielle` + `main`).
  Aucune modification directe de `main` ou `release/1.0`.
- Chaque lot passe la CI complète (tests moteur, essais navigateur, ruff, mypy, contrôle des scripts).
- Aucune règle métier, donnée ou format d'export modifié. Aucune commande retirée d'un écran : le registre
  `actions.json` du lot 0 sert de référence.
- Données fictives uniquement (lieu `XTST`, réservoir fictif).

## Outils

| Outil | Rôle |
| --- | --- |
| `outils/interface_demo.py <dossier>` | Serveur jetable avec un ouvrage fictif ; adresse dans `<dossier>/url.txt` |
| `outils/interface_releve.py <url> <dossier> [référence]` | Captures de chaque écran (clair, sombre), registre des commandes, commandes disparues |
| `outils/interface_inventaire.py` | Mesures des feuilles de style et des scripts |
