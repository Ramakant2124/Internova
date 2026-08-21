"""Admin configuration for documents."""
from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "student", "internship", "document_type", "status", "uploaded_at")
    list_filter = ("document_type", "status")
    search_fields = ("title", "student__full_name")
    readonly_fields = ("uploaded_at", "created_at", "updated_at")
