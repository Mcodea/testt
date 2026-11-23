# Lot 7c : retrait de l'ancienne coque V30

L'ancienne coque (v030-shell.js et ses éléments masqués : en-tête, ruban, onglets de documents, titre de vue, arbre,
inspecteur) n'était plus affichée depuis le lot 2 : la coque de bureau (ogias-coque.js) l'avait remplacée. Elle
restait chargée.

Inventaire avant retrait, ce qu'elle faisait encore :

| Comportement | Devenu |
| --- | --- |
| Thème sombre mémorisé, appliqué au chargement | Repris en tête de ogias-coque.js |
| Échap ferme la fenêtre de dialogue | Déjà assuré par app.js (doublon) |
| Bouton d'aide et nom d'utilisateur de l'en-tête | En-tête masqué ; l'aide est au menu Aide de la coque |
| Ruban, onglets, arbre, inspecteur (render / refresh) | Plus appelés depuis le lot 2 |

Retirés : v030-shell.js (214 lignes), les éléments masqués de index.html, puis 158 règles CSS devenues mortes
(outil interface_css_mort.py ; app.css 868 → 678 lignes au total du lot 7). Restent : zone de travail, barre d'état,
fenêtre de dialogue.

Vérification : captures de tous les écrans, clair et sombre, avant (copie propre du dépôt) et après chaque étape,
comparées pixel à pixel : seule l'heure de l'ouvrage de démonstration diffère. Registre des commandes, audit
d'accessibilité, 735 tests moteur et 104 essais navigateur : sans écart.
