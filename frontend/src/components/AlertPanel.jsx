import { useState } from 'react';

const SEVERITY_COLORS = {
  critical: { bg: 'rgba(220,38,38,0.15)', border: '#ef4444', text: '#fca5a5', dot: '#ef4444' },
  high: { bg: 'rgba(234,88,12,0.12)', border: '#f97316', text: '#fdba74', dot: '#f97316' },
};

const SEVERITY_ICON = { critical: '🚨', high: '⚠️' };

export default function AlertPanel({ alerts = [], onAcknowledge, onDismiss }) {
  const [filter, setFilter] = useState('new');

  const filtered = alerts.filter(a => filter === 'all' || a.status === filter);
  const newCount = alerts.filter(a => a.status === 'new').length;

  return (
    <div className="alert-panel">
      <div className="alert-panel-header">
        <span className="alert-panel-title">
          🔔 Alerts
          {newCount > 0 && <span className="alert-badge">{newCount}</span>}
        </span>
        <div className="alert-filter-row">
          {['new', 'acknowledged', 'all'].map(f => (
            <button
              key={f}
              className={`alert-filter-btn ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 && (
        <div className="alert-empty">
          {filter === 'new' ? 'No new alerts.' : 'Nothing to show.'}
        </div>
      )}

      <div className="alert-list">
        {filtered.map(alert => {
          const colors = SEVERITY_COLORS[alert.severity] || SEVERITY_COLORS.high;
          return (
            <div
              key={alert.id}
              className="alert-item"
              style={{ background: colors.bg, borderLeft: `3px solid ${colors.border}` }}
            >
              <div className="alert-item-top">
                <span className="alert-icon">{SEVERITY_ICON[alert.severity]}</span>
                <span className="alert-handle" style={{ color: colors.text }}>
                  {alert.handle}
                </span>
                <span className="alert-platform">{alert.platform}</span>
                <span className="alert-score">{alert.risk_score?.toFixed(1)}</span>
              </div>
              <div className="alert-msg">{alert.message}</div>
              <div className="alert-meta">
                <span className="alert-ts">
                  {new Date(alert.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })}
                </span>
                {alert.status === 'new' && (
                  <div className="alert-actions">
                    <button className="alert-btn ack" onClick={() => onAcknowledge(alert.id)}>
                      ✓ Ack
                    </button>
                    <button className="alert-btn dis" onClick={() => onDismiss(alert.id)}>
                      ✗ Dismiss
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
