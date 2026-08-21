"""Supervisor Template/View inside the Company Dashboard architecture.

Every view is scoped to a ``supervisor`` resolved and authorized by
:func:`supervisors.access.supervisor_template_required` (company user with a
PIN-verified supervisor in session, or the supervisor's own account). Only
interns assigned to that supervisor are ever shown.
"""
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Avg
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import StudentProfile
from accounts.utils import paginate
from attendance.analytics import supervisor_analytics
from attendance.forms import AttendanceMarkForm
from attendance.models import Attendance
from attendance.reports import REPORT_TYPES, build_attendance_report
from attendance.services import attendance_summary, mark_attendance
from internships.models import SupervisorAssignment
from progress.models import DailyWorkLog, ReviewStatus, WeeklyProgress
from tasks.models import Task, TaskStatus
from tasks.services import review_task

from .access import supervisor_template_required


def _assignments(supervisor):
    return SupervisorAssignment.objects.filter(
        supervisor=supervisor, active=True
    ).select_related("student", "student__user", "internship", "internship__company")


def _assigned_student_ids(supervisor):
    return SupervisorAssignment.objects.filter(
        supervisor=supervisor, active=True
    ).values_list("student_id", flat=True)


def _assigned_internship_ids(supervisor):
    return SupervisorAssignment.objects.filter(
        supervisor=supervisor, active=True
    ).values_list("internship_id", flat=True)


def _get_assigned_student(supervisor, student_pk):
    student = get_object_or_404(StudentProfile, pk=student_pk)
    if not SupervisorAssignment.objects.filter(
        supervisor=supervisor, student=student, active=True
    ).exists():
        raise PermissionDenied
    return student


@supervisor_template_required
def dashboard(request, supervisor):
    assignments = list(_assignments(supervisor))
    students = list({a.student.pk: a.student for a in assignments}.values())

    active_interns = sum(
        1 for a in assignments if a.internship.status in ("ALLOCATED", "ACTIVE")
    )
    pending_reviews = (
        DailyWorkLog.objects.filter(
            student_id__in=[s.pk for s in students], status="PENDING"
        ).count()
        + WeeklyProgress.objects.filter(
            student_id__in=[s.pk for s in students], status="PENDING"
        ).count()
    )
    pending_tasks = Task.objects.filter(
        student_id__in=[s.pk for s in students],
        internship_id__in=[a.internship.pk for a in assignments],
        status=TaskStatus.SUBMITTED,
    ).count()

    context = {
        "supervisor": supervisor,
        "total_assigned": len(students),
        "active_interns": active_interns,
        "pending_reviews": pending_reviews,
        "pending_tasks": pending_tasks,
        "recent_notifications": supervisor.user.notifications.all()[:6]
        if supervisor.user_id
        else [],
    }
    return render(request, "supervisors/dashboard.html", context)


@supervisor_template_required
def students_list(request, supervisor):
    ids = _assigned_student_ids(supervisor)
    qs = StudentProfile.objects.filter(id__in=ids).select_related(
        "user", "college"
    ).prefetch_related("supervisor_assignments__internship")
    q = request.GET.get("q", "")
    if q:
        qs = qs.filter(full_name__icontains=q)
    page = paginate(request, qs, per_page=15)
    return render(
        request,
        "supervisors/students.html",
        {"students": page, "q": q, "supervisor": supervisor},
    )


@supervisor_template_required
def student_detail(request, supervisor, student_pk):
    student = _get_assigned_student(supervisor, student_pk)
    assignment = (
        SupervisorAssignment.objects.filter(
            supervisor=supervisor, student=student, active=True
        )
        .select_related("internship", "internship__company")
        .first()
    )
    internship = assignment.internship if assignment else None
    attendance = attendance_summary(student, internship)
    tasks = Task.objects.filter(student=student)
    if internship:
        tasks = tasks.filter(internship=internship)
    pending_tasks = tasks.filter(status__in=["PENDING", "IN_PROGRESS"]).count()
    weekly_avg = round(
        WeeklyProgress.objects.filter(student=student)
        .aggregate(avg=Avg("progress_percentage"))["avg"]
        or 0,
        1,
    )
    return render(
        request,
        "supervisors/student_detail.html",
        {
            "supervisor": supervisor,
            "student": student,
            "assignment": assignment,
            "internship": internship,
            "attendance": attendance,
            "tasks": tasks[:10],
            "pending_tasks": pending_tasks,
            "weekly_avg": weekly_avg,
        },
    )


