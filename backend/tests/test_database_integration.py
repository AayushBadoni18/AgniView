import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agniview.pipeline import ThermalPipeline
from agniview.repository import PostgresRepository


DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is required for PostGIS integration")


def test_migrations_and_thermal_memory_end_to_end():
    import psycopg

    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        for table in ("ai_answers", "satellite_enrichment_cache", "alerts", "ingestion_jobs", "classified_events", "historical_thermal_profiles", "osm_industrial_zones", "raw_firms_detections"):
            connection.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        for migration in sorted((Path(__file__).parents[2] / "database" / "migrations").glob("*.sql")):
            connection.execute(migration.read_text())
        assert connection.execute("SELECT PostGIS_Version()").fetchone()[0]

    repository = PostgresRepository(DATABASE_URL)
    repository.upsert_osm_zone({"osm_key": "way/1", "id": 1, "osm_type": "way", "name": "Test works",
                                "tags": {"landuse": "industrial"}, "geometry": {"type": "Polygon", "coordinates": [[[77.99, 19.99], [78.01, 19.99], [78.01, 20.01], [77.99, 20.01], [77.99, 19.99]]]}})
    pipeline = ThermalPipeline(repository)
    started = datetime.now(timezone.utc) - timedelta(minutes=10)
    for index, frp in enumerate((18, 20, 22, 20, 20)):
        detected_at = (started + timedelta(minutes=index)).isoformat()
        event_id = pipeline.process({"identity": f"integration-{index}", "latitude": 20, "longitude": 78,
                                     "detected_at": detected_at, "frp": frp, "satellite": "N20",
                                     "instrument": "VIIRS", "confidence": "n", "brightness": 330, "source": "VIIRS"})
    event = repository.get_event(event_id)
    assert event["classificationSource"] == "historical_profile"
    assert event["fullClassificationSkipped"] is True
    profile = repository._query("""
        SELECT source_geometry IS NOT NULL AS has_geometry, typical_detection_hours AS hours,
               historical_pattern_score AS pattern_score, osm_context_hash
        FROM historical_thermal_profiles LIMIT 1
    """, one=True)
    assert profile["has_geometry"] is True
    assert profile["hours"]
    assert profile["pattern_score"] == 1
    assert profile["osm_context_hash"]

    repository.upsert_osm_zone({"osm_key": "way/1", "id": 1, "osm_type": "way", "name": "Renamed works",
                                "tags": {"landuse": "industrial", "operator": "changed"}, "geometry": {"type": "Polygon", "coordinates": [[[77.98, 19.98], [78.02, 19.98], [78.02, 20.02], [77.98, 20.02], [77.98, 19.98]]]}})
    changed_id = pipeline.process({"identity": "integration-osm-change", "latitude": 20, "longitude": 78,
                                   "detected_at": (started + timedelta(minutes=5)).isoformat(), "frp": 20,
                                   "satellite": "N20", "instrument": "VIIRS", "confidence": "n",
                                   "brightness": 330, "source": "VIIRS"})
    changed = repository.get_event(changed_id)
    assert changed["fullClassificationSkipped"] is False
    assert "OSM industrial context changed" in changed["classificationReason"]
    assert repository._query("SELECT ST_XMax(source_geometry) AS xmax FROM historical_thermal_profiles", one=True)["xmax"] == 78.02

    anomaly_id = pipeline.process({"identity": "integration-anomaly", "latitude": 20, "longitude": 78,
                                   "detected_at": (started + timedelta(minutes=7)).isoformat(), "frp": 100,
                                   "satellite": "N20", "instrument": "VIIRS", "confidence": "h",
                                   "brightness": 380, "source": "VIIRS"})
    anomaly = repository.get_event(anomaly_id)
    assert anomaly["fullClassificationSkipped"] is False
    assert "FRP exceeds historical baseline" in anomaly["classificationReason"]
    assert repository.list_alerts("open")[0]["eventId"] == anomaly_id
