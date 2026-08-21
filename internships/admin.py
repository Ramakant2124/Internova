"""Admin configuration for the internships application."""
from django.contrib import admin

from .models import (
    CompanySupervisor,
    FacultyAssignment,
    Internship,
    InternshipAllocation,
    InternshipApplication,
    InternshipStatusHistory,
)


class InternshipApplicationInline(admin.TabularInline):
    model = InternshipApplication
    extra = 0
    readonly_fields = ("applied_at",)


@admin.register(Internship)
class InternshipAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "internship_type", "stipend", "status", "start_date", "end_date")
    list_filter = ("status", "internship_type", "company")
    search_fields = ("title", "description", "company__company_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(InternshipApplication)
class InternshipApplicationAdmin(admin.ModelAdmin):
    list_display = ("student", "internship", "status", "applied_at")
    list_filter = ("status",)
    search_fields = ("student__full_name", "internship__title")
    readonly_fields = ("applied_at",)


@admin.register(InternshipAllocation)
class InternshipAllocationAdmin(admin.ModelAdmin):
    list_display = ("student", "internship", "status", "allocation_date", "start_date", "end_date")
    list_filter = ("status",)
    search_fields = ("student__full_name", "internship__title")


@admin.register(InternshipStatusHistory)
class InternshipStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("internship", "old_status", "new_status", "changed_by", "created_at")
    list_filter = ("old_status", "new_status")
    readonly_fields = ("created_at",)


@admin.register(FacultyAssignment)
class FacultyAssignmentAdmin(admin.ModelAdmin):
    list_display = ("faculty", "student", "internship", "active", "assigned_at")
    list_filter = ("active",)
    search_fields = ("faculty__full_name", "student__full_name")


@admin.register(CompanySupervisor)
class CompanySupervisorAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "designation", "email", "phone", "is_active")
    list_filter = ("is_active", "company")
    search_fields = ("name", "email")
