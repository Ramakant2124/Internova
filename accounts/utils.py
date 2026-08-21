"""Small shared helpers used across role applications."""
from django.conf import settings
from django.core.paginator import Paginator


def paginate(request, queryset, per_page=None):
    """Return a Django ``Page`` object for the given queryset."""
    per_page = per_page or getattr(settings, "DEFAULT_PAGE_SIZE", 12)
    try:
        page_num = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        page_num = 1
    return Paginator(queryset, per_page).get_page(page_num)


def get_current_profile(user):
    """Return the role-specific profile of the user or None."""
    return user.get_profile() if user.is_authenticated else None
