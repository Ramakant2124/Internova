"""URLs for reports and analytics."""
from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.reports_home, name="home"),
    path("analytics/", views.analytics, name="analytics"),
    path("analytics/data/", views.analytics_data, name="analytics_data"),
    path("<str:report_type>/", views.report_view, name="report_detail"),
    path("<str:report_type>/export/<str:fmt>/", views.report_export, name="report_export"),
]
