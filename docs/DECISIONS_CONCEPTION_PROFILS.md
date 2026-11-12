# Décisions de conception — profils, codification et familles de signaux

Prises le 10/11/2026 par Claude, en concepteur senior, à la demande explicite de l'utilisateur, à partir de
`OGIAS_Specification_Conception_Codification_Profil_VANNE_MV_V1.pdf` (édition 1.0). Principes : aucun
renommage de l'existant sans bénéfice démontré ; n'ajouter que ce qui apporte une information réelle ;
aucune logique automate imposée (D1, D5) ; projets existants protégés (adoption contrôlée).

## Constat

La spécification confirme ce qu'OGIAS fait déjà : doctrine sans logique automate, un profil par technologie,
codification lieu / ensemble / équipement avec lieu hors du nom (« charte 12 » : `RV01MV01`), même suffixe
pour la même information (`ET_RV01MV01_OUV` / `TS_RV01MV01_OUV`), type IEC séparé, adresses jamais inventées.
Elle apporte quatre nouveautés et trois conflits, tranchés ci-dessous.

## Décisions

| N° | Sujet | Décision | Motif |
| --- | --- | --- | --- |
| P1 | Variables internes `BI`, `EI`, `MI`, `RI` | **Adoptées** comme nouvelle famille « interne déclarée » : variables automate non localisées, documentées, exportées en XSY uniquement si **sélectionnées** ; jamais télétransmises, **aucun %MW**, aucune logique ni calcul imposés. | Vrai gain pour l'automaticien ; conforme à D1/D5. |
| P2 | Communication `RX` / `TX` | **Adoptée** dans un second temps : échanges déclarés seulement s'ils existent, adresses importées ou saisies puis validées, jamais générées. | Besoin réel multi-automates ; aucune adresse inventée. |
| P3 | Suffixe « exactement 3 lettres » | **Règle de conception des nouveaux codes** du dictionnaire transversal : un code nouveau hors 3 lettres produit une **alerte** (pas une erreur). Les codes existants (2 à 9 caractères, V1-3-12) sont **conservés** ; un code composé reste admis quand l'information l'exige (`DEF_EXT`, D2). | L'appliquer à l'existant renommerait ~70 % des codes et casserait les projets et TOPKAPI. |
| P4 | Préfixe `RT` contre `RTR` | **`RTR` conservé.** `RT` est noté comme variante de standard de site, non implémentée. | Changer renommerait tous les retours de téléréglage TOPKAPI existants. |
| P5 | Profil VANNE_MV | Le type **MV est le profil VANNE_MV** (vanne TOR motorisée sans rappel). Ajouts, en **option** : sortie `ST_<repère>_ARR` (« Arrêt dédié câblé »), suggestions `TS_DOV` et `TS_DFE` (« Défauts de manœuvre détaillés ») ; `TS_DEFTPS` conservé. Variables internes candidates BI (P1) : `OUV`, `FER`, `DOV`, `DFE`, `DIS`, `DEF`, non sélectionnées par défaut. | Information réelle sans doublon ; aucune entrée obligatoire ajoutée. |
| P6 | Options modulantes de MV (`POS`, `CONS_POS`, `TM_POS`, `TR_POS`, `RTR_POS`) | **Conservées** tant que FV (vanne de régulation) n'a pas ses E/S (point A1) ; ensuite **dépréciées** pour les nouveaux projets par une révision du référentiel et une correspondance MV → FV, jamais supprimées des projets existants. | Le profil VANNE_MV exclut le modulant, mais FV n'est pas prêt. |
| P7 | Suffixes proposés par la spécification (`BOU`, `BFE`, `BAR`, `DIS`, `ARR` pour l'arrêt distant) | **Non appliqués** aux codes existants (`BP_OUV`, `BP_FER`, `BP_AR`, `DISC`, `TC_AR`) ; inscrits au dictionnaire comme **propositions** pour un futur standard de site. | Renommage sans gain fonctionnel ; la spécification les marque « À ARBITRER ». |
| P8 | Homonymes quand le lieu n'est pas dans le nom | **Contrôle à ajouter** : deux variables de même nom dans un même périmètre cible (programme automate ou table d'échange commune) → erreur avec demande d'arbitrage. | Le lieu absent du nom rend la collision possible entre sites. |
| P9 | Standard de codification | Cible à moyen terme : **standard sélectionnable** (table des préfixes, règle de suffixe, familles actives) ; le standard actuel reste celui des projets existants. Non prioritaire avant la 1.0. | Adaptabilité demandée par la spécification sans rupture. |

