from agniview.ai import event_context


def test_trusted_context_has_canonical_sections_and_quality_notes():
    context = event_context({
        "id": "event-1", "latitude": 20.5, "longitude": 78.2,
        "detectedAt": "2026-09-08T00:00:00+00:00", "instrument": "VIIRS",
        "frp": None, "brightness": 330, "classification": "industrial", "confidence": .91,
        "classificationReason": "Recurring source", "classificationEvidence": {"reasoning": ["Recurring source"]},
        "severity": "medium", "severityScore": 40, "dnbr": None,
        "historicalObservations": 12, "osmContext": {"overlap": True, "zoneName": "Steel works"},
        "profileMeanFrp": 22.5, "profileMedianFrp": 21.0, "profileFrpStddev": 2.5,
        "profileMaxFrp": 31.0, "profileTypicalHours": [2, 14], "profilePatternScore": .92,
        "profileFirstSeen": "2026-01-01T00:00:00+00:00", "profileLastSeen": "2026-09-08T00:00:00+00:00",
        "nearbyEvents": [
            {"id": "event-1", "frp": None, "classification": "industrial"},
            {"id": "event-0", "detectedAt": "2026-09-07T00:00:00+00:00", "frp": 20,
             "classification": "industrial", "fullClassificationSkipped": True},
        ],
        "satelliteEvidence": {"available": False, "reason": "Cloudy"},
    })

    assert context["event_id"] == "event-1"
    assert context["coordinates"] == {"latitude": 20.5, "longitude": 78.2}
    assert context["historical_profile"]["observation_count"] == 12
    assert context["historical_profile"]["mean_frp"] == 22.5
    assert context["historical_profile"]["typical_detection_hours"] == [2, 14]
    assert context["nearby_events"] == [{"event_id": "event-0", "timestamp": "2026-09-07T00:00:00+00:00", "frp": 20, "classification": "industrial", "full_classification_skipped": True}]
    assert context["osm_context"]["zoneName"] == "Steel works"
    assert context["satellite_context"]["reason"] == "Cloudy"
    assert "FRP unavailable" in context["data_quality_notes"]
    assert "dNBR unavailable" in context["data_quality_notes"]


def test_trusted_context_ignores_frontend_injected_fields():
    context = event_context({"id": "event-1", "frp": 10, "classification": "unknown", "confidence": .4, "frontendClaim": "wildfire"})
    assert "frontendClaim" not in str(context)
