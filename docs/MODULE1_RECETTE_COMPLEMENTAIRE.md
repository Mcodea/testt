# OGIAS V0.26 — Module 1 : sécurisation complémentaire de l'import

## Périmètre (9 novembre 2026)

Travail effectué sur une COPIE de `OGIAS_V026_Module1_Integre_Interface.zip`. Aucun ouvrage réel n'a été ouvert, modifié, ou incorporé à l'archive.

### Défauts constatés et corrigés

1. L'ancienne route HTTP `/api/inventaire/appliquer` restait accessible malgré l'introduction du module strict Inbound. Elle contournait les garanties de prévisualisation et pouvait accepter un import partiel. Désormais, les anciennes routes `/api/inventaire/apercu` et `/api/inventaire/appliquer` retournent une erreur métier explicite. L'interface utilise uniquement `/api/inbound/apercu` puis `/api/inbound/appliquer` avec jeton et confirmation.
2. Le rapport était tronqué visuellement aux 250 premières lignes. Cela pouvait cacher une erreur située plus loin : l'utilisateur voyait le nombre d'erreurs, mais pas la ligne fautive. Désormais, une consultation paginée par 100 lignes est proposée, via `/api/inbound/lignes?jeton=...&page=...`. **Le moteur contrôle toujours toutes les lignes du fichier**, pas seulement la page affichée.
3. Les tests d'intégration historiques ont été actualisés pour vérifier le **refus de tout le lot** en cas de ligne hors ouvrage, puis la confirmation d'un fichier corrigé. Ce changement reflète la politique métier validée : ne jamais importer partiellement un lot contenant une erreur bloquante.

### Propriétés conservées

- Les fichiers sources et les projets originaux restent intacts pendant la prévisualisation.
- Un aperçu ne peut être appliqué qu'avec un jeton en cours de validité et la confirmation explicite.
- Le moteur recalcule l'aperçu depuis le fichier source et l'état courant du projet avant l'intégration.
- Les anciens repères ne sont pas renommés automatiquement.
- La sauvegarde réelle n'est réalisée qu'après une confirmation autorisée.
- Aucun adressage n'est inventé.

### Recette automatisée

Commande depuis la racine du projet :

```bash
python -m pytest -q
```

Résultat dans l'environnement de développement : **327 tests réussis, 25 ignorés**. Vérification de syntaxe JS : `node --check sorep_web/static/app.js` réussie.

Le nouveau test `tests/inbound/test_pagination.py` inclut un fichier fictif de 120 lignes avec un doublon en dernière ligne : la deuxième page rend l'anomalie visible, et le moteur interdit l'application du lot.

### Limites et qualification

- L'interface de pagination est implémentée, mais sa manipulation dans Chromium n'a pas pu être qualifiée dans cet environnement, l'accès local à `127.0.0.1` étant bloqué par l'environnement navigateur utilisé. À vérifier sur Windows.
- Aucun essai de compatibilité des exports Control Expert, SOFREL S4W ou TOPKAPI n'est couvert par cette livraison.
- Les 25 tests ignorés restent à qualifier ou documenter selon leur domaine.

### Vérification manuelle conseillée (Windows)

1. Décompresser l'archive dans un dossier neuf, puis ouvrir `OGIAS.bat`.
2. Créer un **ouvrage fictif** dans l'application.
3. Importer un CSV d'inventaire de plus de 100 lignes comprenant une erreur dans une ligne supérieure à 100.
4. Vérifier la présence des boutons **Précédent** / **Suivant** et l'affichage du diagnostic en page 2.
5. Vérifier que **Confirmer l'import** est désactivé malgré la première page conforme.
6. Corriger la source, refaire l'aperçu et confirmer uniquement les données de test.

