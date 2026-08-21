# attendance module

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from notifications.models import Notification

from accounts.factories import (
    create_college,
    create_company,
    create_internship,
    create_student,
)
from attendance.models import Attendance, AttendanceStatus
from attendance.services import (
    attendance_summary,
    mark_attendance,
    send_attendance_warnings,
    student_check_in,
    student_check_out,
    working_days,
)
from internships.services import allocate_internship


class WorkingDaysTest(TestCase):
    def test_working_days_skips_weekends(self):
        start = timezone.localdate() - timedelta(days=6)
        days = working_days(start, timezone.localdate())
        self.assertTrue(all(day.weekday() < 5 for day in days))


class MarkAttendanceTest(TestCase):
    def setUp(self):
        self.college = create_college()
        self.company = create_company()
        self.student = create_student(self.college)
        self.internship = create_internship(self.company, status="ACTIVE")
        today = timezone.localdate()
        self.internship.start_date = today - timedelta(days=10)
        self.internship.end_date = today + timedelta(days=10)
        self.internship.save()
        allocate_internship(
            self.student, self.internship, self.college.user,
            start_date=self.internship.start_date, end_date=self.internship.end_date,
        )

    def test_mark_attendance_then_duplicate_raises(self):
        today = timezone.localdate()
        mark_attendance(
            self.student, self.internship, today, AttendanceStatus.PRESENT
        )
        with self.assertRaises(ValidationError):
            mark_attendance(
                self.student, self.internship, today, AttendanceStatus.ABSENT
            )
        self.assertEqual(
            Attendance.objects.filter(student=self.student, date=today).count(), 1
        )

    def test_attendance_summary_percentage(self):
        today = timezone.localdate()
        for offset in range(10):
            day = today - timedelta(days=offset)
            if day.weekday() >= 5:
                continue
            status = AttendanceStatus.PRESENT if offset != 3 else AttendanceStatus.HALF_DAY
            mark_attendance(self.student, self.internship, day, status)
        summary = attendance_summary(self.student, self.internship)
        self.assertGreater(summary["total_working_days"], 0)
        self.assertAlmostEqual(
            summary["percentage"],
            round((summary["present"] + 0.5 * summary["half"])
                  / summary["total_working_days"] * 100, 1),
        )

    def test_check_in_out_flow(self):
        today = timezone.localdate()
        student_check_in(self.student, self.internship)
        record = Attendance.objects.get(student=self.student, date=today)
        self.assertEqual(record.status, AttendanceStatus.PRESENT)
        with self.assertRaises(ValidationError):
            student_check_in(self.student, self.internship)
        student_check_out(self.student, self.internship)
        record.refresh_from_db()
        self.assertIsNotNone(record.check_out)

    def test_check_out_without_check_in_raises(self):
        with self.assertRaises(ValidationError):
            student_check_out(self.student, self.internship)

    def test_send_attendance_warnings_creates_notification(self):
        today = timezone.localdate()
        for offset in range(12):
            day = today - timedelta(days=offset)
            if day.weekday() >= 5:
                continue
            status = (
                AttendanceStatus.PRESENT if offset % 2 == 0 else AttendanceStatus.ABSENT
            )
            mark_attendance(self.student, self.internship, day, status)
        summary = attendance_summary(self.student, self.internship)
        warnings = send_attendance_warnings()
        if summary["irregular"]:
            self.assertEqual(warnings, 1)
            self.assertTrue(
                Notification.objects.filter(
                    recipient=self.student.user,
                    notification_type="ATTENDANCE_WARNING",
                ).exists()
            )
            self.assertEqual(send_attendance_warnings(), 0)
        else:
            self.assertEqual(warnings, 0)
