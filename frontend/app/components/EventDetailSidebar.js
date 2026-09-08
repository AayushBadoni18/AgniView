"use client";

import { useState } from "react";
import { X, ExternalLink, Activity, Info, AlertTriangle, Target, Sun, MapPin, Copy, ChevronRight } from "lucide-react";
import { LineChart, Line, ResponsiveContainer, YAxis, Tooltip, ReferenceLine } from "recharts";

// Mock data for the FRP Analysis line chart
const frpData = Array.from({ length: 24 }).map((_, i) => ({
  time: i,
  current: i < 18 ? null : (i === 23 ? 9842 : Math.pow(i - 17, 3) * 50),
  baseline: 100 + (Math.sin(i / 3) * 50)
}));

export default function EventDetailSidebar({ event, onClose }) {
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [conversation, setConversation] = useState([]);

  if (!event) return null;
  if (event.loading) return <div className="glass-panel" style={{ gridColumn: '2 / 3', gridRow: '3 / 4', margin: '1rem 1rem 1rem 0', display: 'grid', placeItems: 'center', color: 'var(--text-secondary)' }}>Loading intelligence...</div>;

  const isCritical = event.severity === "high" || event.isAnomaly;

  async function ask(e) {
    e.preventDefault();
    if (!question.trim()) return;
    setAsking(true);
    try {
      const response = await fetch(`/api/events/${event.id}/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) });
      const answer = await response.json();
      setConversation((items) => [...items, { question, answer: answer.answer || "No response." }]);
      setQuestion("");
    } catch {
      setConversation((items) => [...items, { question, answer: "AI service unavailable." }]);
    } finally {
      setAsking(false);
    }
  }

  return (
    <aside className="glass-panel" style={{
      gridColumn: '2 / 3',
      gridRow: '3 / 4',
      margin: '1rem 1rem 1rem 0',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      border: isCritical ? '1px solid rgba(239, 68, 68, 0.4)' : undefined,
      boxShadow: isCritical ? '0 0 20px rgba(239, 68, 68, 0.15)' : undefined
    }}>
      
      {/* Header Alert Card */}
      <div style={{
        background: isCritical ? 'linear-gradient(135deg, rgba(239,68,68,0.2) 0%, rgba(239,68,68,0.05) 100%)' : 'rgba(255,255,255,0.02)',
        padding: '1.25rem',
        borderBottom: '1px solid var(--border-subtle)',
        position: 'relative'
      }}>
        <button onClick={onClose} style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}><X size={20} /></button>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          {isCritical && <AlertTriangle size={16} color="var(--accent-critical)" />}
          <span className="text-xs font-bold" style={{ color: isCritical ? 'var(--accent-critical)' : 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {isCritical ? 'Critical Alert' : 'Event Analysis'}
          </span>
          <span className="text-xs text-muted" style={{ marginLeft: 'auto', marginRight: '1.5rem' }}>Just Now</span>
        </div>
        
        <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
          {event.classification === 'industrial' ? 'Thermal Anomaly Detected' : 'Wildfire Detected'}
        </h2>
        
        <div className="text-sm text-muted" style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Activity size={14} /> Reverse-geocoding...
        </div>

        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}><Target size={14} color="var(--text-secondary)"/><span className="text-xs">{event.latitude.toFixed(4)}°, {event.longitude.toFixed(4)}°</span></div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}><Info size={14} color="var(--accent-success)"/><span className="text-xs">High Confidence ({Math.round(event.confidence * 100)}%)</span></div>
        </div>

        <button style={{
          width: '100%',
          padding: '0.5rem',
          background: isCritical ? 'rgba(239, 68, 68, 0.15)' : 'rgba(255, 255, 255, 0.05)',
          border: isCritical ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid var(--border-subtle)',
          borderRadius: '4px',
          color: isCritical ? '#fca5a5' : 'var(--text-primary)',
          cursor: 'pointer',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '0.5rem',
          transition: 'all 0.2s'
        }}>
          View Alert Details <ChevronRight size={16} />
        </button>
      </div>

      {/* Scrollable Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem' }}>
        
        {/* Detection Details */}
        <div style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 className="text-xs font-bold text-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>Detection Details</h3>
            <span style={{ fontSize: '0.65rem', color: 'var(--accent-success)', display: 'flex', alignItems: 'center', gap: '4px' }}><div style={{width: '6px', height: '6px', background: 'var(--accent-success)', borderRadius: '50%'}}></div> TRACKING</span>
          </div>

          <div style={{ background: 'var(--bg-secondary)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: isCritical ? 'var(--accent-critical)' : 'var(--accent-warning)', border: '2px solid white' }}></div>
              <div>
                <div className="text-sm font-semibold">{event.classification} ({event.source || 'VIIRS'})</div>
                <div className="text-xs text-muted">Pass: {event.satellite || 'Unknown'}</div>
              </div>
              {isCritical && <div style={{ marginLeft: 'auto', background: 'rgba(239,68,68,0.2)', color: 'var(--accent-critical)', fontSize: '0.65rem', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold' }}>CRIT</div>}
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', marginBottom: '1.5rem', color: 'var(--text-secondary)' }}>
              <MapPin size={16} style={{ marginTop: '2px' }} />
              <div>
                <div className="text-sm">Uncatalogued sector</div>
                <div className="text-xs text-muted" style={{ fontFamily: 'monospace' }}>{event.latitude.toFixed(5)}°, {event.longitude.toFixed(5)}°</div>
              </div>
            </div>

            {/* Fire Radiative Power Bar */}
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span className="text-xs text-muted" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Activity size={12} /> FIRE RADIATIVE POWER</span>
                <span className="text-lg font-bold">{event.frp || 0} <span className="text-xs text-muted">MW</span></span>
              </div>
              <div style={{ height: '4px', background: 'var(--bg-primary)', borderRadius: '2px', position: 'relative' }}>
                <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: `${Math.min((event.frp || 0) / 100, 100)}%`, background: 'var(--accent-critical)', borderRadius: '2px', boxShadow: '0 0 10px var(--accent-critical)' }}></div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px', fontSize: '0.65rem', color: 'var(--text-tertiary)' }}>
                <span>1</span><span>100</span><span>1k</span><span>10k MW</span>
              </div>
            </div>

            {/* Grid Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <span className="text-xs text-muted" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Target size={12} /> CONFIDENCE</span>
                <div className="text-lg font-bold" style={{ margin: '4px 0' }}>{Math.round(event.confidence * 100)}%</div>
                <div style={{ height: '2px', background: 'var(--bg-primary)', borderRadius: '1px' }}>
                  <div style={{ width: `${Math.round(event.confidence * 100)}%`, height: '100%', background: 'var(--accent-success)', borderRadius: '1px' }}></div>
                </div>
              </div>
              <div>
                <span className="text-xs text-muted" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Sun size={12} /> BRIGHTNESS</span>
                <div className="text-lg font-bold" style={{ margin: '4px 0' }}>{event.brightness || 'N/A'} <span className="text-xs font-normal text-muted">K</span></div>
                <div className="text-xs text-muted">extreme heat</div>
              </div>
              <div>
                <span className="text-xs text-muted" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Clock size={12} /> FIRST DETECTED</span>
                <div className="text-sm font-bold" style={{ margin: '4px 0' }}>{new Date(event.detectedAt).toLocaleTimeString()}</div>
                <div className="text-xs text-muted">{new Date(event.detectedAt).toLocaleDateString()}</div>
              </div>
            </div>

          </div>
        </div>

        {/* FRP Analysis Chart */}
        <div style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 className="text-xs font-bold text-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>FRP Analysis (MW) <span style={{ textTransform: 'none', fontWeight: 'normal' }}>— Last 24 Hours</span></h3>
          </div>
          <div style={{ height: '180px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={frpData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <YAxis stroke="var(--text-tertiary)" fontSize={10} tickFormatter={(value) => `${value > 1000 ? (value/1000).toFixed(0) + 'k' : value}`} />
                <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: '4px' }} />
                <Line type="monotone" dataKey="baseline" stroke="var(--text-tertiary)" strokeDasharray="3 3" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="current" stroke="var(--accent-critical)" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', fontSize: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><div style={{ width: '12px', height: '2px', background: 'var(--accent-critical)' }}></div> This Event</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-tertiary)' }}><div style={{ width: '12px', height: '2px', background: 'var(--text-tertiary)', borderTop: '2px dashed var(--bg-primary)' }}></div> 7-Day Baseline (Avg)</div>
          </div>
        </div>

        {/* AI Chat */}
        <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1.5rem' }}>
          <h3 className="text-xs font-bold text-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem' }}>Ask Point AI</h3>
          <p className="text-sm" style={{ marginBottom: '1rem', lineHeight: 1.6 }}>{event.aiSummary}</p>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem' }}>
            {conversation.map((msg, i) => (
              <div key={i} style={{ background: 'var(--bg-secondary)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <strong className="text-xs" style={{ color: 'var(--accent-info)', display: 'block', marginBottom: '4px' }}>Q: {msg.question}</strong>
                <p className="text-sm text-muted">{msg.answer}</p>
              </div>
            ))}
          </div>

          <form onSubmit={ask} style={{ display: 'flex', gap: '0.5rem' }}>
            <input 
              value={question} 
              onChange={e => setQuestion(e.target.value)}
              placeholder="Ask about this anomaly..."
              style={{ flex: 1, background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', padding: '0.5rem 0.75rem', borderRadius: '4px', color: 'var(--text-primary)', fontSize: '0.875rem' }}
            />
            <button disabled={asking} style={{ background: 'var(--accent-info)', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer', fontSize: '0.875rem', fontWeight: 'bold' }}>
              {asking ? '...' : 'Ask'}
            </button>
          </form>
        </div>

      </div>
    </aside>
  );
}
