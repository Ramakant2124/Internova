"""Root URL configuration for the Internship Management System."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("student/", include("students.urls")),
    path("college/", include("college.urls")),
    path("faculty/", include("faculty.urls")),
    path("company/supervisor/", include("supervisors.urls")),
    path("company/", include("companies.urls")),
    path("certificates/", include("certificates.urls")),
    path("notifications/", include("notifications.urls")),
    path("documents/", include("documents.urls")),
    path("reports/", include("reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
