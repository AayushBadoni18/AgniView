# Runbook

## Local startup

```text
copy .env.example .env
docker compose up --build
```

Verify `http://localhost:5000/health`, `http://localhost:3000`, and the MinIO console at `http://localhost:9001`. Stop with `docker compose down`; persistent MinIO data is kept in the named volume unless explicitly removed.

Use `docker compose --profile ingestion up --build` only after configuring a FIRMS key. Set `SATELLITE_ENRICHMENT_ENABLED=true` plus Earthdata credentials to enable HLS enrichment. External failures are recorded in `ingestion_jobs`, logged as correlated JSON events, and retried at the next interval. Never put secrets in committed files.

Without Docker, set `DEMO_MODE=true`, run Flask from `backend/`, and run `npm start` after building `frontend/`. The UI explicitly indicates when no Mapbox token is available and retains an interactive event list.

## Credentialed final gates

Keep credentials only in `.env`. Set `NASA_FIRMS_API_KEY` and start `docker compose --profile ingestion up worker`; confirm a successful `ingestion_jobs` row and a classified event. Set `SATELLITE_ENRICHMENT_ENABLED=true` plus `NASA_EARTHDATA_USERNAME`/`NASA_EARTHDATA_PASSWORD`; confirm an available satellite evidence record with pre/post NBR and dNBR. Set `NEXT_PUBLIC_MAPBOX_TOKEN`, rebuild `frontend`, and confirm the basemap and marker clusters render. Never commit the populated `.env`.
