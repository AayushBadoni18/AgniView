# AgniView

AgniView combines NASA FIRMS detections, OpenStreetMap context, persistent thermal-source profiles and optional satellite burn-change evidence. Deterministic rules classify events; point-specific AI explains stored evidence. “Self-learning” means profile reuse and anomaly-triggered re-evaluation, not neural retraining.

Geospatial thermal-event intelligence for distinguishing recurring industrial heat sources from potential wildfire activity.

## Quick start

```text
copy .env.example .env
docker compose up --build
```

- Backend health: http://localhost:5000/health
- Frontend: http://localhost:3000
- MinIO console: http://localhost:9001
- PostgreSQL: localhost:5432

Add `NEXT_PUBLIC_MAPBOX_TOKEN` to `.env` for the Mapbox basemap. Start hourly FIRMS ingestion and weekly OSM refresh with `docker compose --profile ingestion up --build` after setting `NASA_FIRMS_API_KEY`. To enrich full classifications with HLS imagery, also set `SATELLITE_ENRICHMENT_ENABLED=true` and the Earthdata credentials.

For a credential-free local demo, install dependencies and run:

```text
python -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
DEMO_MODE=true PYTHONPATH=backend .venv/bin/python -m flask --app backend/app run
cd frontend && npm ci --ignore-scripts && npm run dev
```

Windows PowerShell users may need `.venv\Scripts\python.exe`; MSYS Python creates `.venv\bin\python.exe`.
In PowerShell, set demo variables with `$env:DEMO_MODE='true'` and `$env:PYTHONPATH='backend'` before starting Flask.

## Verification

```text
.venv/bin/python -m pytest backend/tests -q
cd frontend && npm test && npm run build && npm audit --omit=dev
```

The no-key demo uses four clearly identified fixtures, including historical reuse and anomaly fallback. Production mode uses PostgreSQL/PostGIS and never treats demo fixtures as live detections. See `docs/TESTING.md` for the real PostGIS test command.
