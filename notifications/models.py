"""Persistent in-app notifications."""
from django.db import models

from accounts.models import User


class NotificationType(models.TextChoices):
    ALLOCATION = "ALLOCATION", "Allocation"
    FACULTY_ASSIGNMENT = "FACULTY_ASSIGNMENT", "Faculty Assignment"
    TASK = "TASK", "Task"
    TASK_APPROVAL = "TASK_APPROVAL", "Task Approval"
    TASK_REJECTION = "TASK_REJECTION", "Task Rejection"
    PROGRESS_REVIEW = "PROGRESS_REVIEW", "Progress Review"
    ATTENDANCE_WARNING = "ATTENDANCE_WARNING", "Attendance Warning"
    DOCUMENT_VERIFICATION = "DOCUMENT_VERIFICATION", "Document Verification"
    CERTIFICATE_VERIFICATION = "CERTIFICATE_VERIFICATION", "Certificate Verification"
    INTERNSHIP_COMPLETION = "INTERNSHIP_COMPLETION", "Internship Completion"
    FEEDBACK = "FEEDBACK", "Feedback"
    PENDING_APPROVAL = "PENDING_APPROVAL", "Pending Approval"
    COMPLETION_APPROVAL = "COMPLETION_APPROVAL", "Completion Approval"
    APPLICATION = "APPLICATION", "Application"
    GENERAL = "GENERAL", "General"


class Notification(models.Model):
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    notification_type = models.CharField(
        max_length=40,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL,
    )
    is_read = models.BooleanField(default=False, db_index=True)
    related_url = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} -> {self.recipient.username}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=["is_read"])
