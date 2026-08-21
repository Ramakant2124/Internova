"""Task management model."""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from accounts.models import StudentProfile, User
from internships.models import CompanySupervisor, Internship


class TaskPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class TaskStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    COMPLETED = "COMPLETED", "Completed"


class Task(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="tasks"
    )
    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="tasks"
    )
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tasks"
    )
    supervisor = models.ForeignKey(
        CompanySupervisor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    priority = models.CharField(
        max_length=20, choices=TaskPriority.choices, default=TaskPriority.MEDIUM, db_index=True
    )
    status = models.CharField(
        max_length=20, choices=TaskStatus.choices, default=TaskStatus.PENDING, db_index=True
    )
    progress_percentage = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(100), MinValueValidator(0)]
    )
    student_comments = models.TextField(blank=True)
    attachment = models.FileField(upload_to="task_attachments/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["student", "status", "due_date"])]

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        if not self.due_date:
            return False
        return self.due_date < timezone.localdate() and self.status not in (
            TaskStatus.APPROVED,
            TaskStatus.COMPLETED,
        )

    @property
    def status_color(self):
        if self.is_overdue:
            return "danger"
        return ""
