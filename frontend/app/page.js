"use client";

import { useEffect, useRef, useState } from "react";
import MapView from "./MapView";
import TopNavigation from "./components/TopNavigation";
import MetricsBar from "./components/MetricsBar";
import Timeline from "./components/Timeline";
import EventDetailSidebar from "./components/EventDetailSidebar";
import { filterQuery } from "./ui.mjs";

const emptyCollection = { type: "FeatureCollection", features: [] };
async function json(url, signal) {
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error("Request failed");
  return response.json();
}

export default function Home() {
  const [collection, setCollection] = useState(emptyCollection);
  const [selected, setSelected] = useState(null);
  const [filters, setFilters] = useState({ classification: "", severity: "", source: "", region: "", minConfidence: "", start: "", end: "" });
  const [status, setStatus] = useState("loading");
  const [retry, setRetry] = useState(0);
  const selectionRequest = useRef(null);

  useEffect(() => {
    const request = new AbortController();
    setCollection(emptyCollection);
    setStatus("loading");
    json(`/api/events/map?${filterQuery(filters)}`, request.signal)
      .then(data => { if (!request.signal.aborted) { setCollection(data); setStatus("ready"); } })
      .catch(() => { if (!request.signal.aborted) setStatus("error"); });
    return () => request.abort();
  }, [filters, retry]);
  useEffect(() => () => selectionRequest.current?.abort(), []);

  function closeEvent() {
    selectionRequest.current?.abort();
    setSelected(null);
  }
  function updateFilters(changes) {
    closeEvent();
    setFilters(previous => ({ ...previous, ...changes }));
  }
  async function selectEvent(id) {
    selectionRequest.current?.abort();
    const request = new AbortController();
    selectionRequest.current = request;
    setSelected({ loading: true, id });
    try {
      const [detail, summary, history] = await Promise.all([
        json(`/api/events/${id}`, request.signal),
        json(`/api/events/${id}/ai-summary`, request.signal),
        json(`/api/events/${id}/history`, request.signal),
      ]);
      const summaryId = summary.eventId ?? summary.event_id;
      if (detail.id !== id || (summaryId && summaryId !== id)) throw new Error("Event context mismatch");
      if (!request.signal.aborted) setSelected({ ...detail, aiSummary: summary.summary, history: history.data });
    } catch {
      if (!request.signal.aborted) setSelected({ error: true, id });
    }
  }

  return <main className="dashboard-layout">
    <TopNavigation filters={filters} onChange={updateFilters} />
    <MetricsBar collection={collection} status={status} />
    <MapView collection={collection} onSelect={selectEvent} />
    {selected ? <EventDetailSidebar key={selected.id} event={selected} onClose={closeEvent} onRetry={() => selectEvent(selected.id)} /> :
      <aside className="glass-panel event-detail empty-detail"><h2>No event selected</h2><p>Select a map marker or an event in the accessible list to inspect its evidence.</p></aside>}
    <Timeline filters={filters} onChange={updateFilters} />
    {status === "error" && <div className="request-error" role="alert">Events unavailable. <button onClick={() => setRetry(value => value + 1)}>Retry events</button></div>}
  </main>;
}
