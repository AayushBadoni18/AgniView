from copy import deepcopy

from agniview.ai import context_hash, event_context
from agniview.api import create_app
from agniview.repository import DemoRepository


EVENT = {
    "id": "evt-1", "latitude": 20.5, "longitude": 78.2,
    "detectedAt": "2026-09-08T14:32:00+00:00", "satellite": "NOAA-20",
    "instrument": "VIIRS", "frp": 38.2, "brightness": 331.2,
    "classification": "industrial", "confidence": 0.94, "severity": "medium",
    "severityScore": 55, "dnbr": None, "classificationSource": "historical_profile",
    "classificationReason": "Known recurring industrial thermal source",
    "fullClassificationSkipped": True, "historicalObservations": 27,
    "industrialOverlap": True, "aiSummary": None,
}


class FakeRepository:
    last_filters = None

    def list_events(self, **filters):
        self.last_filters = filters
        return [EVENT], 1

    def map_events(self, **filters):
        self.last_filters = filters
        return [EVENT]

    def get_event(self, event_id):
        return EVENT if event_id == "evt-1" else None

    def event_history(self, event_id):
        return [EVENT] if event_id == "evt-1" else []

    def save_ai_summary(self, event_id, summary, context_hash, context_version):
        return None

    def record_ai_cache_hit(self, event_id):
        return None

    def get_ai_answer(self, event_id, question_hash, context_hash, context_version):
        return None

    def save_ai_answer(self, event_id, question, question_hash, context_hash, context_version, answer):
        return None

    def list_alerts(self, status=None):
        return [{"id": "alert-1", "eventId": "evt-1", "status": status or "open"}]

    def set_alert_status(self, alert_id, status):
        return {"id": alert_id, "eventId": "evt-1", "status": status} if alert_id == "alert-1" else None

    def metrics(self):
        return {"totalDetectionsProcessed": 1, "reusedClassifications": 1}


def client():
    return create_app(FakeRepository()).test_client()


def test_lists_paginated_events():
    response = client().get("/api/events?page=1&pageSize=20&classification=industrial")
    assert response.status_code == 200
    assert response.get_json()["pagination"]["totalItems"] == 1


def test_rejects_invalid_bbox():
    response = client().get("/api/events/map?bbox=bad")
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_validates_time_and_confidence_filters():
    repository = FakeRepository()
    app = create_app(repository).test_client()
    assert app.get("/api/events?minConfidence=2").status_code == 422
    assert app.get("/api/events?start=not-a-date").status_code == 422
    response = app.get("/api/events?minConfidence=.8&start=2026-09-01T00:00:00Z")
    assert response.status_code == 200
    assert repository.last_filters["min_confidence"] == .8
    assert app.get("/api/events?region=" + "x" * 101).status_code == 422


def test_validates_filters_on_every_filtered_endpoint():
    for path in ("/api/alerts?status=bad", "/api/exports/events.csv?classification=bogus"):
        response = client().get(path)
        assert response.status_code == 422
        assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_returns_event_detail_and_not_found():
    assert client().get("/api/events/evt-1").status_code == 200
    assert client().get("/api/events/missing").status_code == 404


def test_ask_ai_uses_backend_event_context_and_validates_question():
    response = client().post("/api/events/evt-1/ask", json={"question": "Why industrial?", "frp": 999999})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["event_id"] == "evt-1" and payload["context_version"] == "v1" and payload["generated_at"]
    assert "38.2" in payload["answer"]
    assert "999999" not in payload["answer"]
    assert client().post("/api/events/evt-1/ask", json={"question": ""}).status_code == 422


def test_ask_ai_receives_repository_history_as_trusted_context():
    class Provider:
        context = None
        def answer_event_question(self, _question, context):
            self.context = context
            return "grounded"

    class Repository(FakeRepository):
        def event_history(self, _event_id):
            return [EVENT, {**EVENT, "id": "evt-0", "detectedAt": "2026-09-07T14:32:00+00:00"}]

    provider = Provider()
    app = create_app(Repository(), provider).test_client()
    assert app.post("/api/events/evt-1/ask", json={"question": "What happened before?"}).status_code == 200
    assert [item["event_id"] for item in provider.context["nearby_events"]] == ["evt-0"]


def test_exports_csv_and_pdf():
    assert client().get("/api/exports/events.csv").mimetype == "text/csv"
    pdf = client().get("/api/exports/events.pdf")
    assert pdf.mimetype == "application/pdf"
    assert pdf.data.startswith(b"%PDF-1.4")


