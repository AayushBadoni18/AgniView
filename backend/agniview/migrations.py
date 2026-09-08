"""Ordered, checksummed PostgreSQL migrations, committed atomically with their ledger."""
import argparse
import hashlib
import os
from pathlib import Path
import re


def migrate(connection, directory, baseline=None):
    files = sorted(Path(directory).glob("*.sql"))
    if not files or any(not re.fullmatch(rf"{index:03d}_[a-z0-9_]+\.sql", file.name)
                        for index, file in enumerate(files, 1)):
        raise ValueError("Migrations must be contiguous numbered SQL files starting at 001")
    if baseline is not None and baseline not in {p.name[:3] for p in files}:
        raise ValueError("Unknown baseline version")
    scripts = [(p.name, p.read_text(encoding="utf-8")) for p in files]
    checksums = {name: hashlib.sha256(script.encode()).hexdigest() for name, script in scripts}
    applied = []
    with connection.transaction():
        connection.execute("SELECT pg_advisory_xact_lock(734219001)")
        connection.execute("SET LOCAL search_path TO public")
        has_ledger, has_legacy = connection.execute(
            "SELECT to_regclass('schema_migrations'), to_regclass('raw_firms_detections')"
        ).fetchone()
        if has_legacy and not has_ledger and baseline is None:
            raise ValueError("Existing schema requires an explicit verified baseline; see docs/RUNBOOK.md")
        if baseline is not None and (has_ledger or not has_legacy):
            raise ValueError("A baseline is only allowed for an existing schema without a ledger")
        connection.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
            name text PRIMARY KEY, checksum text NOT NULL,
            applied_at timestamptz NOT NULL DEFAULT now(), baselined boolean NOT NULL DEFAULT false
        )""")
        recorded = dict(connection.execute("SELECT name, checksum FROM schema_migrations").fetchall())
        if list(sorted(recorded)) != [name for name, _ in scripts][:len(recorded)]:
            raise ValueError("Migration ledger is not a prefix of the available migrations")
        for name, checksum in recorded.items():
            if checksums.get(name) != checksum:
                raise ValueError("An applied migration changed; restore the original file")
        for name, script in scripts:
            if name in recorded:
                continue
            baselined = baseline is not None and name[:3] <= baseline
            if not baselined:
                connection.execute(script)
                applied.append(name)
            connection.execute(
                "INSERT INTO schema_migrations(name, checksum, baselined) VALUES (%s, %s, %s)",
                (name, checksums[name], baselined),
            )
    return applied


def main():
    import psycopg

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", default="/migrations")
    parser.add_argument("--baseline", help="Verified legacy version, e.g. 007; backup first")
    args = parser.parse_args()
    try:
        with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as connection:
            applied = migrate(connection, args.directory, args.baseline)
        print(f"Migrations applied: {len(applied)}")
    except Exception as error:
        # Driver exceptions can contain connection details; never print them.
        raise SystemExit(f"Migration failed ({type(error).__name__}); see migration runbook") from None


if __name__ == "__main__":
    main()
