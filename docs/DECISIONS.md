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

## 2026-09-08 — Windowed HLS reads

- Decision: Use Rasterio 1.5.1 in the CPython 3.12 container and read only a 3×3 event window from HLS NIR, SWIR1, and Fmask COG assets.
- Reason: Rasterio's documented windows respect GeoTIFF blocks and NASA HLS defines S30 B8A/B11 and L30 B05/B06 for NBR.
- Limitation: the local MSYS/UCRT Python lacks a compatible wheel; the same reader API was exercised with Rasterio 1.4.4 on Windows CPython 3.11, while container installation remains part of the Docker gate.
- Confidence: High for algorithm/API; credentialed remote access remains unverified.

## 2026-09-08 — OSM identity

- Decision: Persist `osm_type/id` as the primary key rather than numeric OSM ID alone.
- Reason: way and relation numeric ID namespaces can collide.
- Confidence: High.
