"use client";

import { useEffect, useState } from "react";
import MapView from "./MapView";
import TopNavigation from "./components/TopNavigation";
import MetricsBar from "./components/MetricsBar";
import Timeline from "./components/Timeline";
import EventDetailSidebar from "./components/EventDetailSidebar";
import { filterQuery } from "./ui.mjs";

export default function Home() {
  const [collection, setCollection] = useState({ type: "FeatureCollection", features: [] });
  const [selected, setSelected] = useState(null);
  const [filters, setFilters] = useState({ classification: "", severity: "", source: "", region: "", minConfidence: "", start: "" });
  const [status, setStatus] = useState("loading");

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
        fetch(`/api/events/${id}`).then(r => r.ok ? r.json() : Promise.reject()),
        fetch(`/api/events/${id}/ai-summary`).then(r => r.ok ? r.json() : Promise.reject()),
        fetch(`/api/events/${id}/history`).then(r => r.ok ? r.json() : Promise.reject()),
      ]);
      setSelected({ ...detail, aiSummary: summary.summary, history: history.data, conversation: [] });
    } catch {
      setSelected({ error: true, id });
    }
  }

  return (
    <main className="dashboard-layout">
      {/* Top Navigation Row (Grid row 1, col 1-2) */}
      <TopNavigation />

      {/* Metrics Bar Row (Grid row 2, col 1-2) */}
      <MetricsBar />

      {/* Main Map Area (Grid row 3, col 1) */}
      <MapView collection={collection} onSelect={selectEvent} />

      {/* Sidebar Panel (Grid row 3, col 2) - overlay on map or distinct grid cell */}
      {selected ? (
        <EventDetailSidebar event={selected} onClose={() => setSelected(null)} />
      ) : (
        <div style={{
          gridColumn: '2 / 3',
          gridRow: '3 / 4',
          margin: '1rem 1rem 1rem 0',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-tertiary)',
          border: '1px dashed var(--border-subtle)',
          borderRadius: '8px',
          background: 'var(--bg-tertiary)',
          backdropFilter: 'blur(12px)',
          padding: '2rem',
          textAlign: 'center'
        }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: 'rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4"></path><path d="M12 8h.01"></path></svg>
          </div>
          <h3 className="text-sm font-semibold mb-2">No Event Selected</h3>
          <p className="text-xs">Click on any thermal anomaly marker on the map to view detailed satellite evidence, historical profiles, and AI analysis.</p>
        </div>
      )}

      {/* Timeline Row (Grid row 4, col 1-2) */}
      <Timeline />
      
      {/* Loading overlay if backend unavailable */}
      {status === "error" && (
        <div style={{ position: 'fixed', bottom: '80px', left: '50%', transform: 'translateX(-50%)', background: 'var(--accent-critical)', color: 'white', padding: '0.5rem 1rem', borderRadius: '24px', zIndex: 100, fontSize: '0.875rem', fontWeight: 'bold', boxShadow: '0 4px 12px rgba(239, 68, 68, 0.4)' }}>
          Backend unavailable. Loading mock/cached data...
        </div>
      )}
    </main>
  );
}
