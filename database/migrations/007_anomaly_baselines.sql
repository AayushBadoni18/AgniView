ALTER TABLE raw_firms_detections
    ADD COLUMN scan double precision,
    ADD COLUMN track double precision,
    ADD COLUMN cluster_size integer;

ALTER TABLE historical_thermal_profiles
    ADD COLUMN mean_scan double precision,
    ADD COLUMN mean_track double precision,
    ADD COLUMN max_cluster_size integer,
    ADD COLUMN manual_review_required boolean NOT NULL DEFAULT false;
