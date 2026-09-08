# Architecture Decisions

## 2026-09-08 — Initial stack

- Decision: Next.js/React frontend, Flask REST backend, PostgreSQL/PostGIS, MinIO, and Docker Compose.
- Reason: This is the stack explicitly named by the master implementation directive.
- Alternatives: Not evaluated because the directive is authoritative.
- Confidence: High.

## 2026-09-08 — No Redis in Phase 0

- Decision: Do not provision Redis until a real cache implementation needs it.
- Reason: Avoid unused infrastructure.
- Confidence: High.

## 2026-09-08 — Psycopg 3.3

- Decision: Use pure-Python Psycopg 3.3.5 with system `libpq` instead of the original binary 3.2.3 scaffold pin.
- Reason: Psycopg 3.3 supports Python 3.14, while the local MSYS/UCRT interpreter has no matching `psycopg-binary` wheel.
- Impact: No application-level API change; enables reproducible local installation.
- Confidence: High.

## 2026-09-09 — Corrected windowed HLS NBR

- Decision: Standard NBR uses NIR/SWIR2: S30 B8A/B12 and L30 B05/B07. The previous B11/B06 decision was incorrect (those are SWIR1).
- Sources: [NASA HLS band definitions and masking](https://hls.gsfc.nasa.gov/algorithms/) and [USGS NBR](https://www.usgs.gov/landsat-missions/landsat-normalized-burn-ratio).
- Read a co-registered 3×3 window in all three assets. Exclude cloud, cloud adjacency, shadow, snow, fill, nonfinite values and reflectance outside the conservative analysis interval [0, 1]. Use the same remaining pixels for both medians. Grid mismatches and empty valid sets are unavailable evidence.
- This [0, 1] interval is an analysis filter, not a claim about all scientifically valid HLS product values. Negative or above-one retrievals are intentionally excluded from this heuristic.
- Persist item IDs, acquisition times, scene cloud cover, selected bands, valid/total pixel counts, grid resolution/CRS and processing version. Missing metadata remains null. A 3×3 window at HLS 30 m resolution is nominally 90×90 m, clipped at raster edges; it is not a 500 m generated thumbnail.
- `DNBR_WILDFIRE_THRESHOLD=0.30` is configurable and unvalidated for operational wildfire decisions. Change `CLASSIFICATION_PIPELINE_VERSION` when changing classification thresholds. A fixed `v2-swir2-joint-mask` algorithm identity invalidates old satellite cache keys even if the configured version is unchanged.
- Authenticated Earthdata verification remains open; satellite enrichment stays disabled by default.

## 2026-09-09 — Migration and test safety

- Destructive integration setup only accepts dedicated `agniview_test` / `agniview_test_*` database URIs and checks the resolved database name.
- A one-shot Compose migration service precedes API and ingestion workers; contiguous SQL files and checksums are recorded transactionally under an advisory lock.
- Legacy volumes require an explicit operator-verified baseline after backup. Recovery uses transaction rollback on failure or a tested backup restore after a successful incompatible upgrade; no automatic destructive down migration.
- Linux/PostGIS regression evidence: clean install, 007 legacy upgrade, concurrent runners, changed-file refusal and failed-run restart passed on 2026-09-09.

## 2026-09-08 — OSM identity

- Decision: Persist `osm_type/id` as the primary key rather than numeric OSM ID alone.
- Reason: way and relation numeric ID namespaces can collide.
- Confidence: High.

## 2026-09-09 — Optional visual asset library

- Decision: Record `react-three-fiber`, `shadergradient`, `liquid-glass.js`, and `liquid-logo` as optional visual assets only; do not add them to the baseline frontend.
- Reason: The current product value is the geospatial intelligence workflow, and the existing CSS/Mapbox UI does not require a WebGL runtime. The extra stack would add bundle, browser, and maintenance cost without covering a MUST BUILD requirement.
- Use: R3F plus ShaderGradient only for an explicitly approved 3D/ambient visual and lazy-load it. Use liquid-glass.js only for a concrete panel surface with a CSS fallback. Use liquid-logo only to export static branding artwork.
- Installation: If a 3D/shader surface is approved, run `npm install three @react-three/fiber @shadergradient/react three-stdlib camera-controls` in `frontend/`. Vendor a pinned liquid-glass.js source only when needed; liquid-logo needs no production install.
- Plugins: none supplied; no plugin dependency is recorded.

## 2026-09-09 — User-wide agent design toolkit

- Decision: Install the identified reusable skills/tools user-wide rather than adding them to AgniView dependencies.
- Installed: Vercel `web-design-guidelines`, Taste Skill’s `design-taste-frontend` and `image-to-code`, Microsoft `playwright-cli` skill plus `@playwright/cli`, Impeccable, and UI UX Pro Max.
- Reason: These improve future agent workflows without changing the application runtime or production bundle.
- Not installed: “Awesome design” (directory/reference) and “Emil Kowalski” (design/motion reference); neither is a uniquely identifiable installable package.
