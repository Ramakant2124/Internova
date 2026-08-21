# companies module

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.factories import (
    create_college,
    create_company,
    create_internship,
    create_student,
    create_supervisor,
)
from certificates.models import Certificate
from internships.models import CompanySupervisor, SupervisorAssignment
from internships.services import allocate_internship
from notifications.models import Notification
from progress.models import Approval
from tasks.models import Task, TaskStatus
from tasks.services import create_task


class CompanyPortalTest(TestCase):
    def setUp(self):
        self.college = create_college()
        self.company = create_company()
        self.student = create_student(self.college)
        self.internship = create_internship(self.company, status="ACTIVE")
        today = timezone.localdate()
        self.internship.start_date = today - timedelta(days=10)
        self.internship.end_date = today + timedelta(days=30)
        self.internship.save()
        self.allocation = allocate_internship(
            self.student, self.internship, self.college.user,
            self.internship.start_date, self.internship.end_date,
        )
        self.client.force_login(self.company.user)

    def test_dashboard_renders(self):
        self.assertEqual(
            self.client.get(reverse("companies:dashboard")).status_code, 200
        )

    def test_supervisor_add(self):
        response = self.client.post(
            reverse("companies:supervisor_add"),
            {"name": "Jane Doe", "designation": "Manager",
             "email": "jane@example.test", "phone": "1234567890"},
        )
        self.assertRedirects(response, reverse("companies:supervisors"))
        self.assertTrue(
            CompanySupervisor.objects.filter(company=self.company).count() == 1
        )

    def test_task_assign_requires_supervisor(self):
        supervisor = create_supervisor(self.company)
        url = reverse("companies:task_assign")
        response = self.client.post(
            url,
            {
                "student": str(self.student.pk),
                "supervisor": str(supervisor.pk),
                "title": "Write unit tests",
                "description": "Cover services.",
                "due_date": (timezone.localdate() + timedelta(days=5)).isoformat(),
                "priority": "MEDIUM",
            },
        )
        self.assertRedirects(response, reverse("companies:tasks"))
        task = Task.objects.get(student=self.student)
        self.assertEqual(task.supervisor, supervisor)
        self.assertTrue(
            SupervisorAssignment.objects.filter(
                supervisor=supervisor, student=self.student, active=True
            ).exists()
        )

    def test_task_cannot_be_assigned_without_supervisor(self):
        response = self.client.post(
            reverse("companies:task_assign"),
            {
                "student": str(self.student.pk),
                "title": "No supervisor task",
                "description": "Should be rejected.",
                "due_date": (timezone.localdate() + timedelta(days=5)).isoformat(),
                "priority": "MEDIUM",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.filter(student=self.student).count(), 0)

    def test_task_assign_rejects_other_company_supervisor(self):
        other_company = create_company(username="other_company2")
        other_supervisor = create_supervisor(other_company, username="other_sup")
        response = self.client.post(
            reverse("companies:task_assign"),
            {
                "student": str(self.student.pk),
                "supervisor": str(other_supervisor.pk),
                "title": "Bad supervisor task",
                "due_date": (timezone.localdate() + timedelta(days=5)).isoformat(),
                "priority": "MEDIUM",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.filter(student=self.student).count(), 0)

    def test_student_assign_supervisor(self):
        supervisor = create_supervisor(self.company)
        response = self.client.post(
            reverse("companies:student_assign_supervisor", args=[self.student.pk]),
            {"supervisor": str(supervisor.pk)},
        )
        self.assertRedirects(
            response, reverse("companies:student_detail", args=[self.student.pk])
        )
        self.assertTrue(
            SupervisorAssignment.objects.filter(
                supervisor=supervisor, student=self.student, active=True
            ).exists()
        )

    def test_attendance_select_renders(self):
        response = self.client.get(reverse("companies:attendance"))
        self.assertEqual(response.status_code, 200)

    def test_attendance_verify_rejects_wrong_pin(self):
        supervisor = create_supervisor(self.company)
        response = self.client.post(
            reverse("companies:attendance"),
            {"supervisor": str(supervisor.pk), "pin": "wrong-pin"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("active_supervisor_id", self.client.session)

    def test_attendance_verify_correct_pin_enters_supervisor_view(self):
        supervisor = create_supervisor(self.company)
        response = self.client.post(
            reverse("companies:attendance"),
            {"supervisor": str(supervisor.pk), "pin": "1234"},
        )
        self.assertRedirects(
            response, reverse("supervisors:students", args=[supervisor.pk])
        )
        self.assertEqual(self.client.session["active_supervisor_id"], supervisor.pk)

    def test_attendance_verify_rejects_other_company_supervisor(self):
        other_company = create_company(username="attendance_other_company")
        other_supervisor = create_supervisor(other_company, username="other_att_sup")
        response = self.client.post(
            reverse("companies:attendance"),
            {"supervisor": str(other_supervisor.pk), "pin": "1234"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("active_supervisor_id", self.client.session)

    def test_attendance_exit_clears_supervisor_session(self):
        supervisor = create_supervisor(self.company)
        session = self.client.session
        session["active_supervisor_id"] = supervisor.pk
        session.save()
        response = self.client.post(reverse("companies:attendance_exit"))
        self.assertRedirects(response, reverse("companies:dashboard"))
        self.assertNotIn("active_supervisor_id", self.client.session)

    def test_company_needs_pin_verification_for_supervisor_view(self):
        supervisor = create_supervisor(self.company)
        self.assertEqual(
            self.client.get(
                reverse("supervisors:students", args=[supervisor.pk])
            ).status_code,
            403,
        )

    def test_task_review(self):
        task = create_task(
            title="Fix login",
            description="Fix the login flow.",
            student=self.student, internship=self.internship,
            assigned_by=self.company.user,
        )
        task.status = TaskStatus.SUBMITTED
        task.save(update_fields=["status"])
        response = self.client.post(
            reverse("companies:task_review", args=[task.pk]),
            {"decision": "approve", "comments": "Nice."},
        )
        self.assertRedirects(response, reverse("companies:tasks"))
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.APPROVED)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student.user, notification_type="TASK_APPROVAL"
            ).exists()
        )

    def test_completion_request(self):
        self.internship.status = "ACTIVE"
        self.internship.save()
        response = self.client.post(
            reverse("companies:completion_request", args=[self.allocation.pk]),
            {"reason": "All work is done."},
        )
        self.assertRedirects(response, reverse("companies:completion"))
        self.assertTrue(
            Approval.objects.filter(
                content_type=ContentType.objects.get_for_model(self.allocation),
                object_id=self.allocation.pk,
                approval_type=Approval.ApprovalType.COMPLETION,
            ).exists()
        )

    def test_certificate_upload(self):
        url = reverse("companies:certificate_upload", args=[self.student.pk])
        response = self.client.post(
            url,
            {
                "certificate_file": ContentFile(b"%PDF-1.4 demo", name="c.pdf"),
                "issue_date": timezone.localdate().isoformat(),
            },
        )
        self.assertRedirects(response, reverse("companies:certificates"))
        self.assertEqual(
            Certificate.objects.filter(student=self.student).count(), 1
        )
