"""Certificate business logic."""
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from notifications.services import create_notification
from progress.models import Approval

from .models import Certificate, CertificateStatus


def generate_certificate_number():
    """Generate a unique certificate number: INT-YYYY-XXXXXX."""
    year = timezone.localdate().year
    prefix = f"{settings.CERTIFICATE_PREFIX}-{year}-"
    last = (
        Certificate.objects.filter(certificate_number__startswith=prefix)
        .order_by("-certificate_number")
        .first()
    )
    if last:
        try:
            seq = int(last.certificate_number.rsplit("-", 1)[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:06d}"


def get_or_create_certificate(student, internship):
    certificate, created = Certificate.objects.get_or_create(
        student=student,
        internship=internship,
        defaults={"company": internship.company},
    )
    return certificate, created


@transaction.atomic
def upload_certificate(student, internship, cert_file, issue_date=None):
    """Upload (or replace) a certificate file for a student's internship."""
    from internships.models import InternshipStatus

    certificate, created = get_or_create_certificate(student, internship)
    certificate.company = internship.company
    certificate.certificate_file = cert_file
    certificate.issue_date = issue_date or timezone.localdate()
    certificate.start_date = internship.start_date
    certificate.end_date = internship.end_date
    certificate.verification_status = CertificateStatus.UPLOADED
    certificate.save()
    create_notification(
        recipient=student.user,
        title="Certificate Uploaded",
        message=f"A certificate for '{internship.title}' was uploaded.",
        notification_type="CERTIFICATE_VERIFICATION",
        related_url="/student/certificate/",
    )
    return certificate


@transaction.atomic
def request_verification(certificate, requested_by):
    """Submit a certificate for verification."""
    certificate.verification_status = CertificateStatus.PENDING_VERIFICATION
    certificate.save(update_fields=["verification_status", "updated_at"])
    approval = Approval.objects.create(
        content_object=certificate,
        approval_type=Approval.ApprovalType.CERTIFICATE,
        requested_by=requested_by,
    )
    college = certificate.student.college
    if college:
        create_notification(
            recipient=college.user,
            title="Certificate Verification Pending",
            message=f"Verify certificate {certificate.certificate_number} for {certificate.student.full_name}.",
            notification_type="CERTIFICATE_VERIFICATION",
            related_url="/college/certificates/",
        )
    return approval


@transaction.atomic
def verify_certificate(certificate, reviewer, approved, comments=""):
    """Approve or reject a certificate after verification."""
    certificate.verification_status = (
        CertificateStatus.VERIFIED if approved else CertificateStatus.REJECTED
    )
    certificate.verified_by = reviewer
    certificate.verification_date = timezone.now()
    certificate.verification_comments = comments
    certificate.save()

    approval = (
        Approval.objects.filter(
            content_type=ContentType.objects.get_for_model(certificate),
            object_id=certificate.pk,
            approval_type=Approval.ApprovalType.CERTIFICATE,
        )
        .order_by("-created_at")
        .first()
    )
    if approval:
        approval.status = (
            Approval.Status.APPROVED if approved else Approval.Status.REJECTED
        )
        approval.reviewed_by = reviewer
        approval.comments = comments
        approval.save()

    create_notification(
        recipient=certificate.student.user,
        title="Certificate " + ("Verified" if approved else "Rejected"),
        message=(
            f"Your certificate {certificate.certificate_number} was "
            + ("verified successfully." if approved else "rejected.")
            + (f" Comments: {comments}" if comments else "")
        ),
        notification_type="CERTIFICATE_VERIFICATION",
        related_url="/student/certificate/",
    )
    return certificate


def validate_certificate_number(number):
    """Used by the public verification page."""
    return Certificate.objects.filter(certificate_number=number).first()
