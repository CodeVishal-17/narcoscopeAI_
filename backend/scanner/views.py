import threading

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import AccountRecord, IngestJob, ScanRun, TelegramWatch
from .serializers import (
    AccountRecordSerializer,
    IngestJobSerializer,
    ScanRunDetailSerializer,
    ScanRunListSerializer,
    TelegramWatchSerializer,
)


class ScanRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ScanRun.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return ScanRunListSerializer
        return ScanRunDetailSerializer

    @action(detail=False, methods=["get"])
    def latest(self, request):
        run = ScanRun.objects.first()
        if run is None:
            return Response(
                {"detail": "No scans yet. Run the sample scan or a Telegram scrape first."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ScanRunDetailSerializer(run).data)

    @action(detail=False, methods=["post"])
    def run_sample(self, request):
        run = services.run_sample_scan()
        return Response(ScanRunDetailSerializer(run).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "No file provided (field name: file)."},
                             status=status.HTTP_400_BAD_REQUEST)
        try:
            run = services.run_upload_scan(f, f.name)
        except Exception as exc:
            return Response({"detail": f"Could not process file: {exc}"},
                             status=status.HTTP_400_BAD_REQUEST)
        return Response(ScanRunDetailSerializer(run).data, status=status.HTTP_201_CREATED)


class AccountRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AccountRecord.objects.all()
    serializer_class = AccountRecordSerializer

    @action(detail=True, methods=["get"])
    def dossier(self, request, pk=None):
        return Response(services.build_dossier(self.get_object()))


class TelegramWatchViewSet(viewsets.ModelViewSet):
    queryset = TelegramWatch.objects.all()
    serializer_class = TelegramWatchSerializer


class TelegramScanView(APIView):
    """POST {"targets": ["@channel1", "@channel2"], "limit": 200} -> starts a background job."""

    def post(self, request):
        targets = request.data.get("targets") or []
        targets = [t.strip() for t in targets if t and t.strip()]
        if not targets:
            return Response({"detail": "Provide at least one channel/bot username."},
                             status=status.HTTP_400_BAD_REQUEST)

        health = services.telegram_health()
        if not health["ready"]:
            return Response(
                {
                    "detail": "Telegram is not connected yet. Run `python login_telegram.py` "
                              "once from the repo root with TELEGRAM_API_ID/HASH set.",
                    **health,
                },
                status=status.HTTP_409_CONFLICT,
            )

        job = IngestJob.objects.create(source="telegram", targets=targets)
        thread = threading.Thread(target=services.run_telegram_job, args=(job.id,), daemon=True)
        thread.start()
        return Response(IngestJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class IngestJobView(APIView):
    def get(self, request, pk):
        job = get_object_or_404(IngestJob, pk=pk)
        return Response(IngestJobSerializer(job).data)


class TelegramHealthView(APIView):
    def get(self, request):
        return Response(services.telegram_health())


class ModelMetricsView(APIView):
    def get(self, request):
        return Response(services.model_metrics())
