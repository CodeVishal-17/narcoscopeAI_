from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"scans", views.ScanRunViewSet, basename="scan")
router.register(r"accounts", views.AccountRecordViewSet, basename="account")
router.register(r"watchlist", views.TelegramWatchViewSet, basename="watchlist")

urlpatterns = [
    path("", include(router.urls)),
    path("telegram/scan/", views.TelegramScanView.as_view(), name="telegram-scan"),
    path("telegram/health/", views.TelegramHealthView.as_view(), name="telegram-health"),
    path("jobs/<int:pk>/", views.IngestJobView.as_view(), name="ingest-job"),
    path("model/metrics/", views.ModelMetricsView.as_view(), name="model-metrics"),
]