## Lots autorisés (sans nouvelle validation)

Ordre : **P5** (options MV `ST_ARR`, `TS_DOV`, `TS_DFE` dans le référentiel livré, avec tests : options
désactivées → aucun signal ajouté ; aucun %MW pour `ST_ARR`) → **P1** (famille interne déclarée : modèle,
sélection, export XSY non localisé, tests « non sélectionné → absent », « jamais dans TOPKAPI ni la table
d'échange ») → **P3** (alerte du dictionnaire) → **P8** (contrôle d'homonymes). Interface correspondante :
Codex. **P2, P6, P9** : après la 1.0 ou après décision A1.

**Mise en œuvre de P5 (11/11/2026, Claude)** — fait, tests `tests/test_profil_vanne_mv_p5.py`. Arbitrage
réversible : la sortie d'arrêt est nommée **`ST_<repère>_AR`** (clé `ES_AR`) et non `ST_<repère>_ARR`, pour
respecter la doctrine validée n° 3 (même suffixe que la télécommande existante `TC_AR`, comme
`ST_…_OUV` / `TC_…_OUV`) et la pratique déjà livrée des types PD, SP, SV, XV (code `AR`, ligne V1 `CMD_AR`).
`ARR` reste une proposition de futur standard (P7). Aucune règle ne lie `ES_AR` à `TC_AR` : la télécommande
reste portée par l'option « Télécommandée ». Statut des trois signaux : « À valider ». **À confirmer par
l'utilisateur** (AR ou ARR) ; aucun projet ne les emploie encore, le changement serait sans migration.

