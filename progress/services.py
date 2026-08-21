"""Review/approval workflow helpers for work logs and weekly progress."""
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from notifications.services import create_notification

from .models import Approval, ReviewStatus


def _student_related_url(kind, pk):
    return f"/student/{kind}/{pk}/" if kind == "tasks" else f"/student/{kind}/"


def review_submission(obj, decision, reviewer, comments=""):
    """Approve/reject/request-changes for a DailyWorkLog or WeeklyProgress."""
    obj.status = decision
    obj.reviewed_by = reviewer
    obj.reviewed_at = timezone.now()
    obj.review_comments = comments
    obj.save()

    approval = Approval.objects.filter(
        content_type=ContentType.objects.get_for_model(obj),
        object_id=obj.pk,
    ).order_by("-created_at").first()
    if approval:
        approval.status = (
            Approval.Status.APPROVED if decision == ReviewStatus.APPROVED
            else Approval.Status.REJECTED
        )
        approval.reviewed_by = reviewer
        approval.comments = comments
        approval.save()

    kind = obj.__class__.__name__.lower()
    label = {
        "dailyworklog": "Your daily work log",
        "weeklyprogress": "Your weekly progress report",
    }.get(kind, "Your submission")

    status_text = {
        ReviewStatus.APPROVED: "approved",
        ReviewStatus.REJECTED: "rejected",
        ReviewStatus.CHANGES_REQUESTED: "marked as needing changes",
    }.get(decision, decision)

    reference = getattr(obj, "date", None) or obj.week_start
    create_notification(
        recipient=obj.student.user,
        title="Submission " + status_text.title(),
        message=f"{label} for {reference} was {status_text}."
        + (f" Comments: {comments}" if comments else ""),
        notification_type="PROGRESS_REVIEW",
        related_url="/student/work-logs/",
    )
    return obj


def review_document(obj, decision, reviewer, comments=""):
    """Approve/reject/request-changes for a Document."""
    from documents.models import DocumentStatus

    mapping = {
        ReviewStatus.APPROVED: DocumentStatus.APPROVED,
        ReviewStatus.REJECTED: DocumentStatus.REJECTED,
        ReviewStatus.CHANGES_REQUESTED: DocumentStatus.CHANGES_REQUESTED,
    }
    obj.status = mapping.get(decision, DocumentStatus.PENDING)
    obj.verified_by = reviewer
    obj.verified_at = timezone.now()
    obj.verification_comments = comments
    obj.save()

    approval = Approval.objects.filter(
        content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk
    ).order_by("-created_at").first()
    if approval:
        approval.status = (
            Approval.Status.APPROVED if obj.status == DocumentStatus.APPROVED
            else Approval.Status.REJECTED
        )
        approval.reviewed_by = reviewer
        approval.comments = comments
        approval.save()

    create_notification(
        recipient=obj.student.user,
        title="Document " + obj.get_status_display(),
        message=f"Your document '{obj.title}' was {obj.get_status_display().lower()}."
        + (f" Comments: {comments}" if comments else ""),
        notification_type="DOCUMENT_VERIFICATION",
        related_url="/student/documents/",
    )
    return obj
