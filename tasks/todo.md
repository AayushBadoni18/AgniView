# AgniView Task Checklist

## Final credential-free gap audit

- [ ] Include available thermal-profile statistics and related events in trusted AI context.
- [ ] Detect same-zone OSM geometry/tag changes and force full reclassification.
- [ ] Populate source geometry, typical detection hours, and historical pattern score.
- [ ] Prevent Mapbox load timing from retaining an empty initial event collection.
- [ ] Exercise the Next.js API proxy in container CI.
- [ ] Run the full local/PostGIS/container/frontend/API quality gates and update project memory.
- [!] User-only: provide FIRMS, Earthdata, and Mapbox credentials for external verification.

- [x] Phase 0.1 — Repository structure
- [x] Phase 0.2 — Environment configuration
- [x] Phase 0.3 — Validate Docker infrastructure
- [x] Phase 1 — PostGIS and core schema
- [-] Phase 2 — FIRMS ingestion; credentials blocked
- [x] Phase 3 — OSM context and live public metadata
- [x] Phase 4 — Classification engine
- [x] Phase 5 — Persistent classification memory logic
- [-] Phase 6 — Satellite enrichment implemented; credentialed verification blocked
- [x] Phase 7 — Backend REST API
- [-] Phase 8 — Map frontend; Mapbox token blocked
- [x] Phase 9 — Event details
- [x] Phase 10 — Point-specific Ask AI; optional OpenAI provider credential-gated
- [x] Phase 11 — Alert lifecycle and deduplication
- [x] Phase 12–15 — Exports, performance telemetry, observability, and local hardening
- [x] Phase 16–17 — Local deployment and demo hardening
- [-] Phase 18 — Credentialed external runtime gates remain

## Canonical completion gaps

- [x] Add canonical structured evidence and trusted AI context sections.
- [x] Add nearby industrial context and persist severity version.
- [x] Add durable satellite result caching and expose complete satellite evidence.
- [x] Add region/location API and UI filtering plus stronger API failure/filter tests.
- [x] Add history timeline, anomaly demo event, and visible compute savings.
- [x] Add runnable frontend tests and PostGIS integration test harness.
- [x] Exercise live uncredentialed OSM/STAC metadata paths.
- [x] Verify Docker/PostGIS/MinIO.
- [!] Verify credentialed FIRMS/Earthdata/Mapbox paths; optional OpenAI provider also lacks credentials.

## Checkpoint: Phase 0

- [x] Backend focused test passes in a dependency-equipped environment
- [x] Compose validates and all four services start
- [x] Health endpoints and local URLs are manually verified