@supervisor_template_required
def attendance_view(request, supervisor):
    qs = Attendance.objects.filter(
        student_id__in=_assigned_student_ids(supervisor),
        internship_id__in=_assigned_internship_ids(supervisor),
    ).select_related("student", "internship")
    q = request.GET.get("q", "")
    if q:
        qs = qs.filter(student__full_name__icontains=q)
    page = paginate(request, qs, per_page=15)
    return render(
        request,
        "supervisors/attendance.html",
        {"records": page, "q": q, "supervisor": supervisor},
    )


@supervisor_template_required
def attendance_mark(request, supervisor):
    """Mark attendance for interns assigned to the verified supervisor."""
    students = StudentProfile.objects.filter(
        id__in=_assigned_student_ids(supervisor)
    ).distinct().order_by("full_name")
    form = AttendanceMarkForm(students=students)
    if request.method == "POST":
        form = AttendanceMarkForm(request.POST, students=students)
        if form.is_valid():
            student = form.cleaned_data["student"]
            assignment = SupervisorAssignment.objects.filter(
                supervisor=supervisor, student=student, active=True
            ).select_related("internship").first()
            if not assignment:
                messages.error(request, "This intern is not assigned to you.")
                return redirect("supervisors:attendance_mark", pk=supervisor.pk)
            try:
                mark_attendance(
                    student=student,
                    internship=assignment.internship,
                    date=form.cleaned_data["date"],
                    status=form.cleaned_data["status"],
                    remarks=form.cleaned_data["remarks"],
                    check_in=form.cleaned_data["check_in"],
                    check_out=form.cleaned_data["check_out"],
                    marked_by=request.user,
                    supervisor=supervisor,
                )
                messages.success(
                    request, f"Attendance recorded for {student.full_name}."
                )
                return redirect("supervisors:attendance", pk=supervisor.pk)
            except ValidationError as exc:
                messages.error(request, exc.messages[0])
    return render(
        request,
        "supervisors/attendance_mark.html",
        {"form": form, "students": students, "supervisor": supervisor},
    )


@supervisor_template_required
def attendance_analytics(request, supervisor):
    """Attendance analytics for the verified supervisor and their interns."""
    filters = {
        "student_id": request.GET.get("student") or None,
        "date_from": request.GET.get("date_from") or None,
        "date_to": request.GET.get("date_to") or None,
    }
    data = supervisor_analytics(
        supervisor,
        student_id=filters["student_id"],
        date_from=filters["date_from"],
        date_to=filters["date_to"],
    )
    students = StudentProfile.objects.filter(
        id__in=_assigned_student_ids(supervisor)
    ).order_by("full_name")
    data["filters"] = filters
    data["students"] = students
    data["threshold"] = int(_threshold())
    return render(request, "supervisors/attendance_analytics.html", data)


@supervisor_template_required
def attendance_reports(request, supervisor):
    """Attendance reports for the verified supervisor (filterable + export)."""
    report_type = request.GET.get("report_type", "daily")
    if report_type not in REPORT_TYPES:
        report_type = "daily"
    filters = {
        "student_id": request.GET.get("student") or None,
        "date_from": request.GET.get("date_from") or None,
        "date_to": request.GET.get("date_to") or None,
        "status": request.GET.get("status") or None,
    }
    columns, rows = build_attendance_report(report_type, supervisor, filters)
    page = paginate(request, rows, per_page=25)
    students = StudentProfile.objects.filter(
        id__in=_assigned_student_ids(supervisor)
    ).order_by("full_name")
    return render(
        request,
        "supervisors/attendance_reports.html",
        {
            "supervisor": supervisor,
            "report_type": report_type,
            "report_types": REPORT_TYPES,
            "report_title": REPORT_TYPES[report_type],
            "columns": columns,
            "page": page,
            "filters": filters,
            "students": students,
            "attendance_statuses": _attendance_statuses(),
        },
    )


