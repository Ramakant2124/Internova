# internships module

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from notifications.models import Notification
from progress.models import Approval

from accounts.factories import (
    create_college,
    create_company,
    create_faculty,
    create_internship,
    create_student,
)
from internships.models import (
    AllocationStatus,
    ApplicationStatus,
    InternshipStatus,
)
from internships.services import (
    allocate_internship,
    apply_to_internship,
    approve_completion,
    assign_faculty,
    request_completion,
    review_application,
)


class InternshipLifecycleTest(TestCase):
    def setUp(self):
        self.college = create_college()
        self.company = create_company()
        self.faculty = create_faculty(self.college)
        self.student = create_student(self.college)
        self.internship = create_internship(self.company)
        self.today = timezone.localdate()

    def test_apply_creates_pending_application_and_approval(self):
        application = apply_to_internship(self.student, self.internship, "Let me in!")
        self.assertEqual(application.status, ApplicationStatus.PENDING)
        self.assertEqual(application.cover_letter, "Let me in!")
        self.assertTrue(
            Approval.objects.filter(
                content_type=ContentType.objects.get_for_model(application),
                object_id=application.pk,
                status=Approval.Status.PENDING,
            ).exists()
        )

    def test_duplicate_application_raises(self):
        apply_to_internship(self.student, self.internship)
        with self.assertRaises(ValidationError):
            apply_to_internship(self.student, self.internship)

    def test_review_application_approves(self):
        application = apply_to_internship(self.student, self.internship)
        review_application(application, True, self.college.user, "Welcome aboard.")
        application.refresh_from_db()
        self.assertEqual(application.status, ApplicationStatus.APPROVED)
        self.internship.refresh_from_db()
        self.assertEqual(self.internship.status, InternshipStatus.APPROVED)
        self.assertTrue(
            Notification.objects.filter(recipient=self.student.user).filter(
                notification_type="APPLICATION"
            ).exists()
        )

    def test_allocate_transitions_internship_and_blocks_second_allocation(self):
        allocate_internship(
            self.student, self.internship, self.college.user,
            self.today - timedelta(days=1), self.today + timedelta(days=60),
        )
        self.internship.refresh_from_db()
        self.assertEqual(self.internship.status, InternshipStatus.ALLOCATED)
        with self.assertRaises(ValidationError):
            allocate_internship(
                self.student, self.internship, self.college.user,
                self.today, self.today + timedelta(days=30),
            )

    def test_assign_faculty_creates_and_replaces_assignment(self):
        allocation = allocate_internship(
            self.student, self.internship, self.college.user,
            self.today, self.today + timedelta(days=30),
        )
        assign_faculty(self.faculty, self.student, self.internship, self.college.user)
        self.assertTrue(
            self.student.faculty_assignments.filter(
                internship=self.internship, active=True
            ).count()
            == 1
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student.user, notification_type="FACULTY_ASSIGNMENT"
            ).exists()
        )
        _ = allocation

    def test_request_completion_requires_active(self):
        allocate_internship(
            self.student, self.internship, self.college.user,
            self.today, self.today + timedelta(days=30),
        )
        with self.assertRaises(ValidationError):
            request_completion(
                self.student.allocations.get(),
                self.college.user,
                "Not active yet.",
            )

    def test_approve_completion_marks_internship_completed(self):
        self.internship.start_date = self.today - timedelta(days=30)
        self.internship.end_date = self.today - timedelta(days=1)
        self.internship.status = InternshipStatus.ACTIVE
        self.internship.save()
        allocation = allocate_internship(
            self.student, self.internship, self.college.user,
            self.internship.start_date, self.internship.end_date,
        )
        request_completion(allocation, self.company.user, "Done.")
        approve_completion(allocation, self.college.user, "Verified.")
        self.internship.refresh_from_db()
        allocation.refresh_from_db()
        self.assertEqual(self.internship.status, InternshipStatus.COMPLETED)
        self.assertEqual(allocation.status, AllocationStatus.COMPLETED)
