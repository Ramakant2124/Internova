"""End-to-end verification of EVERY export/download feature in the project.

Covers:
- reports module exports (8 report types x CSV/XLSX/PDF x college/faculty/company)
- supervisor attendance report exports (all types x CSV/XLSX/PDF)
- per-student internship report exports (3 roles x 3 formats) incl. edge cases

Each generated file is validated: CSV is re-parsed with csv.reader, XLSX is
re-opened with openpyxl, PDF must start with the %PDF magic marker and be
non-trivial in size.
"""
import csv
from datetime import timedelta
from io import BytesIO, StringIO

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
from internships.services import allocate_internship, apply_to_internship, assign_faculty
from reports.views import REPORT_TYPES


def _make_allocation(student, college, company, internship, user):
    apply_to_internship(student, internship, "Please.")
    today = timezone.localdate()
    allocate_internship(
        student, internship, user, today - timedelta(days=10), today + timedelta(days=30),
    )


def _validate_csv(response):
    text = response.content.decode("utf-8-sig")
    rows = list(csv.reader(StringIO(text)))
    return rows


def _validate_xlsx(response):
    from openpyxl import load_workbook

    wb = load_workbook(BytesIO(response.content))
    return [
        [cell.value for cell in row]
        for sheet in wb.worksheets
        for row in sheet.iter_rows()
    ]


def _validate_pdf(response):
    content = response.content
    assert content[:4] == b"%PDF", "not a valid PDF stream"
    assert len(content) > 1000, "PDF suspiciously small"
    return True


class AllExportsBase(TestCase):
    """Rich dataset so every report type has real rows to export."""

    @classmethod
    def setUpTestData(cls):
        cls.college = create_college()
        cls.company = create_company()
        cls.faculty = create_faculty(cls.college)
        cls.supervisor = create_supervisor(cls.company)
        cls.student = create_student(cls.college)
        cls.internship = create_internship(
            cls.company, status="ACTIVE",
            start=timezone.localdate() - timedelta(days=30),
            end=timezone.localdate() + timedelta(days=60),
        )
        _make_allocation(cls.student, cls.college, cls.company, cls.internship, cls.college.user)
        assign_faculty(cls.faculty, cls.student, cls.internship, cls.college.user)

        from internships.models import SupervisorAssignment
        SupervisorAssignment.objects.create(
            supervisor=cls.supervisor, student=cls.student,
            internship=cls.internship, assigned_by=cls.company.user,
        )

        # Weekly progress + work logs (with tricky characters + long text).
        from progress.models import DailyWorkLog, WeeklyProgress

        WeeklyProgress.objects.create(
            student=cls.student, internship=cls.internship,
            week_start=timezone.localdate() - timedelta(days=7),
            week_end=timezone.localdate(),
            summary='Built API with commas, "quotes" and\nmulti-line text',
            completed_tasks="Auth, payments",
            challenges="None",
            learnings="DRY principles",
            next_week_plan="Testing",
            progress_percentage=55,
            status="APPROVED",
        )
        DailyWorkLog.objects.create(
            student=cls.student, internship=cls.internship,
            date=timezone.localdate() - timedelta(days=1),
            work_description=("Long description: " + "x" * 3000),
            hours_worked=7, tasks_completed="Issue #12, #13",
            challenges='"Flaky" tests', learning_skills="pytest",
            status="APPROVED",
        )
        DailyWorkLog.objects.create(
            student=cls.student, internship=cls.internship,
            date=timezone.localdate(),
            work_description="Normal day", hours_worked=8,
        )

        # Attendance rows for the supervisor reports.
        from attendance.models import Attendance

        now_time = timezone.localtime().time()
        Attendance.objects.create(
            student=cls.student, internship=cls.internship,
            date=timezone.localdate(), status="PRESENT",
            check_in=now_time, check_out=now_time,
            marked_by=cls.supervisor.user, supervisor=cls.supervisor,
        )
        Attendance.objects.create(
            student=cls.student, internship=cls.internship,
            date=timezone.localdate() - timedelta(days=1), status="ABSENT",
            marked_by=cls.supervisor.user, supervisor=cls.supervisor,
        )

        # Certificate + task + feedback so those report types have rows.
        from progress.models import Feedback
        from tasks.models import Task, TaskStatus

        Task.objects.create(
            title="Build feature", student=cls.student,
            internship=cls.internship, assigned_by=cls.company.user,
            supervisor=cls.supervisor, status=TaskStatus.SUBMITTED,
            progress_percentage=80,
        )
        Feedback.objects.create(
            student=cls.student, internship=cls.internship,
            given_by=cls.company.user, feedback_type="COMPANY",
            rating=5, comments="Great work",
        )

        # A completed internship + certificate so the "completion" and
        # "certificates" report types have rows to export.
        cls.past_student = create_student(cls.college, username="past_student")
        past_internship = create_internship(
            cls.company, title="Past Intern", status="COMPLETED",
            start=timezone.localdate() - timedelta(days=120),
            end=timezone.localdate() - timedelta(days=30),
        )
        _make_allocation(
            cls.past_student, cls.college, cls.company, past_internship, cls.college.user,
        )
        from certificates.services import get_or_create_certificate

        get_or_create_certificate(cls.past_student, past_internship)


