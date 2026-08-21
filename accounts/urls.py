"""URL configuration for the accounts application."""
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.login_choice, name="login_choice"),
    path("home/", views.login_choice, name="home"),
    path(
        "login/",
        views.StudentLoginView.as_view(),
        name="login",
    ),
    path("student/login/", views.StudentLoginView.as_view(), name="student_login"),
    path("college/login/", views.CollegeLoginView.as_view(), name="college_login"),
    path("faculty/login/", views.FacultyLoginView.as_view(), name="faculty_login"),
    path("company/login/", views.CompanyLoginView.as_view(), name="company_login"),
    path("supervisor/login/", views.SupervisorLoginView.as_view(), name="supervisor_login"),
    path("logout/", views.AppLogoutView.as_view(), name="logout"),
    path("logout-force/", views.force_logout, name="force_logout"),
    # Password change
    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/password_change_form.html",
            success_url=reverse_lazy("accounts:password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="accounts/password_change_done.html"
        ),
        name="password_change_done",
    ),
    # Password reset
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/password_reset_email.html",
            subject_template_name="accounts/password_reset_subject.txt",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    path('about/', views.about, name='about'),
]


