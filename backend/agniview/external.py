import requests
import os
from hashlib import sha256
from datetime import datetime, timedelta
from functools import lru_cache


def retry_session(retries=None):
    from requests.adapters import HTTPAdapter
    from urllib3.util import Retry

    retries = int(os.getenv("EXTERNAL_API_RETRIES", "3")) if retries is None else retries
    policy = Retry(total=retries, backoff_factor=float(os.getenv("EXTERNAL_API_BACKOFF_SECONDS", ".5")),
                   status_forcelist=(429, 500, 502, 503, 504), allowed_methods={"GET", "POST"},
                   respect_retry_after_header=True)
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=policy))
    return session


class OverpassClient:
    URL = "https://overpass-api.de/api/interpreter"

    def __init__(self, session=None):
        self.session = session or retry_session()
        self.session.headers.update({"User-Agent": "AgniView/1.0 thermal-intelligence"})

    def industrial_features(self, south, west, north, east):
        bbox = f"{south},{west},{north},{east}"
        query = f'[out:json][timeout:60];(way["landuse"="industrial"]({bbox});way["power"="plant"]({bbox});way["man_made"="works"]({bbox});relation["landuse"="industrial"]({bbox}););out geom;'
        response = self.session.post(self.URL, data={"data": query}, timeout=75)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload.get("elements"), list):
            raise ValueError("invalid Overpass response")
        return payload["elements"]


def normalize_osm_element(element):
    if element.get("type") == "relation":
        # ponytail: outer rings only; add inner-ring assignment if hole fidelity becomes material.
        rings = _relation_rings([member.get("geometry") for member in element.get("members", []) if member.get("role") == "outer"])
        if not rings:
            return None
        geometry = {"type": "MultiPolygon", "coordinates": [[ring] for ring in rings]}
    else:
        ring = _ring(element.get("geometry"))
        if not ring:
            return None
        geometry = {"type": "Polygon", "coordinates": [ring]}
    osm_type, osm_id = element.get("type", "way"), int(element["id"])
    return {"osm_key": f"{osm_type}/{osm_id}", "id": osm_id, "osm_type": osm_type, "name": element.get("tags", {}).get("name"), "tags": element.get("tags", {}), "geometry": geometry}


def _ring(points):
    points = points or []
    try:
        coordinates = [[float(point["lon"]), float(point["lat"])] for point in points]
    except (KeyError, TypeError, ValueError):
        return None
    if len(coordinates) < 3:
        return None
    if coordinates[0] != coordinates[-1]:
        coordinates.append(coordinates[0])
    if len(coordinates) < 4:
        return None
    return coordinates


def _relation_rings(parts):
    lines = []
    for points in parts:
        try:
            line = [[float(point["lon"]), float(point["lat"])] for point in (points or [])]
        except (KeyError, TypeError, ValueError):
            continue
        if len(line) >= 2:
            lines.append(line)
    rings = []
    while lines:
        ring = lines.pop(0)
        while ring[0] != ring[-1]:
            match = next(((index, line) for index, line in enumerate(lines) if ring[-1] in (line[0], line[-1])), None)
            if not match:
                ring = []
                break
            index, line = match
            lines.pop(index)
            if line[-1] == ring[-1]:
                line.reverse()
            ring.extend(line[1:])
        if len(ring) >= 4:
            rings.append(ring)
    return rings


