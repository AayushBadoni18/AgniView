"use client";

import { MapPin, Calendar, Factory, Flame, AlertCircle } from "lucide-react";

export default function MetricsBar() {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.5rem 1.5rem',
      gridColumn: '1 / 3',
      gridRow: '2 / 3',
      background: 'var(--bg-secondary)',
      borderBottom: '1px solid var(--border-subtle)',
      zIndex: 9
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {/* Coordinates */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
          <MapPin size={16} />
          <span className="text-sm">Lat: <strong className="text-primary">28.147°</strong> Lon: <strong className="text-primary">78.006°</strong></span>
        </div>

        {/* Data Source */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', borderLeft: '1px solid var(--border-subtle)', paddingLeft: '1rem' }}>
          <Calendar size={16} color="var(--text-secondary)" />
          <div>
            <div className="text-xs text-muted">Data Source: <span style={{ color: 'var(--accent-warning)' }}>Simulated</span></div>
            <div className="text-xs text-muted" style={{ fontSize: '0.65rem' }}>Last Updated: 01:45:34 IST <span style={{ color: 'var(--accent-success)' }}>-199.839s</span></div>
          </div>
        </div>
      </div>

      {/* Counts */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <MetricBadge icon={<Factory size={16} />} label="Industrial Facilities" count="2,067" color="var(--accent-info)" />
        <MetricBadge icon={<Flame size={16} />} label="Wildfires (VIIRS)" count="2,589" color="var(--accent-warning)" />
        <MetricBadge icon={<AlertCircle size={16} />} label="Other Events" count="774" color="var(--text-secondary)" />
      </div>

      {/* FRP Slider (Visual only for mockup) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span className="text-xs text-muted">FRP MW</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span className="text-xs">0</span>
          <div style={{ width: '100px', height: '4px', background: 'linear-gradient(90deg, var(--bg-primary), var(--accent-critical))', borderRadius: '2px', position: 'relative' }}>
            <div style={{ position: 'absolute', left: '10%', top: '-4px', width: '12px', height: '12px', border: '2px solid var(--accent-critical)', borderRadius: '50%', background: 'var(--bg-primary)' }}></div>
          </div>
          <span className="text-xs">10,000+</span>
        </div>
      </div>
    </div>
  );
}

function MetricBadge({ icon, label, count, color }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.4rem 0.75rem',
      background: 'var(--bg-primary)',
      border: '1px solid var(--border-subtle)',
      borderRadius: '6px'
    }}>
      <div style={{ color: color }}>{icon}</div>
      <span className="text-sm text-muted">{label}</span>
      <strong className="text-sm" style={{ color: color }}>{count}</strong>
    </div>
  );
}
