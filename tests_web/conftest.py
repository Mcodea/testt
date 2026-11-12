"""Rendre les échecs navigateur lisibles dans les annotations GitHub Actions."""
import os


def pytest_runtest_logreport(report):
    if not report.failed or os.environ.get('GITHUB_ACTIONS') != 'true':
        return
    fichier, ligne, _ = report.location
    texte = report.longreprtext
    if len(texte) > 10000:
        texte = texte[:7000] + '\n[…]\n' + texte[-3000:]
    texte = (report.nodeid + '\n' + texte).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print(f'\n::error file={fichier},line={ligne + 1},title=Échec navigateur::{texte}', flush=True)
