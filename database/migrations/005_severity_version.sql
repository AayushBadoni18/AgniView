ALTER TABLE classified_events
    ADD COLUMN severity_version text NOT NULL DEFAULT 'v1';
