# Intégration de la bibliothèque des E/S V1 (classeur 2) — analyse et décision

Établi le 10 novembre 2026 (reprise Claude). Outil : `outils/correspondance_es_v1.py`,
rapport : `validation/referentiel/correspondance_es_v1.csv`, test :
`tests/test_correspondance_es_v1.py`.

## Constat vérifié

- Les 144 E/S du catalogue livré (`genvar/data/catalogue_defaut.json`) correspondent
  chacune à exactement une ligne du classeur, sans ambiguïté :
  77 par le code, 58 par le « Code d'origine » (lignes « Harmonisé »), 9 par la
  télétransmission (fins de course de CL, DJ, EV, IS, SV, XV : code catalogue
  `OUV`/`FER`, code V1 `FDC_OUV`/`FDC_FER`).
- Les 49 lignes du classeur sans correspondance sont exactement les 49 « Ajouté ».
- Aucune E/S du catalogue n'est absente du classeur.

## Écart de modèle à trancher (décision à valider)

Le catalogue actuel fusionne l'E/S physique et sa variable supervisée : une entrée
TOR télétransmise **est** la TS (famille TS, code `OUV` → `TS_<repère>_OUV`) ; une
E/S non supervisée est de famille `ES`. Les règles s'écrivent `ES_FDC_OUV → TS_OUV`.

Le classeur V1 distingue toujours l'E/S physique, nommée par sa nature
(`ET_SR02AB01_NIV_B`), de sa télétransmission (`TS_NIV_B`, colonne « Télétransmission »).

- **Option A — conserver le modèle actuel** : reprendre du classeur les codes,
  libellés, variantes et types ajoutés ; la colonne « Télétransmission » fixe la
  famille (TS/TM/TC/TR/CP, ou ES si « Selon les règles du type »). Noms générés
  inchangés pour les ouvrages existants ; la colonne « Nom généré (exemple) » du
  classeur n'est alors pas appliquée telle quelle.
- **Option B — adopter le modèle V1** : une variable par E/S physique
  (`ET_/ST_/EA_/SA_`) plus sa variable de télétransmission. Change le nombre de
  variables, l'adressage %MW, les jeux de référence et les exports TOPKAPI : à
  traiter comme nouvelle révision du référentiel, ouvrages existants figés.

Tant que la décision n'est pas consignée dans `docs/INSTRUCTIONS_EN_COURS.md`,
ne modifier ni les codes du catalogue, ni les règles, ni les jeux de référence.
