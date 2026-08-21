"""Secure, authorized file download for documents."""
import mimetypes

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404

from internships.models import FacultyAssignment, InternshipAllocation

from .models import Document


def _user_can_access(user, doc):
    if not user.is_authenticated:
        return False
    if doc.student.user_id == user.id:
        return True
    if user.role == "COLLEGE":
        return doc.student.college_id == user.college_profile.id
    if user.role == "FACULTY":
        return FacultyAssignment.objects.filter(
            faculty=user.faculty_profile, student=doc.student, active=True
        ).exists()
    if user.role == "COMPANY":
        return InternshipAllocation.objects.filter(
            internship__company=user.company_profile,
            student=doc.student,
        ).exists()
    return False


@login_required
def download_document(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    if not _user_can_access(request.user, doc):
        raise PermissionDenied
    return FileResponse(
        doc.file.open("rb"),
        as_attachment=False,
        content_type=mimetypes.guess_type(doc.file.name)[0] or "application/octet-stream",
    )
