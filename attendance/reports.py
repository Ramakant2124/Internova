"""Attendance report builders used by the supervisor template.

Every report is scoped to a verified supervisor and their assigned interns,
and can be filtered by intern, date range and attendance status.
"""
from datetime import date, datetime, timedelta

from django.conf import settings
from django.utils import timezone

from .analytics import (
    LATE_THRESHOLD,
    _counts,
    _date_range,
    _present_equivalent,
    _records_for,
    _working_day_total,
    intern_stats,
)
from .models import Attendance, AttendanceStatus
from .services import working_days

REPORT_TYPES = {
    "daily": "Daily Attendance Report",
    "weekly": "Weekly Attendance Report",
    "monthly": "Monthly Attendance Report",
    "intern": "Intern-wise Attendance Report",
    "supervisor": "Supervisor-wise Attendance Report",
    "percentage": "Attendance Percentage Report",
    "summary": "Present / Absent / Leave Summary",
    "low": "Low Attendance Report",
    "trend": "Attendance Trend Report",
    "custom": "Custom Date Range Report",
}


def _base_records(supervisor, filters):
    records = _records_for(
        supervisor,
        filters.get("student_id"),
        filters.get("date_from"),
        filters.get("date_to"),
    )
    status = filters.get("status")
    if status:
        records = records.filter(status=status)
    return records


def _status_display(status):
    for value, label in AttendanceStatus.choices:
        if value == status:
            return label
    return status


def _month_bounds(year, month):
    first = date(year, month, 1)
    last = date(year + 1, 1, 1) - timedelta(days=1) if month == 12 else (
        date(year, month + 1, 1) - timedelta(days=1)
    )
    return first, last


def _week_bounds(year, week):
    start = datetime.strptime(f"{year}-W{week:02d}-1", "%G-W%V-%u").date()
    return start, start + timedelta(days=6)


