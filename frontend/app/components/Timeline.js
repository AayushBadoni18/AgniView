"use client";

import { Play, SkipBack, SkipForward, Clock } from "lucide-react";
import { BarChart, Bar, ResponsiveContainer, Cell } from "recharts";

// Mock data for the histogram
const data = Array.from({ length: 48 }).map((_, i) => ({
  time: i,
  count: Math.floor(Math.random() * 100) + 10,
  isCritical: Math.random() > 0.8
}));

export default function Timeline() {
  return (
    <div className="glass-panel" style={{
      gridColumn: '1 / 3',
      gridRow: '4 / 5',
      display: 'flex',
      alignItems: 'center',
      padding: '0.5rem 1.5rem',
      gap: '1.5rem',
      borderTop: '1px solid var(--border-subtle)',
      borderBottom: 'none',
      borderLeft: 'none',
      borderRight: 'none',
      borderRadius: '0',
      zIndex: 10
    }}>
      {/* Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span className="text-xs text-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>Timeline Controls</span>
          <select style={{ 
            background: 'transparent', 
            border: '1px solid var(--border-subtle)', 
            color: 'var(--text-primary)', 
            padding: '0.25rem', 
            borderRadius: '4px',
            fontSize: '0.75rem'
          }}>
            <option>Last 24 Hours</option>
            <option>Last 6 Hours</option>
            <option>Last 7 Days</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button style={{ background: 'transparent', border: '1px solid var(--border-subtle)', padding: '0.25rem', borderRadius: '4px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <span className="text-xs">6H</span>
          </button>
          <button style={{ background: 'rgba(59, 130, 246, 0.2)', border: '1px solid var(--accent-info)', padding: '0.25rem', borderRadius: '4px', color: 'var(--accent-info)', cursor: 'pointer' }}>
            <span className="text-xs">24H</span>
          </button>
          <button style={{ background: 'transparent', border: '1px solid var(--border-subtle)', padding: '0.25rem', borderRadius: '4px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <span className="text-xs">7D</span>
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button style={{ background: 'transparent', border: '1px solid var(--border-subtle)', padding: '0.25rem', borderRadius: '50%', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex' }}><SkipBack size={14} /></button>
          <button style={{ background: 'rgba(59, 130, 246, 0.2)', border: '1px solid var(--accent-info)', padding: '0.5rem', borderRadius: '50%', color: 'var(--accent-info)', cursor: 'pointer', display: 'flex' }}><Play size={16} fill="currentColor" /></button>
          <button style={{ background: 'transparent', border: '1px solid var(--border-subtle)', padding: '0.25rem', borderRadius: '50%', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex' }}><SkipForward size={14} /></button>
        </div>
      </div>

      {/* Histogram */}
      <div style={{ flex: 1, height: '40px', display: 'flex', flexDirection: 'column', position: 'relative' }}>
        <span className="text-xs text-muted" style={{ position: 'absolute', top: '-15px', left: 0, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Event Timeline</span>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <Bar dataKey="count" radius={[2, 2, 0, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.isCritical ? 'var(--accent-critical)' : 'var(--accent-info)'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Clock */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', minWidth: '120px' }}>
        <span className="text-xs text-muted" style={{ textTransform: 'uppercase', color: 'var(--accent-info)' }}>Current Time (IST)</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Clock size={16} color="var(--text-secondary)" />
          <span className="text-xl font-bold" style={{ fontFamily: 'monospace' }}>01:45:49</span>
        </div>
        <span className="text-xs text-muted">09 Sept 2026</span>
      </div>
    </div>
  );
}
