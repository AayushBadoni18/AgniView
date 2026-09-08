import json
import logging

from agniview.observability import log_event


def test_structured_log_has_stable_event_and_correlation(caplog):
    with caplog.at_level(logging.INFO):
        log_event("job_completed", request_id="run-1", job=7)
    assert json.loads(caplog.records[-1].message) == {"event": "job_completed", "request_id": "run-1", "job": 7}
