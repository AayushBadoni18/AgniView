import os
from time import perf_counter
from dataclasses import dataclass, replace
from datetime import timedelta

from .classification import Detection, classify
from .observability import log_event
from .severity import severity


@dataclass(frozen=True)
class PipelineSettings:
    match_radius_meters: float = 1000
    lock_confidence: float = 0.90
    min_consistent: int = 3
    anomaly_std_multiplier: float = 3
    anomaly_min_delta: float = 5
    footprint_multiplier: float = 2
    cluster_multiplier: float = 2
    max_profile_age_days: int = 30
    classification_version: str = "v1"

    @classmethod
    def from_env(cls):
        return cls(
            float(os.getenv("THERMAL_PROFILE_MATCH_RADIUS_METERS", "1000")),
            float(os.getenv("INDUSTRIAL_LOCK_CONFIDENCE", "0.90")),
            int(os.getenv("MIN_CONSISTENT_CLASSIFICATIONS", "3")),
            float(os.getenv("FRP_ANOMALY_STD_MULTIPLIER", "3")),
            float(os.getenv("FRP_ANOMALY_MIN_ABSOLUTE_DELTA", "5")),
            float(os.getenv("FOOTPRINT_ANOMALY_MULTIPLIER", "2")),
            float(os.getenv("CLUSTER_ANOMALY_MULTIPLIER", "2")),
            int(os.getenv("THERMAL_PROFILE_MAX_AGE_DAYS", "30")),
            os.getenv("CLASSIFICATION_PIPELINE_VERSION", "v1"),
        )


class ThermalPipeline:
    def __init__(self, store, settings=None, enricher=None):
        self.store = store
        self.settings = settings or PipelineSettings.from_env()
        self.enricher = enricher

    def process(self, record, *, job_id=None, request_id=None):
        started = perf_counter()
        raw_id = self.store.upsert_raw_detection(record)
        existing = self.store.classified_event_for_raw(raw_id)
        if existing:
            log_event("thermal_event_reused", request_id=request_id or record["identity"], job=job_id,
                      event_id=existing, cache_status="idempotent_hit")
            return existing

        profile, industrial_overlap, zone_id, osm_context, cluster_size = self.store.classification_context(record, self.settings.match_radius_meters)
        record["cluster_size"] = cluster_size
        detection = Detection(record["latitude"], record["longitude"], record.get("frp"), industrial_overlap,
                              osm_context=osm_context, industrial_zone_id=zone_id, scan=record.get("scan"),
                              track=record.get("track"), cluster_size=cluster_size,
                              conflicting_evidence=bool(record.get("conflicting_evidence")),
                              osm_context_hash=osm_context.get("contentHash"))
        result = classify(
            detection,
            profile,
            pipeline_version=self.settings.classification_version,
            match_radius_meters=self.settings.match_radius_meters,
            lock_confidence=self.settings.lock_confidence,
            min_consistent=self.settings.min_consistent,
            anomaly_std_multiplier=self.settings.anomaly_std_multiplier,
            anomaly_min_delta=self.settings.anomaly_min_delta,
            footprint_multiplier=self.settings.footprint_multiplier,
            cluster_multiplier=self.settings.cluster_multiplier,
            max_profile_age=timedelta(days=self.settings.max_profile_age_days),
        )
        enrichment = None
        if self.enricher and not result.full_classification_skipped:
            enrichment = self.enricher.enrich(record)
            if enrichment.get("available"):
                detection = replace(detection, dnbr=enrichment["dnbr"])
                result = classify(detection, profile, pipeline_version=self.settings.classification_version,
                                  match_radius_meters=self.settings.match_radius_meters,
                                  lock_confidence=self.settings.lock_confidence, min_consistent=self.settings.min_consistent,
                                  anomaly_std_multiplier=self.settings.anomaly_std_multiplier,
                                  anomaly_min_delta=self.settings.anomaly_min_delta,
                                  footprint_multiplier=self.settings.footprint_multiplier,
                                  cluster_multiplier=self.settings.cluster_multiplier,
                                  max_profile_age=timedelta(days=self.settings.max_profile_age_days))
        score, label = severity(record.get("frp"), detection.dnbr, result.confidence)
        profile_id = self.store.ensure_profile(profile, record, result, zone_id, self.settings)
        event_id = self.store.save_classified_event(raw_id, profile_id, result, score, label, enrichment)
        self.store.refresh_profile(event_id, profile_id, record, result, zone_id, self.settings)
        self.store.sync_alert(event_id, profile_id, record, result, label)
        duration_ms = (perf_counter() - started) * 1000
        self.store.record_processing_metrics(event_id, duration_ms)
        log_event("thermal_event_classified", request_id=request_id or record["identity"], job=job_id,
                  event_id=event_id, profile_id=profile_id, classification_source=result.source,
                  duration_ms=round(duration_ms, 2), cache_status="historical_hit" if result.full_classification_skipped else "miss")
        return event_id
