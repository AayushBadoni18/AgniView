# Implementation Plan: AgniView

## Active pre-deployment objective — 2026-09-09

The supplied goal-objective.md and Phase 13 addendum supersede prior completion
claims. Work in dependency order, with regression tests before behavioral fixes;
do not commit/push or expose `.env`. Each phase needs measured evidence.

1. Dedicated test-database guards; migration ledger, clean install, legacy upgrade,
   atomic failure/restart and concurrent runner tests.
2. Correct SWIR2 NBR bands, shared-pixel quality masks, configurable heuristic and provenance.
3. Rasterio container/local COG smoke; one authenticated Earthdata verification.
4. Selection/filter response races, accessible list, responsive and Mapbox E2E.
5. Snapshot-safe OSM removal/change lifecycle and malformed-feature isolation.
6. Atomic/idempotent ingestion and concurrent PostGIS regressions.
7. Explicit AI provider configuration, bounded costs, durable timestamps/caches/isolation.
8. Real object-storage asset flow or documented removal of unsupported implementation claims.
9. Dependencies/images, secrets, least privilege, headers, CSV/body/usage hardening.
10. Deployment boundary and authorization; defer user-controlled identity choice until other work is done.
11. Full local/Linux/CI quality gates, scans, proxy and container smoke tests.
12. Reconcile all memory, instructions and checklists against verified results.
13. RootCause.pdf claim-by-claim parity, scientific references, costs/licensing,
    reproducible benchmarks, and explicit correction of unsupported pitch promises.

Current slice: phase 1. Remaining phases and all 33 final gates are open until
verified; earlier checked milestones below describe historical work only.

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
