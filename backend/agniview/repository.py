import os
from hashlib import sha256
from copy import deepcopy

from .alerts import alert_for

EVENT_SELECT = """
SELECT e.id::text, ST_Y(d.location::geometry) AS latitude,
       ST_X(d.location::geometry) AS longitude, d.detected_at AS "detectedAt",
       d.satellite, d.instrument, d.frp, d.brightness,
       e.classification, e.classification_confidence AS confidence, e.profile_id::text AS "profileId",
       e.severity_label AS severity, e.severity_score AS "severityScore",
       e.severity_version AS "severityVersion",
       e.dnbr, e.evidence AS "classificationEvidence", e.evidence->'osm_context' AS "osmContext",
       e.evidence->'satellite' AS "satelliteEvidence", e.classification_source AS "classificationSource",
       e.classification_reason AS "classificationReason",
       e.full_classification_skipped AS "fullClassificationSkipped",
       COALESCE(p.observation_count, 0) AS "historicalObservations",
       p.mean_frp AS "profileMeanFrp", p.median_frp AS "profileMedianFrp",
       p.frp_stddev AS "profileFrpStddev", p.max_frp AS "profileMaxFrp",
       p.typical_detection_hours AS "profileTypicalHours",
       p.historical_pattern_score AS "profilePatternScore",
       p.first_seen AS "profileFirstSeen", p.last_seen AS "profileLastSeen",
       COALESCE((e.evidence->>'industrial_overlap')::boolean, false) AS "industrialOverlap", e.ai_summary AS "aiSummary",
       COALESCE((e.evidence->>'is_anomaly')::boolean, false) AS "isAnomaly",
       e.ai_context_hash AS "aiContextHash", e.ai_context_version AS "aiContextVersion"
FROM classified_events e
JOIN raw_firms_detections d ON d.id = e.raw_detection_id
LEFT JOIN historical_thermal_profiles p ON p.id = e.profile_id
"""