class EarthdataStacClient:
    URL = "https://cmr.earthdata.nasa.gov/stac/LPCLOUD/search"

    def __init__(self, session=None):
        self.session = session or retry_session()

    def search(self, bbox, datetime_range, limit=10):
        payload = {"collections": ["HLSS30_2.0", "HLSL30_2.0"], "bbox": bbox, "datetime": datetime_range, "limit": min(limit, 100)}
        response = self.session.post(self.URL, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        if result.get("type") != "FeatureCollection" or not isinstance(result.get("features"), list):
            raise ValueError("invalid STAC response")
        return result["features"]


def nbr(nir: float, swir: float) -> float | None:
    denominator = nir + swir
    return None if denominator == 0 else (nir - swir) / denominator


def dnbr(pre_nir: float, pre_swir: float, post_nir: float, post_swir: float) -> float | None:
    before, after = nbr(pre_nir, pre_swir), nbr(post_nir, post_swir)
    return None if before is None or after is None else before - after


class RasterioPointReader:
    @lru_cache(maxsize=512)
    def read(self, href, longitude, latitude, size=3):
        import numpy
        import rasterio
        from rasterio.warp import transform
        from rasterio.windows import Window

        username, password = os.getenv("NASA_EARTHDATA_USERNAME"), os.getenv("NASA_EARTHDATA_PASSWORD")
        options = {"GDAL_HTTP_USERPWD": f"{username}:{password}"} if username and password else {}
        with rasterio.Env(**options):
            with rasterio.open(href) as dataset:
                x, y = transform("EPSG:4326", dataset.crs, [longitude], [latitude])
                row, column = dataset.index(x[0], y[0])
                offset = size // 2
                values = dataset.read(1, window=Window(column - offset, row - offset, size, size), masked=True)
                return None if values.count() == 0 else float(numpy.ma.median(values))


class SatelliteEnricher:
    def __init__(self, stac=None, reader=None, cache=None):
        self.stac = stac or EarthdataStacClient()
        self.reader = reader or RasterioPointReader()
        self.cache = cache

    def enrich(self, record):
        detected = datetime.fromisoformat(str(record["detected_at"]).replace("Z", "+00:00"))
        latitude, longitude = record["latitude"], record["longitude"]
        version = os.getenv("SATELLITE_PROCESSING_VERSION", "v1")
        cache_key = sha256(f"{latitude:.5f}|{longitude:.5f}|{detected.date()}|{version}".encode()).hexdigest()
        if self.cache and (cached := self.cache.get_satellite_cache(cache_key)):
            return cached

        def finish(result):
            if self.cache:
                self.cache.save_satellite_cache(cache_key, result, 720 if result.get("available") else 6)
            return result

        bbox = [longitude - .001, latitude - .001, longitude + .001, latitude + .001]
        pre = self._best(self.stac.search(bbox, f"{(detected - timedelta(days=60)).isoformat()}/{(detected - timedelta(days=1)).isoformat()}"))
        post = self._best(self.stac.search(bbox, f"{(detected + timedelta(days=1)).isoformat()}/{(detected + timedelta(days=60)).isoformat()}"))
        if not pre or not post:
            return finish({"available": False, "reason": "Suitable pre/post HLS imagery unavailable"})
        try:
            before = self._observation(pre, longitude, latitude)
            after = self._observation(post, longitude, latitude)
        except Exception as error:
            return finish({"available": False, "reason": f"Imagery read failed: {type(error).__name__}"})
        if not before or not after:
            return finish({"available": False, "reason": "Imagery is cloudy, masked, or incomplete"})
        change = dnbr(before[0], before[1], after[0], after[1])
        return finish({"available": change is not None, "preNbr": nbr(*before[:2]), "postNbr": nbr(*after[:2]),
                       "dnbr": change, "preItem": pre.get("id"), "postItem": post.get("id"),
                       "thumbnailUrl": _thumbnail_href(post),
                       "quality": "clear_at_event" if change is not None else "invalid_reflectance"})

    @staticmethod
    def _best(features):
        return min(features, key=lambda item: item.get("properties", {}).get("eo:cloud_cover") if item.get("properties", {}).get("eo:cloud_cover") is not None else 100) if features else None

    def _observation(self, feature, longitude, latitude):
        product = f'{feature.get("collection", "")} {feature.get("id", "")}'.upper()
        nir_band, swir_band = ("B8A", "B11") if "S30" in product else ("B05", "B06")
        hrefs = [_asset_href(feature, band) for band in (nir_band, swir_band, "FMASK")]
        if not all(hrefs):
            return None
        nir_value = self.reader.read(hrefs[0], longitude, latitude)
        swir_value = self.reader.read(hrefs[1], longitude, latitude)
        quality = self.reader.read(hrefs[2], longitude, latitude, 1)
        if nir_value in (None, -9999) or swir_value in (None, -9999) or quality is None or int(quality) & 0b00011110:
            return None
        return nir_value * .0001, swir_value * .0001, int(quality)


def _asset_href(feature, band):
    for key, asset in feature.get("assets", {}).items():
        href = asset.get("href", "")
        if key.upper() == band or f".{band}." in href.upper():
            return href
    return None


def _thumbnail_href(feature):
    for key, asset in feature.get("assets", {}).items():
        if key.lower() in {"browse", "thumbnail", "overview"} or "thumbnail" in asset.get("roles", []):
            return asset.get("href")
    return None
