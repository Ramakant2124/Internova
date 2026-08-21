"""URLs for the college portal."""
from django.urls import path

from . import views

app_name = "college"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    # Students
    path("students/", views.students_list, name="students"),
    path("students/add/", views.student_add, name="student_add"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/edit/", views.student_edit, name="student_edit"),
    path(
        "students/<int:pk>/toggle/",
        views.student_toggle_active,
        name="student_toggle_active",
    ),
    path(
        "students/<int:pk>/password/",
        views.student_set_password,
        name="student_set_password",
    ),
    # Companies
    path("companies/", views.companies_list, name="companies"),
    path("companies/add/", views.company_add, name="company_add"),
    path("companies/<int:pk>/edit/", views.company_edit, name="company_edit"),
    path(
        "companies/<int:pk>/toggle/",
        views.company_toggle_active,
        name="company_toggle_active",
    ),
    # Internships
    path("internships/", views.internships_list, name="internships"),
    path("internships/add/", views.internship_add, name="internship_add"),
    path(
        "internships/<int:pk>/",
        views.internship_detail,
        name="internship_detail",
    ),
    path("internships/<int:pk>/edit/", views.internship_edit, name="internship_edit"),
    # Applications
    path("applications/", views.applications_list, name="applications"),
    path(
        "applications/<int:pk>/review/",
        views.application_review,
        name="application_review",
    ),
    # Allocations
    path("allocations/", views.allocations_list, name="allocations"),
    path("allocations/add/", views.allocation_create, name="allocation_create"),
    path(
        "allocations/<int:pk>/assign-faculty/",
        views.allocation_assign_faculty,
        name="allocation_assign_faculty",
    ),
    path(
        "allocations/<int:pk>/terminate/",
        views.allocation_terminate,
        name="allocation_terminate",
    ),
    # Faculty
    path("faculty/", views.faculty_list, name="faculty"),
    path("faculty/add/", views.faculty_add, name="faculty_add"),
    path("faculty/<int:pk>/edit/", views.faculty_edit, name="faculty_edit"),
    # Attendance
    path("attendance/", views.attendance_view, name="attendance"),
    # Progress reviews
    path("progress/", views.progress_reviews, name="progress"),
    path(
        "progress/<str:kind>/<int:pk>/review/",
        views.progress_review_action,
        name="progress_review_action",
    ),
    # Approvals
    path("approvals/", views.approvals_list, name="approvals"),
    path("approvals/<int:pk>/action/", views.approval_action, name="approval_action"),
    # Certificates
    path("certificates/", views.certificates_list, name="certificates"),
    path(
        "certificates/<int:pk>/verify/",
        views.certificate_verify_action,
        name="certificate_verify",
    ),
]
