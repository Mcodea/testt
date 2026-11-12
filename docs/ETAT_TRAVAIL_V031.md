# État de travail V0.31

## Terminé
- Restauration de la V0.30 officielle et contrôle des sources de l'interface.
- 373 tests réussis, 25 ignorés sur la base.
- État des lieux et plan de refonte.

## En cours
- Design system et simplification de la navigation.
- Vue Variables unifiée avec les mêmes contrôles d'adressage que la V0.30.

## À faire
- Refonte de tous les autres écrans et modales.
- Parcours métier de bout en bout en projet neuf et existant.
- Comparaison avant/après des exports, contrôle des captures et de l'accessibilité.
- Compilation, tests finaux et archive unique `OGIAS_V031.zip` seulement après satisfaction de tous les critères.

## Décisions
- Ne pas utiliser les noms et adresses fictives des images dans l'installation.
- La validation depuis la table doit **d'abord** demander une prévisualisation et appliquer par empreinte avant de valider les lignes : interdiction d'afficher une simple proposition comme validée.
- Les fichiers originaux de projets restent hors de la copie de travail.

## Reprise et progrès du présent tour
- Base V0.30 official : 373 passed, 25 skipped (retest après changements effectué).
- `sorep_web/static/v031-ui.js` : coque indigo, barre latérale, en-tête compact, recherche globale, frise unique.
- `sorep_web/static/v031.css` : design system, tableaux, dashboard, modales et thème sombre local (la charte complète reste à auditer).
- `sorep_web/static/v031-variables.js` : accueil, dashboard et écran Variables unifié ; les actions passent par `/api/adressage/action` et `/api/variables/action`.
- Validation E2E sur API réelles (via pont Python à cause du blocage navigateur vers localhost) : quatre propositions pour un ouvrage synthétique appliquées avec empreinte puis validées ; aucune erreur JavaScript ; moteur conservé.
- Vues de contrôle visuel produites sous `ogias_v031_dev/`, uniquement avec données synthétiques.

## Reste critique avant V0.31 livrable
- Auditer et refondre la présentation de tous les écrans techniques, fenêtres et erreurs.
- Corriger les contrastes et exigences strictes relatives aux jetons CSS (l'ancien CSS contient encore des constantes).
- Vérifier tableau à 5 000 lignes, filtres/pagination et navigation clavier.
- Tester les refus de collision, adresses existantes, captures 1366×768, comparatif des exports, vérification complète des fonctions conservées.
- VERSION, LISEZ-MOI et compte rendu final uniquement après recette.

## Reprise du 10 novembre 2026 — premier lot

- Diagnostic de reprise enregistré dans `docs/DIAGNOSTIC_REPRISE_V031.md` ;
  plan accepté par l'utilisateur, travail sur `codex/diagnostic-finalisation-v031`.
- Précondition du test Qt corrigée : ouvrir Ouvrage avant d'exiger la visibilité
  de son arbre. Les 25 tests Qt réussissent, sans changement de la fenêtre.
- Deux défauts Variables reproduits puis corrigés : activation au clavier par
  Espace et alignement en-têtes/cellules des vues échange et télétransmission
  (état sans résultat compris). Moteur, API et formats de projet inchangés.
- Recette Chromium sur API réelles ajoutée sous `tests_web/` : 6 tests réussis,
  dont annulation sans écriture et refus d'un plan périmé. Exécution distincte
  de pytest, documentée dans `tests_web/README.md`.
- Suite complète : **393 réussis, 9 échoués, aucun ignoré** sur 402 tests.
  Les neuf échecs dépendent toujours de `validation/ddt/exemple_DDT_reconstitue.xsy`
  et de `validation/hybride/`, absents des ressources accessibles. Aucun test
  supprimé, désactivé ou affaibli pour masquer cette absence.
- Les documents Word Schneider et SOFREL reçus sont des références techniques,
  pas les fichiers de validation manquants. Aucune règle ni adresse n'en est
  déduite automatiquement.
- Détail, preuves et limites : `docs/REPRISE_V031_LOT1.md`. La recette complète
  V0.31 et la livraison restent à terminer ; version et archive non mises à jour.

## Restauration des jeux de validation — 10 novembre 2026

- `validation.zip` fourni par l'utilisateur contient les ressources manquantes.
  58 fichiers restaurés à l'identique sous `validation/`, hors cache Python.
  Provenance et empreintes : `validation/SOURCE_ARCHIVE.json`.
- Les 9 échecs dus aux fichiers absents sont levés sans modification du moteur,
  des tests, des seuils ou des corrigés : **402 tests réussis, 0 échec, 0 ignoré**.
- Les modules ciblés DDT/hybride passent leurs 24 tests ; la recette navigateur
  passe ses 6 tests. Le XSY synthétique développe 7 champs DDT sans créer
  d'adresse de champ depuis l'adresse du parent.
- Les rapports récupérés dans l'archive restent des preuves historiques ; les
  nouveaux lancements et leurs limites sont distingués dans `validation/README.md`.
- Le rapprochement reste une proposition à confirmer : sur le jeu difficile,
  la méthode hybride retrouve 12 des 18 liens attendus, avec 1 fausse proposition,
  5 liens non proposés et 2 faux positifs sur signaux absents. Aucun ajustement
  du moteur ou du corrigé n'a été fait pour améliorer ce score.
- Le blocage de récupération des jeux est levé. Restent les étapes de compatibilité,
  recette exhaustive d'interface, performances, Windows et livraison prévues dans
  le plan de reprise. Une suite verte ne constitue pas une qualification industrielle.
