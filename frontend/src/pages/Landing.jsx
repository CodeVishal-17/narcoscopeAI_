import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import "./Landing.css";

const PIPELINE = [
  {
    n: "01",
    tag: "Ingest",
    title: "Watch public channels",
    body: "Reads public Telegram channels and bots live via the official API, plus WhatsApp groups and Instagram content from exports — nothing private, nothing intercepted.",
  },
  {
    n: "02",
    tag: "Score",
    title: "Flag & score",
    body: "A hybrid engine — rules first, then a trained ML classifier, then LLM adjudication for ambiguous cases — scores every message.",
  },
  {
    n: "03",
    tag: "Link",
    title: "Correlate identities",
    body: "Groups accounts across platforms that share a payment handle or bio pattern — the legal, public-data OSINT layer.",
  },
  {
    n: "04",
    tag: "Escalate",
    title: "Analyst review",
    body: "A human investigator reviews the dossier and, if warranted, submits it to the platform for lawful subscriber-record disclosure.",
  },
];

const FEATURES = [
  {
    title: "Telegram bots & channels",
    body: "Live-fetched via the official API: detects command bots, price-list patterns, and 'backup channel' links posted when a storefront gets banned and reappears.",
  },
  {
    title: "Instagram handles & stories",
    body: "Reads coded bios and caption patterns ('DM for price', emoji substitution) that slip past plain keyword filters.",
  },
  {
    title: "Cross-platform correlation",
    body: "The same UPI ID on a Telegram channel and an Instagram profile is treated as one operator, not two separate leads.",
  },
];

export default function Landing() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api
      .latestScan()
      .then((scan) =>
        setStats({
          accounts: scan.accounts_analyzed,
          flagged: scan.flagged_accounts,
          clusters: scan.clusters.length,
          platforms: new Set(scan.accounts.map((a) => a.platform)).size,
        })
      )
      .catch(() => setStats(null));
  }, []);

  const stat = (v) => (stats ? v : "—");

  return (
    <div className="landing">
      <nav className="lp-nav">
        <div className="lp-brand">
          <span className="lp-mark">N</span>
          NarcoScope<span className="lp-brand-ai">AI</span>
        </div>
        <div className="lp-nav-links">
          <a href="#how">How it works</a>
          <a href="#engine">Engine</a>
          <a href="#legal">Legal scope</a>
        </div>
        <Link className="btn btn-primary lp-nav-cta" to="/dashboard">
          Open dashboard
        </Link>
      </nav>

      <header className="lp-hero">
        <div className="lp-hero-glow" />
        <div className="lp-hero-inner">
          <div className="lp-eyebrow">
            <span className="lp-live-dot" />
            Live prototype · real &amp; synthetic data
          </div>
          <h1 className="lp-title">
            Detect drug-sale activity across <span>Telegram, WhatsApp &amp; Instagram</span>
          </h1>
          <p className="lp-tagline">
            NarcoScope AI flags trafficking-related accounts in India, scores the risk, and
            builds the evidence trail investigators need for lawful action.
          </p>
          <div className="lp-hero-ctas">
            <Link className="btn btn-primary" to="/dashboard">
              Open investigator dashboard
            </Link>
            <a className="btn btn-ghost" href="#how">
              See how it works
            </a>
          </div>

          <div className="lp-stats">
            <div className="lp-stat">
              <div className="lp-stat-num">{stat(stats?.accounts)}</div>
              <div className="lp-stat-label">Accounts analyzed</div>
            </div>
            <div className="lp-stat">
              <div className="lp-stat-num accent-critical">{stat(stats?.flagged)}</div>
              <div className="lp-stat-label">Flagged high / critical</div>
            </div>
            <div className="lp-stat">
              <div className="lp-stat-num">{stat(stats?.clusters)}</div>
              <div className="lp-stat-label">Linked operator clusters</div>
            </div>
            <div className="lp-stat">
              <div className="lp-stat-num">{stat(stats?.platforms)}</div>
              <div className="lp-stat-label">Platforms covered</div>
            </div>
          </div>
        </div>
      </header>

      <section id="how" className="lp-section">
        <div className="lp-section-head">
          <span className="lp-section-tag">Pipeline</span>
          <h2>From a public post to an evidence-backed lead</h2>
          <p>Four stages, with a human in the loop before anything leaves the system.</p>
        </div>
        <div className="lp-pipeline">
          {PIPELINE.map((s) => (
            <div className="lp-step" key={s.n}>
              <div className="lp-step-top">
                <span className="lp-step-n">{s.n}</span>
                <span className="lp-step-tag">{s.tag}</span>
              </div>
              <h3>{s.title}</h3>
              <p>{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="engine" className="lp-section">
        <div className="lp-section-head">
          <span className="lp-section-tag">Detection engine</span>
          <h2>Built for how trafficking actually shows up</h2>
          <p>Not a generic keyword filter — tuned to each platform's patterns.</p>
        </div>
        <div className="lp-features">
          {FEATURES.map((f) => (
            <div className="lp-feature" key={f.title}>
              <div className="lp-feature-dot" />
              <h3>{f.title}</h3>
              <p>{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="legal" className="lp-section">
        <div className="lp-legal">
          <span className="lp-section-tag">Scope &amp; limits</span>
          <p>
            <strong>
              IP addresses, phone numbers, and email IDs are not extracted from public content
            </strong>{" "}
            — platforms don't expose that data, and no legitimate tool can. NarcoScope AI's job
            ends at building a well-evidenced dossier; obtaining subscriber records requires an
            investigator to submit that evidence through lawful process (Section 91 CrPC/BNSS, or
            an MLAT request for foreign platforms). Every escalation passes through human analyst
            review before it goes anywhere.
          </p>
        </div>
      </section>

      <section className="lp-final">
        <h2>See it flag activity in real time</h2>
        <p>Runs on live Telegram data and synthetic samples — safe to explore, easy to extend.</p>
        <Link className="btn btn-primary" to="/dashboard">
          Open investigator dashboard
        </Link>
      </section>

      <footer className="lp-footer">
        <span>NarcoScope AI · prototype build</span>
        <span>Live Telegram ingestion · no WhatsApp / Instagram interception</span>
      </footer>
    </div>
  );
}
