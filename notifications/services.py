"""Notification creation helper."""
from .models import Notification, NotificationType


def create_notification(recipient, title, message="", notification_type=NotificationType.GENERAL, related_url=""):
    """Create a persistent notification for a user."""
    if recipient is None:
        return None
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        related_url=related_url or "",
    )


def unread_count(user):
    if not user or not user.is_authenticated:
        return 0
    return user.notifications.filter(is_read=False).count()
