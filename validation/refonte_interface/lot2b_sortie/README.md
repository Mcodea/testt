# Lot 2b — Panneau de sortie (18/11/2026)

Fin du lot 2 (coque de bureau). Sous la zone de travail, un panneau à deux onglets :

- **Contrôles** : les points à régler pour passer à l'étape suivante et les points à vérifier, chacun cliquable vers
  l'endroit à corriger. Un résumé reste visible dans l'en-tête même panneau réduit (« 1 point à régler… »,
  « Étape prête »). Avant, ce bloc s'ajoutait en bas de chaque écran, au-dessus du pied d'étape.
- **Journal** : chaque message affiché (succès ou refus) y reste consultable pendant la session, avec l'heure ; les
  refus sont comptés en rouge. Avant, les messages disparaissaient après quelques secondes sans trace.

Le panneau se réduit et se rouvre (choix mémorisé). À l'écran Matériel, l'onglet « Contrôles » du poste de travail
renvoie désormais au panneau de sortie au lieu de répéter la liste.

Les anciens styles du bloc de contrôles (v031.css, industrial-ui.css) sont retirés : 7 `!important` et 3 couleurs en
dur de moins ; le plafond automatique des anciennes feuilles est abaissé d'autant.

## Vérification

- Tests moteur : 729 réussis ; essais navigateur : 93 réussis (dont `test_panneau_de_sortie_controles_et_journal`) ;
  ruff ; contrôle des scripts.
- Registre des commandes comparé au lot 0 : aucune commande disparue (les liens de contrôle sont relevés dans le
  panneau de sortie).
