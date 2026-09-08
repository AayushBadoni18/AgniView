# AgniView — Canonical Project Memory

This file is the authoritative project context for future coding agents. The project is currently assumed to be unimplemented. Do not silently replace the requirements below with a simpler raw-detection map.

## Product definition

AgniView is a geospatial thermal-event intelligence system, not merely a map of NASA FIRMS detections. It helps users distinguish recurring industrial heat sources from potentially dangerous wildfire activity by combining thermal detections, geospatial context, historical evidence, satellite evidence when available, deterministic classification, and point-specific AI explanations.

The system must become faster as it sees repeated activity at known locations while remaining able to re-evaluate a trusted industrial location when new evidence suggests a real fire.

“Self-learning” has a precise MVP meaning: persistent thermal-source profiles, accumulated historical evidence, confidence evolution, classification reuse, anomaly-triggered re-evaluation, and profile updates. It does not mean autonomous neural-network retraining. The stored history should be suitable for later supervised-ML experimentation.

## Mandatory user experience

Every event marker on the interactive map must be clickable. Clicking a marker opens an event detail panel showing, when available:

- event ID, latitude, longitude, and detection timestamp;
- satellite/source, FRP, and brightness/thermal information;
- classification, confidence, severity, and classification reasoning;
- dNBR/NBR and related satellite evidence;
- OSM industrial-zone intersection and surrounding land use;
- historical thermal behavior and related activity;
- imagery or thumbnail.

The panel must include `Ask AI about this point...`. This is a contextual geospatial/event assistant, not a generic chatbot. Example questions include why the event is industrial, whether it could be a forest fire, how severe it is, what FRP/dNBR means, whether the location was previously active, and what evidence supports the classification.

Conceptual frontend components:

`EventDetailPanel`, `EventMetrics`, `ClassificationBadge`, `ClassificationEvidence`, `HistoricalActivitySummary`, `AISummary`, `AskAIInput`, `AIConversation`, `ConfidenceIndicator`, `SatelliteEvidence`.

Suggested hierarchy:

```text
MapPage
 ├── Map
 │    └── EventMarkers
 └── EventDetailPanel
      ├── EventHeader
      ├── EventMetrics
      ├── ClassificationEvidence
      ├── HistoricalActivitySummary
      ├── SatelliteEvidence
      └── PointAI
           ├── AISummary
           ├── AIConversation
           └── AskAIInput
```

Conversation state is temporary and may remain frontend/session scoped for the MVP. It must reset or switch context when a different event is selected. Answers or context for Event A must never leak into Event B.

## Point-specific AI contract

The backend, never the frontend, constructs trusted context for the selected event before calling an LLM. Context should be structurally equivalent to:

```json
{
  "event_id": "...",
  "coordinates": {"latitude": 0, "longitude": 0},
  "timestamp": "...",
  "source": "VIIRS",
  "frp": 0,
  "brightness": null,
  "classification": "industrial",
  "classification_confidence": 0.91,
  "classification_reasoning": [],
  "severity": "medium",
  "severity_score": 0,
  "dnbr": null,
  "historical_profile": {},
  "osm_context": {},
  "satellite_context": {},
  "nearby_events": [],
  "data_quality_notes": []
}
```

Only facts present in the system may be inserted. Missing values must be stated as unavailable, never fabricated. The LLM is an explanation/Q&A layer, not the primary classifier, and must not silently override deterministic/geospatial classification.

Required endpoint concept:

```text
POST /api/events/{event_id}/ask
```

Request:

```json
{"question":"Why was this classified as industrial?"}
```

Response should include `event_id`, `question`, `answer`, `classification`, `confidence`, `context_version`, and `generated_at`.

Support either `GET /api/events/{event_id}/ai-summary` or an AI summary embedded in `GET /api/events/{event_id}`. The initial explanation must be cached and regenerated only when material context changes, such as classification/confidence changes, new dNBR evidence, severity changes, or substantial historical enrichment. Reopening a point must not repeatedly consume LLM resources.

