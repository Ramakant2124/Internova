"""Supervisor Template/View URL patterns.

Mounted at ``/company/supervisor/`` inside the Company Dashboard. Every
pattern starts with the verified supervisor's ``pk``; access is enforced by
:func:`supervisors.access.supervisor_template_required`.
"""
from django.urls import path

from . import views

app_name = "supervisors"

urlpatterns = [
    path("<int:pk>/", views.dashboard, name="dashboard"),
    path("<int:pk>/students/", views.students_list, name="students"),
    path(
        "<int:pk>/students/<int:student_pk>/",
        views.student_detail,
        name="student_detail",
    ),
    path("<int:pk>/attendance/", views.attendance_view, name="attendance"),
    path(
        "<int:pk>/attendance/mark/", views.attendance_mark, name="attendance_mark"
    ),
    path(
        "<int:pk>/attendance/analytics/",
        views.attendance_analytics,
        name="attendance_analytics",
    ),
    path(
        "<int:pk>/attendance/reports/",
        views.attendance_reports,
        name="attendance_reports",
    ),
    path(
        "<int:pk>/attendance/reports/export/",
        views.attendance_report_export,
        name="attendance_reports_export",
    ),
    path("<int:pk>/tasks/", views.tasks_view, name="tasks"),
    path(
        "<int:pk>/tasks/<int:task_pk>/review/",
        views.task_review,
        name="task_review",
    ),
    path("<int:pk>/progress/", views.progress_view, name="progress"),
    path(
        "<int:pk>/notifications/",
        views.notifications_view,
        name="notifications",
    ),
]
