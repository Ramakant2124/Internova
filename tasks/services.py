"""Task business logic."""
from django.db import transaction

from notifications.services import create_notification

from .models import Task, TaskStatus


def _task_url(task_id):
    return f"/student/tasks/{task_id}/"


def create_task(title, description, student, internship, assigned_by,
                start_date=None, due_date=None, priority=None, attachment=None,
                supervisor=None):
    """Create a task and notify the student."""
    task = Task.objects.create(
        title=title,
        description=description,
        student=student,
        internship=internship,
        assigned_by=assigned_by,
        supervisor=supervisor,
        start_date=start_date,
        due_date=due_date,
        priority=priority or "MEDIUM",
        attachment=attachment,
    )
    create_notification(
        recipient=student.user,
        title="New Task Assigned",
        message=f"A new task was assigned: '{task.title}'.",
        notification_type="TASK",
        related_url=f"/student/tasks/{task.pk}/",
    )
    return task


@transaction.atomic
def review_task(task, decision, reviewer, comments=""):
    """Approve or reject a submitted task and notify the student."""
    task.status = TaskStatus.APPROVED if decision else TaskStatus.REJECTED
    if decision:
        task.progress_percentage = 100
    task.save(update_fields=["status", "progress_percentage", "updated_at"])
    create_notification(
        recipient=task.student.user,
        title="Task " + ("Approved" if decision else "Rejected"),
        message=f"Task '{task.title}' was {('approved' if decision else 'rejected')}."
        + (f" Reason: {comments}" if comments else ""),
        notification_type="TASK_APPROVAL" if decision else "TASK_REJECTION",
        related_url=_task_url(task.pk),
    )
    return task
