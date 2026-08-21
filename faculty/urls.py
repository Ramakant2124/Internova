"""URLs for the faculty portal."""
from django.urls import path

from . import views

app_name = "faculty"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("students/", views.students_list, name="students"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/evaluate/", views.evaluation_create, name="evaluation_create"),
    path("students/<int:pk>/feedback/", views.feedback_create, name="feedback_create"),
    path("attendance/", views.attendance_view, name="attendance"),
    path("work-logs/", views.work_logs, name="work_logs"),
    path("work-logs/<int:pk>/review/", views.review_action, {"kind": "work"}, name="work_log_review"),
    path("weekly-progress/", views.weekly_progress, name="weekly_progress"),
    path("weekly-progress/<int:pk>/review/", views.review_action, {"kind": "weekly"}, name="weekly_review"),
    path("tasks/", views.tasks_view, name="tasks"),
    path("evaluations/", views.evaluations, name="evaluations"),
    path("feedback/", views.feedback_view, name="feedback"),
    path("certificates/", views.certificates_view, name="certificates"),
    path("certificates/<int:pk>/verify/", views.certificate_verify, name="certificate_verify"),
]
