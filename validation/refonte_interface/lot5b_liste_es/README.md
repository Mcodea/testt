# Lot 5b — Liste des E/S (18/11/2026)

## Ruban de l'écran

| Groupe | Commandes |
| --- | --- |
| Validation du contenu | Valider la sélection (avec le nombre d'E/S cochées), Valider les affichées |
| Affichage | Masquer / afficher le détail (quand une E/S est ouverte) |
| Échanges | Exporter la liste (Excel) |
| Étape suivante | Matériel |

L'ancien bandeau « es-ruban » disparaît : ses onglets Général, Affichage et Outils n'agissaient pas. Les boutons sont
déplacés, jamais recréés ; ils sont retirés avant chaque nouveau dessin de l'écran (filtres, ouverture d'une ligne)
pour que chaque commande agisse sur l'état affiché.

## Tableau dense

Le tableau des E/S reçoit le tri par colonne, les filtres par colonne, le redimensionnement, le menu contextuel et la
copie vers Excel, **sans** la sélection du composant : les cases à cocher de l'écran restent la seule sélection, et
le clic sur une ligne ouvre toujours son détail. Le tri et les filtres sont conservés quand l'écran se redessine.
L'en-tête de page est allégé (titre et étape déjà donnés par l'onglet et le parcours).

## Vérification

- Tests moteur : 733 réussis ; essais navigateur : 101 réussis (dont `test_liste_des_es_ruban_et_tableau_dense`) ;
  ruff ; contrôle des scripts.
- Registre des commandes comparé au lot 0 : aucune commande disparue.
