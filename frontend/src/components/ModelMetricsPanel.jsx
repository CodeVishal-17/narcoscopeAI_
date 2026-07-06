export default function ModelMetricsPanel({ metrics }) {
  if (!metrics) {
    return <div className="db-metrics db-metrics-muted">Loading model accuracy…</div>;
  }
  if (!metrics.available) {
    return (
      <div className="db-metrics db-metrics-muted">
        <strong>No verified accuracy yet.</strong>
        <p>{metrics.reason}</p>
      </div>
    );
  }
  return (
    <div className="db-metrics">
      <div className={`db-metrics-flag ${metrics.reliable ? "ok" : "warn"}`}>
        {metrics.reliable ? "Reliable test set" : "Indicative only"}
      </div>
      <div className="db-metrics-grid">
        <div className="db-metrics-cell">
          <span className="db-metrics-k">Precision</span>
          <span className="db-metrics-v">{metrics.precision}</span>
        </div>
        <div className="db-metrics-cell">
          <span className="db-metrics-k">Recall</span>
          <span className="db-metrics-v">{metrics.recall}</span>
        </div>
        <div className="db-metrics-cell">
          <span className="db-metrics-k">F1</span>
          <span className="db-metrics-v">{metrics.f1}</span>
        </div>
        <div className="db-metrics-cell">
          <span className="db-metrics-k">N (test)</span>
          <span className="db-metrics-v">{metrics.n}</span>
        </div>
      </div>
      {metrics.warnings?.map((w, i) => (
        <div className="db-metrics-warn" key={i}>
          {w}
        </div>
      ))}
    </div>
  );
}
