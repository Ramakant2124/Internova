"""Notification views shared by all roles."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from accounts.decorators import redirect_to_dashboard
from accounts.utils import paginate

from .models import Notification


@login_required
def notification_list(request):
    qs = request.user.notifications.all()
    notifications = paginate(request, qs, per_page=15)
    return render(
        request, "notifications/list.html", {"notifications": notifications}
    )


@require_POST
@login_required
def mark_read(request, pk):
    notification = get_object_or_404(
        request.user.notifications.all(), pk=pk
    )
    notification.mark_read()
    return redirect(notification.related_url or "notifications:list")


@require_POST
@login_required
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect("notifications:list")


@require_POST
@login_required
def clear_all(request):
    request.user.notifications.all().delete()
    messages.success(request, "Notifications cleared.")
    return redirect("notifications:list")
