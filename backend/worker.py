import os
import time
from uuid import uuid4

from agniview.firms import FirmsClient
from agniview.external import SatelliteEnricher
from agniview.repository import PostgresRepository
from agniview.pipeline import ThermalPipeline
from agniview.observability import configure_logging, log_event


configure_logging()


def ingest_once():
    run_id, repository = str(uuid4()), PostgresRepository()
    job_id = repository.start_job("firms")
    processed, rejected_count = 0, 0
    try:
        records, rejected = FirmsClient(os.environ["NASA_FIRMS_API_KEY"]).fetch_area(
            os.getenv("FIRMS_AREA", "54,5.5,102,40"), os.getenv("FIRMS_SOURCE", "VIIRS_NOAA20_NRT"))
        rejected_count = len(rejected)
        enricher = SatelliteEnricher(cache=repository) if os.getenv("SATELLITE_ENRICHMENT_ENABLED") == "true" else None
        pipeline = ThermalPipeline(repository, enricher=enricher)
        for record in records:
            try:
                event_id = pipeline.process(record, job_id=job_id, request_id=run_id)
                processed += 1
                log_event("firms_record_processed", request_id=run_id, entry_point="scheduler", job=job_id, event_id=event_id)
            except Exception as error:
                rejected_count += 1
                log_event("firms_record_failed", level=40, request_id=run_id, entry_point="scheduler",
                          job=job_id, error_type=type(error).__name__, retry_count=int(os.getenv("EXTERNAL_API_RETRIES", "3")))
        repository.finish_job(job_id, "succeeded", processed, rejected_count)
        log_event("firms_ingestion_completed", request_id=run_id, entry_point="scheduler",
                  job=job_id, records_processed=processed, records_rejected=rejected_count)
    except Exception as error:
        repository.finish_job(job_id, "failed", processed, rejected_count, error)
        log_event("firms_ingestion_failed", level=40, request_id=run_id, entry_point="scheduler",
                  job=job_id, error_type=type(error).__name__, retry_count=int(os.getenv("EXTERNAL_API_RETRIES", "3")))
        raise


if __name__ == "__main__":
    while True:
        try:
            ingest_once()
        except Exception:
            pass
        time.sleep(int(os.getenv("FIRMS_INTERVAL_SECONDS", "3600")))
