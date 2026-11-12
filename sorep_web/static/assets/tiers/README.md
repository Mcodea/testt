# Ressources graphiques embarquées

OGIAS sert ces fichiers localement. Aucun CDN, téléchargement à l'exécution ou
paquet JavaScript supplémentaire n'est nécessaire.

| Ressource | Version | Licence | Fichier livré |
| --- | --- | --- | --- |
| Inter | 4.1 | SIL OFL 1.1 | `../fonts/InterVariable.woff2` |
| JetBrains Mono | 2.304 | SIL OFL 1.1 | `../fonts/JetBrainsMono-Regular.woff2` |
| Lucide | 0.468.0 | ISC | `../lucide/sprite.svg` (21 icônes) |

Les polices et licences sont copiées sans modification depuis les archives
officielles. Les enfants SVG originaux de Lucide sont regroupés dans des symboles,
sans modification des géométries. Le style de trait et la taille viennent de
l'interface. Les noms historiques de `V31.icon` gardent leur sens et leurs appels.

`manifest.json` contient les URLs sources, versions et SHA-256 des archives, puis
les SHA-256 des fichiers livrés. Les licences complètes sont à côté des ressources
et accessibles depuis **À propos**. Le constructeur portable copie l'ensemble du
dossier statique, y compris ces fichiers. Les polices sous OFL peuvent être
embarquées dans un logiciel vendu ; elles ne sont pas vendues isolément.

Tests : `tests_web/test_ressources_embarquees.py` (chargement Chromium, chasse fixe,
icônes rendues, empreintes, licences, accès extérieurs interdits pendant l'essai).
