// Renders a court-oriented evidence dossier into a new window and triggers the
// browser's print dialog (Save as PDF). Using the browser to print keeps Hindi/
// Devanagari rendering correct, which server-side PDF fonts often get wrong.

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
}

function nl2br(s) {
  return esc(s).replace(/\n/g, "<br>");
}


export function printDossier(d) {
  const a = d.account;
  const generated = new Date(d.generated_at).toLocaleString();

  const evidenceRows = d.evidence
    .map(
      (ev, i) => `
      <div class="ev">
        <div class="ev-head">
          <span class="ev-n">Evidence ${i + 1}</span>
          <span class="ev-prob">confidence ${(ev.final_prob * 100).toFixed(0)}% · ${esc(ev.decided_by)}</span>
        </div>
        <div class="ev-text">${esc(ev.text)}</div>
        <div class="ev-meta">
          ${[...(ev.matched_terms || []), ...(ev.matched_phrases || [])]
            .map((t) => `<span class="tag">${esc(t)}</span>`)
            .join(" ")}
        </div>
        <div class="ev-hash"><b>SHA-256:</b> ${esc(ev.sha256)}</div>
      </div>`
    )
    .join("");

  const linkedRows = d.linked_accounts.length
    ? `<table class="linked">
        <tr><th>Payment handle</th><th>Linked account</th><th>Platform</th></tr>
        ${d.linked_accounts
          .map(
            (l) =>
              `<tr><td>${esc(l.payment_handle)}</td><td>${esc(l.handle)}</td><td>${esc(l.platform)}</td></tr>`
          )
          .join("")}
      </table>`
    : `<p class="muted">No cross-platform links found for this account in this scan.</p>`;

  // Triangulation identifiers extracted from public content
  const tri = d.triangulation || {};
  const triRows = [
    ["Mobile numbers", tri.mobile_numbers],
    ["Email IDs", tri.emails],
    ["UPI / Payment IDs", tri.upi_ids],
    ["Telegram links", tri.telegram_links],
    ["Instagram links", tri.instagram_links],
    ["WhatsApp links", tri.whatsapp_links],
    ["Crypto addresses", tri.crypto_addresses],
  ]
    .filter(([, vals]) => vals && vals.length)
    .map(([label, vals]) =>
      `<tr><td class="k">${esc(label)}</td><td>${vals.map((v) => `<span class="id">${esc(v)}</span>`).join(" &nbsp;")}</td></tr>`
    ).join("");

  const triangulationSection = `
    <div class="section-title">&#128269; Extracted identifiers &mdash; for triangulation</div>
    ${tri.note ? `<p class="meta-note">${esc(tri.note)}</p>` : ""}
    ${ triRows
      ? `<table class="meta">${triRows}</table>`
      : `<p class="muted">No identifiable metadata found in public content for this account.</p>` }`;

  const legalSection = d.legal_request_template
    ? `<div class="section-title">&#9878;&#65039; Legal request template (Section 91 BNSS)</div>
       <div class="legal-template">${nl2br(d.legal_request_template)}</div>`
    : "";

  const html = `<!doctype html><html><head><meta charset="utf-8" />
  <title>Dossier ${esc(d.dossier_id)}</title>
  <style>
    @page { margin: 20mm; }
    * { box-sizing: border-box; }
    body {
      font-family: "Segoe UI", "Nirmala UI", "Noto Sans Devanagari", Arial, sans-serif;
      color: #111; line-height: 1.5; font-size: 12px; margin: 0;
    }
    h1 { font-size: 20px; margin: 0 0 2px; }
    .sub { color: #555; font-size: 11px; margin-bottom: 16px; }
    .id { font-family: monospace; }
    .band { display: inline-block; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px; }
    .CRITICAL { background: #fde2e2; color: #b42318; }
    .HIGH { background: #fef0d3; color: #b45309; }
    .MEDIUM { background: #fdf7cf; color: #92700a; }
    .LOW { background: #d8f5e3; color: #067647; }
    .section-title { font-size: 13px; font-weight: 700; margin: 22px 0 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
    table { border-collapse: collapse; width: 100%; font-size: 11px; }
    .meta td { padding: 3px 8px 3px 0; }
    .meta td.k { color: #555; width: 160px; }
    .linked th, .linked td { border: 1px solid #ccc; padding: 5px 8px; text-align: left; }
    .ev { border: 1px solid #ddd; border-radius: 6px; padding: 10px 12px; margin-bottom: 10px; page-break-inside: avoid; }
    .ev-head { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 6px; }
    .ev-n { font-weight: 700; }
    .ev-prob { color: #555; }
    .ev-text { font-size: 13px; margin-bottom: 6px; }
    .tag { background: #eef; color: #334; padding: 1px 6px; border-radius: 4px; font-size: 10px; }
    .ev-hash { font-family: monospace; font-size: 9.5px; color: #666; word-break: break-all; margin-top: 6px; }
    .cert { border: 1px solid #ccc; border-left: 3px solid #b45309; border-radius: 6px; padding: 12px 14px; font-size: 11px; color: #333; background: #fafafa; }
    .meta-note { font-size: 10.5px; color: #444; border-left: 3px solid #6366f1; padding: 6px 10px; margin: 6px 0 10px; background: #f8f7ff; border-radius: 0 4px 4px 0; }
    .legal-template { border: 1.5px solid #b45309; border-radius: 6px; padding: 14px 16px; font-size: 10.5px; color: #222; background: #fffbf5; white-space: pre-wrap; font-family: "Courier New", monospace; line-height: 1.8; }
    .muted { color: #777; }
    .foot { margin-top: 24px; font-size: 10px; color: #888; border-top: 1px solid #eee; padding-top: 8px; }
    @media print { .noprint { display: none; } }
    .noprint { position: fixed; top: 12px; right: 12px; }
    .noprint button { font-size: 13px; padding: 8px 14px; cursor: pointer; }
  </style></head><body>
    <div class="noprint"><button onclick="window.print()">Print / Save as PDF</button></div>
    <h1>NarcoScope AI — Evidence Dossier</h1>
    <div class="sub">Dossier ID <span class="id">${esc(d.dossier_id)}</span> · generated ${esc(generated)}</div>

    <div class="section-title">Subject account</div>
    <table class="meta">
      <tr><td class="k">Handle</td><td><b>${esc(a.handle)}</b></td></tr>
      <tr><td class="k">Platform</td><td>${esc(a.platform)} (${esc(a.account_type)})</td></tr>
      <tr><td class="k">Risk</td><td><span class="band ${esc(a.risk_band)}">${esc(a.risk_band)}</span> &nbsp; score ${a.risk_score}</td></tr>
      <tr><td class="k">Automated (bot)</td><td>${a.is_probable_bot ? "Likely" : "No"}</td></tr>
      <tr><td class="k">Flagged messages</td><td>${a.flagged_message_count} of ${a.total_messages_seen}</td></tr>
      <tr><td class="k">Ingestion source</td><td>${esc(a.source)}</td></tr>
    </table>

    <div class="section-title">Key evidence (${d.evidence.length})</div>
    ${evidenceRows || '<p class="muted">No individually flagged messages.</p>'}

    <div class="section-title">Cross-platform links (shared payment handle)</div>
    ${linkedRows}

    ${triangulationSection}

    ${legalSection}

    <div class="section-title">Integrity &amp; legal note</div>
    <div class="cert">${esc(d.certificate)}</div>

    <div class="foot">NarcoScope AI · prototype · Generated for analyst review — verify hashes and certify under Section 63 BSA, 2023 before evidentiary use.</div>
  </body></html>`;

  const w = window.open("", "_blank", "width=820,height=900");
  if (!w) {
    alert("Popup blocked — allow popups for this site to generate the dossier.");
    return;
  }
  w.document.write(html);
  w.document.close();
  w.focus();
  setTimeout(() => w.print(), 400);
}
