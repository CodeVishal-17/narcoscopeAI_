import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import AccountTable from "../components/AccountTable.jsx";
import AccountDrawer from "../components/AccountDrawer.jsx";
import NetworkGraph from "../components/NetworkGraph.jsx";
import TelegramPanel from "../components/TelegramPanel.jsx";
import ModelMetricsPanel from "../components/ModelMetricsPanel.jsx";
import AlertPanel from '../components/AlertPanel.jsx';
import { printDossier } from "../utils/dossier.js";
import "./Dashboard.css";

const BAND_FILTERS = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];
const PLATFORM_FILTERS = ["ALL", "telegram", "instagram", "whatsapp"];
const BAND_LABEL = { ALL: "All accounts", LOW: "Low / clear" };

// Template for the "upload accounts JSON" workflow (Instagram / WhatsApp exports).
const UPLOAD_TEMPLATE = [
  {
    account_id: "ig_example_1",
    platform: "instagram",
    handle: "@some_handle",
    account_type: "profile",
    payment_handles: ["someone@upi"],
    external_links: ["https://t.me/theirbackupchannel"],
    bio: "Paste the profile bio text here",
    messages: [
      { text: "Paste a post caption here" },
      { text: "Paste another caption or story text here" },
    ],
  },
  {
    account_id: "ig_example_2",
    platform: "instagram",
    handle: "@another_handle",
    account_type: "profile",
    payment_handles: [],
    external_links: [],
    bio: "Another profile's bio",
    messages: [{ text: "One caption is enough to get a score" }],
  },
];

