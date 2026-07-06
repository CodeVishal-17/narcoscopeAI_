// Operator network view: each shared payment handle becomes a hub, with the
// accounts that use it (across platforms) as spokes — visualising "one operator,
// many storefronts", which is the core investigative insight.

const BAND_COLOR = {
  CRITICAL: "#f2555a",
  HIGH: "#f5a623",
  MEDIUM: "#f5d023",
  LOW: "#4ade80",
};

function ClusterGraph({ cluster, byAccId, onSelect }) {
  const nodes = cluster.account_ids.map((id) => byAccId[id]).filter(Boolean);
  const W = 300;
  const H = 210;
  const cx = W / 2;
  const cy = H / 2;
  const r = nodes.length <= 2 ? 66 : 78;

  const positions = nodes.map((_, i) => {
    const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  });

  return (
    <div className="db-cluster-card">
      <svg viewBox={`0 0 ${W} ${H}`} className="db-cluster-svg">
        {positions.map((p, i) => (
          <line key={`l${i}`} x1={cx} y1={cy} x2={p.x} y2={p.y} className="db-net-edge" />
        ))}
        {/* hub */}
        <g>
          <rect x={cx - 30} y={cy - 14} width="60" height="28" rx="7" className="db-net-hub" />
          <text x={cx} y={cy + 4} className="db-net-hub-text" textAnchor="middle">
            UPI
          </text>
        </g>
        {/* account nodes */}
        {nodes.map((n, i) => {
          const p = positions[i];
          return (
            <g
              key={n.account_id}
              className="db-net-node"
              onClick={() => onSelect(n.id)}
              style={{ cursor: "pointer" }}
            >
              <circle cx={p.x} cy={p.y} r="16" fill={BAND_COLOR[n.risk_band] || "#5e6b80"} />
              <text x={p.x} y={p.y + 4} className="db-net-node-plat" textAnchor="middle">
                {n.platform.slice(0, 2).toUpperCase()}
              </text>
              <text x={p.x} y={p.y + 30} className="db-net-node-label" textAnchor="middle">
                {n.handle.length > 18 ? n.handle.slice(0, 17) + "…" : n.handle}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="db-cluster-handle">
        <span className="db-cluster-mono">{cluster.payment_handle}</span> · {nodes.length} accounts,{" "}
        {new Set(nodes.map((n) => n.platform)).size} platforms
      </div>
    </div>
  );
}

export default function NetworkGraph({ clusters, accounts, onSelect }) {
  const byAccId = Object.fromEntries(accounts.map((a) => [a.account_id, a]));
  const real = clusters.filter((c) => c.account_ids.length > 1);
  if (real.length === 0) return null;

  return (
    <div className="db-network">
      <div className="db-network-head">
        Operator networks
        <span>accounts linked across platforms by a shared payment handle — likely one operator</span>
      </div>
      <div className="db-network-grid">
        {real.map((c) => (
          <ClusterGraph key={c.payment_handle} cluster={c} byAccId={byAccId} onSelect={onSelect} />
        ))}
      </div>
    </div>
  );
}