AI grounding rules:

1. Answer using event data plus relevant domain knowledge.
2. Distinguish measured facts from inference.
3. Never claim unavailable satellite, dNBR, FRP, OSM, weather, historical, or classification evidence.
4. Explain uncertainty and mention confidence when relevant.
5. Say when evidence is insufficient.
6. Be concise and technically useful.

## Canonical ingestion/classification flow

```text
NASA FIRMS detection
  -> validation and normalization
  -> duplicate detection check
  -> PostGIS spatial lookup
  -> historical thermal-profile lookup
      -> no trusted profile: full classification pipeline
      -> trusted profile: anomaly/validity checks
          -> normal: reuse classification
          -> anomalous/stale/incompatible: full classification pipeline
  -> update thermal profile
  -> store classified event and provenance
  -> generate or retrieve cached AI explanation
  -> expose through API
  -> display on map
```

Expensive work must be reused when a prior result exists, is fresh enough, was created with a compatible pipeline version, and remains valid for current evidence. Expensive work includes satellite retrieval, STAC queries, COG reads, NBR/dNBR processing, complex spatial analysis, full classification, and repeated LLM calls.

## Persistent thermal memory

Use PostgreSQL/PostGIS as the durable source of truth. Redis or an in-memory cache may handle short-lived repeated API requests, summaries, map queries, and other expensive results, but Redis must not be the sole source of classification memory.

`historical_thermal_profiles` should conceptually include:

`id/profile_id`, centroid, source geometry, industrial zone ID, classification, classification confidence, locked state, observation counts by label, mean/median/stddev/max FRP, typical detection hours, first/last seen, last full classification time, classification version, consecutive consistent classifications, historical pattern score, created/updated timestamps.

`classified_events` should conceptually include:

`id`, `raw_detection_id`, `profile_id`, classification, classification confidence, classification source, classification reason, classification version, `full_classification_skipped`, severity score/label, dNBR, created/updated timestamps.

Use PostGIS geometry/geography types and GiST indexes where appropriate. Exact schema may be refined during implementation, but the behavior and fields above are mandatory.

### Spatial matching

Do not require identical satellite coordinates. Matching hierarchy:

1. Same known OSM industrial polygon.
2. Existing thermal-profile geometry contains the detection.
3. Detection is within configurable radius of the historical centroid.
4. Spatial clustering associates it with the source.

Use PostGIS operations such as `ST_Contains`, `ST_Intersects`, and `ST_DWithin`. Configure the radius (for example `THERMAL_PROFILE_MATCH_RADIUS_METERS`) rather than scattering a hard-coded distance.

### Locking and fast path

A profile may be trusted/locked when it is industrial, confidence is at least `INDUSTRIAL_LOCK_CONFIDENCE`, and consecutive consistent classifications reach `MIN_CONSISTENT_CLASSIFICATIONS`. Initial defaults may be `0.90` and `3`; they are configurable implementation defaults, not scientifically validated constants.

For a trusted, normal detection:

```text
classification_source = "historical_profile"
full_classification_skipped = true
```

Store why it was reused, the profile ID, and the inherited confidence. Update profile statistics and store the event normally.

### Re-evaluation is mandatory

Locked classifications are never irreversible. Run the full pipeline again when any of these applies:

- FRP is abnormally above the historical baseline;
- thermal footprint or spatial behavior changes;
- an unusual cluster develops or the event persists abnormally;
- dNBR/NBR indicates actual burning;
- confidence falls;
- OSM land-use data changes;
- profile is stale;
- pipeline version changes;
- manual review overrides the profile;
- new evidence conflicts with the prior label.

Anomaly logic may use a configurable rule such as `frp > mean_frp + K * frp_stddev`. Do not treat “industrial” as proof that a fire cannot occur.

Confidence should evolve with repeated consistent and contradictory evidence. A simple weighted heuristic is sufficient for MVP. A complex probabilistic model is not required.

