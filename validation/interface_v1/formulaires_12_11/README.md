# Formulaires — contraste et continuité visuelle, 12 novembre 2026

Base publique : c43f713, Mcodea/testt, branche claude/referentiel-v2.
Consigne active : refonte visuelle seule ; ne pas intégrer de nouvelles fonctions
R3/R8, ne pas modifier état, API, métier ou export sous couvert de présentation.

Les captures avant/après sont produites par Chromium sur le serveur réel. Les
formulaires Neuf/Existant restent vides ; la vue Adressage réutilise la fixture
Variables et les valeurs calculées par le moteur existant. Aucun contenu n’est
ajouté aux composants, aucune capture retouchée. Aucun essai industriel déduit.

Référence visuelle : palette industrielle demandée dans le chat le 12/11.
Aucune maquette de formulaire de création n’a été fournie. comparaison.html
compare les écrans réels avant/après ; les trois maquettes de docs/maquettes
restent intactes, leurs couleurs ayant été remplacées par la consigne du chat.

| Anomalie reproduite | Correction CSS | Test automatique |
| --- | --- | --- |
| Labels et titre presque illisibles en sombre | Couleurs du thème ; contraste texte/fond au moins 4,5:1 | test_creation_sombre_labels_et_titres_lisibles : Neuf/Existant, trois résolutions |
| Badge du mode et boutons très clairs isolés | Palette partagée avec la fiche ; focus conservé | test_creation_controles_et_modes_herites_de_la_palette : clair/sombre |
| Double bordure et marge intérieure du formulaire | Une seule carte, champs compacts et actions accessibles | test_creation_une_carte_et_actions_accessibles_aux_trois_resolutions |
| Onglet actif des listes peu contrasté en sombre | Bleu/texte blanc, contraste au moins 4,5:1 | test_liste_et_protocoles_sans_modification : quatre onglets |
| Niveau d’adressage actif privé de son ancien repère en ombre | Contour continu de 2 px, indépendant du focus ; bordure de statut conservée | test_cartes_adressage_sombres_et_selection_visible_sans_ecriture : trois niveaux |

Tous les tests sont dans tests_web/test_formulaires_industriels.py.
Dix-huit sous-cas ont échoué avant correction ; cinq tests et dix-huit sous-cas
passent après correction. Le calcul du contraste applique la formule WCAG aux
couleurs réellement calculées et au premier fond opaque dans l’ascendance DOM.
Le bouton Créer conserve son comportement historique : contrôles à la soumission,
aucune nouvelle règle de désactivation. Le changement de thème conserve son
animation de couleur existante ; les tests attendent son état final.

Après les consultations et changements de thème, les objets API et listes restent
identiques ; le projet enregistré de la fixture Variables reste identique à
l’octet ; aucun POST lors du test de changement de thème. Aucun JavaScript,
identifiant, gestionnaire, état, API, donnée, moteur ou export n’est modifié.
Le seul code produit changé est industrial-ui.css (20 lignes de présentation).

Validation locale finale : 730 Python / 18 sous-cas (194,22 s), 65 navigateur /
70 sous-cas (110,68 s), aucun ignoré ; couverture 89,283831 %, exports 100 %.
Ruff, mypy 49 fichiers, JS et audit strict des dépendances passent. Les sept
seuils de performance sont inchangés : rendu 75,9 ms, filtre 97,4 ms, adressage
0,719 s. Audit données et suivi CI : verification.json et Actions publiques.
La conformité WCAG de toute l’application reste partielle : seuls les éléments
ci-dessus sont prouvés ici, pas une certification globale.
