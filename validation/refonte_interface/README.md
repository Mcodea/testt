# Refonte de l'interface OGIAS

Plan validé le 18/11/2026 : faire d'OGIAS un logiciel d'ingénierie de bureau, avec une identité propre, sans toucher
au moteur ni aux règles métier. Huit lots, appliqués dans l'ordre, chacun vérifié avant le suivant.

| Lot | Contenu | État |
| --- | --- | --- |
| 0. Socle | Branche à jour, inventaire des styles, captures et registre des commandes « avant » | Fait |
| 1. Système de design | Jetons, thèmes clair et sombre, une feuille `ogias.css` | À faire |
| 2. Coque de bureau | Menus, ruban, explorateur, onglets, inspecteur, barre d'état | À faire |
| 3. Composants de bureau | Tableau dense, grille de propriétés, menu contextuel, raccourcis | À faire |
| 4. Identité | Fil de l'information, symboles propres | À faire |
| 5. Écrans | Un sous-lot par écran | À faire |
| 6. Fenêtre Windows | Fenêtre native et installateur | À faire |
| 7. Finition | Retrait des anciennes couches, accessibilité, performances | À faire |

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
| `outils/interface_releve.py <url> <dossier>` | Captures de chaque écran (clair, sombre) et registre des commandes |
| `outils/interface_inventaire.py` | Mesures des feuilles de style et des scripts |
