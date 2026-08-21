"""Attendance analytics for supervisors and their assigned interns.

Built on the supervisor -> intern -> attendance record relationship so every
statistic is scoped to the verified supervisor's assigned interns only.
"""
from datetime import time, timedelta

from django.conf import settings
from django.db.models import Count, Q

from internships.models import SupervisorAssignment

from .models import Attendance, AttendanceStatus
from .services import working_days

LATE_THRESHOLD = time(9, 30)
CONSISTENT_ABSENCE_STREAK = 3


def _counts(records):
    return {
        "present": records.filter(status=AttendanceStatus.PRESENT).count(),
        "half": records.filter(status=AttendanceStatus.HALF_DAY).count(),
        "leave": records.filter(status=AttendanceStatus.LEAVE).count(),
        "absent": records.filter(status=AttendanceStatus.ABSENT).count(),
    }


def _date_range(internship, date_from, date_to):
    today = timezone_localdate()
    start = internship.start_date or today
    end = internship.end_date or today
    if date_from and date_from > start:
        start = date_from
    if date_to and date_to < end:
        end = date_to
    return start, end


def _present_equivalent(status):
    if status == AttendanceStatus.PRESENT:
        return 1.0
    if status == AttendanceStatus.HALF_DAY:
        return 0.5
    return 0.0


def timezone_localdate():
    from django.utils import timezone

    return timezone.localdate()


def intern_stats(supervisor, student_id=None, date_from=None, date_to=None):
    """Per-intern attendance statistics for the supervisor's assigned interns."""
    assignments = SupervisorAssignment.objects.filter(
        supervisor=supervisor, active=True
    ).select_related("student", "student__user", "internship")
    if student_id:
        assignments = assignments.filter(student_id=student_id)

    rows = []
    for a in assignments:
        start, end = _date_range(a.internship, date_from, date_to)
        if start > end:
            continue
        records = Attendance.objects.filter(
            student=a.student, internship=a.internship, date__range=(start, end)
        )
        total = len(working_days(start, end))
        counts = _counts(records)
        recorded_days = records.count()
        missing = max(0, total - recorded_days)
        absent = counts["absent"] + missing
        late = records.filter(
            check_in__gt=LATE_THRESHOLD, status=AttendanceStatus.PRESENT
        ).count()
        present_equiv = counts["present"] + 0.5 * counts["half"]
        percentage = round(present_equiv / total * 100, 1) if total else 0.0
        rows.append(
            {
                "student": a.student,
                "internship": a.internship,
                "start": start,
                "end": end,
                "total_working_days": total,
                "present": counts["present"],
                "half": counts["half"],
                "leave": counts["leave"],
                "absent": absent,
                "late": late,
                "present_equivalent": round(present_equiv, 1),
                "percentage": percentage,
                "irregular": (
                    total > 0
                    and percentage < settings.ATTENDANCE_WARNING_THRESHOLD
                ),
            }
        )
    return rows


def _records_for(supervisor, student_id=None, date_from=None, date_to=None):
    records = Attendance.objects.filter(supervisor=supervisor)
    if student_id:
        records = records.filter(student_id=student_id)
    if date_from:
        records = records.filter(date__gte=date_from)
    if date_to:
        records = records.filter(date__lte=date_to)
    return records


def _working_day_total(supervisor, student_id=None, date_from=None, date_to=None):
    assignments = SupervisorAssignment.objects.filter(
        supervisor=supervisor, active=True
    ).select_related("internship")
    if student_id:
        assignments = assignments.filter(student_id=student_id)
    total = 0
    for a in assignments:
        start, end = _date_range(a.internship, date_from, date_to)
        if start <= end:
            total += len(working_days(start, end))
    return total


def _grouped(records, *group_fields):
    groups = {
        "present": Count("id", filter=Q(status=AttendanceStatus.PRESENT)),
        "half": Count("id", filter=Q(status=AttendanceStatus.HALF_DAY)),
        "leave": Count("id", filter=Q(status=AttendanceStatus.LEAVE)),
        "absent": Count("id", filter=Q(status=AttendanceStatus.ABSENT)),
    }
    return list(
        records.values(*group_fields).annotate(**groups).order_by(*group_fields)
    )


