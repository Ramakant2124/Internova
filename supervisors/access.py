"""Supervisor template access control.

The Supervisor Template/View lives inside the Company Dashboard architecture.
It can be entered two ways:

1. A company user verifies a supervisor's PIN from the company dashboard
   (``companies:attendance``), which stores ``active_supervisor_id`` in the
   session.
2. A supervisor logs in directly with their own account.

In both cases every supervisor-template URL carries the supervisor ``pk`` and
is authorized by :func:`get_supervisor_context`, which guarantees that a
verified supervisor only ever sees their own assigned interns.
"""
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect

from internships.models import CompanySupervisor

SESSION_KEY = "active_supervisor_id"


def current_supervisor(request):
    """Resolve the supervisor currently active in the request, if any."""
    user = request.user
    if not user.is_authenticated:
        return None
    if user.role == "SUPERVISOR":
        try:
            return user.supervisor_profile
        except CompanySupervisor.DoesNotExist:
            return None
    if user.role == "COMPANY":
        sup_id = request.session.get(SESSION_KEY)
        if not sup_id:
            return None
        return user.company_profile.supervisors.filter(
            pk=sup_id, is_active=True
        ).first()
    return None


def get_supervisor_context(request, pk):
    """Return the supervisor for ``pk`` if the user may act for them."""
    user = request.user
    if not user.is_authenticated:
        return redirect("accounts:login_choice")
    supervisor = get_object_or_404(CompanySupervisor, pk=pk)
    if user.role == "SUPERVISOR":
        try:
            own_profile = user.supervisor_profile
        except CompanySupervisor.DoesNotExist:
            raise PermissionDenied
        if own_profile.pk != pk:
            raise PermissionDenied
        return supervisor
    if user.role == "COMPANY":
        if (
            request.session.get(SESSION_KEY) != pk
            or supervisor.company_id != user.company_profile.pk
            or not supervisor.is_active
        ):
            raise PermissionDenied
        return supervisor
    raise PermissionDenied


def supervisor_template_required(view_func):
    """Decorator requiring access to the supervisor template for URL ``pk``.

    The wrapped view receives ``(request, supervisor, ...)``.
    """

    @wraps(view_func)
    def _wrapped(request, pk, *args, **kwargs):
        supervisor = get_supervisor_context(request, pk)
        if isinstance(supervisor, HttpResponseRedirect):
            return supervisor
        return view_func(request, supervisor, *args, **kwargs)

    return _wrapped
