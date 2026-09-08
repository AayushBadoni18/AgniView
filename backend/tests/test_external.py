from agniview.alerts import alert_for
from agniview.external import SatelliteEnricher, dnbr, nbr, normalize_osm_element, retry_session
from agniview.severity import severity


def test_nbr_and_dnbr_formulas():
    assert nbr(0.8, 0.2) == 0.6000000000000001
    assert round(dnbr(0.8, 0.2, 0.4, 0.6), 2) == 0.8
    assert nbr(0, 0) is None


def test_external_session_retries_transient_failures_only():
    retries = retry_session(3).get_adapter("https://").max_retries
    assert retries.total == 3
    assert 429 in retries.status_forcelist and 503 in retries.status_forcelist
    assert "POST" in retries.allowed_methods


def test_alerts_only_high_confidence_wildfire_or_anomaly():
    assert alert_for({"id": "1", "classification": "industrial", "confidence": 0.99}) is None
    alert = alert_for({"id": "2", "classification": "wildfire", "confidence": 0.9, "severity": "high"})
    assert alert["deduplicationKey"] == "2:wildfire:high"


def test_severity_is_bounded_and_explainable():
    assert severity(0, None, 1) == (0.0, "low")
    score, label = severity(1000, 1, 1)
    assert score == 90.0
    assert label == "high"


def test_normalizes_closed_osm_way_polygon():
    feature = normalize_osm_element({"id": 42, "type": "way", "tags": {"landuse": "industrial"}, "geometry": [{"lat": 20, "lon": 78}, {"lat": 20, "lon": 79}, {"lat": 21, "lon": 79}, {"lat": 20, "lon": 78}]})
    assert feature["id"] == 42
    assert feature["osm_key"] == "way/42"
    assert feature["geometry"]["type"] == "Polygon"


def test_rejects_incomplete_osm_geometry():
    assert normalize_osm_element({"id": 1, "type": "way", "geometry": []}) is None


def test_normalizes_relation_outer_members():
    ring = [{"lat": 20, "lon": 78}, {"lat": 20, "lon": 79}, {"lat": 21, "lon": 79}, {"lat": 20, "lon": 78}]
    feature = normalize_osm_element({"id": 9, "type": "relation", "members": [{"role": "outer", "geometry": ring}]})
    assert feature["geometry"]["type"] == "MultiPolygon"


def test_joins_split_relation_outer_ring_without_fabricating_triangles():
    first = [{"lat": 20, "lon": 78}, {"lat": 20, "lon": 79}, {"lat": 21, "lon": 79}]
    second = [{"lat": 21, "lon": 79}, {"lat": 20, "lon": 78}]
    feature = normalize_osm_element({"id": 9, "type": "relation", "members": [{"role": "outer", "geometry": first}, {"role": "outer", "geometry": second}]})
    assert feature["geometry"]["coordinates"][0][0] == [[78, 20], [79, 20], [79, 21], [78, 20]]


def test_hls_enrichment_reads_only_needed_assets_and_calculates_dnbr():
    def item(item_id, values):
        return {"id": item_id, "collection": "HLSS30_2.0", "properties": {"eo:cloud_cover": 2},
                "assets": {band: {"href": f"{item_id}.{band}.tif"} for band in values}}

    pre, post = item("pre", ("B8A", "B11", "Fmask")), item("post", ("B8A", "B11", "Fmask"))
    class Stac:
        calls = 0
        def search(self, *_args, **_kwargs):
            self.calls += 1
            return [pre if self.calls == 1 else post]
    class Reader:
        values = {"pre.B8A.tif": 8000, "pre.B11.tif": 2000, "pre.Fmask.tif": 0,
                  "post.B8A.tif": 4000, "post.B11.tif": 6000, "post.Fmask.tif": 0}
        def read(self, href, *_coordinates): return self.values[href]

    class Cache:
        value = None
        def get_satellite_cache(self, _key): return self.value
        def save_satellite_cache(self, _key, value, _ttl_hours): self.value = value
    stac, cache = Stac(), Cache()
    enricher = SatelliteEnricher(stac, Reader(), cache)
    result = enricher.enrich({"detected_at": "2026-09-08T00:00:00Z", "latitude": 20, "longitude": 78})
    assert result["available"] is True
    assert round(result["dnbr"], 2) == .8
    assert result["preItem"] == "pre" and result["postItem"] == "post"
    assert enricher.enrich({"detected_at": "2026-09-08T00:00:00Z", "latitude": 20, "longitude": 78}) == result
    assert stac.calls == 2


def test_hls_enrichment_fails_gracefully_when_imagery_is_missing():
    class Stac:
        def search(self, *_args, **_kwargs): return []
    assert SatelliteEnricher(Stac()).enrich({"detected_at": "2026-09-08T00:00:00Z", "latitude": 20, "longitude": 78})["available"] is False
