# AgniView Project State

## Current phase

Pre-deployment remediation, phase 3 of the supplied 13-phase objective.

## Overall status

Implementation and hardening gaps remain. The prior claim that only credentialed
validation remained was incorrect. Complete mandatory readiness work before the
advanced roadmap. Credentials are configured; never display them.

## Last verified

2026-09-09: Linux with isolated PostGIS passed 89 backend tests. Native Windows
Python 3.12 passes 84, with only 5 PostGIS tests skipped. Both include 27 real local
COG cases. Corrected backend image build and permanent Rasterio/COG smoke pass.
Rasterio/Affine emits 82 upstream pending-deprecation warnings. Later gates remain open.

## Verified system

- Flask REST API for events, map GeoJSON, details, profile history, point AI, alerts, metrics, and CSV/PDF exports.
- Eight PostgreSQL/PostGIS migrations with a transactional checksum ledger, advisory lock, explicit legacy baseline, safe restart and clean/007-upgrade/concurrent/failure regression coverage.
- Deterministic classification with structured evidence, severity, confidence evolution, trusted-profile reuse, and all canonical re-evaluation signals.
- FIRMS, Overpass, CMR STAC, Rasterio COG, and optional OpenAI adapters with bounded requests, retries, and explicit unavailable states.
- Persistent satellite-result, AI-summary, and normalized-question answer caches.
- Next.js/React/Mapbox UI with filters, clickable markers/fallback events, details, timeline, imagery state, anomaly state, savings, Ask AI, and event isolation.
- Docker Compose services for PostGIS, MinIO, backend, and frontend, plus ingestion-profile workers and CI definitions.

## Earlier verification evidence (historical)

- Linux/PostGIS: 45 tests pass, including migrations from empty tables and real spatial profile/reuse/anomaly flow.
- Local Python: 44 pass, 1 database test skipped because MSYS Python cannot load libpq.
- Frontend: 2 tests pass; production build passes; `npm audit --omit=dev` reports 0 vulnerabilities.
- Containers: four services running; backend/PostGIS healthy; frontend, backend, and MinIO return HTTP 200.
- Database: PostGIS 3.4; locked industrial profile; historical fast-path event; later anomaly full evaluation; four GiST indexes; profile lookup uses the centroid index.
- Production smoke: event/detail/map/history/region/summary/Ask AI routes and Next.js proxy pass; repeated identical Q&A is served from persistent cache.
- Browser rendering: desktop and responsive headless Chrome render four demo events and savings; responsive DOM has no horizontal overflow. The isolated interactive-browser provider was unavailable, so automated API tests cover state transitions.
- Live public metadata: Overpass returned and normalized industrial features; CMR STAC returned HLS S30 items/assets. The COG asset redirect correctly reached the Earthdata credential boundary.

## Open external gates

- `NASA_FIRMS_API_KEY`: credentialed ingestion request through the production worker.
- Earthdata credentials: authenticated HLS COG read from returned STAC assets.
- `NEXT_PUBLIC_MAPBOX_TOKEN`: token-backed basemap and marker-cluster rendering.
- Optional `LLM_API_KEY`/`LLM_MODEL`: OpenAI provider verification; the deterministic grounded provider already satisfies local point-Q&A behavior.

## Database migrations

Latest migration: `008_osm_evidence_version.sql`

## Next exact task

Finish authenticated Earthdata HLS verification, then phases 4–13 in `tasks/plan.md`.
Phases 1–2 and the image/local COG portion of phase 3 passed. Keep satellite
enrichment disabled by default until the live gate passes. The supplied baseline
already verifies FIRMS (255 processed, zero rejected) and Mapbox marker/details;
avoid unnecessary repeated FIRMS requests. No commits or pushes are authorized.

## Recent decisions

- PostgreSQL/PostGIS remains durable truth; Redis is still omitted because database caches satisfy the MVP.
- Collision-safe OSM keys use element type and ID (`way/…`, `relation/…`).
- Same-origin Next.js proxy is baked with `backend:5000` for Compose and uses localhost for non-container builds.
- Severity and anomaly thresholds are configurable heuristics, not scientifically validated claims.
- The LLM explains trusted context and never replaces deterministic classification.
