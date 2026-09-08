# Data Pipeline

Implemented flow: NASA FIRMS detection → validation/normalization → idempotent PostGIS upsert → OSM/profile lookup → historical reuse or full classification → optional HLS enrichment → profile/alert/telemetry update → cached AI explanation → API/map.

`FirmsClient` implements the NASA FIRMS Area CSV contract, validates scan/track and every core field, and produces deterministic identities. `worker.py` performs the full pipeline approximately hourly, isolates rejected records, retries transient external failures, and persists job outcomes.

`osm_worker.py` refreshes industrial land-use, power-plant, and works geometries weekly. `EarthdataStacClient` searches `HLSS30_2.0` and `HLSL30_2.0`; Rasterio reads a 3×3 event window from only the needed NIR, SWIR1, and Fmask COGs. S30 uses B8A/B11 and L30 uses B05/B06. Cloud/fill/missing imagery degrades to explicit unavailable evidence.

Classification, profile confidence/locking, FRP/footprint/cluster/OSM/manual/conflict/dNBR/version/staleness escape paths, alert deduplication, and AI context invalidation are deterministic and tested against real PostGIS. Satellite results and point answers use durable PostgreSQL caches keyed by compatible context/version hashes.
