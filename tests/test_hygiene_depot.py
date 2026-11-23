"""Hygiène du dépôt (cahier V1-10-14) : aucun fichier temporaire, aucune sauvegarde de travail, aucun secret suivi."""
import re
import subprocess
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
TEMPORAIRES = re.compile(r"(\.tmp|\.bak|\.orig|\.rej|\.swp|\.pyc|~)$|(^|/)(__pycache__|\.DS_Store|Thumbs\.db)(/|$)|\.verrou$")
SECRETS = [re.compile(p) for p in (r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", r"\bghp_[A-Za-z0-9]{30,}", r"\bgithub_pat_[A-Za-z0-9_]{30,}",
                                   r"\bAKIA[0-9A-Z]{16}\b", r"\bsk-[A-Za-z0-9]{32,}", r"xox[baprs]-[A-Za-z0-9-]{20,}")]
EXTENSIONS_TEXTE = {".py", ".js", ".json", ".md", ".txt", ".yml", ".yaml", ".html", ".css", ".bat", ".lock", ".ini", ".toml", ".csv", ".xsy"}


def _suivis():
    try:
        sortie = subprocess.run(["git", "ls-files"], cwd=RACINE, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        raise unittest.SkipTest("dépôt git indisponible (archive extraite)")
    return [x for x in sortie.splitlines() if x]


class TestHygieneDepot(unittest.TestCase):
    def test_aucun_fichier_temporaire_suivi(self):
        trouves = [f for f in _suivis() if TEMPORAIRES.search(f)]
        self.assertEqual(trouves, [])

    def test_aucun_secret_suivi(self):
        trouves = []
        for f in _suivis():
            chemin = RACINE / f
            if chemin.suffix.lower() not in EXTENSIONS_TEXTE or not chemin.is_file() or chemin.stat().st_size > 2_000_000:
                continue
            texte = chemin.read_text(encoding="utf-8", errors="ignore")
            trouves += [f"{f} : {p.pattern[:30]}" for p in SECRETS if p.search(texte)]
        self.assertEqual(trouves, [])

    def test_aucun_fichier_d_environnement_suivi(self):
        suspects = [f for f in _suivis() if re.search(r"(^|/)(\.env(\..*)?|id_rsa|id_ed25519|credentials\.json|.*\.pem|.*\.key)$", f)]
        self.assertEqual(suspects, [])


if __name__ == "__main__":
    unittest.main()
