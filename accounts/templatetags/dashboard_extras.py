"""Template filters and helpers for dashboards."""
from django import template

register = template.Library()

_BADGE_COLORS = {
    "ACTIVE": "success",
    "APPROVED": "success",
    "VERIFIED": "success",
    "COMPLETED": "success",
    "PRESENT": "success",
    "PAID": "success",
    "ALLOCATED": "info",
    "IN_PROGRESS": "info",
    "SUBMITTED": "info",
    "UPLOADED": "info",
    "IN_PROCESS": "info",
    "APPLIED": "warning",
    "PENDING": "warning",
    "CHANGES_REQUESTED": "warning",
    "PENDING_VERIFICATION": "warning",
    "HALF_DAY": "warning",
    "REJECTED": "danger",
    "ABSENT": "danger",
    "OVERDUE": "danger",
    "CRITICAL": "danger",
    "HIGH": "danger",
    "CANCELLED": "dark",
    "NOT_UPLOADED": "secondary",
    "LEAVE": "secondary",
    "LOW": "secondary",
    "MEDIUM": "primary",
    "ACTIVE_": "success",
}


@register.filter
def badge_class(value):
    """Map a status value to a Bootstrap 5 badge colour."""
    return _BADGE_COLORS.get(value, "secondary")


@register.filter
def status_label(value):
    """Human friendly label for a machine-readable status."""
    if not value:
        return "-"
    return value.replace("_", " ").title()


@register.filter
def subtract(value, arg):
    """Subtract arg from value (useful for progress bars)."""
    try:
        return value - arg
    except (TypeError, ValueError):
        return 0


@register.filter
def multiply(value, arg):
    try:
        return value * arg
    except (TypeError, ValueError):
        return 0


@register.filter
def divide(value, arg):
    try:
        if arg in (0, None):
            return 0
        return value / arg
    except (TypeError, ValueError):
        return 0


@register.filter
def query_string(request):
    """Serialize GET parameters (minus `page`) for pagination links."""
    parts = [f"{k}={v}" for k, v in request.GET.items() if k != "page"]
    return "&".join(parts)
