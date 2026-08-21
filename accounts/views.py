"""Views for authentication and account management."""
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
)
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from .decorators import get_role_dashboard_url, redirect_to_dashboard
from .forms import (
    CollegeAuthenticationForm,
    CompanyAuthenticationForm,
    FacultyAuthenticationForm,
    StudentAuthenticationForm,
    SupervisorAuthenticationForm,
)


def login_choice(request):
    """Landing page showing the four portal login options."""
    if request.user.is_authenticated:
        return redirect(get_role_dashboard_url(request.user))
    return render(request, "accounts/home.html")


class _RoleLoginView(LoginView):
    template_name = "accounts/login.html"
    form_class = None  # set per role
    portal_name = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["portal_name"] = self.portal_name
        return context

    def get_success_url(self):
        return get_role_dashboard_url(self.request.user)

    def form_valid(self, form):
        """Login the user and send to their own dashboard."""
        from django.contrib.auth import login

        login(self.request, form.get_user())
        return HttpResponseRedirect(self.get_success_url())


class StudentLoginView(_RoleLoginView):
    form_class = StudentAuthenticationForm
    portal_name = "Student Portal"


class CollegeLoginView(_RoleLoginView):
    form_class = CollegeAuthenticationForm
    portal_name = "College Training & Placement Portal"


class FacultyLoginView(_RoleLoginView):
    form_class = FacultyAuthenticationForm
    portal_name = "Faculty / Mentor Portal"


class CompanyLoginView(_RoleLoginView):
    form_class = CompanyAuthenticationForm
    portal_name = "Company Portal"


class SupervisorLoginView(_RoleLoginView):
    form_class = SupervisorAuthenticationForm
    portal_name = "Supervisor Portal"


class AppLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login_choice")


@require_POST
def force_logout(request):
    """Used by tests and multi-role edge cases; logs out the current user."""
    auth_logout(request)
    return HttpResponseRedirect(reverse_lazy("accounts:login_choice"))

def about(request):
    return render(request, "accounts/about.html")
