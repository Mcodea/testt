# OGIAS 0.30 — Compte rendu de refonte UI/UX

Date : 9 novembre 2026. Base de travail : **OGIAS V0.29**, sans branche métier parallèle. Cet état concerne le développement de la couche visuelle ; les exports industriels ne sont **pas qualifiés**.

## 1. Architecture et parti pris

- Fenêtre locale en mode application Edge/Chrome, serveur Python conservé (`sorep_web/serveur.py`). Aucune API métier supprimée.
- Structure constante : barre de titre OGIAS ; ruban contextuel avec icônes SVG locales et commandes reliées aux contrôles existants ; onglets de documents ; en-tête et jalons de l'ouvrage ; espace central avec arborescence et inspecteur repliable ; barre d'état.
- Thèmes clair/sombre persistants localement. Jetons CSS pour couleurs métier, saisie, erreurs et états ; transitions désactivées avec `prefers-reduced-motion`.
- Identité : bleu nuit et blanc, bleu électrique pour la commande primaire, or limité à la signature et au numéro de version. Affichage adapté à 1280×800 et 1440×900.
- **Règles industrielles inchangées** : proposition ≠ validation ; adresses historiques des projets existants protégées ; code `XTSTRV01HV01` dans les jeux d'essais fictifs ; aucune compatibilité d'export certifiée.
- Le CSS métier historique est conservé sous des sélecteurs de compatibilité lorsque les composants existants en dépendent. Les règles 0.30 le surchargent à la fin d'`app.css`. Le moteur `genvar/` conserve sa logique.
- Polices utilisées hors ligne : Segoe UI Variable/Segoe UI et Consolas/Cascadia Code si présentes sur Windows ; secours `system-ui` et `monospace`. **Aucun fichier de police n'est redistribué**. Les icônes SVG sont intégrées au JavaScript local.

## 2. Inventaire des fonctions et correspondance vers les écrans 0.30

| Fonction héritée | Écran / emplacement de la V0.30 | Contrôle / service conservé |
|---|---|---|
| Voir, rechercher et reprendre un ouvrage | Accueil / Mes ouvrages | `/api/accueil`, `/api/ouvrir` |
| Créer projet neuf ou existant | Accueil → Nouvel ouvrage → Identification | `/api/nouveau`, `/api/fiche-ouvrage` |
| Lieu, type, numéro proposé, codification, révision | Identification de l'ouvrage ; gestion des listes via la fiche | `/api/numero-ouvrage`, `/api/listes-ouvrage/action` |
| Gérer automates et protocoles | Ouvrage → Gestion des listes ; fiche d'ouvrage | `/api/listes-ouvrage` |
| Import contrôlé d'inventaire, aperçu, confirmation | Équipements → ruban Importer → modale d'import | `/api/inbound/*`, session historique conservée |
| Unités fonctionnelles et groupes, édition et suppression | Équipements → arborescence et ruban « Nouvelle UF » | `/api/uf` |
| Ajout, édition, duplication et suppression d'un équipement | Équipements → liste/arbre et fiche, actions contextuelles | `/api/equipement/*` |
| Options et signaux physiques par modèle | Fiche équipement → Paramétrage des E/S | `/api/equipement/configurer` |
| Paramètres analogiques et impulsions | Fiche équipement → Configuration des E/S / dialogue dédié | `/api/equipement/configurer` |
| Retenir / écarter les informations proposées avec motif | Fiche équipement → Informations fonctionnelles | `/api/equipement/proposition` |
| Lignes du modèle et variables locales | Fiche équipement → Lignes de modèle | `/api/equipement/ligne` |
| Validation du paramétrage des équipements | Fiche équipement → Valider | `/api/equipement/valider` |
| Contenu d'E/S, nature, sens, désignation et échelle | Étape 2 → Liste des E/S, panneau d'édition | `/api/es`, `/api/es/definir` |
| Validation du contenu, par sélection ou ensemble affiché | Étape 2 → Liste des E/S | `/api/es/valider`, niveau `contenu` |
| Proposition des racks et des cartes, réserve | Étape 3 → Matériel ; ruban Calculer | `/api/materiel`, `/api/materiel/action` |
| Correction des cartes et de leurs emplacements | Étape 3 → Matériel ; fenêtre « Ajuster les cartes » | `/api/modules` |
| Implantation des voies et préservation des voies validées | Étape 3 → Matériel ; ruban « Implanter » ; liste par voie | `/api/modules` |
| Validation du matériel et des voies | Étape 3 → Matériel | `/api/materiel/action`, `/api/es/valider` |
| Variables d'échange et leurs adresses | Étape 4 → Table d'échange | `/api/variables` |
| Points et identifiants de télétransmission | Étape 4 → Télétransmission | `/api/supervision` |
| Plan d'adressage à trois niveaux ; réservations et conflits | Étape 4 → Adressage automatique | `/api/adressage` |
| Prévisualisation sans écriture, application sur empreinte, validation tracée | Étape 4 → Adressage automatique ; ruban | `/api/adressage/action` |
| Conservation des adresses existantes et disponibilité non vérifiée | Étape 4 → Mode projet existant | moteur d'adressage historique |
| Recette consolidée et accès aux anomalies | Étape 5 → Recette et panneau Validation | `/api/recette` |
| Exports des E/S, cartes, variables XSY/TXT/Excel, TOPKAPI | Matériel, Variables, Adressage et Recette → actions contextuelles | `/api/export` et routes existantes |
| Référentiel publié, modèles, signaux, règles | Onglet Référentiel métier → arborescence, vue centrale | `/api/referentiel/vue` |
| Brouillon, édition, contrôles, comparaison, publication | Ruban Versionning selon l'état du référentiel | `/api/referentiel/cycle/action` |
| Import/export Excel du référentiel | Référentiel → ruban Échanges | `/api/referentiel/cycle/action` et export existant |
| Révisions historiques et restauration vers brouillon | Référentiel → Historique et cycle de vie | `/api/referentiel/cycle/action` |
| Adoption d'une nouvelle révision par un ouvrage | Fiche Ouvrage → Avertissement de version, action d'adoption | `/api/referentiel/adopter` |
| Corbeille / suppression et duplication | Accueil / Ouvrage et fiche selon objet | services historiques conservés |
| Thème sombre, replis, clavier, aide | Ruban « Affichage », panneaux latéraux, aide locale | `v030-shell.js`, `aide.html` |