Classification provenance values may include `full_pipeline`, `historical_profile`, `manual_override`, `heuristic`, and `satellite_enrichment`. Retain classification version, reason, profile ID, and skip flag for debugging, explainability, analytics, and future training data.

## Versioning and metrics

Persist and compare versions such as:

```text
CLASSIFICATION_PIPELINE_VERSION=v1
AI_CONTEXT_VERSION=v1
SEVERITY_MODEL_VERSION=v1
```

Incompatible versions should force reclassification or summary regeneration.

Future/portfolio metrics should include total detections, full classifications, reused classifications, cache-hit rate, satellite/raster/AI calls avoided, estimated compute saved, and fast-path versus full-pipeline latency. These are NICE-TO-HAVE for the initial MVP and SHOULD exist in the finished hackathon/portfolio version.

## MVP priorities

MUST BUILD:

- clickable markers and event detail panel;
- classification reasoning and evidence;
- historical thermal profiles and spatial matching;
- classification fast path and anomaly-triggered full reclassification;
- provenance;
- point-specific AI context, Ask AI, and cached AI summary.

SHOULD BUILD:

- persistent AI-answer cache;
- cache-hit/compute-saving metrics;
- confidence evolution;
- explicit version invalidation;
- historical activity timeline.

NICE TO HAVE:

- streaming responses, suggested questions, rich charts;
- profile administration, manual correction, active learning;
- automated ML retraining.

## Future ML

Structure history for features such as FRP and deviation from baseline, industrial-polygon distance/intersection/category, detection counts and label ratios, time-of-day/seasonality, dNBR/NBR change, cluster size, duration, distance from centroid, and satellite source. Candidate future models include logistic regression, random forest, XGBoost, or other gradient-boosted trees. Deep learning is not required for MVP. Candidate labels are `wildfire`, `industrial`, and `unknown`.

## Acceptance criteria

Ask AI is complete when marker click opens details, structured facts and explanation appear, users can ask questions, backend retrieves selected-event context, answers are event-specific and grounded, missing evidence is not fabricated, summaries are reused, and changing events changes context correctly.

Persistent memory is complete when new detections search profiles, known recurring sources can skip expensive work, provenance is stored, profile statistics update, anomalies bypass the shortcut, stale/version-incompatible profiles reclassify, and compute-saving metrics can be calculated.

## Required implementation additions when coding begins

In dependency order, implement the profile schema and GiST index; event profile/provenance fields; PostGIS profile lookup and configurable radius; confidence/locking/anomaly logic; fast-path reuse and full-pipeline fallback; profile updates and versioning; tests for normal reuse and anomalous fallback; event-detail/evidence APIs; AI context builder/provider/Ask AI/summary persistence and invalidation; detail-panel components and marker/API wiring; conversation isolation and loading/error states; fast/full-path metrics; API/integration/E2E coverage; and a recurring-industrial-source demo scenario.

## Explicitly unknown / not yet decided

The supplied knowledge does not establish the final frontend framework, backend language/framework, repository layout, authentication model, hosting provider, exact database schema, exact FIRMS/STAC/OSM/Sentinel API contracts, severity formula, freshness windows, anomaly K, rate limits, notification channels, or deployment commands. Future agents must inspect authoritative project files when they exist and must not invent these as already-decided facts. If a missing decision blocks implementation, surface it instead of silently redesigning the system.

The first supplied attachment is a knowledge-transfer document template and completeness checklist, not additional project facts. It requires explicit separation of final decisions, alternatives, uncertainty, roadmap, testing, deployment, and onboarding information when those details become available.

## Agent boundaries

- Preserve the requirements in this file across architecture, schema, API, frontend, tests, and documentation changes.
- Treat “self-learning” accurately; do not claim neural-network retraining unless implemented.
- Keep deterministic/geospatial classification authoritative over LLM output.
- Never fabricate missing evidence.
- Prefer the smallest implementation that satisfies the mandatory requirements.

## Curated visual asset library

These are approved optional references for future frontend work, not baseline AgniView dependencies:

