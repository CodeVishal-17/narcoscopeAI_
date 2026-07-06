"""
Web labeling UI (FastAPI) — fast, keyboard-driven hand-labeling at volume.

Labeling from the CLI works but is slow; collecting the few hundred real labels
you need for trustworthy accuracy goes much faster in a browser. This serves a
single-page UI that shows one message at a time with the model's current
prediction and rule evidence, and records your verdict (with provenance) through
the same leak-proof LabelStore the CLI uses.

Run:
    python -m narcoscope.labeling.server
    # then open http://127.0.0.1:8100

Message source (in priority order):
    --source path/to/accounts.json   CLI arg
    NARCOSCOPE_LABEL_SOURCE env var
    the bundled sample data (default)

Keyboard:  1 = drug-sale   0 = benign   S = skip   (also clickable buttons)
"""

from __future__ import annotations

import argparse
import os

from ..config import SAMPLE_DATA
from ..ingestion import FileIngestor
from ..labeling import LabelStore, split_of
from ..labeling.dataset import _key
from ..model.hybrid import HybridClassifier

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, JSONResponse
except ImportError as _e:  # pragma: no cover
    raise RuntimeError("FastAPI is required: pip install fastapi uvicorn") from _e


def _load_messages(source) -> list:
    accounts = FileIngestor.load(source)
    return [
        {"platform": acc.platform, "handle": acc.handle, "text": m.text}
        for acc in accounts for m in acc.messages
    ]


def create_app(source=None) -> "FastAPI":
    source = source or os.getenv("NARCOSCOPE_LABEL_SOURCE") or str(SAMPLE_DATA)
    messages = _load_messages(source)
    clf = HybridClassifier()
    store = LabelStore()

    app = FastAPI(title="NarcoScope Labeler")
    skipped: set = set()   # session-local: skipped this run, not persisted

    def _next_message():
        seen = store.labeled_keys()
        for msg in messages:
            k = _key(msg["text"])
            if k not in seen and k not in skipped:
                return msg
        return None

    @app.get("/", response_class=HTMLResponse)
    def index():
        return _PAGE

    @app.get("/api/next")
    def api_next():
        msg = _next_message()
        if msg is None:
            return JSONResponse({"done": True})
        v = clf.classify_message(msg["text"])
        return {
            "done": False,
            "text": msg["text"],
            "platform": msg["platform"],
            "handle": msg["handle"],
            "prediction": v.final_prob,
            "decided_by": v.decided_by,
            "split": split_of(msg["text"]),
            "evidence": {
                "terms": v.signals.matched_terms,
                "phrases": v.signals.matched_phrases,
                "emoji": v.signals.matched_emoji,
                "rule_score": v.signals.score,
            },
        }

    @app.post("/api/label")
    async def api_label(request: Request):
        body = await request.json()
        store.add(
            body["text"], int(body["label"]),
            platform=body.get("platform", ""), handle=body.get("handle", ""),
            labeled_by=body.get("by", "web"), source="web",
        )
        return {"ok": True}

    @app.post("/api/skip")
    async def api_skip(request: Request):
        body = await request.json()
        skipped.add(_key(body["text"]))
        return {"ok": True}

    @app.get("/api/stats")
    def api_stats():
        s = store.stats()
        acc = None
        test_texts, test_labels = store.test_set()
        if test_texts:
            preds = [int(clf.classify_message(t).is_flagged) for t in test_texts]
            correct = sum(1 for p, y in zip(preds, test_labels) if p == y)
            acc = {
                "n": len(test_labels),
                "accuracy": round(correct / len(test_labels), 3),
                "reliable": len(test_labels) >= 50,
            }
        remaining = sum(1 for m in messages if _key(m["text"]) not in store.labeled_keys())
        return {"stats": s, "test_accuracy": acc, "remaining": remaining,
                "source": os.path.basename(str(source))}

    return app


