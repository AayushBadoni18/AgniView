# Architecture

The target system is a vertical application: Next.js/React presents Mapbox GL JS and event details; Flask exposes REST APIs and orchestrates ingestion, geospatial enrichment, classification, persistent thermal profiles, satellite enrichment, and point-specific AI; PostgreSQL/PostGIS is durable truth; MinIO stores generated assets. Docker Compose is the local orchestration layer.

The frontend calls same-origin `/api` routes, which Next.js proxies to Flask; this avoids broad CORS. Flask validates boundary input and returns consistent errors. Its repository layer uses parameterized Psycopg queries. `DEMO_MODE=true` explicitly selects a four-event fixture repository; normal mode requires PostgreSQL/PostGIS.

External clients are narrow adapters for FIRMS, Overpass, and CMR STAC. FIRMS and OSM workers persist durable job outcomes and emit correlated JSON events. Full classifications may use block-aware Rasterio HLS windows; historical fast-path events avoid that work. Alerts and AI summaries are durable, deduplicated/versioned state. Point AI uses a backend-built allowlisted context; `LLM_PROVIDER=openai` activates the Responses API when both `LLM_API_KEY` and `LLM_MODEL` are set.
