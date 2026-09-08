# Implementation Plan: AgniView

## Overview

Build AgniView incrementally as a geospatial thermal-event intelligence system. The first vertical slice establishes reproducible local services; later slices add durable geospatial data, FIRMS ingestion, classification memory, map interaction, event-specific AI, and portfolio hardening.

## Architecture decisions

- Next.js/React frontend, Flask REST backend, PostgreSQL/PostGIS, MinIO, and Docker Compose.
- PostgreSQL/PostGIS is durable truth; Redis is deferred until a real cache requires it.
- Classification memory is persistent and confidence-aware; LLM output explains rather than classifies.

## Task list

### Phase 0 — Foundation

- [x] Create repository structure and persistent engineering memory.
- [x] Define environment placeholders and local Compose services.
- [-] Validate backend/frontend locally; database/MinIO runtime awaits Docker.

### Phase 1 — Database

- [x] Add PostGIS initialization and core tables.
- [x] Add historical thermal profiles, provenance, and spatial indexes.

### Phase 2–6 — Data and intelligence

- [x] Implement FIRMS ingestion, validation, deduplication, and scheduling.
- [x] Add OSM industrial context and satellite enrichment.
- [x] Implement full classification, severity, profile reuse, anomaly escape, and version invalidation.

### Phase 7–10 — Product path

- [x] Add event/map APIs and the map frontend.
- [x] Add clickable event details and evidence.
- [x] Add grounded, cached, point-specific Ask AI with context isolation.

### Phase 11–18 — Hardening

- [x] Add alerts, exports, metrics, observability, test hardening, deployment definitions, and demo quality gates.

## Risks

| Risk | Mitigation |
|---|---|
| Local Python lacks libpq | Run database integration in the verified Linux backend container. |
| External API limits or unavailable imagery | Add explicit adapters, retries, freshness checks, and honest unavailable-data states in their milestones. |
| Trusted industrial profile hides a real fire | Require anomaly checks and full-pipeline escape path. |

## Open questions

Authentication and hosting remain intentionally undecided by the supplied directive. Docker/PostGIS and credentialed provider validation remain external gates.

## Final gap-remediation pass

1. Enrich trusted point context with stored profile behavior and related events.
2. Persist stable OSM evidence hashes and make changed same-zone evidence invalidate reuse.
3. Populate the canonical profile geometry, typical-hour, and pattern-score fields.
4. Fix Mapbox's asynchronous load/data race and add container-proxy CI coverage.
5. Re-run all local and Docker/PostGIS gates, then reconcile every checklist and project-state claim.

Only credentialed FIRMS, Earthdata COG, and Mapbox execution requires user-supplied secrets.
