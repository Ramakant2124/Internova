# reports module

from datetime import timedelta

from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.factories import (
    create_college,
    create_company,
    create_faculty,
    create_internship,
    create_student,
)
from internships.services import allocate_internship, apply_to_internship, assign_faculty
from reports.views import REPORT_TYPES, get_report_rows


class ReportsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.college = create_college()
        self.company = create_company()
        self.faculty = create_faculty(self.college)
        self.student = create_student(self.college)
        self.internship = create_internship(self.company)
        self.today = timezone.localdate()
        apply_to_internship(self.student, self.internship, "Please.")
        allocate_internship(
            self.student, self.internship, self.college.user,
            self.today - timedelta(days=5), self.today + timedelta(days=20),
        )
        assign_faculty(self.faculty, self.student, self.internship, self.college.user)

    def test_all_report_types_build_rows(self):
        request = self.factory.get("/reports/")
        request.user = self.college.user
        for report_type in REPORT_TYPES:
            columns, rows = get_report_rows(report_type, request)
            self.assertTrue(columns)

    def test_company_scope_filters_rows(self):
        from progress.models import WeeklyProgress

        other_company = create_company(username="other_company")
        other_internship = create_internship(other_company)
        other_student = create_student(self.college, username="other_student")
        WeeklyProgress.objects.create(
            student=self.student, internship=self.internship,
            week_start=self.today - timedelta(days=6), week_end=self.today,
            summary="Mine", progress_percentage=60,
        )
        WeeklyProgress.objects.create(
            student=other_student, internship=other_internship,
            week_start=self.today - timedelta(days=6), week_end=self.today,
            summary="Theirs", progress_percentage=60,
        )
        request = self.factory.get("/reports/")
        request.user = self.company.user
        _, rows = get_report_rows("progress", request)
        self.assertTrue(any(row[0] == self.student.full_name for row in rows))
        self.assertFalse(any(row[0] == other_student.full_name for row in rows))

    def test_report_pages_require_role(self):
        self.client.force_login(self.college.user)
        for report_type in REPORT_TYPES:
            response = self.client.get(reverse("reports:report_detail", args=[report_type]))
            self.assertEqual(response.status_code, 200, report_type)

    def test_export_csv(self):
        self.client.force_login(self.college.user)
        response = self.client.get(
            reverse("reports:report_export", args=["students", "csv"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_export_xlsx(self):
        self.client.force_login(self.college.user)
        response = self.client.get(
            reverse("reports:report_export", args=["students", "xlsx"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_export_pdf(self):
        self.client.force_login(self.college.user)
        response = self.client.get(
            reverse("reports:report_export", args=["students", "pdf"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_unknown_report_type_404(self):
        self.client.force_login(self.college.user)
        response = self.client.get(reverse("reports:report_detail", args=["placement"]))
        self.assertEqual(response.status_code, 404)

    def test_students_denied_from_reports(self):
        self.client.force_login(self.student.user)
        response = self.client.get(reverse("reports:home"))
        self.assertEqual(response.status_code, 403)

    def test_weekly_progress_populates_progress_report(self):
        from progress.models import WeeklyProgress

        WeeklyProgress.objects.create(
            student=self.student, internship=self.internship,
            week_start=self.today - timedelta(days=6), week_end=self.today,
            summary="Week of work.", progress_percentage=50,
        )
        request = self.factory.get("/reports/")
        request.user = self.college.user
        _, rows = get_report_rows("progress", request)
        self.assertTrue(any(self.student.full_name in row for row in rows))
