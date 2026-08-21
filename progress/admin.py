"""Admin configuration for the progress application."""
from django.contrib import admin

from .models import (
    Approval,
    DailyWorkLog,
    Feedback,
    PerformanceEvaluation,
    WeeklyProgress,
)


@admin.register(DailyWorkLog)
class DailyWorkLogAdmin(admin.ModelAdmin):
    list_display = ("student", "internship", "date", "hours_worked", "status", "reviewed_by")
    list_filter = ("status",)
    search_fields = ("student__full_name", "work_description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(WeeklyProgress)
class WeeklyProgressAdmin(admin.ModelAdmin):
    list_display = ("student", "internship", "week_start", "week_end", "progress_percentage", "status")
    list_filter = ("status",)
    search_fields = ("student__full_name", "summary")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PerformanceEvaluation)
class PerformanceEvaluationAdmin(admin.ModelAdmin):
    list_display = (
        "student", "internship", "faculty", "overall_performance", "created_at"
    )
    search_fields = ("student__full_name", "faculty__full_name")
    readonly_fields = ("overall_performance", "created_at", "updated_at")


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("student", "internship", "feedback_type", "rating", "given_by", "created_at")
    list_filter = ("feedback_type",)
    search_fields = ("student__full_name", "comments")


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = (
        "approval_type", "content_type", "object_id", "status",
        "requested_by", "reviewed_by", "created_at",
    )
    list_filter = ("approval_type", "status")
