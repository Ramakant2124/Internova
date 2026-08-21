# faculty module

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.factories import (
    create_college,
    create_company,
    create_faculty,
    create_internship,
    create_student,
    create_supervisor,
)
from internships.services import allocate_internship, assign_faculty
from progress.models import DailyWorkLog, ReviewStatus
from tasks.models import Task, TaskStatus


class FacultyPortalTest(TestCase):
    def setUp(self):
        self.college = create_college()
        self.company = create_company()
        self.faculty = create_faculty(self.college)
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
        assign_faculty(self.faculty, self.student, self.internship, self.college.user)
        self.client.force_login(self.faculty.user)

    def test_dashboard_renders(self):
        response = self.client.get(reverse("faculty:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_attendance_is_view_only(self):
        response = self.client.get(reverse("faculty:attendance"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student Attendance")
        self.assertNotContains(response, "Mark Attendance")

    def test_tasks_page_is_view_only(self):
        supervisor = create_supervisor(self.company)
        Task.objects.create(
            title="Company task",
            description="Assigned by company.",
            student=self.student,
            internship=self.internship,
            assigned_by=self.company.user,
            supervisor=supervisor,
            status=TaskStatus.SUBMITTED,
            progress_percentage=60,
        )
        response = self.client.get(reverse("faculty:tasks"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Company task")
        self.assertContains(response, supervisor.name)
        self.assertContains(response, "60%")
        self.assertNotContains(response, 'name="decision"')
        self.assertNotContains(response, "Assign Task")

    def test_cannot_assign_task(self):
        url = f"/faculty/students/{self.student.pk}/assign-task/"
        response = self.client.post(
            url,
            {
                "title": "Blocked",
                "description": "Faculty cannot assign.",
                "due_date": (timezone.localdate() + timedelta(days=7)).isoformat(),
                "priority": "HIGH",
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Task.objects.filter(student=self.student).count(), 0)

    def test_cannot_review_any_task(self):
        task = Task.objects.create(
            title="Any task",
            student=self.student,
            internship=self.internship,
            assigned_by=self.faculty.user,
            status=TaskStatus.SUBMITTED,
        )
        response = self.client.post(
            f"/faculty/tasks/{task.pk}/review/",
            {"decision": "approve", "comments": "ok"},
        )
        self.assertEqual(response.status_code, 404)
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.SUBMITTED)

    def test_review_work_log(self):
        log = DailyWorkLog.objects.create(
            student=self.student, internship=self.internship,
            date=timezone.localdate(),
            work_description="Worked on UI.", hours_worked=7,
        )
        url = reverse("faculty:work_log_review", args=[log.pk])
        response = self.client.post(
            url, {"decision": ReviewStatus.APPROVED, "comments": "Good"}
        )
        self.assertRedirects(response, reverse("faculty:work_logs"))
        log.refresh_from_db()
        self.assertEqual(log.status, ReviewStatus.APPROVED)

    def test_faculty_cannot_review_unassigned_student(self):
        other = create_student(self.college, username="unassigned_student")
        log = DailyWorkLog.objects.create(
            student=other, internship=self.internship, date=timezone.localdate(),
            work_description="x", hours_worked=1,
        )
        url = reverse("faculty:work_log_review", args=[log.pk])
        response = self.client.post(url, {"decision": ReviewStatus.APPROVED})
        self.assertEqual(response.status_code, 403)
