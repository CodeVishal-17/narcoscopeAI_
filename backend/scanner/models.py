from django.db import models


class ScanRun(models.Model):
    """One execution of the detection pipeline (analyze()) over a batch of accounts."""

    SOURCE_CHOICES = [
        ("sample", "Synthetic sample data"),
        ("upload", "Uploaded JSON file"),
        ("telegram", "Live Telegram scrape"),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    source_label = models.CharField(max_length=255, blank=True)
    accounts_analyzed = models.IntegerField(default=0)
    flagged_accounts = models.IntegerField(default=0)
    model_stages = models.JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"ScanRun #{self.pk} ({self.source}, {self.created_at:%Y-%m-%d %H:%M})"


class AccountRecord(models.Model):
    """One account's risk report from a given scan run."""

    scan_run = models.ForeignKey(ScanRun, related_name="accounts", on_delete=models.CASCADE)
    account_id = models.CharField(max_length=255)
    platform = models.CharField(max_length=30)
    handle = models.CharField(max_length=255)
    account_type = models.CharField(max_length=30)
    source = models.CharField(max_length=30)
    is_probable_bot = models.BooleanField(default=False)
    risk_score = models.FloatField()
    risk_band = models.CharField(max_length=10)
    flagged_message_count = models.IntegerField(default=0)
    total_messages_seen = models.IntegerField(default=0)
    features = models.JSONField(default=dict)
    evidence_sample = models.JSONField(default=list)
    message_verdicts = models.JSONField(default=list)

    class Meta:
        ordering = ["-risk_score"]
        indexes = [
            models.Index(fields=["scan_run", "risk_band"]),
            models.Index(fields=["scan_run", "platform"]),
        ]

    def __str__(self):
        return f"{self.platform}:{self.handle} ({self.risk_band})"


class LinkedCluster(models.Model):
    """Accounts across platforms sharing a payment handle, for one scan run."""

    scan_run = models.ForeignKey(ScanRun, related_name="clusters", on_delete=models.CASCADE)
    payment_handle = models.CharField(max_length=255)
    account_ids = models.JSONField(default=list)

    def __str__(self):
        return f"{self.payment_handle} -> {self.account_ids}"


class TelegramWatch(models.Model):
    """Watchlist of public Telegram channels/bots to re-scrape."""

    username = models.CharField(max_length=255, unique=True)
    label = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True)
    last_scanned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return self.username


class IngestJob(models.Model):
    """
    Tracks a background ingestion+analysis run (e.g. a live Telegram scrape),
    which can take longer than a single request should block for.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("done", "Done"),
        ("error", "Error"),
    ]

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    source = models.CharField(max_length=20, choices=ScanRun.SOURCE_CHOICES)
    targets = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    result_scan_run = models.ForeignKey(
        ScanRun, null=True, blank=True, on_delete=models.SET_NULL, related_name="jobs"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"IngestJob #{self.pk} ({self.status})"
