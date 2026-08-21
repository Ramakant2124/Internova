"""Reusable role-based authorization helpers."""
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def role_required(*roles):
    """Decorator requiring an authenticated user with one of the given roles."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("accounts:login_choice")
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


student_required = role_required("STUDENT")
college_required = role_required("COLLEGE")
faculty_required = role_required("FACULTY")
company_required = role_required("COMPANY")
supervisor_required = role_required("SUPERVISOR")


class RoleRequiredMixin:
    """Mixin requiring a role; subclasses set ``roles``."""

    roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login_choice")
        if request.user.role not in self.roles:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class StudentRequiredMixin(RoleRequiredMixin):
    roles = ["STUDENT"]


class CollegeRequiredMixin(RoleRequiredMixin):
    roles = ["COLLEGE"]


class FacultyRequiredMixin(RoleRequiredMixin):
    roles = ["FACULTY"]


class CompanyRequiredMixin(RoleRequiredMixin):
    roles = ["COMPANY"]


class SupervisorRequiredMixin(RoleRequiredMixin):
    roles = ["SUPERVISOR"]


def redirect_to_dashboard(user):
    """Return the correct dashboard URL for the given user."""
    mapping = {
        "STUDENT": "students:dashboard",
        "COLLEGE": "college:dashboard",
        "FACULTY": "faculty:dashboard",
        "COMPANY": "companies:dashboard",
        "SUPERVISOR": "supervisors:dashboard",
    }
    return mapping.get(user.role, "accounts:login_choice")


def get_role_dashboard_url(user):
    """Return the correct dashboard URL (string) for the given user."""
    from django.urls import reverse

    if user.role == "SUPERVISOR":
        try:
            supervisor = user.supervisor_profile
        except Exception:
            supervisor = None
        if supervisor is not None:
            return reverse("supervisors:dashboard", args=[supervisor.pk])
        return reverse("accounts:login_choice")
    return reverse(redirect_to_dashboard(user))
