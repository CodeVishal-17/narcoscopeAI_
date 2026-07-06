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

from .models import AccountRecord, Alert, IngestJob, LinkedCluster, ScanRun, TelegramWatch


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
                extracted_metadata=r.get("extracted_metadata", {}),
            )
            for r in output["reports"]
        ])
        LinkedCluster.objects.bulk_create([
            LinkedCluster(scan_run=run, payment_handle=handle, account_ids=ids)
            for handle, ids in output["linked_account_clusters"].items()
        ])
        generate_alerts(run)
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


def generate_alerts(scan_run: ScanRun) -> list:
    """
    After a scan, generate Alert rows for every HIGH and CRITICAL account.
    Also does fuzzy cross-platform handle matching — if two accounts from
    different platforms have handles within edit-distance 2 (ignoring @,
    dots, underscores) they are flagged as potentially the same operator.
    """
    import difflib
    import re

    alerts = []
    high_accounts = scan_run.accounts.filter(risk_band__in=["HIGH", "CRITICAL"])

    for acc in high_accounts:
        severity = "critical" if acc.risk_band == "CRITICAL" else "high"
        msg = (
            f"{acc.risk_band} risk account detected: {acc.handle} on "
            f"{acc.platform}. Risk score: {acc.risk_score:.2f}. "
            f"{acc.flagged_message_count} flagged message(s) out of "
            f"{acc.total_messages_seen} analyzed."
        )
        if acc.is_probable_bot:
            msg += " Automated bot behaviour detected."
        alert = Alert.objects.create(
            severity=severity,
            account=acc,
            scan_run=scan_run,
            message=msg,
            platform=acc.platform,
            handle=acc.handle,
            risk_score=acc.risk_score,
        )
        alerts.append(alert)

    # Cross-platform fuzzy handle matching
    all_accounts = list(scan_run.accounts.all())

    def _normalize_handle(h: str) -> str:
        return re.sub(r'[@._\-\s]', '', h.lower())

    handles = [(acc, _normalize_handle(acc.handle)) for acc in all_accounts]
    flagged_pairs = set()

    for i, (acc_a, norm_a) in enumerate(handles):
        for j, (acc_b, norm_b) in enumerate(handles):
            if i >= j:
                continue
            if acc_a.platform == acc_b.platform:
                continue
            if not norm_a or not norm_b:
                continue
            ratio = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()
            if ratio >= 0.82:  # ~82% similarity => likely same operator
                pair_key = tuple(sorted([acc_a.id, acc_b.id]))
                if pair_key not in flagged_pairs:
                    flagged_pairs.add(pair_key)
                    msg = (
                        f"Cross-platform handle match: '{acc_a.handle}' ({acc_a.platform}) "
                        f"\u2248 '{acc_b.handle}' ({acc_b.platform}) \u2014 "
                        f"similarity {ratio:.0%}. Likely same operator."
                    )
                    # Attach to the higher-risk account
                    main = acc_a if acc_a.risk_score >= acc_b.risk_score else acc_b
                    severity = "critical" if main.risk_band == "CRITICAL" else "high"
                    if main.risk_band in ("HIGH", "CRITICAL"):
                        Alert.objects.create(
                            severity=severity,
                            account=main,
                            scan_run=scan_run,
                            message=msg,
                            platform=main.platform,
                            handle=f"{acc_a.handle} \u2248 {acc_b.handle}",
                            risk_score=max(acc_a.risk_score, acc_b.risk_score),
                        )

    return alerts


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

    # Extracted identifiers for triangulation
    meta = account.extracted_metadata or {}
    triangulation = {
        "mobile_numbers": meta.get("mobile_numbers", []),
        "emails": meta.get("emails", []),
        "upi_ids": meta.get("upi_ids", []),
        "telegram_links": meta.get("telegram_links", []),
        "instagram_links": meta.get("instagram_links", []),
        "whatsapp_links": meta.get("whatsapp_links", []),
        "crypto_addresses": meta.get("crypto_addresses", []),
        "note": (
            "These identifiers were extracted from publicly visible content only. "
            "IP addresses, phone numbers and email IDs registered with the platform "
            "are NOT accessible without lawful process. Use the legal request template "
            "below (Section 91 BNSS) to formally demand subscriber records from the platform."
        ),
    }

    # Pre-filled legal request template for the investigating officer
    platform_authority = {
        "telegram": "Telegram Messenger Inc. (support@telegram.org / law enforcement portal)",
        "instagram": "Meta Platforms Inc. (Indian LE portal: https://www.facebook.com/records)",
        "whatsapp": "WhatsApp LLC / Meta Platforms Inc. (Indian LE portal: https://www.facebook.com/records)",
    }.get(account.platform, f"{account.platform.title()} platform authority")

    legal_request_template = (
        f"PRODUCTION ORDER UNDER SECTION 91 BNSS (CrPC) / MLAT REQUEST\n\n"
        f"To: {platform_authority}\n\n"
        f"Subject: Request for subscriber records pertaining to account '{account.handle}' "
        f"on {account.platform.title()}\n\n"
        f"Dossier Reference: {dossier_id}\n"
        f"Generated by: NarcoScope AI (Anti-Narcotics OSINT System)\n"
        f"Generated at: {generated_at.strftime('%d %B %Y, %H:%M UTC')}\n\n"
        f"Pursuant to Section 91 of the Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS), "
        f"[and/or MLAT if foreign platform], you are requested to furnish the following "
        f"information relating to the above account, which has been flagged for suspected "
        f"drug trafficking activity (Risk Band: {account.risk_band}, Score: {account.risk_score:.2f}):\n\n"
        f"  1. Full legal name and registered address of the account holder\n"
        f"  2. Mobile number(s) and email ID(s) registered with the account\n"
        f"  3. IP addresses used at time of account creation and during the period "
        f"[INSERT DATE RANGE from evidence timestamps]\n"
        f"  4. Device identifiers (IMEI, MAC, user-agent) associated with the account\n"
        f"  5. Payment method details if any in-app transactions occurred\n\n"
        f"OSINT identifiers found in public content (for correlation):\n"
        f"  Mobile numbers: {', '.join(triangulation['mobile_numbers']) or 'None found in public content'}\n"
        f"  UPI/Payment IDs: {', '.join(triangulation['upi_ids']) or 'None found in public content'}\n"
        f"  Emails: {', '.join(triangulation['emails']) or 'None found in public content'}\n\n"
        f"This request is made in connection with investigation of offences under the "
        f"Narcotic Drugs and Psychotropic Substances (NDPS) Act, 1985.\n\n"
        f"Investigating Officer: ____________________\n"
        f"Rank / Station: ____________________\n"
        f"Date: {generated_at.strftime('%d/%m/%Y')}\n\n"
        f"[This template must be reviewed, signed, and submitted on official letterhead by "
        f"the investigating officer. This document is generated by NarcoScope AI for "
        f"investigative support only and is NOT itself a legal order.]"
    )

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
        "triangulation": triangulation,
        "legal_request_template": legal_request_template,
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


def list_alerts(status_filter: str | None = None, limit: int = 50) -> list:
    qs = Alert.objects.select_related("account", "scan_run")[:limit]
    if status_filter:
        qs = Alert.objects.filter(status=status_filter).select_related("account", "scan_run")[:limit]
    return list(qs)


def acknowledge_alert(alert_id: int) -> Alert:
    from django.utils import timezone
    alert = Alert.objects.get(pk=alert_id)
    alert.status = "acknowledged"
    alert.acknowledged_at = timezone.now()
    alert.save(update_fields=["status", "acknowledged_at"])
    return alert


def dismiss_alert(alert_id: int) -> Alert:
    alert = Alert.objects.get(pk=alert_id)
    alert.status = "dismissed"
    alert.save(update_fields=["status"])
    return alert
