"""URLs for the company portal."""
from django.urls import path

from . import views

app_name = "companies"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    # Intern Attendance (Supervisor Template/View entry)
    path("attendance/", views.attendance_select, name="attendance"),
    path("attendance/exit/", views.attendance_exit, name="attendance_exit"),
    # Internships
    path("internships/", views.internships_list, name="internships"),
    path("internships/add/", views.internship_add, name="internship_add"),
    path("internships/<int:pk>/", views.internship_detail, name="internship_detail"),
    path("internships/<int:pk>/edit/", views.internship_edit, name="internship_edit"),
    # Students
    path("students/", views.students_list, name="students"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path(
        "students/<int:pk>/assign-supervisor/",
        views.student_assign_supervisor,
        name="student_assign_supervisor",
    ),
    path("students/<int:pk>/feedback/", views.feedback_create, name="feedback_create"),
    path("students/<int:pk>/certificate/", views.certificate_upload, name="certificate_upload"),
    # Tasks
    path("tasks/", views.tasks_view, name="tasks"),
    path("tasks/assign/", views.task_assign, name="task_assign"),
    path("tasks/<int:pk>/review/", views.task_review, name="task_review"),
    # Progress
    path("progress/", views.progress_view, name="progress"),
    path(
        "progress/<str:kind>/<int:pk>/review/",
        views.progress_review_action,
        name="progress_review_action",
    ),
    # Supervisors
    path("supervisors/", views.supervisors_view, name="supervisors"),
    path("supervisors/add/", views.supervisor_add, name="supervisor_add"),
    path("supervisors/<int:pk>/edit/", views.supervisor_edit, name="supervisor_edit"),
    # Feedback & completion
    path("feedback/", views.feedback_view, name="feedback"),
    path("completion/", views.completion_view, name="completion"),
    path(
        "completion/<int:pk>/request/",
        views.completion_request,
        name="completion_request",
    ),
    # Certificates
    path("certificates/", views.certificates_view, name="certificates"),

]
