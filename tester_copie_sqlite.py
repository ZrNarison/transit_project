import sqlite3
import uuid
from pathlib import Path

import django
from django.conf import settings
from django.db import connection

django.setup()

destination = Path(settings.BASE_DIR) / f"test_copie_{uuid.uuid4().hex}.sqlite3"

try:
    if connection.vendor != "sqlite":
        raise RuntimeError("La base configurée n'est pas SQLite.")

    connection.ensure_connection()

    with connection.cursor() as cursor:
        cursor.execute("VACUUM INTO %s", [str(destination)])

    db = sqlite3.connect(str(destination))
    try:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]

        table_count = db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = ?",
            ("table",),
        ).fetchone()[0]
    finally:
        db.close()

    print("Copie créée :", destination.exists())
    print("Intégrité SQLite :", integrity)
    print("Nombre de tables :", table_count)

finally:
    if destination.exists():
        destination.unlink()
