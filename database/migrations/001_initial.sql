CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE raw_firms_detections (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    identity text NOT NULL UNIQUE,
    location geography(Point, 4326) NOT NULL,
    detected_at timestamptz NOT NULL,
    satellite text,
    instrument text,
    confidence text,
    frp double precision,
    brightness double precision,
    source text NOT NULL,
    raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE osm_industrial_zones (
    id bigint PRIMARY KEY,
    osm_type text NOT NULL,
    name text,
    tags jsonb NOT NULL DEFAULT '{}'::jsonb,
    geometry geometry(Geometry, 4326) NOT NULL,
    refreshed_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE historical_thermal_profiles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    centroid geography(Point, 4326) NOT NULL,
    source_geometry geometry(Geometry, 4326),
    industrial_zone_id bigint REFERENCES osm_industrial_zones(id) ON DELETE SET NULL,
    classification text NOT NULL CHECK (classification IN ('wildfire', 'industrial', 'unknown')),
    classification_confidence double precision NOT NULL CHECK (classification_confidence BETWEEN 0 AND 1),
    classification_locked boolean NOT NULL DEFAULT false,
    observation_count integer NOT NULL DEFAULT 0,
    industrial_observation_count integer NOT NULL DEFAULT 0,
    wildfire_observation_count integer NOT NULL DEFAULT 0,
    unknown_observation_count integer NOT NULL DEFAULT 0,
    consecutive_consistent_classifications integer NOT NULL DEFAULT 0,
    mean_frp double precision,
    median_frp double precision,
    frp_stddev double precision,
    max_frp double precision,
    typical_detection_hours smallint[],
    historical_pattern_score double precision,
    first_seen timestamptz NOT NULL,
    last_seen timestamptz NOT NULL,
    last_full_classification_at timestamptz,
    classification_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE classified_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_detection_id uuid NOT NULL UNIQUE REFERENCES raw_firms_detections(id) ON DELETE CASCADE,
    profile_id uuid REFERENCES historical_thermal_profiles(id) ON DELETE SET NULL,
    classification text NOT NULL CHECK (classification IN ('wildfire', 'industrial', 'unknown')),
    classification_confidence double precision NOT NULL CHECK (classification_confidence BETWEEN 0 AND 1),
    classification_source text NOT NULL,
    classification_reason text NOT NULL,
    classification_version text NOT NULL,
    full_classification_skipped boolean NOT NULL DEFAULT false,
    severity_score double precision NOT NULL DEFAULT 0,
    severity_label text NOT NULL DEFAULT 'low',
    dnbr double precision,
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    ai_summary text,
    ai_context_version text,
    ai_context_hash text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX raw_firms_location_gist ON raw_firms_detections USING gist (location);
CREATE INDEX osm_industrial_geometry_gist ON osm_industrial_zones USING gist (geometry);
CREATE INDEX thermal_profiles_centroid_gist ON historical_thermal_profiles USING gist (centroid);
CREATE INDEX thermal_profiles_geometry_gist ON historical_thermal_profiles USING gist (source_geometry);
CREATE INDEX classified_events_classification_idx ON classified_events (classification, created_at DESC);
