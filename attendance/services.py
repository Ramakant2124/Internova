"""Attendance calculations and rules."""
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from notifications.services import create_notification

from .models import Attendance, AttendanceStatus


def working_days(start, end):
    """Return all weekday dates (Mon-Fri) between start and end inclusive."""
    days = []
    day = start
    while day <= end:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    return days


def _active_allocation(student, internship):
    return student.allocations.filter(internship=internship, status="ACTIVE").first()


def attendance_summary(student, internship=None):
    """Compute attendance statistics for a student/internship.

    Returns a dict with total_working_days, present, half, leave, absent and
    percentage (present-equivalent / working days * 100).
    """
    records = Attendance.objects.filter(student=student)
    if internship is not None:
        records = records.filter(internship=internship)

    allocation = None
    if internship is not None:
        allocation = _active_allocation(student, internship)

    if internship is None and not records.exists():
        return {
            "total_working_days": 0, "present": 0, "half": 0,
            "leave": 0, "absent": 0, "percentage": 0.0, "irregular": False,
        }

    if allocation is None and internship is not None:
        return {
            "total_working_days": 0, "present": 0, "half": 0,
            "leave": 0, "absent": 0, "percentage": 0.0, "irregular": False,
        }

    start = None
    end = timezone.localdate()
    if internship is not None:
        start = allocation.start_date or allocation.internship.start_date or allocation.allocation_date
        end = min(end, allocation.end_date or end)
    else:
        first = records.order_by("date").first()
        start = first.date if first else end

    total = len(working_days(start, end)) if start else 0
    present = records.filter(status=AttendanceStatus.PRESENT).count()
    half = records.filter(status=AttendanceStatus.HALF_DAY).count()
    leave = records.filter(status=AttendanceStatus.LEAVE).count()
    recorded_absent = records.filter(status=AttendanceStatus.ABSENT).count()

    recorded_days = records.filter(date__range=(start, end)).count()
    missing = max(0, total - recorded_days)
    absent = recorded_absent + missing

    present_equiv = present + 0.5 * half
    percentage = round((present_equiv / total * 100), 1) if total else 0.0
    irregular = total > 0 and percentage < settings.ATTENDANCE_WARNING_THRESHOLD

    return {
        "total_working_days": total,
        "present": present,
        "half": half,
        "leave": leave,
        "absent": absent,
        "percentage": percentage,
        "irregular": irregular,
    }


def mark_attendance(student, internship, date, status, remarks="", check_in=None,
                    check_out=None, marked_by=None, supervisor=None):
    """Record attendance. Duplicate records for the same student/internship/day raise."""
    existing = Attendance.objects.filter(student=student, internship=internship, date=date).first()
    if existing:
        raise ValidationError(f"Attendance for {date} is already recorded.")
    return Attendance.objects.create(
        student=student,
        internship=internship,
        date=date,
        status=status,
        remarks=remarks,
        check_in=check_in,
        check_out=check_out,
        marked_by=marked_by,
        supervisor=supervisor,
    )


def student_check_in(student, internship):
    """Self check-in for today."""
    today = timezone.localdate()
    record, created = Attendance.objects.get_or_create(
        student=student,
        internship=internship,
        date=today,
        defaults={"status": AttendanceStatus.PRESENT, "check_in": timezone.localtime().time()},
    )
    if not created:
        if record.check_in:
            raise ValidationError("You have already checked in today.")
        record.check_in = timezone.localtime().time()
        record.status = AttendanceStatus.PRESENT
        record.save(update_fields=["check_in", "status", "updated_at"])
    return record


def student_check_out(student, internship):
    """Self check-out for today."""
    today = timezone.localdate()
    record = Attendance.objects.filter(
        student=student, internship=internship, date=today
    ).first()
    if not record:
        raise ValidationError("Check in first before checking out.")
    record.check_out = timezone.localtime().time()
    record.save(update_fields=["check_out", "updated_at"])
    return record


def monthly_counts(student, internship, year, month):
    records = Attendance.objects.filter(
        student=student, internship=internship, date__year=year, date__month=month
    )
    return {
        "present": records.filter(status=AttendanceStatus.PRESENT).count(),
        "half": records.filter(status=AttendanceStatus.HALF_DAY).count(),
        "leave": records.filter(status=AttendanceStatus.LEAVE).count(),
        "absent": records.filter(status=AttendanceStatus.ABSENT).count(),
    }


def send_attendance_warnings():
    """Create notifications for students below the attendance threshold.

    Only when no warning notification exists for the student in the last week.
    """
    from internships.models import InternshipAllocation

    allocations = InternshipAllocation.objects.filter(
        status="ACTIVE"
    ).select_related("student", "internship")
    warnings = 0
    since = timezone.now() - timedelta(days=7)
    for allocation in allocations:
        summary = attendance_summary(allocation.student, allocation.internship)
        if not summary["irregular"]:
            continue
        already = allocation.student.user.notifications.filter(
            notification_type="ATTENDANCE_WARNING", created_at__gte=since
        ).exists()
        if already:
            continue
        create_notification(
            recipient=allocation.student.user,
            title="Attendance Warning",
            message=(
                f"Your attendance is {summary['percentage']}% for "
                f"'{allocation.internship.title}', below the "
                f"{settings.ATTENDANCE_WARNING_THRESHOLD:.0f}% threshold."
            ),
            notification_type="ATTENDANCE_WARNING",
            related_url="/student/attendance/",
        )
        warnings += 1
    return warnings
