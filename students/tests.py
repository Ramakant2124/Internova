# students module

from datetime import timedelta

from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.factories import (
    create_college,
    create_company,
    create_faculty,
    create_internship,
    create_student,
)
from certificates.models import Certificate
from documents.models import Document, DocumentType
from internships.models import FacultyAssignment
from internships.services import allocate_internship
from progress.models import DailyWorkLog


class StudentPortalTest(TestCase):
    def setUp(self):
        self.college = create_college()
        self.company = create_company()
        self.student = create_student(self.college)
        self.internship = create_internship(self.company, status="ACTIVE")
        today = timezone.localdate()
        self.internship.start_date = today - timedelta(days=5)
        self.internship.end_date = today + timedelta(days=30)
        self.internship.save()
        allocate_internship(
            self.student, self.internship, self.college.user,
            self.internship.start_date, self.internship.end_date,
        )
        self.client.force_login(self.student.user)

    def test_dashboard_requires_student(self):
        response = self.client.get(reverse("students:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_check_in_creates_attendance(self):
        response = self.client.post(reverse("students:check_in"))
        self.assertRedirects(response, reverse("students:attendance"))
        self.assertEqual(
            self.student.attendance.filter(date=timezone.localdate()).count(), 1
        )

    def test_check_out_requires_post(self):
        response = self.client.get(reverse("students:check_out"))
        self.assertEqual(response.status_code, 405)

    def test_work_log_post_creates_log(self):
        url = reverse("students:work_logs")
        response = self.client.post(
            url,
            {
                "date": timezone.localdate().isoformat(),
                "work_description": "Worked on the report.",
                "hours_worked": "6",
            },
        )
        self.assertRedirects(response, url)
        self.assertEqual(
            DailyWorkLog.objects.filter(student=self.student).count(), 1
        )

    def test_certificate_upload(self):
        url = reverse("students:certificate_upload")
        response = self.client.post(
            url,
            {
                "certificate_file": ContentFile(b"%PDF-1.4 demo", name="c.pdf"),
                "issue_date": timezone.localdate().isoformat(),
            },
        )
        self.assertRedirects(response, reverse("students:certificate"))
        self.assertEqual(
            Certificate.objects.filter(student=self.student).count(), 1
        )

    def test_document_delete_own_only(self):
        document = Document.objects.create(
            student=self.student, internship=self.internship,
            document_type=DocumentType.OFFER_LETTER,
            title="Offer Letter",
            file=ContentFile(b"%PDF-1.4 test", name="offer.pdf"),
        )
        url = reverse("students:document_delete", args=[document.pk])
        response = self.client.post(url)
        self.assertRedirects(response, reverse("students:documents"))
        self.assertFalse(Document.objects.filter(pk=document.pk).exists())

    def test_mentor_select_creates_assignment(self):
        faculty = create_faculty(self.college)
        response = self.client.post(
            reverse("students:mentor_select"), {"faculty": str(faculty.pk)}
        )
        self.assertRedirects(response, reverse("students:mentor"))
        self.assertTrue(
            FacultyAssignment.objects.filter(
                student=self.student, faculty=faculty, active=True
            ).exists()
        )

    def test_mentor_change_moves_assignment(self):
        first = create_faculty(self.college)
        second = create_faculty(self.college, username="faculty2")
        url = reverse("students:mentor_select")
        self.client.post(url, {"faculty": str(first.pk)})
        self.client.post(url, {"faculty": str(second.pk)})
        self.assertFalse(
            FacultyAssignment.objects.filter(
                student=self.student, faculty=first, active=True
            ).exists()
        )
        self.assertTrue(
            FacultyAssignment.objects.filter(
                student=self.student, faculty=second, active=True
            ).exists()
        )
        self.assertEqual(
            FacultyAssignment.objects.filter(
                student=self.student, active=True
            ).count(),
            1,
        )

    def test_mentor_select_other_college_denied(self):
        other_college = create_college(username="other_college")
        faculty = create_faculty(other_college, username="otherfaculty")
        response = self.client.post(
            reverse("students:mentor_select"), {"faculty": str(faculty.pk)}
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            FacultyAssignment.objects.filter(student=self.student).exists()
        )