- `react-three-fiber` (`@react-three/fiber`): keep for a real 3D visualization or interactive shader scene. It pairs with React 19 through R3F 9. Do not add it for ordinary map, panel, chart, or CSS animation work.
- `shadergradient` (`@shadergradient/react`): keep for an optional ambient/hero shader background. It requires the R3F/Three stack and should be lazy-loaded so the operational map UI does not pay its cost.
- `liquid-glass.js`: keep as a zero-dependency visual reference for a restrained glass panel treatment. Prefer the smallest maintained, browser-compatible source and a CSS fallback; do not make event details or controls depend on WebGL.
- `liquid-logo`: keep as a design-time branding asset/reference only. Export a static AgniView logo asset; do not embed the logo generator or its animation runtime in the production dashboard.

Installation policy:

- Baseline: install none of the above.
- If a 3D/shader surface is explicitly approved, from `frontend/` run `npm install three @react-three/fiber @shadergradient/react three-stdlib camera-controls`, then lazy-load the client-only component and run the existing frontend tests/build.
- `liquid-glass.js` is copied or vendored only when a concrete surface needs it; there is no required npm dependency. Pin the source commit and check its license before committing.
- `liquid-logo` is used outside the app to create/export static artwork; no install command is required.
- No plugins were supplied in the request, so none are installed or treated as project requirements.

## User-wide development toolkit

Installed for reuse across projects on 2026-09-09:

- `web-design-guidelines` from `vercel-labs/agent-skills`: UI quality, accessibility, responsive layout, and interaction review.
- `taste-skill` (`design-taste-frontend`) from `Leonxlnx/taste-skill`: anti-generic frontend direction.
- `image-to-code-skill` (`image-to-code`) from `Leonxlnx/taste-skill`: reference-image analysis to frontend implementation.
- `playwright-cli` skill from `microsoft/playwright-cli`, plus the global `@playwright/cli` command: token-efficient browser testing and inspection.
- `impeccable` from `pbakaus/impeccable`: design audit/polish workflow and detectors.
- `ui-ux-pro-max` from `nextlevelbuilder/ui-ux-pro-max-skill`: design-system and cross-platform UI/UX guidance.

These are reusable agent skills/tools, not AgniView runtime dependencies. Apply only when the task is actually UI, visual, or browser-testing work; preserve product requirements and accessibility over stylistic guidance.

Reference-only items: “Awesome design” is a curated directory, not one installable skill; “Emil Kowalski” is a design/motion reference. No plugin package was identified for either name.

## Implementation directive

The canonical initial stack is React/Next.js frontend, Mapbox GL JS map, Python Flask REST backend, PostgreSQL/PostGIS, S3-compatible storage via MinIO locally, and Docker Compose. Primary thermal data is NASA FIRMS VIIRS/MODIS; industrial context is OSM/Overpass; satellite enrichment is NASA Earthdata STAC with Sentinel-2/HLS COGs. Do not add Redis until a real cache implementation requires it.

Work vertically and incrementally: read state, identify the milestone, implement the smallest complete unit, run focused validation, update state, and leave a commit-ready checkpoint. Do not claim a milestone complete without passing its acceptance criteria. Record unavoidable architecture deviations in `docs/DECISIONS.md`.

Required persistent project files are `docs/PROJECT_STATE.md`, `docs/MILESTONES.md`, `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/DATA_PIPELINE.md`, `docs/TESTING.md`, and `docs/RUNBOOK.md`.


## Model Routing Rules
- Generate all baseline structures using model: gpt-5.6-sol (reasoning: medium).
- For refactoring, gap filling, and optimization, switch to model: gpt-6-astra (reasoning: medium).

## Security Guardrails
- Treat any hardcoded credentials or un-sanitized raw database queries as a blocking test failure.

## Token Optimization
- Prior to upgrading a task to Astra, compress the payload: remove heavily commented boilerplate files and dummy assets to stay under the 272k token premium threshold.
- Do not run continuous terminal test loops on Astra without a strict execution limit of 3 retries.
