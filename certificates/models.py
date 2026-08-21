"""Internship certificate management."""
import uuid

from django.db import models

from accounts.models import CompanyProfile, StudentProfile, User
from internships.models import Internship
from .validators import validate_file_extension, validate_file_size


def certificate_upload_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"certificates/{instance.student.student_id}/{uuid.uuid4().hex}.{ext}"


class CertificateStatus(models.TextChoices):
    NOT_UPLOADED = "NOT_UPLOADED", "Not Uploaded"
    UPLOADED = "UPLOADED", "Uploaded"
    PENDING_VERIFICATION = "PENDING_VERIFICATION", "Pending Verification"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"


class Certificate(models.Model):
    certificate_number = models.CharField(max_length=30, unique=True, db_index=True, blank=True)
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="certificates"
    )
    company = models.ForeignKey(
        CompanyProfile, on_delete=models.CASCADE, related_name="certificates"
    )
    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="certificates"
    )
    issue_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    certificate_file = models.FileField(
        upload_to=certificate_upload_path,
        blank=True,
        validators=[validate_file_extension, validate_file_size],
    )
    verification_status = models.CharField(
        max_length=30,
        choices=CertificateStatus.choices,
        default=CertificateStatus.NOT_UPLOADED,
        db_index=True,
    )
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_certificates"
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    verification_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "internship"],
                name="unique_certificate_per_internship",
            )
        ]

    def __str__(self):
        return self.certificate_number or f"Certificate {self.pk}"

    def save(self, *args, **kwargs):
        if not self.certificate_number:
            from .services import generate_certificate_number

            self.certificate_number = generate_certificate_number()
        super().save(*args, **kwargs)
