import os
import time
from uuid import uuid4

from agniview.external import OverpassClient, normalize_osm_element
from agniview.repository import PostgresRepository
from agniview.observability import configure_logging, log_event


configure_logging()


def refresh_once():
    bounds = [float(value) for value in os.getenv("OSM_BBOX", "5.5,54,40,102").split(",")]
    if len(bounds) != 4:
        raise ValueError("OSM_BBOX must be south,west,north,east")
    repository, accepted, rejected, run_id = PostgresRepository(), 0, 0, str(uuid4())
    job_id = repository.start_job("osm")
    try:
        for element in OverpassClient().industrial_features(*bounds):
            feature = normalize_osm_element(element)
            if feature:
                repository.upsert_osm_zone(feature)
                accepted += 1
            else:
                rejected += 1
        repository.finish_job(job_id, "succeeded", accepted, rejected)
        log_event("osm_refresh_completed", request_id=run_id, entry_point="scheduler", job=job_id,
                  records_processed=accepted, records_rejected=rejected)
    except Exception as error:
        repository.finish_job(job_id, "failed", accepted, rejected, error)
        log_event("osm_refresh_failed", level=40, request_id=run_id, entry_point="scheduler",
                  job=job_id, error_type=type(error).__name__, retry_count=int(os.getenv("EXTERNAL_API_RETRIES", "3")))
        raise


if __name__ == "__main__":
    while True:
        try:
            refresh_once()
        except Exception:
            pass
        time.sleep(int(os.getenv("OSM_REFRESH_INTERVAL_SECONDS", "604800")))
