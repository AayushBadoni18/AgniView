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

    pre, post = item("pre", ("B8A", "B12", "Fmask")), item("post", ("B8A", "B12", "Fmask"))
    class Stac:
        calls = 0
        def search(self, *_args, **_kwargs):
            self.calls += 1
            return [pre if self.calls == 1 else post]
    class Reader:
        def read_observation(self, hrefs, *_coordinates):
            prefix = hrefs[0].split(".")[0]
            assert hrefs == (f"{prefix}.B8A.tif", f"{prefix}.B12.tif", f"{prefix}.Fmask.tif")
            return {"nir": .8 if prefix == "pre" else .4, "swir": .2 if prefix == "pre" else .6,
                    "validPixels": 9, "totalPixels": 9}

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
    assert result["preObservation"]["bands"] == ["B8A", "B12", "FMASK"]
    assert result["processingVersion"] == "v2-swir2-joint-mask"
    assert enricher.enrich({"detected_at": "2026-09-08T00:00:00Z", "latitude": 20, "longitude": 78}) == result
    assert stac.calls == 2


def test_hls_enrichment_fails_gracefully_when_imagery_is_missing():
    class Stac:
        def search(self, *_args, **_kwargs): return []
    assert SatelliteEnricher(Stac()).enrich({"detected_at": "2026-09-08T00:00:00Z", "latitude": 20, "longitude": 78})["available"] is False


def test_l30_uses_swir2_and_rejects_unknown_product():
    class Reader:
        def read_observation(self, hrefs, *_args):
            assert hrefs == ("B05", "B07", "FMASK")
            return {"nir": .8, "swir": .2, "validPixels": 9, "totalPixels": 9}
    feature = {"collection": "HLSL30_2.0", "assets": {b: {"href": b} for b in ["B05", "B06", "B07", "FMASK"]}}
    enricher = SatelliteEnricher(reader=Reader())
    assert enricher._observation(feature, 78, 20)["bands"] == ["B05", "B07", "FMASK"]
    feature["collection"] = "unknown"
    assert enricher._observation(feature, 78, 20) is None
