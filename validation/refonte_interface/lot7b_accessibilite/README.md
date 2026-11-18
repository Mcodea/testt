# Lot 7b : accessibilité (WCAG 2.1 AA)

Outil : `outils/interface_accessibilite.py <url>`, sur chaque écran (Mes ouvrages, Tableau de bord, Équipements,
Liste des E/S, Matériel, Variables, Adressage, Recette, Référentiel), en clair et en sombre, page entière :

- contraste du texte sur son fond réel (4,5:1 ; 3:1 pour le grand texte ; texte désactivé exempté) ;
- nom accessible de chaque bouton, lien et champ ;
- aucune commande active retirée du parcours au clavier (tabindex="-1" hors tableau dense et menus).

Premier passage : 13 défauts de contraste, 0 sans nom, 0 hors clavier. Corrigés par les jetons, dans `ogias.css` :

| Élément | Avant | Thème |
| --- | --- | --- |
| Mention de la barre d'état (« Exports industriels non qualifiés ») | 2,6:1 | clair, tous écrans |
| Bouton « Structure / ajouter » enfoncé | 2,4:1 | sombre |
| « + installer » d'un emplacement du rack | 3,4:1 | sombre |
| Menu « Autres actions » de l'écran Adressage | 2,1:1 | sombre |
| Compteur d'erreurs des contrôles de la Recette | 3,9:1 | sombre |

Après : 0 défaut. L'audit tourne dans `tests_web/test_registre_commandes.py` : toute régression fait échouer la CI.
Le banc de performance reste dans son budget (interface 0,07 s, filtrage 0,08 s pour 5000 variables).
