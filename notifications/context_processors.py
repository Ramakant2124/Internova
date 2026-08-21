"""Context processor exposing unread notification count and recent items."""
from .services import unread_count


def notification_context(request):
    if request.user.is_authenticated:
        recent = request.user.notifications.all()[:8]
        return {
            "unread_count": unread_count(request.user),
            "recent_notifications": recent,
        }
    return {"unread_count": 0, "recent_notifications": []}
