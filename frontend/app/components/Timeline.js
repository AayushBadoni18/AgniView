"use client";

import { useState } from "react";

export default function Timeline({ filters, onChange }) {
  const [anchor, setAnchor] = useState(null);
  const [hours, setHours] = useState(72);
  function apply(hours, end = anchor) {
    const start = end - 72 * 60 * 60 * 1000;
    setHours(hours);
    onChange({ start: new Date(start).toISOString(), end: new Date(start + hours * 60 * 60 * 1000).toISOString() });
  }
  function explore() {
    const end = Date.now();
    setAnchor(end);
    apply(72, end);
  }
  return <section className="temporal-controls glass-panel" aria-label="Temporal exploration">
    <button onClick={explore}>Explore previous 72 hours</button>
    <label>Hours through previous 72 hours<input type="range" min="0" max="72" step="1" value={hours} disabled={!anchor} onChange={event => apply(Number(event.target.value))} /></label>
    <p>{filters.start ? `${new Date(filters.start).toLocaleString()} — ${new Date(filters.end).toLocaleString()} (end exclusive)` : "All stored events"}</p>
    <button onClick={() => { setAnchor(null); setHours(72); onChange({ start: "", end: "" }); }}>Reset time filter</button>
  </section>;
}
