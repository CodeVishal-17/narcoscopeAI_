import RiskBadge from "./RiskBadge.jsx";
import MetadataPanel from './MetadataPanel.jsx';

function handleFor(accounts, accountId) {
  const match = accounts.find((a) => a.account_id === accountId);
  return match ? match.handle : accountId;
}

export default function AccountDrawer({ account, clusters, allAccounts, loading, onClose, onGenerateDossier }) {
  if (loading) {
    return (
      <aside className="db-drawer db-drawer-empty">
        <span>Loading account evidence…</span>
      </aside>
    );
  }
  if (!account) {
    return null;
  }

  const linkedClusters = clusters.filter((c) => c.account_ids.includes(account.account_id));

  return (
    <aside className="db-drawer">
      <div className="db-drawer-head">
        <button className="db-drawer-close" onClick={onClose} aria-label="Close">✕</button>
        <h2>{account.handle}</h2>
        <div className="db-drawer-sub">
          <span>{account.platform}</span>
          <span className="db-dot-sep" />
          <span>{account.account_type}</span>
          <RiskBadge band={account.risk_band} />
        </div>
      </div>

      <div className="db-kv">
        <div className="db-kv-item">
          <div className="db-kv-k">Risk score</div>
          <div className="db-kv-v">{account.risk_score.toFixed(2)}</div>
        </div>
        <div className="db-kv-item">
          <div className="db-kv-k">Automated</div>
          <div className="db-kv-v">{account.is_probable_bot ? "Likely bot" : "No"}</div>
        </div>
        <div className="db-kv-item">
          <div className="db-kv-k">Flagged messages</div>
          <div className="db-kv-v">
            {account.flagged_message_count}/{account.total_messages_seen}
          </div>
        </div>
        <div className="db-kv-item">
          <div className="db-kv-k">Dataset Type</div>
          <div className="db-kv-v">
            <span
              style={{
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: '600',
                backgroundColor: account.source?.includes('Synthetic') || account.source === 'sample' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(6, 182, 212, 0.2)',
                color: account.source?.includes('Synthetic') || account.source === 'sample' ? '#c084fc' : '#22d3ee',
                border: account.source?.includes('Synthetic') || account.source === 'sample' ? '1px solid rgba(168, 85, 247, 0.4)' : '1px solid rgba(6, 182, 212, 0.4)',
                display: 'inline-block',
              }}
            >
              {account.source === 'file' || account.source === 'sample' ? '🧪 Synthetic (Model Training)' : account.source === 'telegram_live' ? '🌐 Real OSINT (Live Scrape)' : account.source}
            </span>
          </div>
        </div>
        {account.features?.unique_substances > 0 && (
          <div className="db-kv-item">
            <div className="db-kv-k">Unique substances</div>
            <div className="db-kv-v">{account.features.unique_substances}</div>
          </div>
        )}
        {account.features?.burstiness > 0 && (
          <div className="db-kv-item">
            <div className="db-kv-k">Burst posting</div>
            <div className="db-kv-v" style={{color:'#f97316'}}>Detected (bot cadence)</div>
          </div>
        )}
      </div>

      <div className="db-drawer-section">Evidence · top matches</div>
      {account.evidence_sample.length === 0 && (
        <div className="db-drawer-note">
          No individually flagged messages — risk comes from the aggregate pattern.
        </div>
      )}
      {account.evidence_sample.map((ev, i) => (
        <div className="db-evidence" key={i}>
          <div className="db-evidence-top">
            <span className="db-evidence-conf">{(ev.final_prob * 100).toFixed(0)}%</span>
            <span className="db-evidence-by">{ev.decided_by}</span>
          </div>
          <div className="db-evidence-text">{ev.text}</div>
          <div className="db-evidence-tags">
            {ev.matched_terms.map((t) => (
              <span className="db-tag term" key={`term-${t}`}>
                {t}
              </span>
            ))}
            {ev.matched_phrases.map((p) => (
              <span className="db-tag phrase" key={`phrase-${p}`}>
                {p}
              </span>
            ))}
            {ev.matched_emoji.map((e, idx) => (
              <span className="db-tag phrase" key={`emoji-${idx}`}>
                {e}
              </span>
            ))}
          </div>
        </div>
      ))}

      <MetadataPanel metadata={account.features?.extracted_metadata || null} />

      {linkedClusters.length > 0 && (
        <>
          <div className="db-drawer-section">Linked accounts · shared payment handle</div>
          {linkedClusters.map((c) => (
            <div className="db-cluster" key={c.payment_handle}>
              <strong>{c.payment_handle}</strong> also used by{" "}
              {c.account_ids
                .filter((id) => id !== account.account_id)
                .map((id) => handleFor(allAccounts, id))
                .join(", ")}
            </div>
          ))}
        </>
      )}

      <button className="btn btn-primary db-dossier-btn" onClick={onGenerateDossier}>
        Generate legal-request dossier
      </button>
      <p className="db-legal-note">
        Packages this evidence for an investigator to submit under lawful process (Section 91
        CrPC/BNSS, or MLAT). No subscriber data is extracted automatically — a human analyst must
        review and file the request.
      </p>
    </aside>
  );
}
