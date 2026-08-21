"""Admin configuration for accounts."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    CollegeProfile,
    CompanyProfile,
    FacultyProfile,
    StudentProfile,
    User,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "is_active", "last_login", "date_joined")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Application", {"fields": ("role",)}),
    )


class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "student_id",
        "email",
        "department",
        "year",
        "semester",
        "college",
    )
    search_fields = ("full_name", "student_id", "email")
    list_filter = ("department", "year", "college")
    readonly_fields = ("created_at", "updated_at")


admin.site.register(StudentProfile, StudentProfileAdmin)


class CollegeProfileAdmin(admin.ModelAdmin):
    list_display = ("college_name", "college_code", "city", "state", "contact_email")
    search_fields = ("college_name", "college_code")
    readonly_fields = ("created_at", "updated_at")


admin.site.register(CollegeProfile, CollegeProfileAdmin)


class FacultyProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "employee_id", "department", "designation", "college")
    search_fields = ("full_name", "employee_id", "email")
    list_filter = ("department", "college")
    readonly_fields = ("created_at", "updated_at")


admin.site.register(FacultyProfile, FacultyProfileAdmin)


class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ("company_name", "company_code", "industry", "city", "state", "email")
    search_fields = ("company_name", "company_code", "industry")
    list_filter = ("industry", "city")
    readonly_fields = ("created_at", "updated_at")


admin.site.register(CompanyProfile, CompanyProfileAdmin)