def build_attendance_report(report_type, supervisor, filters):
    """Return (columns, rows) for the requested attendance report."""
    today = timezone.localdate()
    date_from = filters.get("date_from") or None
    date_to = filters.get("date_to") or None
    student_id = filters.get("student_id") or None

    if report_type in ("daily", "custom"):
        records = (
            _base_records(supervisor, filters)
            .select_related("student", "internship", "supervisor")
            .order_by("-date", "student__full_name")
        )
        columns = ["Date", "Intern", "Internship", "Status", "Check-in",
                   "Check-out", "Remarks"]
        rows = [
            [
                r.date,
                r.student.full_name,
                r.internship.title,
                r.get_status_display(),
                r.check_in or "",
                r.check_out or "",
                r.remarks or "",
            ]
            for r in records
        ]
        return columns, rows

    rows = intern_stats(supervisor, student_id, date_from, date_to)

    if report_type == "intern":
        columns = ["Intern", "Internship", "Working Days", "Present", "Half",
                   "Leave", "Absent", "Late", "Attendance %"]
        return columns, [
            [
                r["student"].full_name,
                r["internship"].title,
                r["total_working_days"],
                r["present"],
                r["half"],
                r["leave"],
                r["absent"],
                r["late"],
                f"{r['percentage']}%",
            ]
            for r in rows
        ]

    if report_type == "percentage":
        columns = ["Intern", "Working Days", "Present Equivalent",
                   "Attendance %", "Status"]
        return columns, [
            [
                r["student"].full_name,
                r["total_working_days"],
                r["present_equivalent"],
                f"{r['percentage']}%",
                "Low" if r["irregular"] else "Regular",
            ]
            for r in rows
        ]

    if report_type == "low":
        columns = ["Intern", "Internship", "Working Days", "Attendance %"]
        low = [r for r in rows if r["irregular"]]
        return columns, [
            [
                r["student"].full_name,
                r["internship"].title,
                r["total_working_days"],
                f"{r['percentage']}%",
            ]
            for r in low
        ]

    if report_type == "supervisor":
        records = _records_for(supervisor, student_id, date_from, date_to)
        counts = _counts(records)
        total_working = _working_day_total(supervisor, student_id, date_from, date_to)
        present_equiv = counts["present"] + 0.5 * counts["half"]
        percentage = round(present_equiv / total_working * 100, 1) if total_working else 0.0
        late = records.filter(
            check_in__gt=LATE_THRESHOLD, status=AttendanceStatus.PRESENT
        ).count()
        columns = ["Supervisor", "Interns", "Working Days", "Present", "Half",
                   "Leave", "Absent", "Late", "Attendance %"]
        return columns, [[
            supervisor.name,
            len(rows),
            total_working,
            counts["present"],
            counts["half"],
            counts["leave"],
            counts["absent"],
            late,
            f"{percentage}%",
        ]]

    if report_type == "summary":
        counts = _counts(_base_records(supervisor, filters))
        columns = ["Attendance Status", "Count"]
        return columns, [[label, counts[key]] for key, label in (
            ("present", "Present"),
            ("half", "Half Day"),
            ("leave", "Leave"),
            ("absent", "Absent"),
        )]

    if report_type == "monthly":
        columns = ["Intern", "Month", "Working Days", "Present", "Half",
                   "Leave", "Absent", "Attendance %"]
        out = []
        for r in rows:
            months = _months_in_range(r["start"], r["end"])
            for ym in months:
                first, last = _month_bounds(*ym)
                wd = len(working_days(max(r["start"], first), min(r["end"], last)))
                records = Attendance.objects.filter(
                    student=r["student"], internship=r["internship"],
                    date__month=ym[1], date__year=ym[0],
                )
                counts = _counts(records)
                pe = counts["present"] + 0.5 * counts["half"]
                out.append([
                    r["student"].full_name,
                    f"{ym[1]:02d}/{ym[0]}",
                    wd,
                    counts["present"],
                    counts["half"],
                    counts["leave"],
                    counts["absent"],
                    f"{round(pe / wd * 100, 1) if wd else 0.0}%",
                ])
        return columns, out

    if report_type == "weekly":
        columns = ["Intern", "Week", "Working Days", "Present", "Half",
                   "Leave", "Absent", "Attendance %"]
        out = []
        for r in rows:
            weeks = _weeks_in_range(r["start"], r["end"])
            for yw in weeks:
                first, last = _week_bounds(*yw)
                wd = len(working_days(max(r["start"], first), min(r["end"], last)))
                records = Attendance.objects.filter(
                    student=r["student"], internship=r["internship"],
                    date__range=(max(r["start"], first), min(r["end"], last)),
                )
                counts = _counts(records)
                pe = counts["present"] + 0.5 * counts["half"]
                out.append([
                    r["student"].full_name,
                    f"W{yw[1]:02d} {yw[0]}",
                    wd,
                    counts["present"],
                    counts["half"],
                    counts["leave"],
                    counts["absent"],
                    f"{round(pe / wd * 100, 1) if wd else 0.0}%",
                ])
        return columns, out

    if report_type == "trend":
        columns = ["Intern", "Month", "Working Days", "Attendance %"]
        out = []
        for r in rows:
            months = _months_in_range(r["start"], r["end"])
            for ym in months:
                first, last = _month_bounds(*ym)
                wd = len(working_days(max(r["start"], first), min(r["end"], last)))
                records = list(Attendance.objects.filter(
                    student=r["student"], internship=r["internship"],
                    date__month=ym[1], date__year=ym[0],
                ))
                pe = sum(_present_equivalent(rec.status) for rec in records)
                out.append([
                    r["student"].full_name,
                    f"{ym[1]:02d}/{ym[0]}",
                    wd,
                    f"{round(pe / wd * 100, 1) if wd else 0.0}%",
                ])
        return columns, out

    return ["No Report"], []


def _months_in_range(start, end):
    out = []
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        out.append((cursor.year, cursor.month))
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return out


def _weeks_in_range(start, end):
    first_week = _week_bounds(*_year_week(start))
    if first_week[0] > start:
        first_week = _week_bounds(*_year_week(first_week[0] + timedelta(days=7)))
    out = []
    cursor_start = first_week[0]
    while cursor_start <= end:
        out.append(_year_week(cursor_start))
        cursor_start += timedelta(days=7)
    return out


def _year_week(day):
    iso = day.isocalendar()
    return iso[0], iso[1]
