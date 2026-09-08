# Data Pipeline

Implemented flow: NASA FIRMS detection → validation/normalization → idempotent PostGIS upsert → OSM/profile lookup → historical reuse or full classification → optional HLS enrichment → profile/alert/telemetry update → cached AI explanation → API/map.

`FirmsClient` implements the NASA FIRMS Area CSV contract, validates scan/track and every core field, and produces deterministic identities. `worker.py` performs the full pipeline approximately hourly, isolates rejected records, retries transient external failures, and persists job outcomes.

`osm_worker.py` refreshes industrial land-use, power-plant, and works geometries weekly. `EarthdataStacClient` searches `HLSS30_2.0` and `HLSL30_2.0`; Rasterio reads aligned 3×3 event windows from NIR, SWIR2, and Fmask COGs. S30 uses B8A/B12 and L30 uses B05/B07. A joint pixel mask excludes cloud, adjacency, shadow, snow, fill, invalid reflectance and nodata in either band before calculating medians. Missing or unusable imagery remains explicit. Evidence includes pixel counts, bands, item IDs, acquisition times, cloud cover and processing version; this is a nominal 90 m HLS window, not a generated 500 m thumbnail. The configurable dNBR threshold is an unvalidated heuristic; see `docs/DECISIONS.md`.

Classification, profile confidence/locking, FRP/footprint/cluster/OSM/manual/conflict/dNBR/version/staleness escape paths, alert deduplication, and AI context invalidation are deterministic and tested against real PostGIS. Satellite results and point answers use durable PostgreSQL caches keyed by compatible context/version hashes.
