from datetime import datetime, timezone

from agniview.classification import Profile
from agniview.pipeline import ThermalPipeline


RECORD = {
    "identity": "firm-1", "latitude": 20.001, "longitude": 78.001,
    "detected_at": "2026-09-08T14:32:00+00:00", "frp": 22.0,
    "satellite": "N20", "instrument": "VIIRS", "confidence": "n",
    "brightness": 331.2, "source": "VIIRS",
}


class Store:
    def __init__(self, profile=None, existing=None):
        self.profile, self.existing = profile, existing
        self.saved = []

    def upsert_raw_detection(self, record): return "raw-1"
    def classified_event_for_raw(self, raw_id): return self.existing
    def classification_context(self, record, radius): return self.profile, True, "zone-1", {"overlap": True, "zoneName": "Plant"}, 1
    def ensure_profile(self, profile, record, result, zone_id, settings): return profile.id if profile else "profile-new"
    def save_classified_event(self, raw_id, profile_id, result, score, label, enrichment=None):
        self.saved.append((result, score, label, enrichment)); return "event-1"
    def refresh_profile(self, event_id, profile_id, record, result, zone_id, settings): return profile_id
    def sync_alert(self, event_id, profile_id, record, result, label): return None
    def record_processing_metrics(self, event_id, duration_ms): assert duration_ms >= 0


def trusted_profile():
    return Profile("profile-1", "industrial", .94, True, 8, 6, 20, 3, datetime(2026, 9, 7, tzinfo=timezone.utc), "v1", 20, 78)


def test_pipeline_is_idempotent_for_already_classified_detection():
    store = Store(existing="event-existing")
    assert ThermalPipeline(store).process(RECORD) == "event-existing"
    assert store.saved == []


def test_pipeline_persists_fast_path_and_refreshes_profile():
    store = Store(profile=trusted_profile())
    assert ThermalPipeline(store).process(RECORD) == "event-1"
    assert store.saved[0][0].source == "historical_profile"


def test_pipeline_runs_full_classification_for_new_source():
    store = Store()
    assert ThermalPipeline(store).process(RECORD) == "event-1"
    assert store.saved[0][0].source == "full_pipeline"
    assert store.saved[0][0].evidence["osm_context"]["zoneName"] == "Plant"


def test_pipeline_uses_available_burn_evidence():
    class Enricher:
        def enrich(self, _record): return {"available": True, "dnbr": .55}

    store = Store()
    ThermalPipeline(store, enricher=Enricher()).process(RECORD)
    assert store.saved[0][0].classification == "wildfire"
    assert store.saved[0][3]["dnbr"] == .55
