# Reprise V0.31 — Premier lot de corrections

10 novembre 2026. Suite du plan `DIAGNOSTIC_REPRISE_V031.md`, après accord de
l'utilisateur pour continuer. Branche : `codex/diagnostic-finalisation-v031`.

Suivi : les neuf échecs restants de ce lot ont ensuite été levés par la
restauration de l'archive fournie par l'utilisateur, sans autre correctif métier.
Voir [validation/README.md](../validation/README.md) pour la provenance et
les nouveaux résultats ; le présent rapport décrit le lot avant restauration.

## Corrections démontrées

### Précondition du test Qt

`tests_qt/test_fumee_qt.py::TestInterfaceQt::test_explorateur_ouvrage` ouvre
désormais la page Ouvrage et traite les événements avant de vérifier son arbre.
L'assertion de visibilité est conservée. Aucun comportement de la fenêtre Qt
n'est changé. Le contrôle ciblé et les tests de navigation associés réussissent
(7 tests), puis la suite Qt complète réussit (25 tests).

### Vue Variables web

Deux défauts ont été reproduits dans Chromium avec les véritables API locales :

- Une ligne focalisée s'ouvrait avec Entrée, mais pas avec Espace. Les deux
  touches ouvrent maintenant le détail. Les événements des cases à cocher
  conservent leur comportement natif et n'ouvrent pas le détail.
- En vue Table d'échange et Télétransmission, une cellule était masquée alors
  que son en-tête restait affiché : 8 en-têtes pour 7 cellules visibles. L'en-tête
  suit désormais la même règle que la cellule ; l'état sans résultat utilise
  aussi le nombre de colonnes correspondant. La vue Toutes garde ses 8 colonnes.

Les corrections sont limitées à trois lignes de `v031-variables.js`. Le moteur,
les API, les règles d'adressage, les formats de projets et le référentiel ne
sont pas modifiés.

## Recette reproductible ajoutée

`tests_web/test_variables_v031.py` ajoute six tests Chromium, exécutés séparément
de pytest comme expliqué dans `tests_web/README.md` :

1. Entrée et Espace ouvrent le détail sans appliquer d'adresse.
2. Espace sur une case à cocher sélectionne sans ouvrir le détail.
3. Les en-têtes correspondent aux cellules dans les trois vues, y compris
   après un filtre sans résultat.
4. L'aperçu puis son annulation laissent le fichier projet identique octet pour
   octet et les adresses inchangées.
5. La confirmation applique les propositions du moteur puis les valide avec
   leur trace ; aucune adresse attendue n'est fabriquée dans cette recette.
6. Une modification du projet après l'aperçu rend l'empreinte périmée : réponse
   HTTP 400, aucune application partielle, fichier projet inchangé après refus.

Les ouvrages et le serveur sont créés dans un dossier temporaire, puis fermés
et supprimés par la recette. Aucun ouvrage utilisateur n'est ouvert. Il n'y a
pas de simulation des API ni de qualification dans un logiciel industriel.

Le lancement avant correction a montré les trois assertions en échec attendues
(touche Espace et deux variantes d'en-têtes). Le lancement final réussit :
**6 tests, aucun échec**, sans exception JavaScript. Les tests Python ciblés
V0.31 / Variables V0.29 réussissent également : **9 tests**. La syntaxe JavaScript
et les contrôles Git d'espacement sont conformes.

Suite complète après corrections : **402 tests exécutés, 393 réussis,
9 échoués, aucun ignoré**, en 73,38 s (code de sortie 1). Les neuf échecs sont
exactement les huit tests DDT et le benchmark hybride décrits ci-dessous ;
aucun nouvel échec applicatif n'est apparu dans cette suite. Le rapport JUnit
actuel est conservé hors dépôt dans `lot1-v031/pytest.xml` avec son journal
`pytest.log`. Les 134 avertissements Qt de dépréciation restent distincts
de ces échecs.

Traces locales : `/workspace/ogias-cloud/lot1-v031/web-avant.log`,
`web-final.log`, `qt-cible.log` et `qt-suite.log`. Les résultats sont conservés
ici ; ces fichiers hors dépôt ne sont pas disponibles dans un clone neuf.

## Jeux de validation toujours manquants

La recherche dans les ressources de travail accessibles, les branches/tags
distants, les références locales et les objets Git non référencés n'a pas
retrouvé la fixture `validation/ddt/exemple_DDT_reconstitue.xsy` ni le banc
`validation/hybride/`. Les seules archives repérées dans les répertoires
temporaires accessibles sont des exports TOPKAPI produits par les tests.
Certains répertoires techniques protégés de `/tmp` ne sont pas inspectables ;
aucune affirmation d'absence globale sur ces répertoires n'est faite.

L'utilisateur a fourni deux documents Word, examinés comme références :

- `OGIAS_Referentiel_Adressage_SOFREL_v1.docx` : spécification d'entrée ; le
  document précise qu'un export réel de S4W-Tools est encore nécessaire pour
  figer le format exact et les règles d'affectation.
- `OGIAS_Reference_Adressage_Schneider_v1.docx` : référence de développement
  avec profils et cas à qualifier ; ses exemples de syntaxe ne prouvent pas
  l'existence d'une voie ni une correspondance de communication.

Aucun des deux fichiers n'embarque de pièce jointe contenant les jeux manquants.
Ils ne remplacent donc ni la fixture XSY ni l'évaluateur et ses deux jeux corrigés.
Leurs liens de sources externes n'ont pas été qualifiés pendant ce lot. Aucune
instruction de ces documents n'est transformée implicitement en nouvelle règle
métier, migration ou extension des familles d'automates prises en charge.

Les neuf tests concernés restent exécutés, sans suppression, désactivation,
changement d'attendus ni génération d'une fixture destinée à les faire passer.
Une sauvegarde des fichiers d'origine est nécessaire pour reprendre leur
validation. Si elle est irrécupérable, un nouveau jeu indépendant doit faire
l'objet de l'accord prévu dans le diagnostic initial.

## Suite de la finalisation

Les contrôles de compatibilité exhaustifs, les jeux de référence V0.30, la
recette des autres écrans, les 5 000 lignes, les autres résolutions/thèmes et
les essais Windows restent à mener selon le plan accepté. Ce lot ne clôture
pas V0.31 et ne qualifie aucun export industriel. Le numéro de version reste
inchangé en attendant la recette de livraison.