function downloadTemplate() {
  const blob = new Blob([JSON.stringify(UPLOAD_TEMPLATE, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "narcoscope_accounts_template.json";
  a.click();
  URL.revokeObjectURL(url);
}

export default function Dashboard() {
  const [scan, setScan] = useState(null);
  const [allScans, setAllScans] = useState([]);
  const [scanError, setScanError] = useState(null);
  const [bandFilter, setBandFilter] = useState("ALL");
  const [platformFilter, setPlatformFilter] = useState("ALL");
  const [selectedId, setSelectedId] = useState(null);
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [health, setHealth] = useState(null);
  const [watchlist, setWatchlist] = useState([]);
  const [job, setJob] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [runningSample, setRunningSample] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const pollRef = useRef(null);
  const fileInputRef = useRef(null);

  const loadScan = useCallback(() => {
    return api
      .latestScan()
      .then((s) => {
        setScan(s);
        setScanError(null);
      })
      .catch((e) => setScanError(e.message));
  }, []);

  const refreshAux = useCallback(() => {
    api.telegramHealth().then(setHealth).catch(() => setHealth({ ready: false }));
    api.listWatchlist().then(setWatchlist).catch(() => {});
    api.modelMetrics().then(setMetrics).catch(() => setMetrics(null));
    api.listAlerts().then(setAlerts).catch(() => setAlerts([]));
    api.listScans().then((res) => setAllScans(res.results || res)).catch(() => {});
  }, []);

  useEffect(() => {
    loadScan();
    refreshAux();
    return () => clearInterval(pollRef.current);
  }, [loadScan, refreshAux]);

  useEffect(() => {
    if (selectedId == null) {
      setSelectedDetail(null);
      return;
    }
    setDetailLoading(true);
    api
      .getAccount(selectedId)
      .then(setSelectedDetail)
      .finally(() => setDetailLoading(false));
  }, [selectedId]);

  const startPolling = (jobId) => {
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const j = await api.getJob(jobId);
      setJob(j);
      if (j.status === "done" || j.status === "error") {
        clearInterval(pollRef.current);
        if (j.status === "done") {
          await loadScan();
          refreshAux();
        }
      }
    }, 2000);
  };

  const handleRunSample = async () => {
    setRunningSample(true);
    try {
      const run = await api.runSampleScan();
      setScan(run);
      setSelectedId(null);
      refreshAux();
    } catch (e) {
      setScanError(e.message);
    } finally {
      setRunningSample(false);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const run = await api.uploadScan(file);
      setScan(run);
      setSelectedId(null);
      refreshAux();
    } catch (err) {
      setScanError(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleTelegramScan = async (targets) => {
    try {
      const j = await api.startTelegramScan(targets);
      setJob(j);
      startPolling(j.id);
    } catch (e) {
      setJob({ status: "error", error: e.body?.detail || e.message });
    }
  };

  const handleAddWatch = async (username) => {
    try {
      const w = await api.addWatch(username);
      setWatchlist((prev) => [...prev, w]);
    } catch {
      api.listWatchlist().then(setWatchlist).catch(() => {});
    }
  };

  const handleRemoveWatch = async (id) => {
    await api.removeWatch(id);
    setWatchlist((prev) => prev.filter((w) => w.id !== id));
  };

  const handleAcknowledge = async (id) => {
    await api.acknowledgeAlert(id);
    api.listAlerts().then(setAlerts).catch(() => {});
  };

  const handleDismiss = async (id) => {
    await api.dismissAlert(id);
    api.listAlerts().then(setAlerts).catch(() => {});
  };

  if (scanError && !scan) {
    return (
      <div className="db">
        <div className="db-empty-full">
          <h2>No scan data yet</h2>
          <p>{scanError}</p>
          <button className="btn btn-primary" onClick={handleRunSample}>
            Run sample scan
          </button>
        </div>
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="db">
        <div className="db-empty-full">Loading…</div>
      </div>
    );
  }

  const filtered = scan.accounts.filter(
    (a) =>
      (bandFilter === "ALL" || a.risk_band === bandFilter) &&
      (platformFilter === "ALL" || a.platform === platformFilter)
  );
  const counts = {
    ALL: scan.accounts.length,
    CRITICAL: scan.accounts.filter((a) => a.risk_band === "CRITICAL").length,
    HIGH: scan.accounts.filter((a) => a.risk_band === "HIGH").length,
    MEDIUM: scan.accounts.filter((a) => a.risk_band === "MEDIUM").length,
    LOW: scan.accounts.filter((a) => a.risk_band === "LOW").length,
  };
  const topAlert = scan.accounts.find((a) => a.risk_band === "CRITICAL") || scan.accounts[0];

  const friendlyLabel =
    scan.source === "sample"
      ? "Synthetic sample data"
      : scan.source === "upload"
        ? scan.source_label?.split(/[\\/]/).pop() || "Uploaded file"
        : scan.source_label;
  const drawerOpen = selectedId != null;

  return (
    <div className={`db ${drawerOpen ? "drawer-open" : ""}`}>
      {/* ---------- mobile top bar ---------- */}
      <div className="db-mobilebar">
        <button
          className="db-menu-btn"
          onClick={() => setMenuOpen(true)}
          aria-label="Open filters and tools"
        >
          ☰
        </button>
        <Link to="/" className="db-mobilebar-brand">
          <span className="db-brand-mark">N</span> NarcoScope AI
        </Link>
      </div>

      {menuOpen && <div className="db-backdrop" onClick={() => setMenuOpen(false)} />}

      {/* ---------- sidebar ---------- */}
      <aside className={`db-sidebar ${menuOpen ? "open" : ""}`}>
        <button
          className="db-sidebar-close"
          onClick={() => setMenuOpen(false)}
          aria-label="Close menu"
        >
          ✕
        </button>
        <Link to="/" className="db-brand">
          <span className="db-brand-mark">N</span>
          <span className="db-brand-text">
            NarcoScope AI
            <span>Anti-narcotics OSINT</span>
          </span>
        </Link>

        <div className="db-nav-group">
          <div className="db-nav-label">Risk band</div>
          <div className="db-chips">
            {BAND_FILTERS.map((b) => (
              <button
                key={b}
                className={`db-chip ${bandFilter === b ? "active" : ""}`}
                onClick={() => {
                  setBandFilter(b);
                  setMenuOpen(false);
                }}
              >
                <span>{BAND_LABEL[b] || b}</span>
                <span className="db-chip-count">{counts[b]}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="db-nav-group">
          <div className="db-nav-label">Platform</div>
          <div className="db-seg">
            {PLATFORM_FILTERS.map((p) => (
              <button
                key={p}
                className={`db-seg-btn ${platformFilter === p ? "active" : ""}`}
                onClick={() => {
                  setPlatformFilter(p);
                  setMenuOpen(false);
                }}
              >
                {p === "ALL" ? "All" : p}
              </button>
            ))}
          </div>
        </div>

        <div className="db-nav-group">
          <div className="db-nav-label">Data source</div>
          <button className="db-action" onClick={handleRunSample} disabled={runningSample}>
            {runningSample ? "Running sample…" : "↻ Run sample scan"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json,.json,.txt,text/plain"
            style={{ display: "none" }}
            onChange={handleUpload}
          />
          <button
            className="db-action db-action-upload"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? "Analyzing…" : "⬆ Upload accounts file"}
          </button>
          <div className="db-upload-hint">
            Instagram: accounts JSON.{" "}
            <button className="db-link-btn" onClick={downloadTemplate}>
              Download template
            </button>
            <br />
            WhatsApp: upload a group's "Export chat" .txt directly.
          </div>
        </div>

        <div className="db-nav-group">
          <div className="db-nav-label">Live Telegram ingestion</div>
          <TelegramPanel
            health={health}
            watchlist={watchlist}
            job={job}
            onScan={handleTelegramScan}
            onAddWatch={handleAddWatch}
            onRemoveWatch={handleRemoveWatch}
          />
        </div>

        <div className="db-nav-group">
          <AlertPanel
            alerts={alerts}
            onAcknowledge={handleAcknowledge}
            onDismiss={handleDismiss}
          />
        </div>

        <div className="db-nav-group">
          <div className="db-nav-label">Model accuracy</div>
          <ModelMetricsPanel metrics={metrics} />
        </div>

        <Link to="/" className="db-back">
          ← Back to landing
        </Link>
      </aside>

      {/* ---------- main ---------- */}
      <main className="db-main">
        <div className="db-topbar">
          <div>
            <h1>Flagged accounts</h1>
            <div className="db-topbar-sub">
              <span className="db-source-pill">{scan.source}</span>
              {friendlyLabel && <span className="db-source-label">{friendlyLabel}</span>}
              <span>· scan #{scan.id} · {new Date(scan.created_at).toLocaleString()}</span>
            </div>
          </div>
          <div className="db-scan-status" style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
            {allScans && allScans.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '12px', color: '#64748b', fontWeight: '500' }}>📜 History:</span>
                <select
                  value={scan?.id || ''}
                  onChange={async (e) => {
                    try {
                      const s = await api.getScan(e.target.value);
                      setScan(s);
                      setSelectedId(null);
                    } catch (err) {
                      console.error(err);
                    }
                  }}
                  style={{
                    background: '#1e293b',
                    color: '#f8fafc',
                    border: '1px solid #334155',
                    padding: '4px 8px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    cursor: 'pointer',
                    outline: 'none',
                    fontWeight: '500'
                  }}
                >
                  {allScans.map((s) => (
                    <option key={s.id} value={s.id}>
                      Scan #{s.id} · {s.source} ({s.accounts_analyzed || 0} accts) · {new Date(s.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <span className="db-dot" /> {scan.accounts_analyzed} analyzed
            </div>
          </div>
        </div>

        <div className="db-stats">
          <div className="db-stat">
            <div className="db-stat-label">Critical risk</div>
            <div className="db-stat-val critical">{counts.CRITICAL}</div>
          </div>
          <div className="db-stat">
            <div className="db-stat-label">High risk</div>
            <div className="db-stat-val high">{counts.HIGH}</div>
          </div>
          <div className="db-stat">
            <div className="db-stat-label">Accounts scanned</div>
            <div className="db-stat-val">{scan.accounts_analyzed}</div>
          </div>
          <div className="db-stat">
            <div className="db-stat-label">Linked clusters</div>
            <div className="db-stat-val">{scan.clusters.length}</div>
          </div>
        </div>

        {topAlert && (
          <div className={`db-alert ${topAlert.risk_band === "LOW" ? "calm" : ""}`}>
            <span className="db-alert-tag">
              {topAlert.risk_band === "LOW" ? "STATUS" : "ALERT"}
            </span>
            <span>
              {topAlert.risk_band !== "LOW"
                ? "Highest-risk account flagged"
                : "No critical alerts"}{" "}
              — <strong>{topAlert.handle}</strong> on {topAlert.platform}, risk{" "}
              {topAlert.risk_score.toFixed(2)} ({topAlert.risk_band})
            </span>
          </div>
        )}

        <AccountTable accounts={filtered} selectedId={selectedId} onSelect={setSelectedId} />

        <NetworkGraph
          clusters={scan.clusters}
          accounts={scan.accounts}
          onSelect={setSelectedId}
        />
      </main>

      {/* ---------- drawer ---------- */}
      {drawerOpen && (
      <AccountDrawer
        account={selectedDetail}
        clusters={scan.clusters}
        allAccounts={scan.accounts}
        loading={detailLoading}
        onClose={() => setSelectedId(null)}
        onGenerateDossier={async () => {
          try {
            const dossier = await api.getDossier(selectedId);
            printDossier(dossier);
          } catch (err) {
            alert(`Could not generate dossier: ${err.message}`);
          }
        }}
      />
      )}
    </div>
  );
}
