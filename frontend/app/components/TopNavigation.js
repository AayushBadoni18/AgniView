"use client";

import { Flame } from "lucide-react";
import { filterQuery } from "../ui.mjs";

export default function TopNavigation({ filters, onChange }) {
  return <header className="top-navigation glass-panel">
    <div className="brand"><Flame aria-hidden="true" size={26} /><div><h1>AgniView</h1><p>Thermal-event intelligence</p></div></div>
    <form className="filters" onSubmit={event => event.preventDefault()}>
      <label>Classification<select value={filters.classification} onChange={event => onChange({ classification: event.target.value })}>
        <option value="">All classifications</option><option value="wildfire">Wildfire</option><option value="industrial">Industrial</option><option value="unknown">Unknown</option>
      </select></label>
      <label>Severity<select value={filters.severity} onChange={event => onChange({ severity: event.target.value })}>
        <option value="">All severities</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
      </select></label>
      <label>Region<input type="search" value={filters.region} placeholder="Region or location" onChange={event => onChange({ region: event.target.value })} /></label>
    </form>
    <nav aria-label="Event exports"><a href={`/api/exports/events.csv?${filterQuery(filters)}`}>CSV</a><a href={`/api/exports/events.pdf?${filterQuery(filters)}`}>PDF</a></nav>
  </header>;
}
