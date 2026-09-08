"use client";

import { useEffect, useState } from "react";
import MapView from "./MapView";
import { filterQuery, savingsLabel } from "./ui.mjs";


export default function Home() {
  const [collection, setCollection] = useState({ type: "FeatureCollection", features: [] });
  const [selected, setSelected] = useState(null);
  const [filters, setFilters] = useState({ classification: "", severity: "", source: "", region: "", minConfidence: "", start: "" });
  const [status, setStatus] = useState("loading");
  const [metrics, setMetrics] = useState(null);
  const exportQuery = filterQuery(filters);

  useEffect(() => { fetch("/api/metrics").then(checkedJson).then(setMetrics).catch(() => {}); }, []);

  useEffect(() => {
    const query = filterQuery(filters);
    setStatus("loading");
    fetch(`/api/events/map?${query}`)
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((data) => { setCollection(data); setStatus("ready"); })
      .catch(() => setStatus("error"));
  }, [filters]);

  async function selectEvent(id) {
    setSelected({ loading: true, id });
    try {
      const [detail, summary, history] = await Promise.all([
        fetch(`/api/events/${id}`).then(checkedJson),
        fetch(`/api/events/${id}/ai-summary`).then(checkedJson),
        fetch(`/api/events/${id}/history`).then(checkedJson),
      ]);
      setSelected({ ...detail, aiSummary: summary.summary, history: history.data, conversation: [] });
    } catch {
      setSelected({ error: true, id });
    }
  }

  return <main className="app-shell">
    <header>
      <div><p className="eyebrow">THERMAL INTELLIGENCE</p><h1>AgniView</h1><p className="savings">{metrics ? savingsLabel(metrics) : "Loading compute savings…"}</p></div>
      <nav aria-label="Exports"><a className="export" href={`/api/exports/events.csv?${exportQuery}`}>CSV</a><a className="export" href={`/api/exports/events.pdf?${exportQuery}`}>PDF</a></nav>
    </header>

    <section className="filters" aria-label="Event filters">
      <label>Classification<select value={filters.classification} onChange={(event) => setFilters({ ...filters, classification: event.target.value })}>
        <option value="">All</option><option value="wildfire">Wildfire</option><option value="industrial">Industrial</option><option value="unknown">Unknown</option>
      </select></label>
      <label>Severity<select value={filters.severity} onChange={(event) => setFilters({ ...filters, severity: event.target.value })}>
        <option value="">All</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
      </select></label>
      <label>Sensor<select value={filters.source} onChange={(event) => setFilters({ ...filters, source: event.target.value })}>
        <option value="">All</option><option value="VIIRS">VIIRS</option><option value="MODIS">MODIS</option>
      </select></label>
      <label>Region<input type="search" maxLength="100" placeholder="Industrial area" value={filters.region} onChange={(event) => setFilters({ ...filters, region: event.target.value })} /></label>
      <label>Confidence<select value={filters.minConfidence} onChange={(event) => setFilters({ ...filters, minConfidence: event.target.value })}>
        <option value="">Any</option><option value="0.7">70%+</option><option value="0.9">90%+</option>
      </select></label>
      <label>Detected after<input type="date" value={filters.start} onChange={(event) => setFilters({ ...filters, start: event.target.value })} /></label>
      <span role="status">{status === "loading" ? "Loading detections…" : status === "error" ? "Backend unavailable" : `${collection.features.length} events`}</span>
    </section>

    <section className="workspace">
      <MapView collection={collection} onSelect={selectEvent} />
      <EventDetail key={selected?.id || "empty"} event={selected} onClose={() => setSelected(null)} />
    </section>
  </main>;
}


