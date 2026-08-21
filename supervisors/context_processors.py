"""Context processor exposing the currently active supervisor to templates."""

from .access import current_supervisor


def active_supervisor(request):
    """Provide ``active_supervisor`` for sidebar/banner rendering.

    For a company user this is the PIN-verified supervisor stored in the
    session. For a supervisor user it is their own profile. Absent otherwise.
    """
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    return {"active_supervisor": current_supervisor(request)}
