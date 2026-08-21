# progress module

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from notifications.models import Notification

from accounts.factories import (
    create_college,
    create_company,
    create_faculty,
    create_internship,
    create_student,
)
from documents.models import Document, DocumentStatus
from internships.models import InternshipStatus
from internships.services import allocate_internship
from progress.models import (
    DailyWorkLog,
    ReviewStatus,
    WeeklyProgress,
)
from progress.services import review_document, review_submission


class ReviewSubmissionTest(TestCase):
    def setUp(self):
        self.college = create_college()
        self.company = create_company()
        self.faculty = create_faculty(self.college)
        self.student = create_student(self.college)
        self.internship = create_internship(self.company, status=InternshipStatus.ACTIVE)
        today = timezone.localdate()
        self.internship.start_date = today - timedelta(days=10)
        self.internship.end_date = today + timedelta(days=30)
        self.internship.save()
        self.allocation = allocate_internship(
            self.student, self.internship, self.college.user,
            self.internship.start_date, self.internship.end_date,
        )

    def test_review_work_log_approves_and_notifies(self):
        log = DailyWorkLog.objects.create(
            student=self.student, internship=self.internship, date=timezone.localdate(),
            work_description="Worked on module A", hours_worked=8,
        )
        review_submission(log, ReviewStatus.APPROVED, self.faculty.user, "Great job.")
        log.refresh_from_db()
        self.assertEqual(log.status, ReviewStatus.APPROVED)
        self.assertEqual(log.reviewed_by, self.faculty.user)
        self.assertIsNotNone(log.reviewed_at)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student.user, notification_type="PROGRESS_REVIEW"
            ).exists()
        )

    def test_review_weekly_progress_requests_changes(self):
        today = timezone.localdate()
        report = WeeklyProgress.objects.create(
            student=self.student, internship=self.internship,
            week_start=today - timedelta(days=7), week_end=today,
            summary="Week one", progress_percentage=40,
        )
        review_submission(report, ReviewStatus.CHANGES_REQUESTED, self.faculty.user, "Add more detail.")
        report.refresh_from_db()
        self.assertEqual(report.status, ReviewStatus.CHANGES_REQUESTED)


class ReviewDocumentTest(TestCase):
    def setUp(self):
        self.college = create_college()
        self.company = create_company()
        self.student = create_student(self.college)
        self.internship = create_internship(self.company)

    def test_review_document_updates_status(self):
        from django.core.files.base import ContentFile

        from documents.models import DocumentType

        document = Document.objects.create(
            student=self.student, internship=self.internship,
            document_type=DocumentType.OFFER_LETTER,
            title="Offer Letter",
            file=ContentFile(b"%PDF-1.4 test", name="test.pdf"),
        )
        review_document(document, ReviewStatus.APPROVED, self.college.user, "Looks good.")
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.APPROVED)
        self.assertEqual(document.verified_by, self.college.user)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student.user, notification_type="DOCUMENT_VERIFICATION"
            ).exists()
        )
