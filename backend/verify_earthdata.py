"""One bounded authenticated HLS check; emits no credentials or asset URLs.

Run explicitly through the Compose worker environment. This audit point is not
a live detection and never enters ingestion, classification or alert delivery.
"""
import json
import logging
import os
import re

from agniview.external import EarthdataStacClient, SatelliteEnricher, dnbr, nbr, retry_session


def main():
    logging.getLogger("rasterio").disabled = True
    os.environ.update(GDAL_HTTP_TIMEOUT="45", GDAL_HTTP_CONNECTTIMEOUT="15",
                      GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif")
    if not all(os.getenv(key) for key in ("NASA_EARTHDATA_USERNAME", "NASA_EARTHDATA_PASSWORD")):
        print(json.dumps({"available": False, "reason": "Earthdata credentials unavailable"}))
        return 1
    stac = EarthdataStacClient(session=retry_session(0))
    enricher = SatelliteEnricher(stac=stac)
    observations = []
    stage = "metadata"
    try:
        for period in ("2026-05-01T00:00:00Z/2026-06-30T00:00:00Z",
                       "2026-07-02T00:00:00Z/2026-08-30T00:00:00Z"):
            stage = "metadata"
            item = enricher._best(stac.search([77.999, 19.999, 78.001, 20.001], period))
            if not item:
                print(json.dumps({"available": False, "reason": "Pre/post metadata unavailable"}))
                return 1
            stage = "authenticated_cog"
            observation = enricher._observation(item, 78, 20)
            if not observation:
                print(json.dumps({"available": False, "reason": "No jointly valid imagery pixels"}))
                return 1
            observations.append(observation)
        before, after = observations
        change = dnbr(before["nir"], before["swir"], after["nir"], after["swir"])
        assert change is not None
        print(json.dumps({"available": True, "auditPoint": [78, 20],
                          "preNbr": nbr(before["nir"], before["swir"]),
                          "postNbr": nbr(after["nir"], after["swir"]), "dnbr": change,
                          "observations": observations}))
        return 0
    except Exception as error:
        status = re.search(r"(?:HTTP response code:|HTTP status(?: code)?[: ]+)\s*(\d{3})", str(error))
        response = getattr(error, "response", None)
        http_status = response.status_code if response is not None else int(status[1]) if status else None
        safe_reasons = {"Unsupported Earthdata asset host", "Earthdata credentials unavailable",
                        "Earthdata login did not return a data response", "Earthdata redirect limit exceeded",
                        "Reflectance and quality grids must match"}
        print(json.dumps({"available": False, "stage": stage, "errorType": type(error).__name__,
                          "httpStatus": http_status,
                          "reason": str(error) if str(error) in safe_reasons else "Provider read failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
