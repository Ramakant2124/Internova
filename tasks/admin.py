"""Admin configuration for tasks."""
from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "student",
        "internship",
        "priority",
        "status",
        "progress_percentage",
        "due_date",
    )
    list_filter = ("status", "priority")
    search_fields = ("title", "description", "student__full_name")
    readonly_fields = ("created_at", "updated_at")
