def alert_for(event: dict) -> dict | None:
    if event.get("classification") != "wildfire" and not event.get("isAnomaly"):
        return None
    if event.get("confidence", 0) < 0.7:
        return None
    key = f'{event["id"]}:{event.get("classification")}:{event.get("severity")}'
    return {"deduplicationKey": key, "eventId": event["id"], "status": "open", "severity": event.get("severity", "unknown"), "reason": "New wildfire or anomalous thermal event"}