**Décision de l'utilisateur (11/11/2026) : suffixe sur 3 lettres, `ST_<repère>_ARR`** (clé `ES_ARR`), conforme
au texte de P5 et à la règle P3. Appliqué au référentiel livré sans migration (aucun projet ne l'employait).
La télécommande existante `TC_AR` n'est pas renommée (P7). Tests : `tests/test_profil_vanne_mv_p5.py`.

**Mise en œuvre de P1 (11/11/2026, Claude)** — mécanisme fait, tests `tests/test_variables_internes_p1.py`.
Familles `BI`, `EI`, `MI`, `RI` (`catalogue.FAMILLES_INTERNES`) : point « Interne » obligatoire, présence
« Option » obligatoire (retenue seulement si l'option est cochée sur l'équipement, retrait individuel par
`exclus`), ou signal propre de l'équipement ; ni E/S source, ni alarme, ni `suffixe_es` ; une règle « auto » ne
peut pas la retenir d'office (anomalie du référentiel, et `regles.evaluer` la laisse « proposée »).
`modele.generer_internes` les produit ; `generer` (table d'échange, %MW, TOPKAPI, Excel) et `generer_points`
les ignorent ; l'export XSY les ajoute **après** les variables d'échange, sans `topologicalAddress` (format de
variable non localisée déjà présent dans l'échantillon Control Expert ; import réel non essayé). Contrôles :
longueur, caractères et doublons des noms, type logique pris en charge, homonymes P8. **Type logique : celui
déclaré pour chaque signal, jamais déduit de la famille** (types EI/MI/RI non spécifiés). **Aucune variable
interne ajoutée au référentiel livré** : les candidats BI de MV attendent la décision (sens de `DIS`, type).

**Décision de l'utilisateur (11/11/2026) : candidats BI de MV ajoutés** au référentiel livré, option
« Variables internes » (non cochée par défaut), BOOL, statut « À valider » : `BI_OUV`, `BI_FER`, `BI_DOV`,
`BI_DFE`, `BI_DEF`, **`BI_DIS` = disponible**, **`BI_DSC` = discordance de position**. Placés après les
signaux existants de MV : ordre et adresses d'échange inchangés. Les codes télétransmis existants (`TS_DISPO`,
`TS_DISC`) ne sont pas renommés. Tests : `tests/test_variables_internes_p1.py`.

Interdits maintenus : aucun renommage d'un code existant, aucune donnée réelle, aucune logique automate,
aucune adresse inventée, projets existants inchangés sans adoption confirmée.

---

# Décisions — référentiel, publication et propagation des profils (V1.0 du 10/11/2026)

Prises par Claude à la demande de l'utilisateur, à partir de
`OGIAS_Exigences_Referentiel_Profils_Propagation_V1.pdf`. Ici, **profil = type d'équipement** du référentiel
(et ses modèles) ; **instance = équipement** d'un ouvrage.

## Déjà en place (à réutiliser, ne pas refaire)

Cycle brouillon → validation → publication avec révisions et retour arrière (`referentiel_depot`) ;
archivage et suppression bloquée si utilisé (L6) ; adaptations locales d'un équipement (`exclus`, signaux
ajoutés, `libelles`, `commentaires`, `es_meta`, options) sans effet sur le maître ; référentiel figé par
ouvrage ; adoption contrôlée avec aperçu, confirmation, report des adresses et exclusions, sauvegarde, retour
arrière (L2) ; aucune logique automate (D1, D5).

## Décisions

| N° | Exigence | Décision |
| --- | --- | --- |
| R2 | Version par profil | Version **calculée**, pas stockée à part : empreinte SHA-256 du profil (type + ses signaux + ses règles + ses modèles) dans chaque révision publiée ; la version du profil s'incrémente à chaque révision publiée où son empreinte change. Aucune seconde source de vérité. |
| R3 | État de synchronisation d'une instance | Empreinte du profil dans le référentiel figé de l'ouvrage comparée à la version publiée : « À jour », « Mise à jour disponible », « Mise à jour à examiner » (conflit). Affiché par équipement et par profil. |
| R4 | Conflits avec les surcharges locales | L'aperçu d'adoption signale chaque propriété maître modifiée alors que l'instance la surcharge (`libelles`, `commentaires`, `es_meta`) ou l'exclut : la surcharge est **conservée** et le conflit **affiché**, jamais résolu en silence. « Revenir au standard » par propriété, après confirmation. |
| R5 | Rapport d'impact multi-ouvrages | À la publication : liste de tous les ouvrages enregistrés et équipements concernés par chaque profil modifié, avec leur état (R3), sans rien modifier. L'application reste ouvrage par ouvrage par l'adoption contrôlée. |
| R6 | Propagation automatique en conception | **Limitée** aux ouvrages jamais validés ni exportés, et aux changements sans conflit ni renommage ; même dans ce cas : aperçu puis **acceptation en un geste**, jamais d'application silencieuse. Ouvrage validé ou existant : confirmation ligne à ligne (L2), inchangée. |
| R7 | Journal des décisions | Journal ajouté au fichier de l'ouvrage : profil, version, équipement, action (adoption, refus, retour au standard, annulation), date, opérateur (nom de session Windows), sauvegarde associée. |
| R8 | Présentation | Pastilles Brouillon (orange), Publié (vert), Archivé (gris), **toujours avec un libellé lisible** ; indicateur distinct « Révision en cours ». Interface : Codex. |
| R9 | Unicité des noms dans l'ouvrage / l'automate | Confondu avec P8. |

## Ordre des lots (remplace l'ordre précédent)

1. **P5** : options MV `ST_ARR`, `TS_DOV`, `TS_DFE`.
2. **P8 / R9** : contrôle des homonymes.
3. **R2 + R3** : version calculée par profil et état de synchronisation (moteur, tests).
4. **R4** : conflits de surcharge dans l'aperçu d'adoption, « revenir au standard » (moteur, tests).
5. **R5 + R7** : rapport d'impact multi-ouvrages et journal des décisions.
6. **R6** : acceptation en un geste pour les ouvrages en conception.
7. Interface (Codex, en parallèle dès que le moteur expose les données) : R8, états de synchronisation,
   conflits, rapport d'impact, journal.
8. Ensuite seulement : **P1** (variables internes), puis P3.

Garde-fous : aucune modification partielle silencieuse (échec → état « Mise à jour à examiner » et rapport) ;
aucun ouvrage validé modifié sans accord ; adresses, associations et exports préservés tant que les
changements ne sont pas acceptés.