function EventDetail({ event, onClose }) {
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [conversation, setConversation] = useState([]);
  if (!event) return <aside className="detail empty"><p>Select a thermal marker to inspect its evidence.</p></aside>;
  if (event.loading) return <aside className="detail" aria-busy="true">Loading event…</aside>;
  if (event.error) return <aside className="detail"><p>Event details could not be loaded.</p><button onClick={onClose}>Close</button></aside>;

  async function ask(eventSubmit) {
    eventSubmit.preventDefault();
    if (!question.trim()) return;
    setAsking(true);
    try {
      const response = await fetch(`/api/events/${event.id}/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) });
      const answer = await checkedJson(response);
      setConversation((items) => [...items, { question, answer: answer.answer || answer.error?.message || "The question could not be answered." }]);
      setQuestion("");
    } catch {
      setConversation((items) => [...items, { question, answer: "The AI service is currently unavailable." }]);
    } finally {
      setAsking(false);
    }
  }

  return <aside className="detail" aria-label="Selected event details">
    <button className="close" aria-label="Close event details" onClick={onClose}>×</button>
    <p className="eyebrow">EVENT {event.id.slice(0, 8)}</p>
    <div className="title-row"><h2>{label(event.classification)}</h2><strong>{Math.round(event.confidence * 100)}%</strong></div>
    <p className={`badge ${event.severity}`}>Severity: {label(event.severity)}</p>
    {event.isAnomaly && <p className="badge high">Anomaly forced full re-evaluation</p>}
    <dl>
      <div><dt>FRP</dt><dd>{event.frp == null ? "Unavailable" : `${event.frp} MW`}</dd></div>
      <div><dt>Coordinates</dt><dd>{event.latitude.toFixed(4)}, {event.longitude.toFixed(4)}</dd></div>
      <div><dt>Satellite</dt><dd>{event.satellite || event.instrument || "Unavailable"}</dd></div>
      <div><dt>Detected</dt><dd>{new Date(event.detectedAt).toLocaleString()}</dd></div>
      <div><dt>Historical hits</dt><dd>{event.historicalObservations}</dd></div>
      <div><dt>dNBR</dt><dd>{event.dnbr == null ? "Unavailable" : event.dnbr}</dd></div>
      <div><dt>Pre/post NBR</dt><dd>{event.satelliteEvidence?.preNbr == null ? "Unavailable" : `${event.satelliteEvidence.preNbr.toFixed(2)} / ${event.satelliteEvidence.postNbr.toFixed(2)}`}</dd></div>
      <div><dt>Provenance</dt><dd>{event.classificationSource.replaceAll("_", " ")}</dd></div>
    </dl>
    <section><h3>Why this classification?</h3><p>{event.classificationReason}</p>
      {event.classificationEvidence?.frp_deviation != null && <p>FRP deviation: {event.classificationEvidence.frp_deviation.toFixed(1)}σ from profile baseline.</p>}
    </section>
    <section><h3>Industrial context</h3><p>{event.osmContext?.overlap ? `Inside ${event.osmContext.zoneName || "an industrial zone"}.` : event.osmContext?.nearIndustrialZone ? `${Math.round(event.osmContext.distanceMeters)} m from ${event.osmContext.zoneName || "an industrial zone"}.` : "No nearby industrial zone recorded."}</p></section>
    <section><h3>Historical activity</h3><p>{event.historicalObservations} observations in this thermal profile.</p>
      {event.profileMeanFrp != null && <p>Typical FRP: {event.profileMeanFrp.toFixed(1)} MW mean; {event.profileMaxFrp?.toFixed(1) ?? "unavailable"} MW maximum.</p>}
      <ul className="timeline">{(event.history || []).slice(0, 5).map((item) => <li key={item.id}><time>{new Date(item.detectedAt).toLocaleDateString()}</time><span>{label(item.classification)} · {item.frp ?? "—"} MW · {item.fullClassificationSkipped ? "reused" : "full analysis"}</span></li>)}</ul>
    </section>
    <section><h3>Satellite evidence</h3><p>{event.satelliteEvidence?.available ? `Pre/post NBR ${event.satelliteEvidence.preNbr?.toFixed(2)} / ${event.satelliteEvidence.postNbr?.toFixed(2)}; dNBR ${event.satelliteEvidence.dnbr?.toFixed(2)}.` : event.satelliteEvidence?.reason || "Satellite enrichment unavailable."}</p>
      {event.satelliteEvidence?.thumbnailUrl && <img className="satellite-thumbnail" src={event.satelliteEvidence.thumbnailUrl} alt="Satellite view near this thermal event" />}
    </section>
    <section className="ai"><h3>Point AI</h3><p>{event.aiSummary}</p>
      {conversation.map((item, index) => <div className="answer" key={index}><strong>{item.question}</strong><p>{item.answer}</p></div>)}
      <form onSubmit={ask}><label htmlFor="question">Ask AI about this point…</label><div><input id="question" maxLength="500" value={question} onChange={(input) => setQuestion(input.target.value)} /><button disabled={asking}>{asking ? "…" : "Ask"}</button></div></form>
    </section>
  </aside>;
}

function label(value) { return value ? value[0].toUpperCase() + value.slice(1) : "Unknown"; }
async function checkedJson(response) { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); }
