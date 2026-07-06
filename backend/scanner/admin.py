from django.contrib import admin

from .models import AccountRecord, IngestJob, LinkedCluster, ScanRun, TelegramWatch


@admin.register(ScanRun)
class ScanRunAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "source", "source_label", "accounts_analyzed", "flagged_accounts")
    list_filter = ("source",)


@admin.register(AccountRecord)
class AccountRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "scan_run", "platform", "handle", "risk_band", "risk_score", "is_probable_bot")
    list_filter = ("platform", "risk_band")
    search_fields = ("handle", "account_id")


@admin.register(LinkedCluster)
class LinkedClusterAdmin(admin.ModelAdmin):
    list_display = ("id", "scan_run", "payment_handle", "account_ids")


@admin.register(TelegramWatch)
class TelegramWatchAdmin(admin.ModelAdmin):
    list_display = ("username", "label", "active", "added_at", "last_scanned_at")


@admin.register(IngestJob)
class IngestJobAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "source", "created_at", "finished_at", "result_scan_run")
    list_filter = ("status", "source")
