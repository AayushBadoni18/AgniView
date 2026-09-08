import csv
from io import StringIO
import math
import os
from datetime import datetime
from time import perf_counter
from uuid import uuid4

from flask import Flask, Response, g, jsonify, request
from werkzeug.exceptions import HTTPException

from .ai import context_hash, event_context, provider_from_env, question_hash
from .repository import DemoRepository, PostgresRepository
from .pdf import simple_pdf
from .observability import configure_logging, log_event


def create_app(repository=None, ai_provider=None):
    configure_logging()
    app = Flask(__name__)
    repo = repository or (DemoRepository() if os.getenv("DEMO_MODE") == "true" else PostgresRepository())
    provider = ai_provider or provider_from_env()
    context_version = os.getenv("AI_CONTEXT_VERSION", "v1")

    @app.before_request
    def begin_request():
        supplied = request.headers.get("X-Request-ID", "")
        g.request_id = supplied[:128] if supplied else str(uuid4())
        g.request_started = perf_counter()

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["X-Request-ID"] = g.get("request_id", "")
        log_event("http_request", request_id=g.get("request_id"), method=request.method,
                  path=request.path, status=response.status_code,
                  duration_ms=round((perf_counter() - g.get("request_started", perf_counter())) * 1000, 2))
        return response

    @app.errorhandler(Exception)
    def unexpected_error(error):
        if isinstance(error, HTTPException):
            return error
        log_event("http_request_failed", level=40, request_id=g.get("request_id"), error_type=type(error).__name__)
        return _error("INTERNAL_ERROR", "The request could not be completed", 500)

    @app.errorhandler(ValueError)
    def validation_error(error):
        return _error("VALIDATION_ERROR", str(error), 422)

    @app.get("/health")
    @app.get("/api/health")
    def health():
        healthy = getattr(repo, "health", lambda: True)()
        return jsonify({"status": "ok" if healthy else "degraded", "service": "backend", "database": "ok" if healthy else "unavailable"}), 200 if healthy else 503

    @app.get("/api/events")
    def events():
        try:
            page = _bounded_int("page", 1, 1, 100000)
            page_size = _bounded_int("pageSize", 50, 1, 200)
            filters = _filters()
        except ValueError as error:
            return _error("VALIDATION_ERROR", str(error), 422)
        rows, total = repo.list_events(page=page, page_size=page_size, **filters)
        return jsonify({"data": rows, "pagination": {"page": page, "pageSize": page_size, "totalItems": total, "totalPages": math.ceil(total / page_size)}})

    @app.get("/api/events/map")
    def map_events():
        try:
            bbox = _bbox(request.args.get("bbox"))
            filters = _filters()
        except ValueError as error:
            return _error("VALIDATION_ERROR", str(error), 422)
        rows = repo.map_events(bbox=bbox, **filters)
        features = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [event["longitude"], event["latitude"]]}, "properties": event} for event in rows]
        return jsonify({"type": "FeatureCollection", "features": features})

    @app.get("/api/events/<event_id>")
    def event_detail(event_id):
        event = repo.get_event(event_id)
        return jsonify(event) if event else _error("NOT_FOUND", "Event not found", 404)

    @app.get("/api/events/<event_id>/history")
    def event_history(event_id):
        return jsonify({"data": repo.event_history(event_id)})

    @app.get("/api/events/<event_id>/ai-summary")
    def ai_summary(event_id):
        event = repo.get_event(event_id)
        if not event:
            return _error("NOT_FOUND", "Event not found", 404)
        context = _trusted_event_context(repo, event)
        hash_value = context_hash(context)
        cache_valid = (event.get("aiSummary") and event.get("aiContextHash") == hash_value
                       and event.get("aiContextVersion") == context_version)
        summary = event["aiSummary"] if cache_valid else provider.generate_event_summary(context)
        if cache_valid:
            repo.record_ai_cache_hit(event_id)
        else:
            repo.save_ai_summary(event_id, summary, hash_value, context_version)
        return jsonify({"eventId": event_id, "summary": summary, "contextVersion": context_version})

    @app.post("/api/events/<event_id>/ask")
    def ask(event_id):
        payload = request.get_json(silent=True) or {}
        question = payload.get("question")
        if not isinstance(question, str) or not question.strip() or len(question) > 500:
            return _error("VALIDATION_ERROR", "question must contain 1–500 characters", 422)
        event = repo.get_event(event_id)
        if not event:
            return _error("NOT_FOUND", "Event not found", 404)
        context = _trusted_event_context(repo, event)
        question = question.strip()
        event_hash, prompt_hash = context_hash(context), question_hash(question)
        answer = repo.get_ai_answer(event_id, prompt_hash, event_hash, context_version)
        cached = answer is not None
        if not cached:
            answer = provider.answer_event_question(question, context)
            repo.save_ai_answer(event_id, question, prompt_hash, event_hash, context_version, answer)
        return jsonify({"event_id": event_id, "question": question, "answer": answer,
                        "classification": event["classification"], "confidence": event["confidence"],
                        "context_version": context_version, "generated_at": datetime.now().astimezone().isoformat(),
                        "cached": cached})

    @app.get("/api/metrics")
    def metrics():
        return jsonify(repo.metrics())

    @app.get("/api/alerts")
    def alerts():
        status = request.args.get("status")
        if status and status not in {"open", "acknowledged", "resolved"}:
            raise ValueError("status must be one of acknowledged, open, resolved")
        return jsonify({"data": repo.list_alerts(status)})

    @app.patch("/api/alerts/<alert_id>")
    def update_alert(alert_id):
        status = (request.get_json(silent=True) or {}).get("status")
        if status not in {"acknowledged", "resolved"}:
            raise ValueError("status must be acknowledged or resolved")
        alert = repo.set_alert_status(alert_id, status)
        return jsonify(alert) if alert else _error("NOT_FOUND", "Alert not found", 404)

    @app.get("/api/exports/events.csv")
    def export_events():
        rows, _ = repo.list_events(page=1, page_size=200, **_filters())
        output = StringIO()
        fields = ["id", "detectedAt", "latitude", "longitude", "classification", "confidence", "severity", "frp", "satellite"]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
        return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=agniview-events.csv"})

    @app.get("/api/exports/events.pdf")
    def export_pdf():
        rows, _ = repo.list_events(page=1, page_size=100, **_filters())
        lines = ["AgniView Thermal Event Report"] + [f'{row["id"]} | {row["classification"]} | {row["severity"]} | FRP {row.get("frp", "unavailable")}' for row in rows]
        return Response(simple_pdf(lines), mimetype="application/pdf", headers={"Content-Disposition": "attachment; filename=agniview-events.pdf"})

    return app


