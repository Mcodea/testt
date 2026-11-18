"""Serveur OGIAS jetable avec un ouvrage FICTIF, pour les captures et le registre des actions de la refonte.

Usage : python outils/interface_demo.py <dossier de travail>
Écrit l'adresse du serveur dans <dossier>/url.txt puis reste actif jusqu'à l'arrêt du processus.
Aucune donnée réelle : lieu « XTST », réservoir fictif, quinze équipements génériques.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request

RACINE = Path(__file__).resolve().parents[1]


def main(sortie: Path) -> None:
    sortie.mkdir(parents=True, exist_ok=True)
    donnees = sortie / "donnees"
    shutil.rmtree(donnees, ignore_errors=True)
    (sortie / "url.txt").unlink(missing_ok=True)
    journal = sortie / "serveur.log"
    with open(journal, "w", encoding="utf-8") as log:
        srv = subprocess.Popen([sys.executable, "-u", "-m", "sorep_web", "--sans-navigateur"], cwd=RACINE,
                               env={**os.environ, "SOREP_DATA_DIR": str(donnees)},
                               stdout=log, stderr=subprocess.STDOUT)
    url = ""
    for _ in range(600):
        m = re.search(r"http://127\.0\.0\.1:\d+/", journal.read_text(encoding="utf-8"))
        if m:
            url = m.group()
            break
        time.sleep(0.05)
    if not url:
        srv.kill()
        raise SystemExit("Le serveur OGIAS n'a pas démarré : voir " + str(journal))

    def api(route: str, corps: dict | None = None):
        req = urllib.request.Request(url + route.lstrip("/"), data=None if corps is None else json.dumps(corps).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r:
            return json.load(r)

    api("/api/listes-ouvrage/action", {"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
    api("/api/nouveau", {"mode": "Neuf"})
    api("/api/fiche-ouvrage", {"action": "creer", "identification": {
        "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "01", "revision": "A",
        "libelle": "Réservoir fictif de démonstration d'interface", "automate": "Sch - M340"}})
    idents = []
    for k, t in enumerate(["PM", "MV", "HV"] * 5):
        i = api("/api/equipement/ajouter", {"type": t, "numero": f"{k + 1:02d}", "se": "00"})["ident"]
        api("/api/equipement/proposition", {"ident_eq": i, "decision": "retenir"})
        idents.append(i)
    api("/api/equipement/valider", {"idents": idents, "valide": True})
    pts = api("/api/es")["points"]
    api("/api/es/valider", {"niveau": "contenu", "paires": [{"ident_eq": p["ident_eq"], "cle": p["cle"]} for p in pts]})
    api("/api/materiel/action", {"action": "config", "alimentation": "BMX CPS 3500", "processeur": "BMX P34 2020",
                                 "communication": ["BMX NOE 0100"]})
    api("/api/materiel/action", {"action": "appliquer"})
    try:
        api("/api/modules", {"action": "implanter"})
    except Exception:                                       # noqa: BLE001 — l'implantation est facultative ici
        pass
    (sortie / "url.txt").write_text(url, encoding="utf-8")
    print(url, flush=True)
    srv.wait()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]))
