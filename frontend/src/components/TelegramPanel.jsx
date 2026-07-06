import { useState } from "react";

export default function TelegramPanel({ health, watchlist, job, onScan, onAddWatch, onRemoveWatch }) {
  const [input, setInput] = useState("");
  const [newWatch, setNewWatch] = useState("");

  const parseTargets = (raw) =>
    raw
      .split(/[\s,]+/)
      .map((t) => t.trim())
      .filter(Boolean);

  const busy = job && (job.status === "pending" || job.status === "running");

  const statusText =
    health === null
      ? "Checking connection…"
      : health.ready
        ? "Telegram connected"
        : health.credentials_configured
          ? "Run login_telegram.py once"
          : "Telegram not connected";

  return (
    <div className="db-tg">
      <div className={`db-tg-health ${health?.ready ? "ready" : "off"}`}>
        <span className="db-tg-dot" />
        {statusText}
      </div>

      <textarea
        className="db-tg-input"
        placeholder="@channel_one, @channel_two"
        rows={2}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        disabled={!health?.ready || busy}
      />
      <button
        className="btn btn-primary db-tg-scan"
        disabled={!health?.ready || busy || parseTargets(input).length === 0}
        onClick={() => onScan(parseTargets(input))}
      >
        {busy ? "Scraping…" : "Scan channels"}
      </button>

      {job && (
        <div className={`db-tg-job ${job.status}`}>
          {job.status === "pending" && "Queued…"}
          {job.status === "running" && "Fetching messages via Telegram API…"}
          {job.status === "done" && "Scan complete — dashboard updated."}
          {job.status === "error" && `Failed: ${job.error?.split("\n").pop() || "unknown error"}`}
        </div>
      )}

      <div className="db-tg-watch-head">Watchlist</div>
      <div className="db-tg-watchlist">
        {watchlist.map((w) => (
          <div className="db-tg-watch" key={w.id}>
            <span>{w.username}</span>
            <button className="db-tg-watch-x" onClick={() => onRemoveWatch(w.id)} aria-label="Remove">
              ✕
            </button>
          </div>
        ))}
        {watchlist.length === 0 && <div className="db-tg-watch-empty">No channels watched yet.</div>}
      </div>
      <div className="db-tg-add">
        <input
          type="text"
          placeholder="@new_channel"
          value={newWatch}
          onChange={(e) => setNewWatch(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && newWatch.trim()) {
              onAddWatch(newWatch.trim());
              setNewWatch("");
            }
          }}
        />
        <button
          onClick={() => {
            if (newWatch.trim()) {
              onAddWatch(newWatch.trim());
              setNewWatch("");
            }
          }}
        >
          Add
        </button>
      </div>
    </div>
  );
}
