# Runbook

## Local startup

```text
copy .env.example .env
docker compose up --build
```

Verify `http://localhost:5000/health`, `http://localhost:3000`, and the MinIO console at `http://localhost:9001`. Stop with `docker compose down`; persistent MinIO data is kept in the named volume unless explicitly removed.

Use `docker compose --profile ingestion up --build` only after configuring a FIRMS key. Set `SATELLITE_ENRICHMENT_ENABLED=true` plus Earthdata credentials to enable HLS enrichment. External failures are recorded in `ingestion_jobs`, logged as correlated JSON events, and retried at the next interval. Never put secrets in committed files.

Without Docker, set `DEMO_MODE=true`, run Flask from `backend/`, and run `npm start` after building `frontend/`. The UI explicitly indicates when no Mapbox token is available and retains an interactive event list.

## Database upgrades and recovery

Compose now runs a one-shot `migrate` service before API/worker startup, including
on existing volumes. It applies contiguous numbered SQL files in one PostgreSQL
transaction under an advisory lock. `schema_migrations` records the filename,
SHA-256 of normalized SQL text, application time, and whether an operator baselined
a legacy version. Repeated starts are no-ops; changed or missing applied files fail
closed. Failed migrations roll back both schema changes and ledger entries.
Do not edit an applied migration; add the next numbered file. Migration SQL must
support a transaction (no explicit COMMIT or concurrent index creation).

Before upgrading, stop API and ingestion writers, take a restricted-access
`pg_dump -Fc` backup using configured credentials, and test its restore into a
separate database. Keep the old application image and matching migration files.
Never use `docker compose down --volumes` to upgrade or recover application data.

For a legacy volume initialized before the ledger existed, inspect its schema and
verify the highest fully applied migration against the SQL files. Only after that
verification and backup, explicitly adopt that version:

```text
docker compose run --rm migrate python -m agniview.migrations --baseline 007
```

Use `008` instead only when migration 008's two hash columns are already present.
The baseline is an operator assertion about the existing schema, not automatic
schema discovery; it does not execute the adopted files. All newer migrations run
in the same transaction. Do not baseline a partially applied schema. A clean
database needs no baseline. For normal upgrades run:

```text
docker compose run --rm migrate
docker compose up -d backend frontend
```

Restart ingestion only when health and a read-only smoke check pass. On a failed
migration, fix the pending file and rerun; no partial ledger is committed. After a
successful but incompatible upgrade, restore the backup into a separate database,
verify it, switch the configured connection and old application image, and retain
the failed-upgrade database for investigation. No automatic down migration is
provided because dropping columns can destroy evidence.

## Credentialed final gates

Keep credentials only in `.env`. The supplied baseline reports successful FIRMS ingestion and token-backed Mapbox rendering; avoid unnecessary FIRMS quota use. Keep `SATELLITE_ENRICHMENT_ENABLED=false` until an authenticated HLS read passes with correct bands and masks. Never commit the populated `.env`.
