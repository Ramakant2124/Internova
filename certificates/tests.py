# certificates module

from datetime import timedelta

from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.factories import (
    create_college,
    create_company,
    create_internship,
    create_student,
)
from certificates.models import Certificate, CertificateStatus
from certificates.services import (
    generate_certificate_number,
    request_verification,
    upload_certificate,
    verify_certificate,
)


class CertificateFlowTest(TestCase):
    def setUp(self):
        self.college = create_college()
        self.company = create_company()
        self.student = create_student(self.college)
        self.internship = create_internship(self.company, status="COMPLETED")

    def test_certificate_number_format_and_increment(self):
        first = generate_certificate_number()
        parts = first.split("-")
        self.assertEqual(parts[0], "INT")
        self.assertEqual(len(parts[-1]), 6)
        Certificate.objects.create(
            student=self.student, internship=self.internship,
            company=self.company, certificate_number=first,
        )
        second = generate_certificate_number()
        self.assertEqual(int(second.rsplit("-", 1)[-1]), int(first.rsplit("-", 1)[-1]) + 1)

    def test_upload_request_verify_flow(self):
        cert = upload_certificate(
            self.student, self.internship,
            ContentFile(b"%PDF-1.4 demo", name="cert.pdf"),
            issue_date=timezone.localdate(),
        )
        self.assertEqual(cert.verification_status, CertificateStatus.UPLOADED)
        self.assertEqual(cert.company, self.company)

        request_verification(cert, self.student.user)
        cert.refresh_from_db()
        self.assertEqual(cert.verification_status, CertificateStatus.PENDING_VERIFICATION)

        verify_certificate(cert, self.college.user, True, "Verified.")
        cert.refresh_from_db()
        self.assertEqual(cert.verification_status, CertificateStatus.VERIFIED)
        self.assertEqual(cert.verified_by, self.college.user)
        self.assertIsNotNone(cert.verification_date)

    def test_public_verify_page_renders_unknown_number(self):
        response = self.client.get(reverse("certificates:verify_page"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("certificates:verify_detail", args=["INT-2099-000001"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "INT-2099-000001")

    def test_public_verify_page_shows_verified_certificate(self):
        cert = upload_certificate(
            self.student, self.internship,
            ContentFile(b"%PDF-1.4 demo", name="cert.pdf"),
        )
        verify_certificate(cert, self.college.user, True)
        response = self.client.get(
            reverse("certificates:verify_detail", args=[cert.certificate_number])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, cert.student.full_name)
        self.assertContains(response, cert.company.company_name)
