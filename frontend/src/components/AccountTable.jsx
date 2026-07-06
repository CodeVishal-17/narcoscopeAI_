import RiskBadge from "./RiskBadge.jsx";

const BAR_COLOR = {
  CRITICAL: "var(--critical)",
  HIGH: "var(--high)",
  MEDIUM: "var(--medium)",
  LOW: "var(--low)",
};

export default function AccountTable({ accounts, selectedId, onSelect }) {
  if (accounts.length === 0) {
    return (
      <div className="db-table-card">
        <div className="db-table-empty">No accounts match this filter.</div>
      </div>
    );
  }
  return (
    <div className="db-table-card">
      <table className="db-table">
        <thead>
          <tr>
            <th>Platform</th>
            <th>Handle</th>
            <th>Risk score</th>
            <th>Band</th>
            <th>Flagged</th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((a) => (
            <tr
              key={a.id}
              className={a.id === selectedId ? "selected" : ""}
              onClick={() => onSelect(a.id)}
            >
              <td>
                <span className="db-platform">{a.platform}</span>
              </td>
              <td>
                <div className="db-handle">
                  {a.handle}
                  <span className="db-handle-type">{a.account_type}</span>
                  {a.is_probable_bot && a.account_type !== "bot" && (
                    <span className="db-bot-tag">automated</span>
                  )}
                  {a.source && (
                    <span
                      style={{
                        marginLeft: '8px',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontWeight: '600',
                        backgroundColor: a.source.includes('Synthetic') || a.source === 'sample' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(6, 182, 212, 0.2)',
                        color: a.source.includes('Synthetic') || a.source === 'sample' ? '#c084fc' : '#22d3ee',
                        border: a.source.includes('Synthetic') || a.source === 'sample' ? '1px solid rgba(168, 85, 247, 0.4)' : '1px solid rgba(6, 182, 212, 0.4)',
                        display: 'inline-block',
                      }}
                    >
                      {a.source === 'file' || a.source === 'sample' ? '🧪 Synthetic (Model Training)' : a.source === 'telegram_live' ? '🌐 Real OSINT (Live Scrape)' : a.source}
                    </span>
                  )}
                </div>
              </td>
              <td>
                <div className="db-score">
                  <div className="db-bar">
                    <div
                      className="db-bar-fill"
                      style={{
                        width: `${Math.min(a.risk_score * 10, 100)}%`,
                        background: BAR_COLOR[a.risk_band] || "var(--text-muted)",
                      }}
                    />
                  </div>
                  <span className="db-score-num">{a.risk_score.toFixed(2)}</span>
                </div>
              </td>
              <td>
                <RiskBadge band={a.risk_band} />
              </td>
              <td className="db-flagged">
                {a.flagged_message_count}
                <span>/{a.total_messages_seen}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
