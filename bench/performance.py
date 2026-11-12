"""Banc bloquant V1 : 300 équipements, 5 000 variables, aucun ouvrage réel."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

from genvar.catalogue import Catalogue
from genvar.modele import Equipement, Ouvrage, SignalPropre
from genvar.session import Session

LIMITS = {"ouverture": 2, "generation": 3, "adressage": 2, "import_topkapi_70": 10,
          "exports": 5, "interface": 0.2, "filtrage": 0.2}


def fixture() -> Session:
    types = ("HV", "MV", "PM", "LT")
    catalogue = Catalogue(types=[{"code": name, "designation": "Équipement fictif", "options": []}
                                 for name in types])
    ouvrage = Ouvrage(lieu="XTST", code_ouvrage="RV", numero_ouvrage="01", automate="M340",
                      lieu_dans_le_nom=False, libelle="Banc de performance entièrement fictif")
    for index in range(300):
        signals = [SignalPropre(f"Signal fictif {j}", "TS", f"V{j:02d}")
                   for j in range(1, (17 if index < 200 else 16) + 1)]
        ouvrage.equipements.append(Equipement("00", types[index % 4], f"{index // 4 + 1:02d}",
                                              libelle="Équipement fictif", ajouts=signals))
    return Session(catalogue, ouvrage)


def browser_measurements(project: Path, data: Path) -> dict[str, float]:
    from playwright.sync_api import sync_playwright

    log = data / "serveur-bench.log"
    with log.open("w", encoding="utf-8") as output:
        process = subprocess.Popen([sys.executable, "-u", "-m", "sorep_web", "--sans-navigateur"],
                                   env={**os.environ, "SOREP_DATA_DIR": str(data)}, stdout=output,
                                   stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                match = re.search(r"http://127\.0\.0\.1:\d+/", log.read_text(encoding="utf-8"))
                if match:
                    break
                if process.poll() is not None:
                    raise RuntimeError(log.read_text(encoding="utf-8"))
                time.sleep(0.05)
            else:
                raise RuntimeError("Serveur du banc non démarré")
            request = urllib.request.Request(match.group() + "api/ouvrir",
                                             data=json.dumps({"chemin": str(project)}).encode(),
                                             headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=30) as response:
                assert response.status == 200
            with sync_playwright() as playwright:
                options = {"executable_path": os.environ["OGIAS_TEST_CHROMIUM"]} if os.environ.get("OGIAS_TEST_CHROMIUM") else {}
                browser = playwright.chromium.launch(headless=True, **options)
                try:
                    page = browser.new_page(viewport={"width": 1366, "height": 768})
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(match.group() + "#/variables", wait_until="networkidle")
                    page.wait_for_selector("#v31-var-search", timeout=30000)
                    timings = page.evaluate("""async () => {
                      if (E.detailEtape.lignes.length !== 5000) throw Error('5000 variables attendues');
                      const paint = () => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                      let start = performance.now();
                      vueVariablesV31();
                      document.querySelector('.v31-table').getBoundingClientRect();
                      await paint();
                      const render = performance.now() - start;
                      start = performance.now();
                      const input = document.querySelector('#v31-var-search');
                      input.value = 'V01'; input.dispatchEvent(new Event('input', {bubbles:true}));
                      document.querySelector('.v31-table').getBoundingClientRect();
                      await paint();
                      return {interface:render / 1000, filtrage:(performance.now()-start) / 1000};
                    }""")
                    assert not errors, errors
                    assert page.locator(".v31-variable-row").count() > 0
                    return timings
                finally:
                    browser.close()
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


def run() -> dict:
    from genvar.adressage import adresse_topkapi
    from genvar.formats_topkapi import PointTopkapi, ecrire_octets, lire

    results = {}

    def measure(name, function):
        start = time.perf_counter()
        value = function()
        results[name] = time.perf_counter() - start
        return value

    with tempfile.TemporaryDirectory(prefix="ogias-bench-") as temporary:
        data = Path(temporary)
        previous = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = temporary
        try:
            session = fixture()
            assert len(session.ouvrage.equipements) == 300
            assert len(session.variables()) == 5000
            project = data / "XTSTRV01.ouvrage.json"
            session.enregistrer(str(project))
            measure("ouverture", lambda: session.ouvrir(str(project)))
            variables = measure("generation", session.variables)
            assert len(variables) == 5000

            def address():
                plan = session.plan_adressage()
                assert not plan.conflits
                session.appliquer_adressage(plan.empreinte, niveaux=("automate",))

            measure("adressage", address)
            variables = session.variables()
            assert all(v.adresse for v in variables)
            paths = []
            for index in range(70):
                path = data / f"fictif-{index:02d}.$$t"
                points = [PointTopkapi(v.nom, adresse_topkapi(v.adresse), "0", "Signal fictif")
                          for v in variables[index::70]]
                path.write_bytes(ecrire_octets(points))
                paths.append(path)
            assert sum(len(points) for points in measure("import_topkapi_70", lambda: [lire(p) for p in paths])) == 5000

            def exports():
                session.exporter_xsy(str(data / "fictif.xsy"))
                session.exporter_excel(str(data / "fictif.xlsx"))

            measure("exports", exports)
            session.enregistrer(str(project))
            results.update(browser_measurements(project, data))
        finally:
            if previous is None:
                os.environ.pop("SOREP_DATA_DIR", None)
            else:
                os.environ["SOREP_DATA_DIR"] = previous
    return {"equipements": 300, "variables": 5000, "fichiers_topkapi": 70,
            "seconds": results, "limits_seconds": LIMITS,
            "failures": [name for name, seconds in results.items() if seconds >= LIMITS[name]]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/ci/performance.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = run()
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(bool(report["failures"]))
