"use client";

import { useEffect, useState } from "react";
import { savingsLabel } from "../ui.mjs";

export default function MetricsBar({ collection, status }) {
  const [metrics, setMetrics] = useState(null);
  useEffect(() => {
    const request = new AbortController();
    fetch("/api/metrics", { signal: request.signal }).then(response => {
      if (!response.ok) throw new Error("Metrics unavailable");
      return response.json();
    }).then(data => { if (!request.signal.aborted) setMetrics(data); }).catch(() => {});
    return () => request.abort();
  }, []);
  return <section className="metrics-bar" aria-label="Event counts and processing metrics">
    <p role="status">{status === "loading" ? "Loading events…" : status === "error" ? "Events unavailable" : `${collection.features.length} events`}</p>
    <div className="classification-counts">{["industrial", "wildfire", "unknown"].map(label => <span key={label}>{label}: {status === "ready" ? collection.features.filter(event => event.properties.classification === label).length : "—"}</span>)}</div>
    <p>{metrics ? savingsLabel(metrics) : "Processing metrics unavailable"}</p>
  </section>;
}
