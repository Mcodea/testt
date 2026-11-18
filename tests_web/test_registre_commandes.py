"""Aucune commande perdue (refonte de l'interface) : chaque commande visible d'un écran au lot 0 doit l'être encore.

Lance le serveur de démonstration FICTIF (outils/interface_demo.py), relève les commandes visibles de chaque écran
(outils/interface_releve.py, sans captures) et les compare au registre de référence
validation/refonte_interface/lot0_avant/actions.json. Une commande déplacée (ruban, panneau de sortie) est retrouvée ;
une commande disparue fait échouer l'essai.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "outils"))

from interface_releve import disparues, releve  # noqa: E402

REFERENCE = RACINE / "validation" / "refonte_interface" / "lot0_avant" / "actions.json"


class TestRegistreCommandes(unittest.TestCase):
    def test_aucune_commande_disparue_depuis_le_lot_0(self):
        with tempfile.TemporaryDirectory(prefix="ogias-registre-") as dossier:
            dossier = Path(dossier)
            serveur = subprocess.Popen([sys.executable, str(RACINE / "outils" / "interface_demo.py"), str(dossier)],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            try:
                url = ""
                for _ in range(600):
                    if (dossier / "url.txt").exists():
                        url = (dossier / "url.txt").read_text(encoding="utf-8").strip()
                        if url:
                            break
                    if serveur.poll() is not None:
                        break
                    time.sleep(0.1)
                self.assertTrue(url, "Le serveur de démonstration n'a pas démarré")
                resultat = releve(url, dossier / "releve", captures=False)
                self.assertEqual(resultat["erreurs_js"], [])
                self.assertEqual(disparues(REFERENCE, dossier / "releve" / "actions.json"), {})
            finally:
                serveur.terminate()
                try:
                    serveur.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    serveur.kill()


if __name__ == "__main__":
    unittest.main()
