# Recette web OGIAS

Cette suite pilote Chromium avec les véritables fichiers HTML/CSS/JS et le
serveur HTTP OGIAS. Elle utilise des ouvrages fictifs dans un dossier temporaire ;
les adresses du scénario de confirmation proviennent uniquement du moteur
existant. Aucun fichier de production ni fixture DDT manquante n'est utilisé.

Dans un environnement Python de développement disposant des dépendances de
`requirements-qt.txt`, installer Playwright (version vérifiée : 1.62.0) et un
Chromium compatible, puis lancer depuis la racine du dépôt :

```bash
python -m pip install -r requirements-qt.txt playwright==1.62.0
python -m unittest discover -s tests_web -v
```

La suite utilise le Chromium installé sur le système s'il est disponible ; à
défaut, installer le navigateur géré par Playwright avec
`python -m playwright install chromium`. `OGIAS_TEST_CHROMIUM` permet de choisir
explicitement l'exécutable. `OGIAS_TEST_PYTHON` permet de choisir le Python du
serveur lorsque Playwright et les dépendances applicatives sont dans des
environnements distincts. Aucun contournement de vérification TLS n'est requis.

Dans l'environnement cloud déjà préparé :

```bash
OGIAS_TEST_PYTHON=/workspace/.venvs/ogias/bin/python \
OGIAS_TEST_CHROMIUM=/usr/bin/chromium \
python3 -m unittest discover -s tests_web -v
```

Cette recette complémentaire s'exécute séparément de `python -m pytest`, dont
les chemins configurés restent `tests` et `tests_qt`. Elle doit être exécutée
après une modification de l'interface. Elle couvre aussi le lexique, le dictionnaire,
les correspondances, l'archivage et l'adoption contrôlée (sauvegarde téléchargeable,
retour arrière exact, confirmation individuelle, aperçu périmé et refus affichés).
`OGIAS_CAPTURE_DIR` choisit le dossier des captures ; par défaut : `artifacts/ci/captures`.
Une dépendance ou un navigateur
absent provoque un échec explicite ; aucun test n'est silencieusement ignoré.
