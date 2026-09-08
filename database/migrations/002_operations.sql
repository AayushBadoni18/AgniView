CREATE TABLE ingestion_jobs (
    id bigserial PRIMARY KEY,
    source text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    status text NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    records_processed integer NOT NULL DEFAULT 0,
    records_rejected integer NOT NULL DEFAULT 0,
    error text
);

CREATE TABLE alerts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id uuid NOT NULL REFERENCES classified_events(id) ON DELETE CASCADE,
    deduplication_key text NOT NULL UNIQUE,
    status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'resolved')),
    severity text NOT NULL,
    reason text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX alerts_open_idx ON alerts (created_at DESC) WHERE status = 'open';
