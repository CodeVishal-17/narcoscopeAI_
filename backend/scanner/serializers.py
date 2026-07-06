from rest_framework import serializers

from .models import AccountRecord, IngestJob, LinkedCluster, ScanRun, TelegramWatch


class AccountRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountRecord
        fields = [
            "id", "account_id", "platform", "handle", "account_type", "source",
            "is_probable_bot", "risk_score", "risk_band", "flagged_message_count",
            "total_messages_seen", "features", "evidence_sample", "message_verdicts",
        ]


class AccountRecordSummarySerializer(serializers.ModelSerializer):
    """Lighter payload for list views — no per-message verdicts."""

    class Meta:
        model = AccountRecord
        fields = [
            "id", "account_id", "platform", "handle", "account_type", "source",
            "is_probable_bot", "risk_score", "risk_band", "flagged_message_count",
            "total_messages_seen",
        ]


class LinkedClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkedCluster
        fields = ["id", "payment_handle", "account_ids"]


class ScanRunListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanRun
        fields = [
            "id", "created_at", "source", "source_label",
            "accounts_analyzed", "flagged_accounts", "model_stages",
        ]


class ScanRunDetailSerializer(serializers.ModelSerializer):
    accounts = AccountRecordSummarySerializer(many=True, read_only=True)
    clusters = LinkedClusterSerializer(many=True, read_only=True)

    class Meta:
        model = ScanRun
        fields = [
            "id", "created_at", "source", "source_label",
            "accounts_analyzed", "flagged_accounts", "model_stages",
            "accounts", "clusters",
        ]


class TelegramWatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramWatch
        fields = ["id", "username", "label", "active", "added_at", "last_scanned_at"]
        read_only_fields = ["added_at", "last_scanned_at"]


class IngestJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngestJob
        fields = [
            "id", "status", "source", "targets", "created_at",
            "finished_at", "error", "result_scan_run",
        ]
