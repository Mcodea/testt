# Modèles de livrables rangés par logiciel cible (lot 8, 22/11/2026)

Suite du principe « typicals » retenu le 19/11. Un symbole de pompe TOPKAPI n'existe pas dans PcVue, un bloc
Control Expert n'existe pas dans TIA Portal : un seul modèle par type d'équipement ne peut pas servir à tous les
clients. Chaque modèle de la bibliothèque déclare donc **pour quel logiciel** il est écrit, et l'ouvrage ne retient
que les modèles de **ses** logiciels.

## Ce que fait OGIAS

1. **Destination et logiciel du modèle** (facultatifs) : automate, supervision ou IHM, et le nom du logiciel tel que
   l'atelier l'emploie (TOPKAPI, PcVue, Control Expert…). OGIAS ne devine pas ces noms et ne vérifie pas qu'ils
   existent. Ils se déclarent à l'import, dans l'assistant « Créer depuis un export », ou plus tard dans la fiche du
   modèle (le fichier du modèle n'est pas touché). Un modèle sans logiciel déclaré sert à tout ouvrage, comme avant.
2. **Types produits** : déduits du modèle lui-même. Un bloc `DEBUT_EQUIPEMENTS_PM` produit les pompes ; un bloc
   sans filtre, ou une liste de variables, produit tout l'ouvrage (« Tous »).
3. **Choix par l'ouvrage** : la supervision et l'IHM de la fiche de l'ouvrage (issues de son standard) ; pour
   l'automate, l'automate saisi et, pour M340 / M580, Control Expert (correspondance déjà établie dans OGIAS). La
   casse et les espaces ne comptent pas.
4. **Génération groupée** (« Tous les livrables ») : un modèle d'un autre logiciel est « non retenu », avec son
   motif au journal. Un type d'équipement de l'ouvrage qu'aucun modèle sans erreur ne couvre pour le logiciel de
   l'ouvrage est « manquant » : **rien n'est produit à sa place**, jamais la brique d'un autre logiciel.
5. **Couverture par logiciel** (Standards d'ingénierie › Modèles de livrables) : pour chaque logiciel, les types
   couverts et les modèles en erreur ; les briques manquantes de l'ouvrage ouvert sont listées, ainsi que dans
   Recette et livrables.

Un manque n'est signalé que si l'atelier a au moins un modèle pour le logiciel de l'ouvrage dans cette destination :
un atelier qui n'utilise pas de modèle pour sa supervision n'a aucune alerte.

Depuis Recette et livrables, un modèle « Autre logiciel » reste générable à la demande (choix explicite) ; il n'entre
pas dans « Tous les livrables ».

## Limites

- Aucun vrai format de supervision n'a encore été essayé : les essais utilisent des modèles fictifs.
- Destinations limitées à l'automate, la supervision et l'IHM (les champs que la fiche de l'ouvrage connaît). Un
  outil de schéma électrique n'est pas une donnée de l'ouvrage aujourd'hui.

## Vérifications

- `tests/test_modeles_par_logiciel.py` (9 tests) : cible contrôlée et modifiable sans toucher au fichier, ancien
  index sans cible, types couverts, choix par l'ouvrage (casse, M580 → Control Expert, IHM non déclarée), brique
  manquante au journal et rien produit à sa place, modèle en erreur qui ne couvre rien, aucune attente sans modèle du
  logiciel de l'ouvrage, API de l'écran.
- `tests_web/test_coque_bureau.py::test_modeles_par_logiciel_cible` : badges, couverture, manques, correction de
  la destination depuis la fiche, ouvrage inchangé à l'octet.

## Captures (données fictives XTST)

`bibliotheque_par_logiciel.png`, `recette_modeles.png`.
