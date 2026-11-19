# Cahiers d'essais FAT / SAT (lot 3)

C'est l'idée des fiches d'essai point par point générées depuis la base (Typical Manager), adaptée à OGIAS :
**OGIAS édite le cahier, vous le remplissez, OGIAS relit les résultats.** Il n'en déduit jamais aucun.

| Cahier | Une ligne par | Colonnes propres |
| --- | --- | --- |
| FAT (essais en atelier) | entrée / sortie câblée | Adresse, module, voie |
| SAT (essais sur site) | variable de télétransmission | Adresse, registre Modbus (avec décalage), libellé de supervision |

## Utilisation

1. **Éditer le cahier** : Recette et livrables › Essais FAT / SAT › « Éditer le cahier ».
   - Le classeur contient une feuille « Sommaire » (mode d'emploi, avancement) et une feuille par équipement.
   - Les résultats déjà reportés sont pré-remplis.
2. **Remplir** : Résultat (Conforme, Non conforme, Sans objet ; OK, NOK, SO acceptés), remarque, date, visa.
3. **Reporter** : « Reporter un cahier rempli… ».
   - OGIAS montre les résultats nouveaux ou modifiés, non-conformités d'abord, et ce qui est inchangé ou vide.
   - Rien n'est enregistré avant « Confirmer ». Une copie de sécurité de l'ouvrage est faite avant.

## Règles

- **Cellule vide** : elle ne change rien.
- **Cahier erroné** : il n'est pas reporté. C'est le cas d'un résultat inconnu ou d'un point qui n'existe plus
  (clé modifiée ou E/S supprimée).
- **Point à refaire** : un résultat garde l'adresse essayée. Si l'adresse change ensuite, le point redevient
  « à refaire » et le cahier réédité le signale.
- **Suivi** : Recette affiche, par cahier, les points essayés sur le total, les conformes, les non conformes,
  les sans objet, ceux à faire et à refaire, ainsi que la liste des non-conformités avec remarque, visa et date.
- **Dates saisies dans Excel** : elles sont relues en JJ/MM/AAAA.

Le cahier est au format Excel produit par OGIAS. Un cahier à la présentation d'un client, en Word, sera possible
avec le moteur de modèles (lot 1) quand un modèle réel sera fourni.

Vérifications :

- 799 essais du moteur, dont `tests/test_essais.py` (4 essais) ;
- 112 essais navigateur, dont `test_cahiers_d_essais` ;
- ruff, mypy ;
- audit des données : 0 détection ;
- accessibilité : 0 écart.

Captures (ouvrage fictif XTST, résultats fictifs) : `recette_essais_clair.png`, `recette_essais_sombre.png`,
`report_apercu.png` ; cahier vierge d'exemple : `exemple_cahier_FAT_vierge.xlsx`.
