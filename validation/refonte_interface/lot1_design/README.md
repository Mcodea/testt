# Lot 1 — Système de design (18/11/2026)

Une source unique pour les couleurs, polices, tailles, espacements et rayons : `sorep_web/static/ogias.css`,
chargée en dernier. Les trois générations de variables des anciennes feuilles (app.css, v031.css,
industrial-ui.css) y sont rebranchées : toute l'interface prend la même palette, dans les deux thèmes.

## Jetons

| Famille | Jetons |
| --- | --- |
| Surfaces | `--o-fond`, `--o-surface`, `--o-surface-2`, `--o-surface-3`, `--o-ligne`, `--o-ligne-forte`, `--o-champ-bord` |
| Textes | `--o-texte`, `--o-texte-2`, `--o-texte-3` |
| Structure | `--o-nuit`, `--o-nuit-2`, `--o-nuit-ligne`, `--o-nuit-texte`, `--o-nuit-texte-2` |
| Action | `--o-action`, `--o-action-plein`, `--o-action-survol`, `--o-action-fond`, `--o-sur-action` |
| États | `--o-ok*`, `--o-alerte*`, `--o-erreur*` (texte, fond, filet) |
| Polices | `--o-police` (Segoe UI), `--o-mono` (OGIAS-Mono embarquée) |
| Échelles | tailles `--o-t-xs` à `--o-t-xxl` (6), espacements `--o-e-1` à `--o-e-6` (4 px), rayons `--o-r-s/m/l` (3) |

Clair = bureau d'études (bleu nuit #14243B, bleu d'action #1F5FBF). Sombre = salle de contrôle.

## Garde-fous (`tests/test_systeme_design.py`)

- `ogias.css` est la dernière feuille chargée ; aucune couleur écrite hors des deux blocs de jetons ;
- les deux thèmes définissent les mêmes jetons ;
- **contrastes WCAG 2.1 AA calculés** : 4,5:1 pour chaque texte sur chaque surface, 3:1 pour les bordures de champ,
  dans les deux thèmes (deux valeurs ont été corrigées pour y arriver : texte d'aide en clair, survol en sombre) ;
- cliquet : les anciennes feuilles ne peuvent plus gagner de couleur en dur ni de `!important` ;
- aucune nouvelle feuille de style.

Les essais navigateur comparent désormais l'interface aux jetons (`self.jeton('--o-surface')`) et non plus à des
couleurs recopiées.

## Vérification

- Tests moteur : 729 réussis ; essais navigateur : 88 réussis ; ruff ; scripts.
- Registre des commandes comparé au lot 0 : **aucune commande disparue** sur les neuf écrans.
- Captures : `captures/` (Matériel et Variables, clair et sombre).

## Visible pour l'utilisateur

Changement volontairement discret : palette unifiée (fini les trois bleus et les trois gris différents d'un écran
à l'autre), bordures de champ plus lisibles, barres de défilement fines, focus clavier identique partout.
Le changement visible commence au lot 2 (coque de bureau).