def _streak(student, internship, start, end):
    dates = list(
        Attendance.objects.filter(
            student=student,
            internship=internship,
            date__range=(start, end),
            status=AttendanceStatus.ABSENT,
        )
        .order_by("date")
        .values_list("date", flat=True)
    )
    max_streak = current = 0
    prev = None
    for day in dates:
        if prev is not None and (day - prev).days == 1:
            current += 1
        else:
            current = 1
        max_streak = max(max_streak, current)
        prev = day
    return max_streak


def _half_percent(records, days):
    total = len(days)
    present_equiv = sum(_present_equivalent(r.status) for r in records)
    return round(present_equiv / total * 100, 1) if total else 0.0


def supervisor_analytics(supervisor, student_id=None, date_from=None, date_to=None):
    """Full analytics bundle for a verified supervisor and their interns."""
    rows = intern_stats(supervisor, student_id, date_from, date_to)
    records = _records_for(supervisor, student_id, date_from, date_to)
    counts = _counts(records)

    total_working = _working_day_total(supervisor, student_id, date_from, date_to)
    total_present_equiv = sum(r["present_equivalent"] for r in rows)
    overall = (
        round(total_present_equiv / total_working * 100, 1)
        if total_working
        else 0.0
    )

    daily = _grouped(records, "date")
    weekly = _grouped(records, "date__year", "date__week")
    monthly = _grouped(records, "date__year", "date__month")

    comparison = [
        {"label": r["student"].full_name, "percentage": r["percentage"]} for r in rows
    ]

    absences = []
    for r in rows:
        streak = _streak(r["student"], r["internship"], r["start"], r["end"])
        if streak >= CONSISTENT_ABSENCE_STREAK:
            absences.append({"student": r["student"], "streak": streak})

    low = [
        r for r in rows if r["irregular"] and r["total_working_days"] > 0
    ]

    improving = declining = stable = 0
    intern_trends = []
    for r in rows:
        days = working_days(r["start"], r["end"])
        if len(days) < 4:
            continue
        mid = days[len(days) // 2]
        first_records = list(
            Attendance.objects.filter(
                student=r["student"],
                internship=r["internship"],
                date__gte=r["start"],
                date__lt=mid,
            )
        )
        second_records = list(
            Attendance.objects.filter(
                student=r["student"],
                internship=r["internship"],
                date__gte=mid,
                date__lte=r["end"],
            )
        )
        first_pct = _half_percent(first_records, days[: len(days) // 2])
        second_pct = _half_percent(second_records, days[len(days) // 2:])
        if second_pct > first_pct + 1:
            direction = "improving"
        elif second_pct < first_pct - 1:
            direction = "declining"
        else:
            direction = "stable"
        if direction == "improving":
            improving += 1
        elif direction == "declining":
            declining += 1
        else:
            stable += 1
        intern_trends.append(
            {
                "student": r["student"],
                "first": first_pct,
                "second": second_pct,
                "direction": direction,
            }
        )

    return {
        "supervisor": supervisor,
        "intern_stats": rows,
        "totals": {
            "interns": len(rows),
            "total_working_days": total_working,
            "present": counts["present"],
            "half": counts["half"],
            "leave": counts["leave"],
            "absent": counts["absent"],
            "late": records.filter(
                check_in__gt=LATE_THRESHOLD, status=AttendanceStatus.PRESENT
            ).count(),
            "present_equivalent": round(total_present_equiv, 1),
            "percentage": overall,
        },
        "daily": daily,
        "weekly": weekly,
        "monthly": monthly,
        "comparison": comparison,
        "absences": absences,
        "low": low,
        "trends": {
            "improving": improving,
            "declining": declining,
            "stable": stable,
            "interns": intern_trends,
        },
    }
