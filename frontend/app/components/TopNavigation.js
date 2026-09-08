"use client";

import { Search, Bell, AlertTriangle, User, Flame } from "lucide-react";

export default function TopNavigation() {
  return (
    <header className="glass-panel" style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.75rem 1.5rem',
      gridColumn: '1 / 3',
      gridRow: '1 / 2',
      zIndex: 10,
      borderBottom: '1px solid var(--border-subtle)',
      borderLeft: 'none',
      borderRight: 'none',
      borderTop: 'none',
      borderRadius: '0'
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <Flame size={24} color="var(--accent-brand)" />
        <div>
          <h1 className="text-lg font-bold" style={{ margin: 0, lineHeight: 1 }}>AgniView</h1>
          <p className="text-xs text-muted" style={{ margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Fire Intelligence & Resource Monitoring
          </p>
        </div>
      </div>

      {/* Search */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        background: 'var(--bg-secondary)', 
        border: '1px solid var(--border-subtle)',
        borderRadius: '24px',
        padding: '0.5rem 1rem',
        width: '400px',
        gap: '0.5rem'
      }}>
        <Search size={16} color="var(--text-tertiary)" />
        <input 
          type="text" 
          placeholder="Search location, event, facility, or coordinates..." 
          style={{ 
            background: 'transparent', 
            border: 'none', 
            color: 'var(--text-primary)',
            width: '100%',
            fontSize: '0.875rem'
          }}
        />
        <div style={{ 
          background: 'var(--bg-primary)', 
          padding: '0.1rem 0.4rem', 
          borderRadius: '4px', 
          fontSize: '0.75rem',
          color: 'var(--text-tertiary)'
        }}>/</div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {/* Feed Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--bg-secondary)', padding: '0.5rem 1rem', borderRadius: '24px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-warning)', boxShadow: '0 0 8px var(--accent-warning)' }}></div>
          <div>
            <div className="text-xs font-semibold">Simulated Feed</div>
            <div className="text-xs text-muted" style={{ fontSize: '0.65rem' }}>Data latency: &lt; 30s</div>
          </div>
        </div>

        {/* Critical Alerts */}
        <button style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.5rem', 
          background: 'rgba(239, 68, 68, 0.1)', 
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: 'var(--accent-critical)',
          padding: '0.5rem 1rem',
          borderRadius: '24px',
          cursor: 'pointer'
        }}>
          <AlertTriangle size={16} />
          <span className="text-sm font-semibold">9 Critical</span>
        </button>

        {/* Notifications */}
        <button style={{ background: 'transparent', border: 'none', cursor: 'pointer', position: 'relative' }}>
          <Bell size={20} color="var(--text-secondary)" />
          <div style={{ position: 'absolute', top: 0, right: 0, width: '8px', height: '8px', background: 'var(--accent-critical)', borderRadius: '50%' }}></div>
        </button>

        {/* User Profile */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: '0.5rem' }}>
          <div style={{ background: 'var(--accent-info)', width: '32px', height: '32px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <User size={16} color="white" />
          </div>
          <div>
            <div className="text-sm font-semibold">Analyst_47</div>
            <div className="text-xs text-muted" style={{ fontSize: '0.65rem' }}>Level 5 Analyst</div>
          </div>
        </div>
      </div>
    </header>
  );
}
