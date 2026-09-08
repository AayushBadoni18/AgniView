from datetime import datetime, timezone
from hashlib import sha256
from io import StringIO
import csv

from .external import retry_session


def normalize_row(row: dict[str, str]) -> dict:
    try:
        latitude, longitude = float(row["latitude"]), float(row["longitude"])
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid coordinates") from error

    try:
        acquisition_time = str(row["acq_time"]).zfill(4)
        detected_at = datetime.strptime(
            f"{row['acq_date']} {acquisition_time}", "%Y-%m-%d %H%M"
        ).replace(tzinfo=timezone.utc)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid acquisition timestamp") from error

    source = row.get("instrument") or row.get("satellite") or "unknown"
    identity_source = f"{latitude:.5f}|{longitude:.5f}|{detected_at.isoformat()}|{source}"
    return {
        "identity": sha256(identity_source.encode()).hexdigest(),
        "latitude": latitude,
        "longitude": longitude,
        "detected_at": detected_at.isoformat(),
        "satellite": row.get("satellite"),
        "instrument": row.get("instrument"),
        "confidence": row.get("confidence"),
        "frp": _optional_float(row.get("frp")),
        "brightness": _optional_float(row.get("bright_ti4") or row.get("brightness")),
        "scan": _optional_float(row.get("scan")),
        "track": _optional_float(row.get("track")),
        "source": source,
    }


def _optional_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError as error:
        raise ValueError("invalid numeric field") from error


class FirmsClient:
    BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

    def __init__(self, api_key: str, session=None):
        if not api_key:
            raise ValueError("NASA_FIRMS_API_KEY is required")
        self.api_key = api_key
        self.session = session or retry_session()

    def fetch_area(self, area="54,5.5,102,40", source="VIIRS_NOAA20_NRT", days=1):
        if not 1 <= days <= 5:
            raise ValueError("days must be between 1 and 5")
        response = self.session.get(f"{self.BASE_URL}/{self.api_key}/{source}/{area}/{days}", timeout=30)
        response.raise_for_status()
        records, rejected = [], []
        for row in csv.DictReader(StringIO(response.text)):
            try:
                records.append(normalize_row(row))
            except ValueError as error:
                rejected.append({"row": row, "error": str(error)})
        return records, rejected
