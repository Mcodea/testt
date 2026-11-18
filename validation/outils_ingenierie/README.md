# Outils d'ingénierie de l'ouvrage (étape 1)

Décision du 18/11/2026 : plutôt que des « profils », chaque ouvrage déclare les outils réellement utilisés ;
OGIAS applique les règles propres à ces outils, et seulement à eux. Les conventions du maître d'ouvrage (charte de
nommage, plages %MW) sont l'étape suivante : elles ne dépendent d'aucun outil.

| Outil | Où il se choisit | Règle propre appliquée |
| --- | --- | --- |
| Automate / source d'acquisition | Fiche d'identification (inchangé) | M340, M580 : valeur 32 bits sur adresse %MW paire (R-VAR-07, R-EXI-03) |
| Communication | Fiche d'identification (inchangé) | — |
| Supervision | Bloc « Outils d'ingénierie » (nouveau) ; TOPKAPI par défaut | TOPKAPI : libellé de 40 caractères au plus (R-VAR-10) |
| IHM | Bloc « Outils d'ingénierie » (nouveau) ; aucune par défaut | — (format Vijeo non décrit) |

Avant, ces deux règles s'appliquaient à tous les ouvrages, quel que soit l'outil. Un outil non décrit dans OGIAS
n'entraîne aucune règle : rien n'est supposé. Les listes « Supervisions » et « IHM » s'enrichissent par « Gérer
les listes ». Les ouvrages enregistrés gardent TOPKAPI : leur comportement ne change pas.

Défaut corrigé au passage : depuis le 16/11, l'automate s'enregistre « Sch - M340 » ; deux contrôles des projets
existants comparaient encore le nom exact « M340 » et ne se déclenchaient donc plus (adresse paire en 32 bits).
