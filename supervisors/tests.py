# supervisors module - Supervisor Template/View tests

from datetime import timedelta

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
from attendance.models import Attendance
from internships.models import SupervisorAssignment
from internships.services import allocate_internship, assign_supervisor
from tasks.models import Task, TaskStatus


class SupervisorPortalBase(TestCase):
    def setUp(self):
        self.college = create_college()
        self.company = create_company()
        self.supervisor = create_supervisor(self.company)
        self.internship = create_internship(self.company, status="ACTIVE")
        today = timezone.localdate()
        self.internship.start_date = today - timedelta(days=5)
        self.internship.end_date = today + timedelta(days=30)
        self.internship.save()
        self.student = create_student(self.college)
        allocate_internship(
            self.student, self.internship, self.college.user,
            self.internship.start_date, self.internship.end_date,
        )
        assign_supervisor(
            self.supervisor, self.student, self.internship, self.company.user
        )

    def sup_url(self, name, *args):
        return reverse(name, args=[self.supervisor.pk, *args])


class SupervisorAccessTest(SupervisorPortalBase):
    def test_supervisor_can_access_own_template(self):
        self.client.force_login(self.supervisor.user)
        response = self.client.get(self.sup_url("supervisors:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_redirected_to_login(self):
        response = self.client.get(
            reverse("supervisors:dashboard", args=[self.supervisor.pk])
        )
        self.assertRedirects(
            response,
            reverse("accounts:login_choice"),
            fetch_redirect_response=False,
        )

    def test_supervisor_blocked_from_another_supervisor_view(self):
        other = create_supervisor(self.company, username="other_view_sup")
        self.client.force_login(self.supervisor.user)
        response = self.client.get(
            reverse("supervisors:dashboard", args=[other.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_company_without_pin_blocked_from_supervisor_view(self):
        self.client.force_login(self.company.user)
        response = self.client.get(
            reverse("supervisors:dashboard", args=[self.supervisor.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_company_with_verified_pin_can_access_supervisor_view(self):
        self.client.force_login(self.company.user)
        session = self.client.session
        session["active_supervisor_id"] = self.supervisor.pk
        session.save()
        response = self.client.get(self.sup_url("supervisors:students"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.full_name)

    def test_company_cannot_access_another_companys_supervisor(self):
        other_company = create_company(username="sup_other_company")
        other_supervisor = create_supervisor(other_company, username="sup_other_sup")
        self.client.force_login(self.company.user)
        session = self.client.session
        session["active_supervisor_id"] = other_supervisor.pk
        session.save()
        response = self.client.get(
            reverse("supervisors:dashboard", args=[other_supervisor.pk])
        )
        self.assertEqual(response.status_code, 403)


class SupervisorDashboardTest(SupervisorPortalBase):
    def test_dashboard_renders_with_assigned_interns(self):
        self.client.force_login(self.supervisor.user)
        response = self.client.get(self.sup_url("supervisors:dashboard"))
        self.assertEqual(response.status_code, 200)


class SupervisorStudentsTest(SupervisorPortalBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.supervisor.user)

    def test_students_list_shows_only_assigned(self):
        response = self.client.get(self.sup_url("supervisors:students"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.full_name)

    def test_unassigned_student_detail_denied(self):
        other = create_student(self.college, username="other_sup_student")
        response = self.client.get(
            self.sup_url("supervisors:student_detail", other.pk)
        )
        self.assertEqual(response.status_code, 403)

    def test_assigned_student_detail_renders(self):
        response = self.client.get(
            self.sup_url("supervisors:student_detail", self.student.pk)
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.full_name)


class SupervisorAttendanceTest(SupervisorPortalBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.supervisor.user)

    def test_attendance_view_renders(self):
        response = self.client.get(self.sup_url("supervisors:attendance"))
        self.assertEqual(response.status_code, 200)

    def test_attendance_mark_links_record_to_supervisor(self):
        response = self.client.post(
            self.sup_url("supervisors:attendance_mark"),
            {
                "student": str(self.student.pk),
                "date": timezone.localdate().isoformat(),
                "status": "PRESENT",
                "remarks": "On time",
            },
        )
        self.assertRedirects(response, self.sup_url("supervisors:attendance"))
        record = Attendance.objects.get(student=self.student)
        self.assertEqual(record.supervisor, self.supervisor)
        self.assertEqual(record.marked_by, self.supervisor.user)

    def test_attendance_mark_ignores_unassigned_student(self):
        other = create_student(self.college, username="other_att_student")
        response = self.client.post(
            self.sup_url("supervisors:attendance_mark"),
            {
                "student": str(other.pk),
                "date": timezone.localdate().isoformat(),
                "status": "PRESENT",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Attendance.objects.count(), 0)

    def test_attendance_view_excludes_unassigned_students(self):
        other = create_student(self.college, username="other_att_view")
        Attendance.objects.create(
            student=other, internship=self.internship, date=timezone.localdate(),
            status="PRESENT",
        )
        response = self.client.get(self.sup_url("supervisors:attendance"))
        self.assertNotContains(response, other.full_name)

    def test_attendance_analytics_renders(self):
        response = self.client.get(self.sup_url("supervisors:attendance_analytics"))
        self.assertEqual(response.status_code, 200)

    def test_attendance_reports_renders(self):
        response = self.client.get(self.sup_url("supervisors:attendance_reports"))
        self.assertEqual(response.status_code, 200)

    def test_attendance_report_export_csv(self):
        response = self.client.get(
            self.sup_url("supervisors:attendance_reports_export")
            + "?fmt=csv&report_type=daily"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")


class SupervisorTasksTest(SupervisorPortalBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.supervisor.user)

    def _task(self, status=TaskStatus.SUBMITTED):
        return Task.objects.create(
            title="Intern task",
            student=self.student,
            internship=self.internship,
            assigned_by=self.company.user,
            supervisor=self.supervisor,
            status=status,
            progress_percentage=50,
        )

    def test_tasks_view_renders_assigned_intern_tasks(self):
        task = self._task()
        response = self.client.get(self.sup_url("supervisors:tasks"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, task.title)

    def test_task_review_approves_assigned_intern_task(self):
        task = self._task()
        response = self.client.post(
            self.sup_url("supervisors:task_review", task.pk),
            {"decision": "approve", "comments": "Great work"},
        )
        self.assertRedirects(response, self.sup_url("supervisors:tasks"))
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.APPROVED)
        self.assertEqual(task.progress_percentage, 100)

    def test_task_review_denied_for_unassigned_intern_task(self):
        other = create_student(self.college, username="other_task_student")
        other_internship = create_internship(
            create_company(username="other_task_company"), status="ACTIVE"
        )
        task = Task.objects.create(
            title="Other task",
            student=other,
            internship=other_internship,
            assigned_by=other_internship.company.user,
            status=TaskStatus.SUBMITTED,
        )
        response = self.client.post(
            self.sup_url("supervisors:task_review", task.pk),
            {"decision": "approve"},
        )
        self.assertEqual(response.status_code, 403)
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.SUBMITTED)

    def test_supervisor_blocked_from_company_task_assignment(self):
        response = self.client.get(reverse("companies:task_assign"))
        self.assertEqual(response.status_code, 403)
