"use client";

import { useEffect, useRef, useState } from "react";

const value = (number, suffix = "") => number == null ? "Unavailable" : `${number}${suffix}`;
const time = input => input ? new Date(input).toLocaleString() : "Unavailable";

export default function EventDetailSidebar({ event, onClose, onRetry }) {
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [conversation, setConversation] = useState([]);
  const request = useRef(null);
  useEffect(() => () => request.current?.abort(), []);

  async function ask(e) {
    e.preventDefault();
    if (!question.trim() || asking) return;
    const controller = new AbortController();
    request.current = controller;
    const asked = question.trim();
    setAsking(true);
    try {
      const response = await fetch(`/api/events/${event.id}/ask`, { method: "POST", signal: controller.signal,
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: asked }) });
      if (!response.ok) throw new Error("AI unavailable");
      const answer = await response.json();
      if (answer.event_id !== event.id || typeof answer.answer !== "string") throw new Error("Wrong event context");
      if (!controller.signal.aborted) {
        setConversation(items => [...items, { question: asked, answer: answer.answer }]);
        setQuestion("");
      }
    } catch {
      if (!controller.signal.aborted) setConversation(items => [...items, { question: asked, answer: "AI service unavailable. Please retry." }]);
    } finally {
      if (!controller.signal.aborted) setAsking(false);
    }
  }

  const satellite = event.satelliteEvidence || {};
  const osm = event.osmContext || {};
  const reasons = event.classificationEvidence?.reasoning || (event.classificationReason ? [event.classificationReason] : []);
  return <aside className="glass-panel event-detail" aria-label="Selected event details" aria-busy={Boolean(event.loading)}>
    <button className="close-detail" onClick={onClose} aria-label="Close event details">×</button>
    {event.loading ? <p>Loading intelligence…</p> : event.error ? <div role="alert"><p>Event details unavailable.</p><button onClick={onRetry}>Retry event</button></div> : <>
      <header><p className="eyebrow">Event evidence</p><h2 className="classification-heading">{event.classification}</h2><p className="event-id">{event.id}</p></header>
      <p>{value(event.latitude, "°")}, {value(event.longitude, "°")}</p>
      <p>{time(event.detectedAt)}</p>
      {event.isAnomaly && <p className="anomaly">Anomaly forced full re-evaluation</p>}
      <section><h3>Detection metrics</h3><dl>
        <dt>FRP</dt><dd>{value(event.frp, " MW")}</dd>
        <dt>Brightness</dt><dd>{value(event.brightness, " K")}</dd>
        <dt>Satellite / source</dt><dd>{event.satellite || "Unavailable"} / {event.instrument || event.source || "Unavailable"}</dd>
        <dt>Confidence</dt><dd>{event.confidence == null ? "Unavailable" : `${Math.round(event.confidence * 100)}%`}</dd>
        <dt>Severity</dt><dd>{event.severity || "Unavailable"} ({value(event.severityScore)})</dd>
      </dl></section>
      <section><h3>Classification evidence</h3>{reasons.length ? <ul>{reasons.map((reason, index) => <li key={index}>{reason}</li>)}</ul> : <p>Reasoning unavailable.</p>}
        <p>Provenance: {event.classificationSource || "Unavailable"}</p><p>{event.fullClassificationSkipped ? "Classification reused from a historical profile." : "Full classification evaluated."}</p>
      </section>
      <section><h3>Industrial context</h3><p>{osm.zoneName || "Zone name unavailable"}</p><p>Industrial overlap: {osm.overlap == null ? "Unavailable" : osm.overlap ? "Yes" : "No"}</p>
        <p>Distance: {value(osm.distanceMeters, " m")}</p>
        {osm.tags && <dl>{Object.entries(osm.tags).map(([key, text]) => <div key={key}><dt>{key}</dt><dd>{String(text)}</dd></div>)}</dl>}
      </section>
      <section><h3>Historical activity</h3><p>Stored observations: {value(event.historicalObservations)}</p><p>Mean / median FRP: {value(event.profileMeanFrp)} / {value(event.profileMedianFrp)} MW</p>
        <ol className="timeline">{event.history?.map(item => <li key={item.id}>{time(item.detectedAt)} · {item.classification} · {value(item.frp, " MW")} · {item.fullClassificationSkipped ? "reused" : "full evaluation"}</li>)}</ol>
        {!event.history?.length && <p>Historical activity unavailable.</p>}
      </section>
      <section><h3>Satellite evidence</h3>{!satellite.available && <p>{satellite.reason || "Suitable imagery unavailable"}</p>}
        <dl><dt>Pre NBR</dt><dd>{value(satellite.preNbr)}</dd><dt>Post NBR</dt><dd>{value(satellite.postNbr)}</dd><dt>dNBR</dt><dd>{value(satellite.dnbr ?? event.dnbr)}</dd></dl>
        {[satellite.preObservation, satellite.postObservation].filter(Boolean).map((item, index) => <p key={index}>{item.itemId || "Item unavailable"} · {time(item.acquiredAt)} · bands {item.bands?.join(" / ") || "Unavailable"} · valid pixels {value(item.validPixels)}/{value(item.totalPixels)}</p>)}
        <p>Processing: {satellite.processingVersion || "Unavailable"}</p>
        {satellite.thumbnailUrl && /^https:\/\//.test(satellite.thumbnailUrl) ? <a href={satellite.thumbnailUrl} target="_blank" rel="noopener noreferrer">Open provider browse image</a> : <p>Imagery thumbnail unavailable.</p>}
      </section>
      <section><h3>Ask Point AI</h3><p>{event.aiSummary || "Summary unavailable."}</p><div aria-live="polite">{conversation.map((message, index) => <div className="answer" key={index}><strong>{message.question}</strong><p>{message.answer}</p></div>)}</div>
        <form onSubmit={ask} className="ask-form"><label>Ask AI about this point…<input value={question} maxLength={500} required onChange={e => setQuestion(e.target.value)} /></label><button disabled={asking}>{asking ? "Asking…" : "Ask"}</button></form>
      </section>
      <p className="text-muted">Evidence supports analyst triage. Industrial classifications do not rule out a fire; missing or stale evidence limits certainty.</p>
    </>}
  </aside>;
}