def _filters():
    filters = {name: request.args.get(name) for name in ("classification", "severity", "source", "region")}
    for name, allowed in (("classification", {"wildfire", "industrial", "unknown"}),
                          ("severity", {"low", "medium", "high"})):
        if filters[name] and filters[name] not in allowed:
            raise ValueError(f"{name} must be one of {', '.join(sorted(allowed))}")
    if filters["region"]:
        filters["region"] = filters["region"].strip()
        if len(filters["region"]) > 100:
            raise ValueError("region must contain at most 100 characters")
    filters["start"] = _optional_datetime("start")
    filters["end"] = _optional_datetime("end")
    if filters["start"] and filters["end"] and filters["start"] >= filters["end"]:
        raise ValueError("start must be earlier than end")
    raw_confidence = request.args.get("minConfidence")
    if raw_confidence is None:
        filters["min_confidence"] = None
    else:
        try:
            filters["min_confidence"] = float(raw_confidence)
        except ValueError as error:
            raise ValueError("minConfidence must be between 0 and 1") from error
        if not 0 <= filters["min_confidence"] <= 1:
            raise ValueError("minConfidence must be between 0 and 1")
    return filters


def _trusted_event_context(repository, event):
    enriched = {**event, "nearbyEvents": repository.event_history(event["id"])}
    return event_context(enriched)


def _optional_datetime(name):
    value = request.args.get(name)
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO-8601 timestamp") from error


def _bbox(value):
    if value is None:
        return None
    try:
        parts = tuple(float(item) for item in value.split(","))
    except ValueError as error:
        raise ValueError("bbox must be minLon,minLat,maxLon,maxLat") from error
    if len(parts) != 4 or parts[0] >= parts[2] or parts[1] >= parts[3] or not (-180 <= parts[0] <= 180 and -180 <= parts[2] <= 180 and -90 <= parts[1] <= 90 and -90 <= parts[3] <= 90):
        raise ValueError("bbox must be minLon,minLat,maxLon,maxLat")
    return parts


def _bounded_int(name, default, minimum, maximum):
    try:
        value = int(request.args.get(name, default))
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _error(code, message, status):
    return jsonify({"error": {"code": code, "message": message}}), status
