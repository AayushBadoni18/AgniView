from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt


@dataclass(frozen=True)
class Detection:
    latitude: float
    longitude: float
    frp: float | None
    industrial_overlap: bool = False
    dnbr: float | None = None
    osm_context: dict | None = None
    industrial_zone_id: str | None = None
    scan: float | None = None
    track: float | None = None
    cluster_size: int = 1
    conflicting_evidence: bool = False
    osm_context_hash: str | None = None


@dataclass(frozen=True)
class Profile:
    id: str
    classification: str
    confidence: float
    locked: bool
    observations: int
    consecutive_consistent: int
    mean_frp: float
    frp_stddev: float
    last_seen: datetime
    version: str
    latitude: float
    longitude: float
    industrial_zone_id: str | None = None
    mean_scan: float | None = None
    mean_track: float | None = None
    max_cluster_size: int | None = None
    manual_review_required: bool = False
    osm_context_hash: str | None = None


@dataclass(frozen=True)
class ClassificationResult:
    classification: str
    confidence: float
    source: str
    reasons: tuple[str, ...]
    profile_id: str | None
    full_classification_skipped: bool
    evidence: dict


def _distance_meters(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    lat1, lat2 = radians(a_lat), radians(b_lat)
    dlat, dlon = lat2 - lat1, radians(b_lon - a_lon)
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 12_742_000 * asin(sqrt(value))


def classify(
    detection: Detection,
    profile: Profile | None,
    *,
    now: datetime | None = None,
    pipeline_version: str = "v1",
    match_radius_meters: float = 1000,
    lock_confidence: float = 0.90,
    min_consistent: int = 3,
    anomaly_std_multiplier: float = 3,
    anomaly_min_delta: float = 5,
    footprint_multiplier: float = 2,
    cluster_multiplier: float = 2,
    dnbr_wildfire_threshold: float = .30,
    max_profile_age: timedelta = timedelta(days=30),
) -> ClassificationResult:
    now = now or datetime.now(timezone.utc)
    triggers: list[str] = []

    if profile:
        distance = _distance_meters(detection.latitude, detection.longitude, profile.latitude, profile.longitude)
        if distance > match_radius_meters:
            profile = None
        else:
            if profile.classification != "industrial":
                triggers.append("Only trusted industrial profiles may use the fast path")
            if not profile.locked or profile.confidence < lock_confidence or profile.consecutive_consistent < min_consistent:
                triggers.append("Historical profile is not trusted")
            if profile.version != pipeline_version:
                triggers.append("Classification version is stale")
            if now - profile.last_seen > max_profile_age:
                triggers.append("Historical profile is stale")
            if detection.frp is not None and detection.frp > profile.mean_frp + max(anomaly_min_delta, anomaly_std_multiplier * profile.frp_stddev):
                triggers.append("FRP exceeds historical baseline")
            if detection.dnbr is not None and detection.dnbr >= dnbr_wildfire_threshold:
                triggers.append("Burn evidence conflicts with historical profile")
            if (profile.industrial_zone_id and detection.industrial_zone_id != profile.industrial_zone_id
                    or detection.osm_context_hash and detection.osm_context_hash != profile.osm_context_hash):
                triggers.append("OSM industrial context changed")
            if ((profile.mean_scan and detection.scan and detection.scan > profile.mean_scan * footprint_multiplier)
                    or (profile.mean_track and detection.track and detection.track > profile.mean_track * footprint_multiplier)):
                triggers.append("Thermal footprint changed")
            if profile.max_cluster_size and detection.cluster_size > max(profile.max_cluster_size + 3, profile.max_cluster_size * cluster_multiplier):
                triggers.append("Thermal cluster is abnormal")
            if profile.manual_review_required:
                triggers.append("Profile requires manual review")
            if detection.conflicting_evidence:
                triggers.append("New evidence conflicts with historical profile")

            if not triggers:
                return _result(detection, profile, profile.classification, profile.confidence,
                               "historical_profile", ("Known recurring industrial thermal source",), True)

    if detection.dnbr is not None and detection.dnbr >= dnbr_wildfire_threshold:
        classification, confidence, evidence = "wildfire", 0.90, "Strong burn-change evidence"
    elif detection.industrial_overlap:
        classification, confidence, evidence = "industrial", 0.82, "Detection intersects an industrial area"
    else:
        classification, confidence, evidence = "unknown", 0.45, "Insufficient evidence for a confident label"

    return _result(detection, profile, classification, confidence,
                   "satellite_enrichment" if detection.dnbr is not None else "full_pipeline",
                   tuple(triggers + [evidence]), False)


def _result(detection, profile, classification, confidence, source, reasons, skipped):
    deviation = None
    if profile and detection.frp is not None and profile.frp_stddev > 0:
        deviation = (detection.frp - profile.mean_frp) / profile.frp_stddev
    anomaly_reasons = {
        "FRP exceeds historical baseline", "Burn evidence conflicts with historical profile",
        "OSM industrial context changed", "Thermal footprint changed", "Thermal cluster is abnormal",
        "Profile requires manual review", "New evidence conflicts with historical profile",
    }
    evidence = {
        "industrial_overlap": detection.industrial_overlap,
        "historical_detection_count": profile.observations if profile else 0,
        "frp_deviation": deviation,
        "dnbr": detection.dnbr,
        "scan": detection.scan, "track": detection.track, "cluster_size": detection.cluster_size,
        "classification": classification,
        "confidence": confidence,
        "reasoning": list(reasons),
        "is_anomaly": any(reason in anomaly_reasons for reason in reasons),
        "osm_context": detection.osm_context or {"overlap": detection.industrial_overlap},
    }
    return ClassificationResult(classification, confidence, source, reasons,
                                profile.id if profile else None, skipped, evidence)
