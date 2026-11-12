"""Serveur HTTP et Chromium réels, données temporaires, nettoyage garanti."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class ServeurNavigateur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        resources = ExitStack()
        cls.addClassCleanup(resources.close)
        cls.data = Path(resources.enter_context(tempfile.TemporaryDirectory(prefix="ogias-web-tests-")))
        log = resources.enter_context((cls.data / "serveur.log").open("w"))
        python = os.environ.get("OGIAS_TEST_PYTHON", sys.executable)
        entrypoint = os.environ.get("OGIAS_TEST_ENTRYPOINT")
        command = ([python, "-I", "-B", "-X", "utf8", entrypoint, "--sans-navigateur"] if entrypoint else
                   [python, "-u", "-m", "sorep_web", "--sans-navigateur"])
        server = subprocess.Popen(
            command,
            cwd=ROOT, env={**os.environ, "SOREP_DATA_DIR": str(cls.data)},
            stdout=log, stderr=subprocess.STDOUT,
        )

        def stop_server():
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=10)

        resources.callback(stop_server)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            output = (cls.data / "serveur.log").read_text()
            match = re.search(r"http://127\.0\.0\.1:\d+/", output)
            if match:
                cls.url = match.group()
                break
            if server.poll() is not None:
                raise RuntimeError(output)
            time.sleep(0.05)
        else:
            raise RuntimeError("Démarrage OGIAS non confirmé : " + output)

        playwright = resources.enter_context(sync_playwright())
        executable = (os.environ.get("OGIAS_TEST_CHROMIUM") or shutil.which("chromium")
                      or shutil.which("google-chrome"))
        cls.browser = playwright.chromium.launch(
            headless=True, **({"executable_path": executable} if executable else {}),
        )
        resources.callback(cls.browser.close)
        cls.numero = 0

    def api(self, route, data=None):
        request = urllib.request.Request(
            self.url + route.lstrip("/"),
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"{route}: HTTP {error.code}: {error.read().decode()}") from error
