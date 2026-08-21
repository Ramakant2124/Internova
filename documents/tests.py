# documents module

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse

from accounts.factories import (
    create_college,
    create_company,
    create_internship,
    create_student,
)
from documents.models import Document, DocumentStatus, DocumentType
from documents.validators import (
    validate_file_extension,
    validate_file_size,
)


class DocumentValidatorsTest(TestCase):
    def test_extension_allowed_for_pdf(self):
        validate_file_extension(ContentFile(b"x", name="file.pdf"))

    def test_extension_rejected_for_exe(self):
        with self.assertRaises(ValidationError):
            validate_file_extension(ContentFile(b"x", name="file.exe"))

    def test_oversize_rejected(self):
        big = ContentFile(b"x" * (6 * 1024 * 1024), name="big.pdf")
        with self.assertRaises(ValidationError):
            validate_file_size(big)


class DocumentModelTest(TestCase):
    def setUp(self):
        self.college = create_college()
        self.company = create_company()
        self.student = create_student(self.college)
        self.internship = create_internship(self.company)

    def test_document_created_and_owned(self):
        document = Document.objects.create(
            student=self.student, internship=self.internship,
            document_type=DocumentType.OFFER_LETTER,
            title="Offer Letter",
            file=ContentFile(b"%PDF-1.4 test", name="offer.pdf"),
        )
        self.assertEqual(document.status, DocumentStatus.PENDING)
        self.assertEqual(list(self.student.documents.all()), [document])

    def test_download_owner_allowed_other_student_denied(self):
        document = Document.objects.create(
            student=self.student, internship=self.internship,
            document_type=DocumentType.OFFER_LETTER,
            title="Offer Letter",
            file=ContentFile(b"%PDF-1.4 test", name="offer.pdf"),
        )
        url = reverse("documents:download", args=[document.pk])
        self.client.force_login(self.student.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        other = create_student(self.college, username="other_student")
        self.client.force_login(other.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