def test_summary_is_persisted_for_reuse():
    repository = FakeRepository()
    saved = []
    repository.save_ai_summary = lambda *args: saved.append(args)
    response = create_app(repository).test_client().get("/api/events/evt-1/ai-summary")
    assert response.status_code == 200
    assert len(saved) == 1


def test_summary_cache_is_reused_only_for_matching_context():
    class Provider:
        calls = 0

        def generate_event_summary(self, _context):
            self.calls += 1
            return "fresh"

    repository = FakeRepository()
    cached = deepcopy(EVENT)
    cached.update(aiSummary="cached", aiContextHash=context_hash(event_context(cached)), aiContextVersion="v1")
    repository.get_event = lambda _event_id: cached
    saved = []
    repository.save_ai_summary = lambda *args: saved.append(args)
    provider = Provider()
    app = create_app(repository, provider).test_client()

    assert app.get("/api/events/evt-1/ai-summary").get_json()["summary"] == "cached"
    assert provider.calls == 0
    cached["frp"] = 99
    assert app.get("/api/events/evt-1/ai-summary").get_json()["summary"] == "fresh"
    assert provider.calls == 1
    assert len(saved) == 1


def test_alert_lifecycle_and_validation():
    app = client()
    assert app.get("/api/alerts?status=open").get_json()["data"][0]["status"] == "open"
    assert app.patch("/api/alerts/alert-1", json={"status": "acknowledged"}).status_code == 200
    assert app.patch("/api/alerts/alert-1", json={"status": "bad"}).status_code == 422
    assert app.patch("/api/alerts/missing", json={"status": "resolved"}).status_code == 404


def test_unknown_route_remains_not_found():
    response = client().get("/missing-route")
    assert response.status_code == 404
    assert response.headers["X-Request-ID"]


def test_demo_summary_is_generated_once_then_reused():
    class Provider:
        calls = 0
        def generate_event_summary(self, _context): self.calls += 1; return "summary"
    provider = Provider()
    app = create_app(DemoRepository(), provider).test_client()
    path = "/api/events/11111111-1111-1111-1111-111111111111/ai-summary"
    assert app.get(path).status_code == 200
    assert app.get(path).status_code == 200
    assert provider.calls == 1


def test_demo_exposes_profile_history_and_anomaly_fallback():
    app = create_app(DemoRepository()).test_client()
    events = app.get("/api/events?pageSize=20").get_json()["data"]
    anomaly = next(event for event in events if event.get("isAnomaly"))
    assert anomaly["fullClassificationSkipped"] is False
    assert anomaly["classificationSource"] == "satellite_enrichment"
    history = app.get(f'/api/events/{anomaly["id"]}/history').get_json()["data"]
    assert len(history) >= 3
    assert any(event["fullClassificationSkipped"] for event in history)


def test_demo_applies_real_bbox_classification_and_region_filters():
    app = create_app(DemoRepository()).test_client()
    features = app.get("/api/events/map?bbox=78.5,22.5,79,23&classification=wildfire").get_json()["features"]
    assert [feature["properties"]["id"] for feature in features] == ["22222222-2222-2222-2222-222222222222"]
    assert app.get("/api/events?region=Central&pageSize=20").get_json()["pagination"]["totalItems"] == 2


def test_database_failure_returns_stable_error_and_degraded_health():
    class BrokenRepository(FakeRepository):
        def health(self): return False
        def list_events(self, **_filters): raise RuntimeError("database secret detail")
    app = create_app(BrokenRepository()).test_client()
    assert app.get("/health").status_code == 503
    response = app.get("/api/events")
    assert response.status_code == 500
    assert response.get_json() == {"error": {"code": "INTERNAL_ERROR", "message": "The request could not be completed"}}


def test_ask_answer_is_persistently_reused_for_same_question_and_context():
    class Provider:
        calls = 0
        def answer_event_question(self, _question, _context): self.calls += 1; return "grounded"
    provider = Provider()
    repository = FakeRepository()
    cached = {}
    repository.get_ai_answer = lambda event_id, question_hash, context_hash, version: cached.get((event_id, question_hash, context_hash, version))
    repository.save_ai_answer = lambda event_id, question, question_hash, context_hash, version, answer: cached.update({(event_id, question_hash, context_hash, version): answer})
    app = create_app(repository, provider).test_client()
    path = "/api/events/evt-1/ask"
    assert app.post(path, json={"question": "Why?"}).get_json()["answer"] == "grounded"
    assert app.post(path, json={"question": "Why?"}).get_json()["answer"] == "grounded"
    assert provider.calls == 1
