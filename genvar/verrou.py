"""Verrou d'ouvrage (cahier V1-7-04) : un même ouvrage n'est jamais modifié par deux OGIAS à la fois.

À l'ouverture ou à la création d'un ouvrage, OGIAS écrit à côté du fichier `<fichier>.verrou` (JSON : jeton,
ordinateur, utilisateur, processus, depuis). Un second OGIAS qui veut ouvrir le même ouvrage est refusé avec ces
informations.

- Un verrou laissé par un OGIAS arrêté brutalement sur le MÊME ordinateur (processus disparu) est repris
  automatiquement.
- Un verrou d'un AUTRE ordinateur ne peut être repris que sur demande explicite (« forcer ») : OGIAS ne peut pas
  savoir si l'autre poste travaille encore.
- L'OGIAS qui a perdu son verrou ne peut plus enregistrer : ses modifications ne remplacent jamais en silence
  celles du poste qui a repris l'ouvrage.

Création du verrou atomique (O_EXCL). Aucune donnée de l'ouvrage n'est écrite dans le verrou.
"""
from __future__ import annotations

import getpass
import json
import os
import socket
import sys
import uuid
from datetime import datetime, timezone


class VerrouPris(ValueError):
    """Ouvrage verrouillé par un autre OGIAS : le message s'affiche tel quel ; `detail` décrit le détenteur."""

    def __init__(self, message: str, detail: dict):
        super().__init__(message)
        self.detail = detail


def chemin_verrou(chemin: str) -> str:
    return os.path.abspath(chemin) + ".verrou"


def _hote() -> str:
    return socket.gethostname() or "poste inconnu"


def _utilisateur() -> str:
    try:
        return getpass.getuser()
    except Exception:                       # noqa: BLE001 — variable d'environnement absente
        return "utilisateur inconnu"


def processus_actif(pid: int) -> bool:
    """Vrai si le processus existe sur cet ordinateur. Sous Windows, jamais os.kill(pid, 0) : le signal 0 y est
    CTRL_C_EVENT et interromprait le processus."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        k = ctypes.windll.kernel32                                     # type: ignore[attr-defined]
        h = k.OpenProcess(0x1000, False, pid)                          # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(k.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259   # STILL_ACTIVE
        finally:
            k.CloseHandle(h)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def lire(chemin: str) -> dict | None:
    try:
        with open(chemin_verrou(chemin), encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {}                            # verrou illisible : traité comme pris par un inconnu


def _ecrire_exclusif(chemin: str, contenu: dict) -> bool:
    try:
        fd = os.open(chemin_verrou(chemin), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(contenu, fh, ensure_ascii=False)
    return True


def description(d: dict) -> str:
    if not d:
        return "un autre OGIAS (verrou illisible)"
    depuis = str(d.get("depuis", ""))[:16].replace("T", " ")
    return f"{d.get('utilisateur', '?')} sur {d.get('hote', '?')} depuis le {depuis} UTC"


def prendre(chemin: str, jeton: str, forcer: bool = False) -> dict:
    """Prend le verrou de l'ouvrage pour `jeton`. Lève VerrouPris si un autre OGIAS le détient."""
    contenu = {"jeton": jeton, "hote": _hote(), "utilisateur": _utilisateur(), "pid": os.getpid(),
               "depuis": datetime.now(timezone.utc).isoformat(timespec="seconds"), "logiciel": "OGIAS"}
    for _ in range(2):
        if _ecrire_exclusif(chemin, contenu):
            return contenu
        actuel = lire(chemin)
        if actuel is None:
            continue                          # libéré entre-temps : nouvel essai
        if actuel.get("jeton") == jeton:
            return actuel                     # déjà à nous
        meme_poste = actuel.get("hote") == contenu["hote"]
        abandonne = meme_poste and not processus_actif(int(actuel.get("pid") or 0))
        if not (abandonne or forcer):
            raise VerrouPris(
                f"Ouvrage déjà ouvert par {description(actuel)}. Fermez-le sur ce poste"
                + (" ou reprenez-le explicitement si ce poste n'y travaille plus." if not meme_poste else "."),
                {**actuel, "meme_poste": meme_poste})
        try:
            os.unlink(chemin_verrou(chemin))  # verrou abandonné, ou reprise demandée
        except FileNotFoundError:
            pass
        if forcer and not abandonne:
            contenu["repris_de"] = description(actuel)
    raise VerrouPris("Verrou de l'ouvrage impossible à prendre : réessayez.", {})


def detenu_par_autre(chemin: str, jeton: str) -> dict | None:
    """Détenteur actif d'un verrou qui n'est pas le nôtre (None : libre, à nous, ou abandonné sur ce poste)."""
    d = lire(chemin)
    if d is None or d.get("jeton") == jeton:
        return None
    if d and d.get("hote") == _hote() and not processus_actif(int(d.get("pid") or 0)):
        return None
    return d


def detient(chemin: str, jeton: str) -> bool:
    d = lire(chemin)
    return d is not None and d.get("jeton") == jeton


def liberer(chemin: str, jeton: str) -> None:
    """Retire le verrou seulement s'il nous appartient."""
    if chemin and detient(chemin, jeton):
        try:
            os.unlink(chemin_verrou(chemin))
        except FileNotFoundError:
            pass


def nouveau_jeton() -> str:
    return uuid.uuid4().hex