class PostgresRepository:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.environ["DATABASE_URL"]

    def _query(self, query: str, params=(), *, one=False):
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            rows = connection.execute(query, params).fetchall()
        normalized = [_json_ready(row) for row in rows]
        return (normalized[0] if normalized else None) if one else normalized

    def health(self):
        try:
            return self._query("SELECT 1 AS ok", one=True)["ok"] == 1
        except Exception:
            return False

    def list_events(self, *, page=1, page_size=50, classification=None, severity=None, source=None, region=None, start=None, end=None, min_confidence=None, **_):
        conditions, params = [], []
        for column, value in (("e.classification", classification), ("e.severity_label", severity), ("d.instrument", source)):
            if value:
                conditions.append(f"{column} = %s")
                params.append(value)
        for condition, value in (("d.detected_at >= %s", start), ("d.detected_at < %s", end), ("e.classification_confidence >= %s", min_confidence)):
            if value is not None:
                conditions.append(condition); params.append(value)
        if region:
            conditions.append("COALESCE(e.evidence->'osm_context'->>'zoneName', e.evidence->'osm_context'->'tags'->>'addr:state', '') ILIKE %s")
            params.append(f"%{region}%")
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        count = self._query("SELECT count(*) AS count FROM classified_events e JOIN raw_firms_detections d ON d.id=e.raw_detection_id" + where, params, one=True)["count"]
        params.extend([page_size, (page - 1) * page_size])
        rows = self._query(EVENT_SELECT + where + " ORDER BY d.detected_at DESC LIMIT %s OFFSET %s", params)
        return rows, count

    def map_events(self, *, bbox=None, classification=None, severity=None, source=None, region=None, start=None, end=None, min_confidence=None, limit=2000, **_):
        conditions, params = [], []
        if bbox:
            conditions.append("ST_Intersects(d.location::geometry, ST_MakeEnvelope(%s,%s,%s,%s,4326))")
            params.extend(bbox)
        for column, value in (("e.classification", classification), ("e.severity_label", severity), ("d.instrument", source)):
            if value:
                conditions.append(f"{column} = %s")
                params.append(value)
        for condition, value in (("d.detected_at >= %s", start), ("d.detected_at < %s", end), ("e.classification_confidence >= %s", min_confidence)):
            if value is not None:
                conditions.append(condition); params.append(value)
        if region:
            conditions.append("COALESCE(e.evidence->'osm_context'->>'zoneName', e.evidence->'osm_context'->'tags'->>'addr:state', '') ILIKE %s")
            params.append(f"%{region}%")
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(limit)
        return self._query(EVENT_SELECT + where + " ORDER BY d.detected_at DESC LIMIT %s", params)

    def get_event(self, event_id):
        return self._query(EVENT_SELECT + " WHERE e.id::text = %s", (event_id,), one=True)

    def event_history(self, event_id):
        event = self.get_event(event_id)
        if not event:
            return []
        return self._query(EVENT_SELECT + " WHERE e.profile_id=(SELECT profile_id FROM classified_events WHERE id::text=%s) ORDER BY d.detected_at DESC LIMIT 100", (event_id,))

    def save_ai_summary(self, event_id, summary, hash_value, version):
        import psycopg

        with psycopg.connect(self.database_url) as connection:
            connection.execute("UPDATE classified_events SET ai_summary=%s, ai_context_hash=%s, ai_context_version=%s, updated_at=now() WHERE id=%s", (summary, hash_value, version, event_id))

    def record_ai_cache_hit(self, event_id):
        import psycopg

        with psycopg.connect(self.database_url) as connection:
            connection.execute("UPDATE classified_events SET ai_summary_cache_hits=ai_summary_cache_hits+1 WHERE id=%s", (event_id,))

    def get_ai_answer(self, event_id, question_hash, context_hash, context_version):
        row = self._query("""
            UPDATE ai_answers SET cache_hits=cache_hits+1, last_used_at=now()
            WHERE event_id::text=%s AND question_hash=%s AND context_hash=%s AND context_version=%s
            RETURNING answer
        """, (event_id, question_hash, context_hash, context_version), one=True)
        return row["answer"] if row else None

    def save_ai_answer(self, event_id, _question, question_hash, context_hash, context_version, answer):
        import psycopg

        with psycopg.connect(self.database_url) as connection:
            connection.execute("""
                INSERT INTO ai_answers (event_id,question_hash,context_hash,context_version,answer)
                VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
            """, (event_id, question_hash, context_hash, context_version, answer))

    def get_satellite_cache(self, cache_key):
        row = self._query("SELECT result FROM satellite_enrichment_cache WHERE cache_key=%s AND expires_at>now()", (cache_key,), one=True)
        return row["result"] if row else None

    def save_satellite_cache(self, cache_key, result, ttl_hours):
        import json
        import psycopg

        with psycopg.connect(self.database_url) as connection:
            connection.execute("""
                INSERT INTO satellite_enrichment_cache (cache_key,result,expires_at)
                VALUES (%s,%s::jsonb,now()+make_interval(hours => %s))
                ON CONFLICT (cache_key) DO UPDATE SET result=EXCLUDED.result,
                    expires_at=EXCLUDED.expires_at, updated_at=now()
            """, (cache_key, json.dumps(result), ttl_hours))

    def metrics(self):
        row = self._query("""
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE full_classification_skipped) AS reused,
                   count(*) FILTER (WHERE NOT full_classification_skipped) AS full,
                   COALESCE(sum(ai_summary_cache_hits),0) AS ai_hits,
                   avg(classification_duration_ms) FILTER (WHERE full_classification_skipped) AS fast_ms,
                   avg(classification_duration_ms) FILTER (WHERE NOT full_classification_skipped) AS full_ms,
                   (SELECT COALESCE(sum(cache_hits),0) FROM ai_answers) AS ai_answer_hits
            FROM classified_events
        """, one=True)
        total = row["total"]
        return {"totalDetectionsProcessed": total, "fullClassifications": row["full"],
                "reusedClassifications": row["reused"],
                "classificationCacheHitRate": row["reused"] / total if total else 0,
                "satelliteProcessingAvoided": row["reused"], "aiSummaryCallsAvoided": row["ai_hits"],
                "aiAnswerCallsAvoided": row["ai_answer_hits"],
                "aiCallsAvoided": row["ai_hits"] + row["ai_answer_hits"],
                "averageFastPathMs": row["fast_ms"], "averageFullPipelineMs": row["full_ms"]}

    def record_processing_metrics(self, event_id, duration_ms):
        import psycopg

        with psycopg.connect(self.database_url) as connection:
            connection.execute("UPDATE classified_events SET classification_duration_ms=%s WHERE id=%s", (duration_ms, event_id))

    def sync_alert(self, event_id, profile_id, record, result, severity):
        import psycopg

        anomaly = result.evidence.get("is_anomaly", False)
        alert = alert_for({"id": event_id, "classification": result.classification,
                           "confidence": result.confidence, "severity": severity, "isAnomaly": anomaly})
        if not alert:
            return None
        day = str(record["detected_at"])[:10]
        alert["deduplicationKey"] = f"{profile_id}:{result.classification}:{day}"
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute("""
                INSERT INTO alerts (event_id, deduplication_key, severity, reason)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (deduplication_key) DO UPDATE SET event_id=EXCLUDED.event_id, severity=EXCLUDED.severity,
                    reason=EXCLUDED.reason, updated_at=now()
                RETURNING id::text
            """, (event_id, alert["deduplicationKey"], alert["severity"], alert["reason"])).fetchone()
        return row[0]

    def list_alerts(self, status=None):
        where, params = (" WHERE a.status=%s", (status,)) if status else ("", ())
        return self._query("""
            SELECT a.id::text, a.event_id::text AS "eventId", a.status, a.severity,
                   a.reason, a.created_at AS "createdAt", a.updated_at AS "updatedAt"
            FROM alerts a
        """ + where + " ORDER BY a.created_at DESC LIMIT 200", params)

    def set_alert_status(self, alert_id, status):
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            row = connection.execute("""
                UPDATE alerts SET status=%s, updated_at=now() WHERE id::text=%s
                RETURNING id::text, event_id::text AS "eventId", status, severity, reason,
                          created_at AS "createdAt", updated_at AS "updatedAt"
            """, (status, alert_id)).fetchone()
        return _json_ready(row) if row else None

    def upsert_raw_detection(self, record, raw_payload=None):
        import json
        import psycopg

        with psycopg.connect(self.database_url) as connection:
            row = connection.execute("""
                INSERT INTO raw_firms_detections
                    (identity, location, detected_at, satellite, instrument, confidence, frp, brightness, scan, track, source, raw_payload)
                VALUES (%s, ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (identity) DO UPDATE SET identity=EXCLUDED.identity
                RETURNING id::text
            """, (record["identity"], record["longitude"], record["latitude"], record["detected_at"], record["satellite"], record["instrument"], record["confidence"], record["frp"], record["brightness"], record.get("scan"), record.get("track"), record["source"], json.dumps(raw_payload or record))).fetchone()
        return row[0]

    def start_job(self, source):
        import psycopg

        with psycopg.connect(self.database_url) as connection:
            return connection.execute("INSERT INTO ingestion_jobs (source,status) VALUES (%s,'running') RETURNING id", (source,)).fetchone()[0]

    def finish_job(self, job_id, status, processed, rejected, error=None):
        import psycopg

        with psycopg.connect(self.database_url) as connection:
            connection.execute("""
                UPDATE ingestion_jobs SET completed_at=now(), status=%s, records_processed=%s,
                    records_rejected=%s, error=%s WHERE id=%s
            """, (status, processed, rejected, str(error)[:2000] if error else None, job_id))

    def classified_event_for_raw(self, raw_id):
        row = self._query("SELECT id::text FROM classified_events WHERE raw_detection_id=%s", (raw_id,), one=True)
        return row["id"] if row else None

    def classification_context(self, record, radius):
        from datetime import datetime
        from .classification import Profile

        point = (record["longitude"], record["latitude"])
        zone = self._query("""
            SELECT osm_key AS id, name, tags, content_hash,
                   ST_Intersects(geometry, ST_SetSRID(ST_MakePoint(%s,%s),4326)) AS overlap,
                   ST_Distance(geometry::geography, ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography) AS distance
            FROM osm_industrial_zones
            WHERE ST_DWithin(geometry::geography, ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography, %s)
            ORDER BY overlap DESC, distance, ST_Area(geometry::geography) LIMIT 1
        """, (*point, *point, *point, radius), one=True)
        overlap = bool(zone and zone["overlap"])
        zone_id = zone["id"] if overlap else None
        osm_context = ({"overlap": overlap, "nearIndustrialZone": True, "zoneId": zone["id"],
                        "zoneName": zone["name"], "distanceMeters": round(zone["distance"], 1),
                        "tags": zone["tags"], "contentHash": zone["content_hash"]} if zone else
                       {"overlap": False, "nearIndustrialZone": False, "zoneId": None,
                        "zoneName": None, "distanceMeters": None, "tags": {}, "contentHash": None})
        profile = self._query("""
            SELECT id::text, classification, classification_confidence, classification_locked,
                   observation_count, consecutive_consistent_classifications,
                   COALESCE(mean_frp,0) AS mean_frp, COALESCE(frp_stddev,0) AS frp_stddev,
                   last_seen, classification_version, industrial_zone_id,
                   mean_scan, mean_track, max_cluster_size, manual_review_required, osm_context_hash,
                   ST_Y(centroid::geometry) AS latitude, ST_X(centroid::geometry) AS longitude
            FROM historical_thermal_profiles
            WHERE ((%s::text IS NOT NULL AND industrial_zone_id=%s)
                   OR (source_geometry IS NOT NULL AND ST_Intersects(source_geometry, ST_SetSRID(ST_MakePoint(%s,%s),4326)))
                   OR ST_DWithin(centroid, ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography, %s))
            ORDER BY CASE WHEN industrial_zone_id=%s THEN 0 ELSE 1 END,
                     ST_Distance(centroid, ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography)
            LIMIT 1
        """, (zone_id, zone_id, *point, *point, radius, zone_id, *point), one=True)
        cluster = self._query("""
            UPDATE raw_firms_detections SET cluster_size=(
                SELECT count(*) FROM raw_firms_detections nearby
                WHERE nearby.detected_at BETWEEN %s::timestamptz - interval '3 hours'
                                             AND %s::timestamptz + interval '3 hours'
                  AND ST_DWithin(nearby.location, ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography, %s)
            ) WHERE identity=%s RETURNING cluster_size
        """, (record["detected_at"], record["detected_at"], *point, radius, record["identity"]), one=True)["cluster_size"]
        if not profile:
            return None, overlap, zone_id, osm_context, cluster
        return Profile(
            profile["id"], profile["classification"], profile["classification_confidence"],
            profile["classification_locked"], profile["observation_count"],
            profile["consecutive_consistent_classifications"], profile["mean_frp"],
            profile["frp_stddev"], datetime.fromisoformat(profile["last_seen"]), profile["classification_version"],
            profile["latitude"], profile["longitude"], profile["industrial_zone_id"],
            profile["mean_scan"], profile["mean_track"], profile["max_cluster_size"],
            profile["manual_review_required"], profile["osm_context_hash"],
        ), overlap, zone_id, osm_context, cluster

    def ensure_profile(self, profile, record, result, zone_id, settings):
        if profile:
            return profile.id
        import psycopg

        with psycopg.connect(self.database_url) as connection:
            row = connection.execute("""
                INSERT INTO historical_thermal_profiles
                    (centroid, industrial_zone_id, classification, classification_confidence,
                     observation_count, consecutive_consistent_classifications, mean_frp,
                     median_frp, frp_stddev, max_frp, mean_scan, mean_track, max_cluster_size, first_seen, last_seen,
                     last_full_classification_at, classification_version)
                VALUES (ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography, %s, %s, %s,
                        0, 0, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id::text
            """, (record["longitude"], record["latitude"], zone_id, result.classification,
                    result.confidence, record.get("frp"), record.get("frp"), record.get("frp"),
                    record.get("scan"), record.get("track"), record.get("cluster_size", 1),
                    record["detected_at"], record["detected_at"], record["detected_at"],
                    settings.classification_version)).fetchone()
        return row[0]

    def save_classified_event(self, raw_id, profile_id, result, score, label, enrichment=None):
        import json
        import psycopg

        with psycopg.connect(self.database_url) as connection:
            row = connection.execute("""
                INSERT INTO classified_events
                    (raw_detection_id, profile_id, classification, classification_confidence,
                     classification_source, classification_reason, classification_version,
                     full_classification_skipped, severity_score, severity_label, severity_version, evidence, dnbr)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
                ON CONFLICT (raw_detection_id) DO UPDATE SET raw_detection_id=EXCLUDED.raw_detection_id
                RETURNING id::text
            """, (raw_id, profile_id, result.classification, result.confidence, result.source,
                    "; ".join(result.reasons), os.getenv("CLASSIFICATION_PIPELINE_VERSION", "v1"),
                    result.full_classification_skipped, score, label, os.getenv("SEVERITY_MODEL_VERSION", "v1"),
                    json.dumps({**result.evidence, "satellite": enrichment}),
                    enrichment.get("dnbr") if enrichment and enrichment.get("available") else None)).fetchone()
        return row[0]

    def refresh_profile(self, event_id, profile_id, record, result, zone_id, settings):
        import psycopg

        consistent = "CASE WHEN p.classification=%s THEN p.consecutive_consistent_classifications+1 ELSE 1 END"
        confidence = "CASE WHEN p.classification=%s THEN LEAST(0.99,GREATEST(p.classification_confidence,%s)+0.02) ELSE GREATEST(0.1,p.classification_confidence-0.15) END"
        with psycopg.connect(self.database_url) as connection:
            connection.execute(f"""
                WITH stats AS (
                    SELECT count(*) AS n, avg(d.frp) AS mean, percentile_cont(0.5) WITHIN GROUP (ORDER BY d.frp) AS median,
                           COALESCE(stddev_pop(d.frp),0) AS stddev, max(d.frp) AS maximum,
                           avg(d.scan) AS mean_scan, avg(d.track) AS mean_track,
                           max(d.cluster_size) AS max_cluster_size,
                           array_agg(DISTINCT EXTRACT(HOUR FROM d.detected_at)::smallint) AS hours,
                           count(*) FILTER (WHERE e.classification='industrial') AS industrial,
                           count(*) FILTER (WHERE e.classification='wildfire') AS wildfire,
                           count(*) FILTER (WHERE e.classification='unknown') AS unknown
                    FROM classified_events e JOIN raw_firms_detections d ON d.id=e.raw_detection_id
                    WHERE e.profile_id=%s
                )
                UPDATE historical_thermal_profiles p SET
                    classification=%s, classification_confidence={confidence},
                    consecutive_consistent_classifications={consistent},
                    classification_locked=(%s='industrial' AND ({confidence}) >= %s AND ({consistent}) >= %s),
                    observation_count=stats.n, industrial_observation_count=stats.industrial,
                    wildfire_observation_count=stats.wildfire, unknown_observation_count=stats.unknown,
                    mean_frp=stats.mean, median_frp=stats.median, frp_stddev=stats.stddev, max_frp=stats.maximum,
                    mean_scan=stats.mean_scan, mean_track=stats.mean_track, max_cluster_size=stats.max_cluster_size,
                    typical_detection_hours=stats.hours,
                    historical_pattern_score=GREATEST(stats.industrial,stats.wildfire,stats.unknown)::double precision / NULLIF(stats.n,0),
                    source_geometry=CASE WHEN %s THEN p.source_geometry ELSE COALESCE(
                        (SELECT geometry FROM osm_industrial_zones WHERE osm_key=%s),p.source_geometry) END,
                    osm_context_hash=CASE WHEN %s THEN p.osm_context_hash ELSE (SELECT content_hash FROM osm_industrial_zones WHERE osm_key=%s) END,
                    industrial_zone_id=CASE WHEN %s THEN p.industrial_zone_id ELSE COALESCE(%s,p.industrial_zone_id) END,
                    last_seen=%s,
                    last_full_classification_at=CASE WHEN %s THEN p.last_full_classification_at ELSE %s END,
                    classification_version=%s, updated_at=now()
                FROM stats WHERE p.id=%s
            """, (profile_id, result.classification,
                    result.classification, result.confidence, result.classification,
                    result.classification, result.classification, result.confidence, settings.lock_confidence,
                    result.classification, settings.min_consistent,
                    result.full_classification_skipped, zone_id,
                    result.full_classification_skipped, zone_id,
                    result.full_classification_skipped, zone_id, record["detected_at"],
                    result.full_classification_skipped, record["detected_at"], settings.classification_version,
                    profile_id))

    def upsert_osm_zone(self, feature):
        import json
        import psycopg

        content_hash = sha256(json.dumps({"geometry": feature["geometry"], "tags": feature["tags"]}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        with psycopg.connect(self.database_url) as connection:
            connection.execute("""
                INSERT INTO osm_industrial_zones (osm_key, id, osm_type, name, tags, geometry, content_hash, refreshed_at)
                VALUES (%s,%s,%s,%s,%s::jsonb,ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),%s,now())
                ON CONFLICT (osm_key) DO UPDATE SET name=EXCLUDED.name,
                    tags=EXCLUDED.tags, geometry=EXCLUDED.geometry, content_hash=EXCLUDED.content_hash, refreshed_at=now()
            """, (feature["osm_key"], feature["id"], feature["osm_type"], feature["name"], json.dumps(feature["tags"]), json.dumps(feature["geometry"]), content_hash))


def _json_ready(row):
    return {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in row.items()}


class DemoRepository:
    """Explicit local/demo fixture; production uses PostgresRepository."""

    def __init__(self):
        self.events = deepcopy(DEMO_EVENTS)
        for event in self.events:
            event.setdefault("profileId", event["id"])
            event.setdefault("isAnomaly", False)
            event.setdefault("osmContext", {"overlap": event["industrialOverlap"], "nearIndustrialZone": event["industrialOverlap"], "zoneId": None, "zoneName": None, "distanceMeters": 0 if event["industrialOverlap"] else None, "tags": {}})
            event.setdefault("region", event["osmContext"].get("zoneName"))
            event.setdefault("satelliteEvidence", {"available": event["dnbr"] is not None, "dnbr": event["dnbr"], "reason": None if event["dnbr"] is not None else "Suitable pre/post imagery unavailable"})
            event.setdefault("classificationEvidence", {"industrial_overlap": event["industrialOverlap"], "historical_detection_count": event["historicalObservations"], "frp_deviation": None, "dnbr": event["dnbr"], "classification": event["classification"], "confidence": event["confidence"], "reasoning": [event["classificationReason"]], "osm_context": event["osmContext"]})
        self.alerts = [{"id": f"demo-alert-{index}", **alert} for index, event in enumerate(self.events, 1) if (alert := alert_for(event))]
        self.ai_answers = {}

    def list_events(self, *, page=1, page_size=50, classification=None, severity=None, source=None, region=None, start=None, end=None, min_confidence=None, **_):
        rows = self._filter(classification, severity, source, region, start, end, min_confidence)
        return rows[(page - 1) * page_size:page * page_size], len(rows)

    def health(self):
        return True

    def map_events(self, *, bbox=None, classification=None, severity=None, source=None, region=None, start=None, end=None, min_confidence=None, **_):
        rows = self._filter(classification, severity, source, region, start, end, min_confidence)
        if bbox:
            rows = [row for row in rows if bbox[0] <= row["longitude"] <= bbox[2] and bbox[1] <= row["latitude"] <= bbox[3]]
        return rows

    def _filter(self, classification, severity, source, region=None, start=None, end=None, min_confidence=None):
        return [deepcopy(row) for row in self.events if (not classification or row["classification"] == classification) and (not severity or row["severity"] == severity) and (not source or row["instrument"] == source) and (not region or region.casefold() in (row.get("region") or "").casefold()) and (not start or row["detectedAt"] >= start) and (not end or row["detectedAt"] < end) and (min_confidence is None or row["confidence"] >= min_confidence)]

    def get_event(self, event_id):
        return next((deepcopy(row) for row in self.events if row["id"] == event_id), None)

    def event_history(self, event_id):
        event = self.get_event(event_id)
        if not event:
            return []
        rows = deepcopy(DEMO_HISTORY.get(event["profileId"], []))
        rows.extend(deepcopy(item) for item in self.events if item["profileId"] == event["profileId"])
        return sorted(rows, key=lambda item: item["detectedAt"], reverse=True)

    def save_ai_summary(self, event_id, summary, hash_value, version):
        for event in self.events:
            if event["id"] == event_id:
                event["aiSummary"] = summary
                event["aiContextHash"] = hash_value
                event["aiContextVersion"] = version

    def record_ai_cache_hit(self, _event_id):
        return None

    def get_ai_answer(self, event_id, question_hash, context_hash, context_version):
        return self.ai_answers.get((event_id, question_hash, context_hash, context_version))

    def save_ai_answer(self, event_id, _question, question_hash, context_hash, context_version, answer):
        self.ai_answers[(event_id, question_hash, context_hash, context_version)] = answer

    def list_alerts(self, status=None):
        return [deepcopy(alert) for alert in self.alerts if not status or alert["status"] == status]

    def set_alert_status(self, alert_id, status):
        alert = next((item for item in self.alerts if item["id"] == alert_id), None)
        if alert:
            alert["status"] = status
        return deepcopy(alert)

    def metrics(self):
        reused = sum(event["fullClassificationSkipped"] for event in self.events)
        return {"totalDetectionsProcessed": len(self.events), "fullClassifications": len(self.events) - reused,
                "reusedClassifications": reused, "classificationCacheHitRate": reused / len(self.events),
                "satelliteProcessingAvoided": reused, "aiSummaryCallsAvoided": 0,
                "aiAnswerCallsAvoided": 0, "aiCallsAvoided": 0,
                "averageFastPathMs": None, "averageFullPipelineMs": None}


DEMO_EVENTS = [
    {"id": "11111111-1111-1111-1111-111111111111", "profileId": "industrial-profile", "latitude": 20.5937, "longitude": 78.9629, "detectedAt": "2026-09-08T14:32:00+00:00", "satellite": "NOAA-20", "instrument": "VIIRS", "frp": 38.2, "brightness": 331.2, "classification": "industrial", "confidence": 0.94, "severity": "medium", "severityScore": 55, "dnbr": None, "classificationSource": "historical_profile", "classificationReason": "Recurring thermal source inside an OSM industrial area", "fullClassificationSkipped": True, "historicalObservations": 27, "industrialOverlap": True, "osmContext": {"overlap": True, "nearIndustrialZone": True, "zoneId": "way/1001", "zoneName": "Central Steel Works", "distanceMeters": 0, "tags": {"landuse": "industrial"}}, "aiSummary": None},
    {"id": "22222222-2222-2222-2222-222222222222", "latitude": 22.9734, "longitude": 78.6569, "detectedAt": "2026-09-08T12:10:00+00:00", "satellite": "Suomi NPP", "instrument": "VIIRS", "frp": 82.6, "brightness": 356.8, "classification": "wildfire", "confidence": 0.91, "severity": "high", "severityScore": 86, "dnbr": 0.48, "classificationSource": "satellite_enrichment", "classificationReason": "Strong burn-change evidence outside known industrial land use", "fullClassificationSkipped": False, "historicalObservations": 2, "industrialOverlap": False, "aiSummary": None},
    {"id": "33333333-3333-3333-3333-333333333333", "latitude": 18.5204, "longitude": 73.8567, "detectedAt": "2026-09-08T09:45:00+00:00", "satellite": "Aqua", "instrument": "MODIS", "frp": 12.1, "brightness": 310.4, "classification": "unknown", "confidence": 0.46, "severity": "low", "severityScore": 24, "dnbr": None, "classificationSource": "full_pipeline", "classificationReason": "Insufficient corroborating industrial or burn evidence", "fullClassificationSkipped": False, "historicalObservations": 1, "industrialOverlap": False, "aiSummary": None},
    {"id": "44444444-4444-4444-4444-444444444444", "profileId": "industrial-profile", "latitude": 20.5941, "longitude": 78.9632, "detectedAt": "2026-09-08T15:20:00+00:00", "satellite": "Sentinel-2", "instrument": "VIIRS", "frp": 126.4, "brightness": 372.5, "classification": "wildfire", "confidence": 0.90, "severity": "high", "severityScore": 88, "dnbr": 0.57, "classificationSource": "satellite_enrichment", "classificationReason": "FRP exceeded the industrial baseline and burn-change evidence forced full re-evaluation", "fullClassificationSkipped": False, "historicalObservations": 28, "industrialOverlap": True, "isAnomaly": True, "osmContext": {"overlap": True, "nearIndustrialZone": True, "zoneId": "way/1001", "zoneName": "Central Steel Works", "distanceMeters": 0, "tags": {"landuse": "industrial"}}, "satelliteEvidence": {"available": True, "preNbr": 0.61, "postNbr": 0.04, "dnbr": 0.57, "preItem": "HLS.S30.pre", "postItem": "HLS.S30.post", "quality": "clear_at_event"}, "classificationEvidence": {"industrial_overlap": True, "historical_detection_count": 27, "frp_deviation": 8.4, "dnbr": 0.57, "classification": "wildfire", "confidence": 0.90, "reasoning": ["FRP exceeds historical baseline", "Burn evidence conflicts with historical profile", "Strong burn-change evidence"]}, "aiSummary": None},
]

DEMO_HISTORY = {
    "industrial-profile": [
        {"id": "history-industrial-1", "detectedAt": "2026-09-01T14:10:00+00:00", "classification": "industrial", "frp": 34.1, "fullClassificationSkipped": False},
        {"id": "history-industrial-2", "detectedAt": "2026-09-04T14:18:00+00:00", "classification": "industrial", "frp": 36.8, "fullClassificationSkipped": False},
        {"id": "history-industrial-3", "detectedAt": "2026-09-06T14:25:00+00:00", "classification": "industrial", "frp": 37.4, "fullClassificationSkipped": False},
    ]
}
