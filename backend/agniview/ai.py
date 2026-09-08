from hashlib import sha256
import json
import os

import requests


def event_context(event: dict) -> dict:
    evidence = event.get("classificationEvidence") or {}
    satellite = event.get("satelliteEvidence") or {}
    quality = []
    if event.get("frp") is None:
        quality.append("FRP unavailable")
    if event.get("dnbr") is None:
        quality.append("dNBR unavailable")
    if not satellite.get("available"):
        quality.append(satellite.get("reason") or "Satellite enrichment unavailable")
    nearby = [{"event_id": item.get("id"), "timestamp": item.get("detectedAt"),
               "frp": item.get("frp"), "classification": item.get("classification"),
               "full_classification_skipped": item.get("fullClassificationSkipped")}
              for item in (event.get("nearbyEvents") or [])[:20] if item.get("id") != event.get("id")]
    return {
        "event_id": event.get("id"),
        "coordinates": {"latitude": event.get("latitude"), "longitude": event.get("longitude")},
        "timestamp": event.get("detectedAt"),
        "source": event.get("satellite") or event.get("instrument"),
        "frp": event.get("frp"), "brightness": event.get("brightness"),
        "classification": event.get("classification"),
        "classification_confidence": event.get("confidence"),
        "classification_reasoning": evidence.get("reasoning") or ([event["classificationReason"]] if event.get("classificationReason") else []),
        "classification_source": event.get("classificationSource"),
        "severity": event.get("severity"), "severity_score": event.get("severityScore"),
        "severity_version": event.get("severityVersion"),
        "dnbr": event.get("dnbr"),
        "historical_profile": {
            "profile_id": event.get("profileId"),
            "observation_count": event.get("historicalObservations"),
            "mean_frp": event.get("profileMeanFrp"), "median_frp": event.get("profileMedianFrp"),
            "frp_stddev": event.get("profileFrpStddev"), "max_frp": event.get("profileMaxFrp"),
            "typical_detection_hours": event.get("profileTypicalHours"),
            "historical_pattern_score": event.get("profilePatternScore"),
            "first_seen": event.get("profileFirstSeen"), "last_seen": event.get("profileLastSeen"),
        },
        "osm_context": event.get("osmContext") or {"overlap": bool(event.get("industrialOverlap"))},
        "satellite_context": satellite,
        "nearby_events": nearby,
        "data_quality_notes": quality,
    }


def context_hash(context: dict) -> str:
    return sha256(json.dumps(context, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def question_hash(question: str) -> str:
    return sha256(" ".join(question.casefold().split()).encode()).hexdigest()


class GroundedProvider:
    """Credential-free, deterministic explanation provider for local/demo use."""

    def generate_event_summary(self, context: dict) -> str:
        source = context.get("source") or "an unavailable satellite source"
        label = context.get("classification") or "unknown"
        confidence = context.get("classification_confidence")
        confidence_text = f" with {confidence:.0%} confidence" if isinstance(confidence, (int, float)) else ""
        reason = "; ".join(context.get("classification_reasoning") or []) or "the available evidence is limited"
        dnbr = context.get("dnbr")
        burn_text = "Recent dNBR data is unavailable." if dnbr is None else f"The recorded dNBR is {dnbr:.2f}."
        return f"Detected by {source}; classified as {label}{confidence_text}. {reason}. {burn_text}"

    def answer_event_question(self, question: str, context: dict) -> str:
        summary = self.generate_event_summary(context)
        frp = context.get("frp")
        frp_text = "FRP is unavailable." if frp is None else f"The measured FRP is {frp} MW."
        history = context.get("historical_profile", {}).get("observation_count")
        history_text = "Historical activity is unavailable." if history is None else f"This profile has {history} recorded observations."
        return f"{summary} {frp_text} {history_text}"


class OpenAIProvider:
    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def generate_event_summary(self, context: dict) -> str:
        return self._generate("Summarize this thermal event concisely.", context)

    def answer_event_question(self, question: str, context: dict) -> str:
        return self._generate(question, context)

    def _generate(self, question: str, context: dict) -> str:
        response = requests.post("https://api.openai.com/v1/responses", headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, json={"model": self.model, "store": False, "max_output_tokens": 300, "instructions": "Use only supplied event facts. Distinguish facts from inference and explicitly state unavailable evidence.", "input": f"Event facts: {json.dumps(context, sort_keys=True)}\nQuestion: {question}"}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        texts = [part.get("text", "") for item in payload.get("output", []) if item.get("type") == "message" for part in item.get("content", []) if part.get("type") == "output_text"]
        if not texts:
            raise RuntimeError("LLM returned no text")
        return "\n".join(texts)


def provider_from_env():
    if os.getenv("LLM_PROVIDER") == "openai" and os.getenv("LLM_API_KEY") and os.getenv("LLM_MODEL"):
        return OpenAIProvider(os.environ["LLM_API_KEY"], os.environ["LLM_MODEL"])
    return GroundedProvider()
