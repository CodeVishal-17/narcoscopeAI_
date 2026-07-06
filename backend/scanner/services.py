"""
Bridge between the narcoscope detection engine (repo_root/narcoscope) and the
Django ORM. This is the ONLY place that imports narcoscope — every view goes
through these functions so the engine stays a plain importable library, not
something rewritten inside Django.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from narcoscope.ingestion.file_ingestor import FileIngestor
from narcoscope.ingestion.telegram_ingestor import TelegramIngestor
from narcoscope.model.hybrid import HybridClassifier
from narcoscope.pipeline import analyze

from .models import AccountRecord, IngestJob, LinkedCluster, ScanRun, TelegramWatch


def _persist_analysis(output: dict, source: str, source_label: str) -> ScanRun:
    """Write an analyze() output dict into a new ScanRun + child rows."""
    with transaction.atomic():
        run = ScanRun.objects.create(
            source=source,
            source_label=source_label,
            accounts_analyzed=output["accounts_analyzed"],
            flagged_accounts=output["flagged_accounts"],
            model_stages=output["model_stages"],
        )
        AccountRecord.objects.bulk_create([
            AccountRecord(
                scan_run=run,
                account_id=r["account_id"],
                platform=r["platform"],
                handle=r["handle"],
                account_type=r["account_type"],
                source=r["source"],
                is_probable_bot=r["is_probable_bot"],
                risk_score=r["risk_score"],
                risk_band=r["risk_band"],
                flagged_message_count=r["flagged_message_count"],
                total_messages_seen=r["total_messages_seen"],
                features=r["features"],
                evidence_sample=r["evidence_sample"],
                message_verdicts=r["message_verdicts"],
            )
            for r in output["reports"]
        ])
        LinkedCluster.objects.bulk_create([
            LinkedCluster(scan_run=run, payment_handle=handle, account_ids=ids)
            for handle, ids in output["linked_account_clusters"].items()
        ])
    return run


def run_pipeline_on_accounts(accounts: list, source: str, source_label: str) -> ScanRun:
    """Run the hybrid classifier over already-fetched RawAccount objects and store it."""
    clf = HybridClassifier()
    output = analyze(accounts, clf)
    return _persist_analysis(output, source=source, source_label=source_label)


def run_sample_scan() -> ScanRun:
    from narcoscope.config import SAMPLE_DATA
    accounts = FileIngestor.load(SAMPLE_DATA)
    return run_pipeline_on_accounts(accounts, source="sample", source_label=str(SAMPLE_DATA))


def run_upload_scan(file_obj, filename: str) -> ScanRun:
    """
    Accepts either:
      * a JSON accounts file (Instagram exports, sample format), or
      * a raw WhatsApp "Export chat" .txt file — parsed by WhatsAppIngestor.
    WhatsApp groups are end-to-end encrypted with no API, so an exported chat
    from an investigator's own joined group is the only lawful ingestion path.
    """
    if filename.lower().endswith(".txt"):
        return _run_whatsapp_export(file_obj, filename)

    import json
    from narcoscope.ingestion.base import RawAccount

    raw = json.load(file_obj)
    if isinstance(raw, dict):
        raw = raw.get("accounts", [])
    accounts = [RawAccount.from_dict(a) for a in raw]
    return run_pipeline_on_accounts(accounts, source="upload", source_label=filename)


def _run_whatsapp_export(file_obj, filename: str) -> ScanRun:
    import os
    import tempfile
    from narcoscope.ingestion.whatsapp_ingestor import WhatsAppIngestor

    data = file_obj.read()
    if isinstance(data, bytes):
        data = data.decode("utf-8", errors="replace")

    tmp = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    try:
        tmp.write(data)
        tmp.close()
        accounts = WhatsAppIngestor().fetch([tmp.name])
    finally:
        os.unlink(tmp.name)

    # Use the original filename (minus .txt) as the group handle, not the temp name.
    group_name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if group_name.lower().endswith(".txt"):
        group_name = group_name[:-4]
    for a in accounts:
        a.handle = group_name

    return run_pipeline_on_accounts(accounts, source="upload", source_label=filename)


def run_telegram_scan(targets: list, limit: int = 200) -> ScanRun:
    """
    Blocking Telegram scrape + analysis. Only call this from a background
    thread (see run_telegram_job) — it can take tens of seconds per channel.
    """
    ingestor = TelegramIngestor()
    accounts = ingestor.fetch(targets, limit=limit)
    label = ", ".join(targets)
    run = run_pipeline_on_accounts(accounts, source="telegram", source_label=label)
    TelegramWatch.objects.filter(username__in=targets).update(last_scanned_at=timezone.now())
    return run


def run_telegram_job(job_id: int) -> None:
    """
    Worker function executed on a background thread by the API view. Keeping
    this synchronous-and-threaded (rather than adding Celery/Redis) matches
    the actual scale here — one investigator triggering occasional scrapes —
    without pulling in broker infrastructure the project doesn't otherwise need.
    """
    import traceback

    job = IngestJob.objects.get(pk=job_id)
    job.status = "running"
    job.save(update_fields=["status"])
    try:
        run = run_telegram_scan(job.targets)
        job.result_scan_run = run
        job.status = "done"
    except Exception:
        job.status = "error"
        job.error = traceback.format_exc(limit=5)
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "error", "finished_at", "result_scan_run"])


def telegram_health() -> dict:
    """Whether Telegram credentials + an authenticated session are present."""
    import os
    from pathlib import Path
    from narcoscope.config import TELEGRAM_SESSION

    has_creds = bool(os.getenv("TELEGRAM_API_ID") and os.getenv("TELEGRAM_API_HASH"))
    has_session = Path(f"{TELEGRAM_SESSION}.session").exists()
    return {
        "credentials_configured": has_creds,
        "session_ready": has_session,
        "ready": has_creds and has_session,
    }


def build_dossier(account) -> dict:
    """
    Assemble a court-oriented evidence dossier for one flagged account.

    Integrity is computed SERVER-SIDE: each captured message is hashed with
    SHA-256 over its exact UTF-8 bytes, so the dossier can assert the evidence
    has not been altered since capture — the spirit of a Section 65B(4)
    Bharatiya Sakshya Adhiniyam / IT Act electronic-evidence certificate. This
    packages evidence for an investigator; it is NOT itself a legal filing.
    """
    import hashlib
    from datetime import datetime, timezone

    from .models import LinkedCluster

    def _hash(text: str) -> str:
        return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

    evidence = [
        {
            "text": ev["text"],
            "sha256": _hash(ev["text"]),
            "final_prob": ev.get("final_prob"),
            "decided_by": ev.get("decided_by"),
            "matched_terms": ev.get("matched_terms", []),
            "matched_phrases": ev.get("matched_phrases", []),
        }
        for ev in account.evidence_sample
    ]

    # Cross-platform links (same payment handle) within this scan.
    linked = []
    same_ids = set()
    for c in LinkedCluster.objects.filter(scan_run=account.scan_run):
        if account.account_id in c.account_ids:
            for other in c.account_ids:
                if other != account.account_id:
                    same_ids.add((c.payment_handle, other))
    for handle, other_id in sorted(same_ids):
        match = account.scan_run.accounts.filter(account_id=other_id).first()
        linked.append({
            "payment_handle": handle,
            "account_id": other_id,
            "handle": match.handle if match else other_id,
            "platform": match.platform if match else "?",
        })

    generated_at = datetime.now(timezone.utc)
    dossier_id = f"NS-{account.scan_run_id}-{account.id}-{generated_at:%Y%m%d%H%M%S}"

    return {
        "dossier_id": dossier_id,
        "generated_at": generated_at.isoformat(),
        "account": {
            "handle": account.handle,
            "platform": account.platform,
            "account_type": account.account_type,
            "source": account.source,
            "risk_score": account.risk_score,
            "risk_band": account.risk_band,
            "is_probable_bot": account.is_probable_bot,
            "flagged_message_count": account.flagged_message_count,
            "total_messages_seen": account.total_messages_seen,
        },
        "evidence": evidence,
        "linked_accounts": linked,
        "certificate": (
            "This dossier was generated by NarcoScope AI from publicly accessible "
            "content. Each message below is accompanied by a SHA-256 hash computed "
            "over its exact captured text, so its integrity can be verified. No "
            "private data, IP address, phone number, or subscriber record has been "
            "extracted. Obtaining subscriber records requires lawful process "
            "(Section 91 BNSS/CrPC, or MLAT for foreign platforms). This document "
            "is investigative material for analyst review, not a legal filing, and "
            "must be certified by the investigating officer under Section 63 "
            "Bharatiya Sakshya Adhiniyam, 2023 (electronic records) before use as "
            "evidence."
        ),
    }


def model_metrics() -> dict:
    """Real held-out accuracy — same guardrails as narcoscope.evaluate."""
    from narcoscope.evaluate import metrics, MIN_RELIABLE_TEST, MIN_PER_CLASS
    from narcoscope.labeling import LabelStore
    from narcoscope.model.hybrid import HybridClassifier

    texts, labels = LabelStore().test_set()
    if not texts:
        return {
            "available": False,
            "reason": "No hand-labeled test data yet. Label messages via the "
                      "labeling tool, then retrain, to get a real accuracy number.",
        }

    clf = HybridClassifier()
    preds = [int(clf.classify_message(t).is_flagged) for t in texts]
    m = metrics(labels, preds)

    pos, neg = m["positives"], m["n"] - m["positives"]
    warnings = []
    if m["n"] < MIN_RELIABLE_TEST:
        warnings.append(
            f"Test set is small ({m['n']} < {MIN_RELIABLE_TEST}); indicative only."
        )
    if pos < MIN_PER_CLASS or neg < MIN_PER_CLASS:
        warnings.append(f"Class imbalance in test set (pos={pos}, neg={neg}).")

    return {"available": True, "reliable": not warnings, "warnings": warnings, **m}
