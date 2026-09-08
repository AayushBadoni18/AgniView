CREATE TABLE satellite_enrichment_cache (
    cache_key text PRIMARY KEY,
    result jsonb NOT NULL,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ai_answers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id uuid NOT NULL REFERENCES classified_events(id) ON DELETE CASCADE,
    question_hash text NOT NULL,
    context_hash text NOT NULL,
    context_version text NOT NULL,
    answer text NOT NULL,
    cache_hits integer NOT NULL DEFAULT 0,
    last_used_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (event_id, question_hash, context_hash, context_version)
);
