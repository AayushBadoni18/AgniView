ALTER TABLE classified_events
    ADD COLUMN classification_duration_ms double precision,
    ADD COLUMN ai_summary_cache_hits integer NOT NULL DEFAULT 0;

CREATE INDEX alerts_status_created_idx ON alerts (status, created_at DESC);