class ReportsModuleExportTest(AllExportsBase):
    """Every button on /reports/ home + report detail pages."""

    def test_all_report_types_all_formats_all_roles(self):
        roles = (
            ("college", self.college.user),
            ("faculty", self.faculty.user),
            ("company", self.company.user),
        )
        for namespace, user in roles:
            self.client.force_login(user)
            for report_type in REPORT_TYPES:
                for fmt in ("csv", "xlsx", "pdf"):
                    with self.subTest(role=namespace, report=report_type, fmt=fmt):
                        url = reverse("reports:report_export", args=[report_type, fmt])
                        response = self.client.get(url)
                        self.assertEqual(response.status_code, 200, url)
                        if fmt == "csv":
                            self.assertTrue(
                                response["Content-Type"].startswith("text/csv"))
                            rows = _validate_csv(response)
                            self.assertGreaterEqual(len(rows), 2)  # header + data
                        elif fmt == "xlsx":
                            self.assertIn("spreadsheetml", response["Content-Type"])
                            values = _validate_xlsx(response)
                            self.assertGreaterEqual(len(values), 2)
                        else:
                            self.assertEqual(response["Content-Type"], "application/pdf")
                            _validate_pdf(response)

    def test_reports_export_denied_for_student(self):
        self.client.force_login(self.student.user)
        response = self.client.get(reverse("reports:report_export", args=["students", "csv"]))
        self.assertEqual(response.status_code, 403)


class SupervisorAttendanceExportTest(AllExportsBase):
    """CSV/Excel/PDF buttons on the supervisor Attendance Reports page."""

    def test_all_attendance_report_types_all_formats(self):
        from attendance.reports import REPORT_TYPES as ATT_REPORT_TYPES

        self.client.force_login(self.supervisor.user)
        url = reverse(
            "supervisors:attendance_reports_export", args=[self.supervisor.pk]
        )
        for report_type in ATT_REPORT_TYPES:
            for fmt in ("csv", "xlsx", "pdf"):
                with self.subTest(report=report_type, fmt=fmt):
                    response = self.client.get(f"{url}?fmt={fmt}&report_type={report_type}")
                    self.assertEqual(response.status_code, 200)
                    if fmt == "csv":
                        rows = _validate_csv(response)
                        self.assertGreaterEqual(len(rows), 2)
                    elif fmt == "xlsx":
                        values = _validate_xlsx(response)
                        self.assertGreaterEqual(len(values), 2)
                    else:
                        _validate_pdf(response)

    def test_export_requires_supervisor_access(self):
        self.client.force_login(self.student.user)
        url = reverse(
            "supervisors:attendance_reports_export", args=[self.supervisor.pk]
        )
        response = self.client.get(f"{url}?fmt=csv&report_type=daily")
        self.assertIn(response.status_code, (302, 403))


