"""Attendance admin."""
from django.contrib import admin

from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "internship", "date", "status", "check_in", "check_out")
    list_filter = ("status", "date")
    search_fields = ("student__full_name", "student__student_id", "internship__title")
    date_hierarchy = "date"