@supervisor_template_required
def attendance_report_export(request, supervisor):
    """Export the selected attendance report as CSV / XLSX / PDF."""
    fmt = request.GET.get("fmt", "csv")
    if fmt not in ("csv", "xlsx", "pdf"):
        raise PermissionDenied
    report_type = request.GET.get("report_type", "daily")
    if report_type not in REPORT_TYPES:
        report_type = "daily"
    filters = {
        "student_id": request.GET.get("student") or None,
        "date_from": request.GET.get("date_from") or None,
        "date_to": request.GET.get("date_to") or None,
        "status": request.GET.get("status") or None,
    }
    columns, rows = build_attendance_report(report_type, supervisor, filters)
    title = REPORT_TYPES[report_type]
    filename = (
        f"attendance_{report_type}_{supervisor.pk}_"
        f"{timezone.localdate().isoformat()}.{fmt}"
    )
    if fmt == "csv":
        import csv

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(columns)
        writer.writerows(rows)
        return response
    if fmt == "xlsx":
        from openpyxl import Workbook
        from openpyxl.styles import Font

        wb = Workbook()
        ws = wb.active
        ws.title = title[:30]
        ws.append(columns)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for row in rows:
            ws.append(row)
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    data = [columns] + rows
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(table)
    doc.build(elements)
    return response


@supervisor_template_required
def tasks_view(request, supervisor):
    qs = Task.objects.filter(
        student_id__in=_assigned_student_ids(supervisor),
        internship_id__in=_assigned_internship_ids(supervisor),
    ).select_related("student", "internship", "supervisor", "assigned_by")
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)
    page = paginate(request, qs, per_page=15)
    return render(
        request,
        "supervisors/tasks.html",
        {
            "tasks": page,
            "status": status,
            "task_statuses": TaskStatus.choices,
            "supervisor": supervisor,
        },
    )


@require_POST
@supervisor_template_required
def task_review(request, supervisor, task_pk):
    task = get_object_or_404(Task.objects.select_related("internship"), pk=task_pk)
    if not SupervisorAssignment.objects.filter(
        supervisor=supervisor, student=task.student, internship=task.internship,
        active=True,
    ).exists():
        raise PermissionDenied
    decision = request.POST.get("decision", "")
    comments = request.POST.get("comments", "")
    if decision not in ("approve", "reject"):
        messages.error(request, "Invalid decision.")
        return redirect("supervisors:tasks", pk=supervisor.pk)
    review_task(
        task, decision=decision == "approve", reviewer=request.user, comments=comments
    )
    messages.success(request, "Task reviewed.")
    return redirect("supervisors:tasks", pk=supervisor.pk)


@supervisor_template_required
def progress_view(request, supervisor):
    """Intern performance / progress for the verified supervisor's interns."""
    kind = request.GET.get("kind", "work")
    status = request.GET.get("status", "")
    student_filter = request.GET.get("student") or None
    ids = _assigned_student_ids(supervisor)
    internship_ids = _assigned_internship_ids(supervisor)
    if kind == "weekly":
        qs = WeeklyProgress.objects.filter(
            student_id__in=ids, internship_id__in=internship_ids
        )
    else:
        qs = DailyWorkLog.objects.filter(
            student_id__in=ids, internship_id__in=internship_ids
        )
    qs = qs.select_related("student", "internship")
    if student_filter:
        qs = qs.filter(student_id=student_filter)
    if status:
        qs = qs.filter(status=status)
    page = paginate(request, qs, per_page=15)
    students = StudentProfile.objects.filter(id__in=ids).order_by("full_name")
    return render(
        request,
        "supervisors/progress.html",
        {
            "supervisor": supervisor,
            "kind": kind,
            "status": status,
            "page": page,
            "students": students,
            "review_statuses": ReviewStatus.choices,
        },
    )


@supervisor_template_required
def notifications_view(request, supervisor):
    """Notifications for the verified supervisor."""
    qs = supervisor.user.notifications.all() if supervisor.user_id else []
    page = paginate(request, qs, per_page=15)
    return render(
        request,
        "supervisors/notifications.html",
        {"supervisor": supervisor, "notifications": page},
    )


def _threshold():
    from django.conf import settings

    return settings.ATTENDANCE_WARNING_THRESHOLD


def _attendance_statuses():
    from attendance.models import AttendanceStatus

    return AttendanceStatus.choices

