"""Run inside the current container; keep the database backup on the Raspberry."""

import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path


def request(path):
    port = os.getenv("GRAVIA_HTTP_PORT", "8080")
    with urllib.request.urlopen(f"http://localhost:{port}/api/v1/{path}", timeout=5) as response:
        return json.load(response)


def main():
    settings = request("settings")
    deadline = time.monotonic() + min(300, max(65, settings["sessionTimeout"] + 5))
    while request("sessions/active") is not None:
        if time.monotonic() > deadline:
            raise RuntimeError(
                "Pesata ancora attiva: deploy annullato prima di sostituire il container."
            )
        print("Attendo il completamento della pesata attiva...", flush=True)
        time.sleep(5)
    url = os.environ["GRAVIA_DATABASE_URL"]
    if not url.startswith("sqlite:///"):
        raise RuntimeError("Il backup pre-deploy richiede il database SQLite di Gravia.")
    source = Path(url.removeprefix("sqlite:///"))
    if not source.is_file():
        raise RuntimeError("Database SQLite non trovato: deploy annullato.")
    directory = source.parent / "jenkins-backups"
    directory.mkdir(exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", sys.argv[1])
    backup = directory / f"{name}.db"
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as current:
        with sqlite3.connect(backup) as destination:
            current.backup(destination)
            if destination.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise RuntimeError("Backup SQLite non valido: deploy annullato.")
    backup.chmod(0o600)
    print(f"Backup SQLite locale completato: {backup}", flush=True)


if __name__ == "__main__":
    main()
