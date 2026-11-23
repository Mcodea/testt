# Lot 7a : retrait des règles mortes des anciennes feuilles

Outil : `outils/interface_css_mort.py` (liste ; `--appliquer` pour nettoyer). Une règle est morte quand un de ses
sélecteurs vise une classe ou un identifiant qu'aucun script, page, serveur ou moteur ne produit plus (préfixes
dynamiques et jetons entre parenthèses tenus pour vivants, par prudence).

| Feuille | Règles nettoyées | Lignes avant → après | Couleurs en dur | !important |
| --- | --- | --- | --- | --- |
| app.css | 83 | 868 → 806 | 348 → 291 | 28 → 28 |
| v031.css | 45 | 342 → 305 | 53 → 49 | 98 → 94 |
| industrial-ui.css | 43 | 568 → 532 | 83 → 67 | 95 → 92 |

Vérification : captures de tous les écrans (clair et sombre) avant et après, comparées pixel à pixel. Seules
différences : l'heure de modification de l'ouvrage de démonstration (recréé entre les deux relevés) et un écart de
1 sur une composante de couleur à 4 pixels d'anticrénelage. Aucun écran modifié.

Le test `test_aucune_regle_morte_dans_les_anciennes_feuilles` empêche d'en réintroduire.
