# OGIAS — Référentiel par modèle d’équipement

Date : 6 novembre 2026. Architecture validée par l'utilisateur : **E/S physiques propres à chaque modèle et informations de télétransmission associées**.

## Parcours

1. **Référentiel → Type de matériel → Modèle** : ouvrir « Signaux du modèle — E/S physiques et télétransmission ». Modifier, ajouter ou retirer les E/S physiques (famille `ES`, points `ET`, `ST`, `EA`, `SA`) et les signaux fonctionnels (TS, TM, TC, TR, RTR, CP). Chaque signal reçoit un code unique dans sa famille, un statut de présence et, si applicable, une source physique explicite (`ES_...`).
2. **Valider le modèle** : contrôle des doublons, types logiques, sens des E/S et sources manquantes. Une modification remet le modèle à valider. Une option est une possibilité matérielle, jamais l'affirmation d'une présence sur le site.
3. **Inventaire → Équipement** : choisir un modèle et sélectionner les E/S utilisées. Régler ici, *et non dans le modèle*, les échelles 4–20 mA, facteurs et fronts d'impulsion, raccordements, voies et adresses. Valider explicitement le paramétrage avant la liste d'E/S.
4. **Actualiser un modèle dans un ouvrage** : action explicite, après confirmation. Elle remet à valider tous les équipements du même ouvrage qui partagent ce modèle, ainsi que les affectations concernées. Les anciennes adresses ne sont jamais inventées ou réattribuées à l'ouverture.

## Débitmètre — modèle de référence

- `ES_DEB` : entrée analogique de mesure (EA), retenue par défaut ; `TM_DEB` : télémesure issue de `ES_DEB`.
- `ES_DEF_EXT` : défaut externe (ET, option), éventuellement `TS_DEF_EXT`.
- `ES_IMP` : impulsions de comptage (ET, option), permettant le calcul du volume dans l'automate. Le seul compteur de télétransmission est `CP_VOL` ; **pas de deuxième CP**.
- `ES_SENS` : sens d'écoulement (ET, option), éventuellement `TS_SENS`.
- **Aucune sortie TOR ST de remise à zéro** du débitmètre générique. L'initialisation éventuelle du totalisateur est une fonction dans l'automate.

Les options dépendent du matériel réellement installé. Une source d'acquisition différente (communication numérique ou calcul) doit être définie explicitement dans l'étude d'automatisme.

## Données et compatibilité

- Les modèles actuels contenant les anciennes `lignes` reçoivent **en mémoire** une copie initiale des signaux de leur type. Cela ne réécrit pas à l'ouverture le référentiel utilisateur ; leur contenu reste à vérifier et valider.
- Le nouveau champ `signaux` est enregistré lorsque l'utilisateur modifie un modèle ; il contient le périmètre ES et télétransmission du modèle, sans adresse, échelle ni facteur d'impulsion.
- Un ouvrage déjà enregistré sans `signaux` dans son `modeles_snapshot` reste sur son fonctionnement historique. Les projets nouveaux figent le modèle au moment de l'ajout d'un équipement.
- Les `lignes` documentaires historiques restent consultables dans le référentiel pour compatibilité. Elles **ne constituent pas** la liste des variables physiques et fonctionnelles générées ; c'est désormais le champ `signaux` qui la pilote.
- Le catalogue de type historique demeure disponible pour l'ancienne interface et les ouvrages enregistrés ; il sert aussi de base à la création d'un nouveau modèle, mais **ne modifie plus simultanément tous les modèles du même type**.

## Qualification et limites

- Tests Python : 246 réussis, 25 ignorés. JavaScript : syntaxe contrôlée. Page Référentiel : affichage vérifié dans un navigateur de test avec réponses API simulées.
- **Pas de qualification sur le poste Windows utilisateur**.
- **Pas de qualification dans Control Expert, SOFREL S4W ou TOPKAPI 6.3** ; les exports restent à qualifier.
- La restructuration complète des autres étapes du plan (architecture automate exhaustive, reprise XSY avancée dans le web, distribution Windows autonome, révisions et concurrence multiutilisateur) reste à poursuivre.
- L’ancienne interface Qt n’est pas encore harmonisée avec tous les nouveaux écrans de l’interface web.

## Précautions

Extraire la nouvelle archive dans **un dossier distinct**, conserver une copie de l'ancienne version et **sauvegarder séparément les données utilisateur** avant essai. Aucun ouvrage réel ni adresse d'exploitation n'est préchargé. Ne pas remplacer le dossier de production sans recette.
