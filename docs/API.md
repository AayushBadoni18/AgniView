# API

## Implemented

### `GET /health`

Returns `200` with backend/database status, or `503` when the production database check fails.

- `GET /api/events` — paginated events; filters: `classification`, `severity`, `source`, `region`, `start`, `end`, `minConfidence`, `page`, `pageSize`.
- `GET /api/events/map` — bounded GeoJSON; optional `bbox=minLon,minLat,maxLon,maxLat` and event filters.
- `GET /api/events/{id}` — event detail and provenance.
- `GET /api/events/{id}/history` — related profile history.
- `GET /api/events/{id}/ai-summary` — cached/generated grounded summary.
- `POST /api/events/{id}/ask` — body `{ "question": "1–500 characters" }`; response includes `event_id`, `question`, `answer`, `classification`, `confidence`, `context_version`, `generated_at`, and cache status.
- `GET /api/alerts?status=open` — persisted high-confidence wildfire/anomaly alerts.
- `PATCH /api/alerts/{id}` — body `{ "status": "acknowledged" }` or `{ "status": "resolved" }`.
- `GET /api/metrics` — full/fast path, cache-avoidance, and latency metrics.
- `GET /api/exports/events.csv` and `/api/exports/events.pdf` — filtered reports.

Errors use `{ "error": { "code": "...", "message": "..." } }`. Lists are bounded to 200 rows; map responses are bounded to 2,000 features.

## Planned

Authentication and administrative mutation endpoints are not part of the supplied MVP requirements and have not been invented.