**Note :** une fonction propre à un équipement demeure dans sa fiche. Les commandes globales sont redirigées par le ruban vers leurs contrôles d'origine afin de conserver les événements et API déjà opérationnels.

## 3. Écrans refondus / captures

- Accueil / Mes ouvrages et création d'ouvrage.
- Fiche d'ouvrage, inventaire et sélection des équipements.
- Liste des E/S.
- Matériel / architecture et configuration des cartes.
- Variables : Table d'échange, Télétransmission, Adressage automatique.
- Recette et livrables.
- Référentiel publié/brouillon, import et contrôle ; fenêtre de gestion des listes, ajout d'équipement, ajout d'UF, import inventaire, import du référentiel.
- Tous les scénarios d'illustration utilisent uniquement le lieu fictif `XTST` et une copie indépendante de la base de données.

Captures : `docs/captures_v030/` : variantes **light/dark × 1280/1440** (neuf et existant), ainsi que les fenêtres complémentaires. Les rapports machine sont en JSON. Le navigateur utilisé est Chromium automatisé ; ces captures ne prouvent pas le rendu final sur un poste Windows individuel.

## 4. Vérifications

- Suite Python : `python -m pytest -q` : **373 tests réussis, 25 ignorés** (dépendances de développement optionnelles non installées). Aucun test supprimé pour masquer une régression.
- Vérification de syntaxe : `node --check sorep_web/static/app.js` et `v030-shell.js`.
- Vérification de la fenêtre : navigation sans erreur JavaScript et sans débordement horizontal de la page à **1280×800** et **1440×900**, clair/sombre, sur données fictives ; rapports `resultats_v030.json`.
- Vérification des actions via navigateur : `parcours_commandes.json` (ruban E/S et matériel, navigation vers variables et recette, prévisualisation d'adressage, cycle de contrôle du référentiel, modal et touche Échap, changement de thème). Les contrôles portent sur les actions non destructrices.
- En complément des tests Python, un **parcours métier réel en navigateur**, servi par l’API locale sur un dossier totalement fictif `XTST`, a été exécuté : création de l’ouvrage ; ajout d’une vanne ; décision explicite des propositions fonctionnelles ; validation de l’équipement et du contenu des deux E/S ; calcul du matériel, implantation et validation des voies ; proposition de quatre adresses mémoire, prévisualisation, application après confirmation et validation ; déclaration de la convention protocolaire ; recette finale à **0 erreur et 0 alerte**. Les téléchargements du scénario ont été réalisés, mais leur compatibilité industrielle n’a pas été vérifiée.
- Cycle réel du référentiel dans un second parcours navigateur : brouillon → modification du type → contrôle → validation → publication ; un classeur Excel a été exporté, modifié, réimporté en prévisualisant la différence puis intégré au brouillon, sans toucher à la révision publiée. Tous les essais ont utilisé des données fictives et aucune erreur JavaScript n’a été détectée.
- **184 captures PNG** de la nouvelle interface sont archivées sous `docs/captures_v030/`, dont les principales vues neuf/existant en clair/sombre à 1280 et 1440 px, ainsi que les dialogues complémentaires. Les rapports disponibles ne signalent ni erreur JavaScript ni débordement horizontal de page dans les vues contrôlées.
- Une limite du banc d’essai a été corrigée : les téléchargements XLSX devaient être récupérés directement en binaire, et non par une passerelle de test textuelle. Un export Excel récupéré directement est valide et le réimport fonctionne.

## 5. Limitations et qualification industrielle

- Les exports vers **Control Expert, SOFREL S4W-Tools et TOPKAPI 6.3 ne sont pas qualifiés** : il faut tester dans ces applications, sur une copie des projets concernés.
- Le rendu final sur **Windows + Edge en mode application** doit être vérifié sur un poste utilisateur. Les captures locales ne remplacent pas cette recette.
- L'application reste monoprojet au niveau de la session du serveur : les onglets naviguent entre les écrans de l'ouvrage courant et le référentiel ; ils ne constituent pas une session d'édition simultanée de plusieurs ouvrages.
- Les contrôles automatisés ne constituent pas un audit d'accessibilité exhaustif ni une garantie d'absence de défauts dans toutes les données futures.
- Aucun fichier de police tiers n'est inclus dans l'archive ; les polices système garantissent un fonctionnement hors ligne.
- Les éventuels tests ignorés signalent des dépendances de développement optionnelles non disponibles ; ils ne sont pas comptabilisés comme réussis.

## 6. Installation et sécurité

Extraire dans un nouveau dossier, garder les données existantes en sauvegarde et lancer `OGIAS.bat`. Ne pas copier les fixtures d'essai du dossier de développement. L'installation vierge ne précharge ni ouvrages ni équipements fictifs.
