from datetime import datetime, timedelta, timezone

from agniview.classification import Detection, Profile, classify


NOW = datetime(2026, 9, 8, tzinfo=timezone.utc)


def profile(**changes):
    values = {
        "id": "profile-1",
        "classification": "industrial",
        "confidence": 0.94,
        "locked": True,
        "observations": 8,
        "consecutive_consistent": 6,
        "mean_frp": 20.0,
        "frp_stddev": 3.0,
        "last_seen": NOW - timedelta(days=1),
        "version": "v1",
        "latitude": 20.0,
        "longitude": 78.0,
    }
    values.update(changes)
    return Profile(**values)


def detection(**changes):
    values = {"latitude": 20.001, "longitude": 78.001, "frp": 22.0, "industrial_overlap": True, "dnbr": None}
    values.update(changes)
    return Detection(**values)


def test_trusted_normal_profile_uses_fast_path():
    result = classify(detection(), profile(), now=NOW)
    assert result.classification == "industrial"
    assert result.source == "historical_profile"
    assert result.full_classification_skipped is True
    assert result.evidence["historical_detection_count"] == 8
    assert result.evidence["industrial_overlap"] is True


def test_frp_anomaly_forces_full_classification():
    result = classify(detection(frp=40.0), profile(), now=NOW)
    assert result.source == "full_pipeline"
    assert result.full_classification_skipped is False
    assert "FRP exceeds historical baseline" in result.reasons
    assert round(result.evidence["frp_deviation"], 2) == 6.67


def test_frp_change_from_zero_variance_baseline_forces_full_classification():
    result = classify(detection(frp=40.0), profile(mean_frp=20, frp_stddev=0), now=NOW)
    assert result.full_classification_skipped is False
    assert "FRP exceeds historical baseline" in result.reasons


def test_version_mismatch_forces_full_classification():
    result = classify(detection(), profile(version="v0"), now=NOW, pipeline_version="v1")
    assert result.source == "full_pipeline"
    assert "Classification version is stale" in result.reasons


def test_distant_detection_does_not_inherit_profile():
    result = classify(detection(latitude=21.0), profile(), now=NOW)
    assert result.source == "full_pipeline"
    assert result.profile_id is None


def test_burn_evidence_forces_wildfire_classification():
    result = classify(detection(industrial_overlap=False, dnbr=0.55), None, now=NOW)
    assert result.classification == "wildfire"
    assert result.confidence >= 0.8


def test_locked_non_industrial_profile_never_uses_fast_path():
    result = classify(detection(industrial_overlap=False), profile(classification="wildfire"), now=NOW)
    assert result.source == "full_pipeline"
    assert result.full_classification_skipped is False


def test_missing_frp_does_not_break_classification():
    result = classify(detection(frp=None), profile(), now=NOW)
    assert result.source == "historical_profile"
    assert result.evidence["frp_deviation"] is None


def test_non_frp_safety_signals_force_full_reclassification():
    scenarios = (
        (detection(industrial_zone_id="way/2"), profile(industrial_zone_id="way/1"), "OSM industrial context changed"),
        (detection(osm_context_hash="new"), profile(osm_context_hash="old"), "OSM industrial context changed"),
        (detection(scan=4), profile(mean_scan=1), "Thermal footprint changed"),
        (detection(cluster_size=8), profile(max_cluster_size=2), "Thermal cluster is abnormal"),
        (detection(), profile(manual_review_required=True), "Profile requires manual review"),
        (detection(conflicting_evidence=True), profile(), "New evidence conflicts with historical profile"),
    )
    for observed, historical, reason in scenarios:
        result = classify(observed, historical, now=NOW)
        assert result.full_classification_skipped is False
        assert reason in result.reasons


def test_configured_burn_threshold_controls_fast_path_and_industrial_override():
    observed = detection(dnbr=.25)
    burned = classify(observed, profile(), now=NOW, dnbr_wildfire_threshold=.2)
    assert burned.classification == "wildfire"
    assert burned.full_classification_skipped is False
    assert "Burn evidence conflicts with historical profile" in burned.reasons
    normal = classify(observed, profile(), now=NOW, dnbr_wildfire_threshold=.4)
    assert normal.full_classification_skipped is True
