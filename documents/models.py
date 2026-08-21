"""Document upload and verification models."""
import uuid

from django.db import models

from accounts.models import StudentProfile, User
from internships.models import Internship
from .validators import validate_file_extension, validate_file_size


def document_upload_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"documents/{instance.student.student_id}/{uuid.uuid4().hex}.{ext}"


class DocumentType(models.TextChoices):
    OFFER_LETTER = "OFFER_LETTER", "Offer Letter"
    JOINING_LETTER = "JOINING_LETTER", "Joining Letter"
    ID_PROOF = "ID_PROOF", "ID Proof"
    INTERNSHIP_AGREEMENT = "INTERNSHIP_AGREEMENT", "Internship Agreement"
    COMPLETION_LETTER = "COMPLETION_LETTER", "Completion Letter"
    OTHER = "OTHER", "Other"


class DocumentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CHANGES_REQUESTED = "CHANGES_REQUESTED", "Changes Requested"


class Document(models.Model):
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="documents"
    )
    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(max_length=40, choices=DocumentType.choices)
    title = models.CharField(max_length=200)
    file = models.FileField(
        upload_to=document_upload_path,
        validators=[validate_file_extension, validate_file_size],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.PENDING, db_index=True
    )
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_documents"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.title} ({self.student.full_name})"