# --- single-page UI ---------------------------------------------------------
_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>NarcoScope Labeler</title>
<style>
  :root{--bg:#0a0d13;--panel:#111621;--border:#232b3a;--fg:#edeff4;
        --muted:#9aa4b5;--accent:#3b82f6;--pos:#e5484d;--neg:#4ade80;--mono:"IBM Plex Mono",monospace}
  *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--fg);
    font-family:system-ui,sans-serif;display:flex;flex-direction:column;
    align-items:center;padding:32px}
  h1{font-family:var(--mono);font-size:18px;letter-spacing:.02em}
  h1 span{color:var(--accent)}
  .card{background:var(--panel);border:1px solid var(--border);border-radius:12px;
    width:min(720px,92vw);padding:26px;margin-top:14px}
  .meta{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:16px;
    font-family:var(--mono);font-size:12px;color:var(--muted)}
  .chip{border:1px solid var(--border);border-radius:20px;padding:3px 10px}
  .chip.split-test{border-color:var(--accent);color:var(--accent)}
  .pred{margin-left:auto}
  .msg{font-size:18px;line-height:1.5;padding:18px;background:#0d1219;
    border-radius:8px;border:1px solid var(--border);white-space:pre-wrap;word-break:break-word}
  .ev{margin-top:12px;font-family:var(--mono);font-size:12px;color:var(--muted)}
  .btns{display:flex;gap:12px;margin-top:20px}
  button{flex:1;font-family:var(--mono);font-size:14px;padding:14px;border-radius:8px;
    border:1px solid var(--border);background:#0d1219;color:var(--fg);cursor:pointer}
  button.yes{border-color:var(--pos);color:var(--pos)}
  button.no{border-color:var(--neg);color:var(--neg)}
  button:hover{filter:brightness(1.3)}
  .kbd{font-size:11px;opacity:.6}
  .stats{width:min(720px,92vw);margin-top:16px;font-family:var(--mono);font-size:12px;
    color:var(--muted);display:flex;gap:18px;flex-wrap:wrap}
  .stats b{color:var(--fg)}
  .done{font-size:20px;color:var(--neg);padding:40px;text-align:center}
</style></head><body>
<h1>Narco<span>Scope</span> · Labeler</h1>
<div id="app" class="card"></div>
<div id="stats" class="stats"></div>
<script>
let cur=null;
async function load(){
  const r=await fetch('/api/next'); cur=await r.json();
  const app=document.getElementById('app');
  if(cur.done){app.innerHTML='<div class="done">All messages labeled 🎉</div>';refreshStats();return;}
  const ev=cur.evidence;
  const evtxt=[ev.terms.length?'terms: '+ev.terms.join(', '):'',
               ev.phrases.length?'phrases: '+ev.phrases.join(', '):'',
               ev.emoji.length?'emoji: '+ev.emoji.join(' '):'']
               .filter(Boolean).join('  ·  ')||'no rule signals';
  app.innerHTML=`
    <div class="meta">
      <span class="chip">${cur.platform} / ${cur.handle}</span>
      <span class="chip split-${cur.split}">${cur.split} split</span>
      <span class="pred">model: <b>${cur.prediction.toFixed(2)}</b> (${cur.decided_by})</span>
    </div>
    <div class="msg">${escapeHtml(cur.text)}</div>
    <div class="ev">rule score ${ev.rule_score} — ${evtxt}</div>
    <div class="btns">
      <button class="yes" onclick="label(1)">Drug-sale <span class="kbd">[1]</span></button>
      <button class="no" onclick="label(0)">Benign <span class="kbd">[0]</span></button>
      <button onclick="skip()">Skip <span class="kbd">[s]</span></button>
    </div>`;
  refreshStats();
}
async function label(l){
  if(!cur||cur.done)return;
  await fetch('/api/label',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:cur.text,label:l,platform:cur.platform,handle:cur.handle})});
  load();
}
async function skip(){
  if(!cur||cur.done)return;
  await fetch('/api/skip',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:cur.text})});
  load();
}
async function refreshStats(){
  const s=await (await fetch('/api/stats')).json();
  const a=s.test_accuracy;
  document.getElementById('stats').innerHTML=
    `source: <b>${s.source}</b>`+
    ` · labeled: <b>${s.stats.total}</b> (train ${s.stats.train.n} / test ${s.stats.test.n})`+
    ` · remaining: <b>${s.remaining}</b>`+
    (a?` · test accuracy: <b>${a.accuracy}</b> on ${a.n}`+(a.reliable?' ✓':' ⚠ (label more)'):' · no test labels yet');
}
function escapeHtml(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
document.addEventListener('keydown',e=>{
  if(e.key==='1')label(1); else if(e.key==='0')label(0);
  else if(e.key.toLowerCase()==='s')skip();
});
load();
</script></body></html>"""


app = create_app()


def main():
    ap = argparse.ArgumentParser(description="Run the NarcoScope web labeler.")
    ap.add_argument("--source", help="accounts JSON to label (default: sample data)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8100)
    args = ap.parse_args()

    import uvicorn
    uvicorn.run(create_app(args.source), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
