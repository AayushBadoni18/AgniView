import json
import logging
import os


def configure_logging():
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")


def log_event(event, *, level=logging.INFO, **fields):
    logging.log(level, json.dumps({"event": event, **fields}, default=str, separators=(",", ":")))
