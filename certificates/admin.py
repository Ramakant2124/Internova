"""Admin configuration for certificates."""
from django.contrib import admin

from .models import Certificate


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = (
        "certificate_number", "student", "company", "internship",
        "verification_status", "issue_date",
    )
    list_filter = ("verification_status",)
    search_fields = ("certificate_number", "student__full_name", "company__company_name")
    readonly_fields = ("certificate_number", "created_at", "updated_at", "verification_date")