class StudentExportEdgeCaseTest(AllExportsBase):
    """Per-student PDF/XLSX/CSV under awkward real-world conditions."""

    @staticmethod
    def _url(student, fmt):
        return reverse("reports:student_report_export", args=[student.pk, fmt])

    def setUp(self):
        self.client.force_login(self.college.user)

    def test_special_characters_in_name_and_text(self):
        from progress.models import DailyWorkLog, WeeklyProgress

        student = create_student(self.college, username="special_name_student")
        student.full_name = "Ana-María O'Brien Jr. (Intern)"
        student.save(update_fields=["full_name"])
        _make_allocation(student, self.college, self.company, self.internship, self.college.user)
        WeeklyProgress.objects.create(
            student=student, internship=self.internship,
            week_start=timezone.localdate() - timedelta(days=7),
            week_end=timezone.localdate(),
            summary='Commas, "quotes" & <tags> — em-dash ünïcödé',
            progress_percentage=40,
        )
        DailyWorkLog.objects.create(
            student=student, internship=self.internship,
            date=timezone.localdate(),
            work_description="line1\r\nline2\ttabbed, with, commas",
            hours_worked=5,
        )
        for fmt in ("csv", "xlsx", "pdf"):
            with self.subTest(fmt=fmt):
                response = self.client.get(self._url(student, fmt))
                self.assertEqual(response.status_code, 200, fmt)
                disposition = response["Content-Disposition"]
                self.assertIn("attachment; filename=", disposition)
                # Filename must stay ASCII-safe for headers.
                filename = disposition.split('filename="')[1].rstrip('"')
                filename.encode("ascii")
                if fmt == "csv":
                    rows = _validate_csv(response)
                    flat = "\n".join(",".join(r) for r in rows)
                    self.assertIn('Commas, "quotes"', flat)
                    self.assertIn("line1", flat)
                    self.assertIn("line2", flat)
                elif fmt == "xlsx":
                    values = _validate_xlsx(response)
                    joined = "\n".join(str(v) for v in values if v)
                    self.assertIn("Ana-María O'Brien Jr. (Intern)", joined)
                else:
                    _validate_pdf(response)

    def test_large_dataset_multi_page_pdf_and_big_xlsx(self):
        from progress.models import DailyWorkLog, WeeklyProgress

        student = create_student(self.college, username="bulk_student")
        _make_allocation(student, self.college, self.company, self.internship, self.college.user)
        start = timezone.localdate() - timedelta(days=180)
        DailyWorkLog.objects.bulk_create([
            DailyWorkLog(
                student=student, internship=self.internship,
                date=start + timedelta(days=i),
                work_description=f"Day {i}: " + "detail " * 40,
                hours_worked=(i % 9) + 1,
            )
            for i in range(120)
        ])
        WeeklyProgress.objects.bulk_create([
            WeeklyProgress(
                student=student, internship=self.internship,
                week_start=start + timedelta(days=7 * i),
                week_end=start + timedelta(days=7 * i + 6),
                summary=f"Week {i} summary " + "text " * 50,
                progress_percentage=(i % 100),
            )
            for i in range(25)
        ])
        csv_response = self.client.get(self._url(student, "csv"))
        rows = _validate_csv(csv_response)
        self.assertGreaterEqual(len(rows), 170)  # summary + 25 weekly + 120 worklogs
        xlsx_response = self.client.get(self._url(student, "xlsx"))
        values = _validate_xlsx(xlsx_response)
        self.assertGreater(len(values), 140)
        pdf_response = self.client.get(self._url(student, "pdf"))
        _validate_pdf(pdf_response)

    def test_null_and_optional_fields_render_placeholders(self):
        from progress.models import DailyWorkLog, WeeklyProgress

        student = create_student(self.college, username="sparse_student")
        _make_allocation(student, self.college, self.company, self.internship, self.college.user)
        WeeklyProgress.objects.create(
            student=student, internship=self.internship,
            week_start=timezone.localdate() - timedelta(days=7),
            week_end=timezone.localdate(),
        )
        DailyWorkLog.objects.create(
            student=student, internship=self.internship,
            date=timezone.localdate(), work_description="Only required field",
        )
        response = self.client.get(self._url(student, "csv"))
        rows = _validate_csv(response)
        flat = "\n".join(",".join(r) for r in rows)
        self.assertIn("Only required field", flat)
        self.assertNotIn("None", flat)

    def test_only_weekly_or_only_worklog_exports(self):
        from progress.models import DailyWorkLog, WeeklyProgress

        weekly_only = create_student(self.college, username="weekly_only")
        _make_allocation(weekly_only, self.college, self.company, self.internship, self.college.user)
        WeeklyProgress.objects.create(
            student=weekly_only, internship=self.internship,
            week_start=timezone.localdate() - timedelta(days=7),
            week_end=timezone.localdate(), summary="W", progress_percentage=10,
        )
        worklog_only = create_student(self.college, username="worklog_only")
        _make_allocation(worklog_only, self.college, self.company, self.internship, self.college.user)
        DailyWorkLog.objects.create(
            student=worklog_only, internship=self.internship,
            date=timezone.localdate(), work_description="D", hours_worked=4,
        )
        for student, absent_marker, present_row in (
            (weekly_only, "No daily worklog records found.", "W"),
            (worklog_only, "No weekly progress records found.", "D"),
        ):
            with self.subTest(student=student.user.username):
                response = self.client.get(self._url(student, "csv"))
                flat = "\n".join(",".join(r) for r in _validate_csv(response))
                self.assertIn(absent_marker, flat)
                self.assertIn(present_row, flat)

    def test_ajax_empty_data_returns_json_not_redirect(self):
        empty_student = create_student(self.college, username="empty_ajax")
        response = self.client.get(
            self._url(empty_student, "pdf"), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn(b"No report data available", response.content)

    def test_non_ajax_empty_data_still_redirects_with_message(self):
        empty_student = create_student(self.college, username="empty_plain")
        response = self.client.get(self._url(empty_student, "pdf"))
        self.assertEqual(response.status_code, 302)
