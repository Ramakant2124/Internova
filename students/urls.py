"""URLs for the student portal."""
from django.urls import path

from . import views

app_name = "students"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("internship/", views.internship_detail, name="internship"),
    path("company/", views.company_detail, name="company"),
    path("mentor/", views.mentor_detail, name="mentor"),
    path("mentor/select/", views.mentor_select, name="mentor_select"),
    path("attendance/", views.attendance_view, name="attendance"),
    path("attendance/check-in/", views.check_in, name="check_in"),
    path("attendance/check-out/", views.check_out, name="check_out"),
    path("work-logs/", views.work_logs, name="work_logs"),
    path("work-logs/<int:pk>/edit/", views.work_log_edit, name="work_log_edit"),
    path("weekly-progress/", views.weekly_progress_view, name="weekly_progress"),
    path(
        "weekly-progress/<int:pk>/edit/",
        views.weekly_progress_edit,
        name="weekly_progress_edit",
    ),
    path("tasks/", views.tasks_view, name="tasks"),
    path("tasks/<int:pk>/", views.task_detail, name="task_detail"),
    path("documents/", views.documents_view, name="documents"),
    path("documents/<int:pk>/delete/", views.document_delete, name="document_delete"),
    path("certificate/", views.certificate_view, name="certificate"),
    path("certificate/upload/", views.certificate_upload, name="certificate_upload"),
    path(
        "certificate/request-verification/",
        views.certificate_request_verification,
        name="certificate_request_verification",
    ),
    path("feedback/", views.feedback_view, name="feedback"),
    path("internships/", views.internships_available, name="internships_available"),
    path("notifications/", views.notifications_view, name="notifications"),
]
