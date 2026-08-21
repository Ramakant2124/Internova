"""Analytics endpoints and report views with CSV/Excel/PDF exports."""
import csv

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Avg, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import (
    college_required,
    company_required,
    faculty_required,
)
from accounts.models import CompanyProfile, FacultyProfile, StudentProfile
from attendance.models import Attendance
from certificates.models import Certificate
from internships.models import (
    FacultyAssignment,
    Internship,
    InternshipAllocation,
)
from progress.models import WeeklyProgress
from reports.services import irregular_student_details, irregular_students
from tasks.models import Task

REPORT_TYPES = {
    "students": "Student Internship Report",
    "companies": "Company-wise Internship Report",
    "faculty": "Faculty-wise Student Report",
    "attendance": "Attendance Report",
    "progress": "Progress Report",
    "completion": "Internship Completion Report",
    "certificates": "Certificate Verification Report",
    "irregular": "Irregular Student Report",
}


# ---------------------------------------------------------------------------
# Analytics (college / faculty)
# ---------------------------------------------------------------------------
@login_required
def analytics(request):
    if request.user.role not in ("COLLEGE", "FACULTY"):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return render(request, "reports/analytics.html")


@login_required
def analytics_data(request):
    if request.user.role not in ("COLLEGE", "FACULTY"):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    status = request.GET.get("status", "")
    user = request.user

    student_ids = None
    if user.role == "FACULTY":
        student_ids = list(
            FacultyAssignment.objects.filter(
                faculty=user.faculty_profile, active=True
            ).values_list("student_id", flat=True)
        )

    internships = Internship.objects.all()
    if student_ids is not None:
        internships = internships.filter(
            allocations__student_id__in=student_ids
        ).distinct()
    if status:
        internships = internships.filter(status=status)

    status_counts = list(
        internships.values("status").annotate(count=Count("id")).order_by("status")
    )

    attendance_qs = Attendance.objects.all()
    if student_ids is not None:
        attendance_qs = attendance_qs.filter(student_id__in=student_ids)
    attendance_counts = list(
        attendance_qs.values("status").annotate(count=Count("id")).order_by("status")
    )

    alloc_qs = InternshipAllocation.objects.all()
    if student_ids is not None:
        alloc_qs = alloc_qs.filter(student_id__in=student_ids)
    company_wise = list(
        alloc_qs.values("internship__company__company_name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    progress_qs = WeeklyProgress.objects.all()
    if student_ids is not None:
        progress_qs = progress_qs.filter(student_id__in=student_ids)
    student_progress = list(
        progress_qs.values("student__full_name")
        .annotate(avg=Avg("progress_percentage"))
        .order_by("-avg")[:10]
    )

    completed_vs_active = {
        "completed": internships.filter(status="COMPLETED").count(),
        "active": internships.filter(status__in=["ALLOCATED", "ACTIVE"]).count(),
    }
    return JsonResponse(
        {
            "status_counts": status_counts,
            "attendance_counts": attendance_counts,
            "company_wise": company_wise,
            "student_progress": student_progress,
            "completed_vs_active": completed_vs_active,
        }
    )


# ---------------------------------------------------------------------------
# Report data builder
# ---------------------------------------------------------------------------
def _scope(request):
    """Return the queryset filters implied by the user's role."""
    user = request.user
    if user.role == "FACULTY":
        return {
            "student_ids": list(
                FacultyAssignment.objects.filter(
                    faculty=user.faculty_profile, active=True
                ).values_list("student_id", flat=True)
            )
        }
    if user.role == "COMPANY":
        return {"company": user.company_profile}
    return {}


def get_report_rows(report_type, request):
    """Build columns + rows for a report, honouring role scope and filters."""
    user = request.user
    scope = _scope(request)

    date_from = request.GET.get("date_from") or None
    date_to = request.GET.get("date_to") or None
    student_id = request.GET.get("student") or None
    company_id = request.GET.get("company") or None
    faculty_id = request.GET.get("faculty") or None
    internship_id = request.GET.get("internship") or None
    status = request.GET.get("status") or None

    def in_date(qs, field):
        if date_from:
            qs = qs.filter(**{f"{field}__gte": date_from})
        if date_to:
            qs = qs.filter(**{f"{field}__lte": date_to})
        return qs

    if report_type == "students":
        columns = ["Student ID", "Name", "Email", "Department", "Internship", "Company", "Internship Status", "Allocation Status"]
        rows = []
        qs = StudentProfile.objects.select_related("user").order_by("full_name")
        if "student_ids" in scope:
            qs = qs.filter(id__in=scope["student_ids"])
        if student_id:
            qs = qs.filter(id=student_id)
        for s in qs:
            alloc = s.allocations.order_by("-allocation_date").first()
            rows.append(
                [
                    s.student_id,
                    s.full_name,
                    s.email,
                    s.department,
                    alloc.internship.title if alloc else "-",
                    alloc.internship.company.company_name if alloc else "-",
                    alloc.internship.status if alloc else "-",
                    alloc.status if alloc else "-",
                ]
            )
        return columns, rows

    if report_type == "companies":
        columns = ["Company", "Industry", "City", "Internships", "Allocated Students"]
        rows = []
        qs = CompanyProfile.objects.all().order_by("company_name")
        if "company" in scope:
            qs = qs.filter(pk=scope["company"].pk)
        if company_id:
            qs = qs.filter(id=company_id)
        for c in qs:
            rows.append(
                [
                    c.company_name,
                    c.industry,
                    c.city,
                    c.internships.count(),
                    InternshipAllocation.objects.filter(internship__company=c).count(),
                ]
            )
        return columns, rows

    if report_type == "faculty":
        columns = ["Faculty", "Department", "Assigned Students", "Active Internships"]
        rows = []
        qs = FacultyProfile.objects.select_related("user").order_by("full_name")
        if faculty_id:
            qs = qs.filter(id=faculty_id)
        for f in qs:
            assignments = f.assignments.filter(active=True)
            rows.append(
                [
                    f.full_name,
                    f.department,
                    assignments.count(),
                    assignments.filter(internship__status__in=["ALLOCATED", "ACTIVE"]).count(),
                ]
            )
        return columns, rows

    if report_type == "attendance":
        columns = ["Student", "Internship", "Date", "Status", "Check In", "Check Out"]
        rows = []
        qs = Attendance.objects.select_related("student", "internship").order_by("-date")
        if "student_ids" in scope:
            qs = qs.filter(student_id__in=scope["student_ids"])
        if "company" in scope:
            qs = qs.filter(internship__company=scope["company"])
        qs = in_date(qs, "date")
        if student_id:
            qs = qs.filter(student_id=student_id)
        if internship_id:
            qs = qs.filter(internship_id=internship_id)
        if status:
            qs = qs.filter(status=status)
        for a in qs[:500]:
            rows.append(
                [
                    a.student.full_name,
                    a.internship.title,
                    a.date.isoformat(),
                    a.get_status_display(),
                    a.check_in.isoformat() if a.check_in else "-",
                    a.check_out.isoformat() if a.check_out else "-",
                ]
            )
        return columns, rows

    if report_type == "progress":
        columns = ["Student", "Internship", "Week Start", "Week End", "Progress %", "Status"]
        rows = []
        qs = WeeklyProgress.objects.select_related("student", "internship").order_by("-week_start")
        if "student_ids" in scope:
            qs = qs.filter(student_id__in=scope["student_ids"])
        if "company" in scope:
            qs = qs.filter(internship__company=scope["company"])
        if student_id:
            qs = qs.filter(student_id=student_id)
        if status:
            qs = qs.filter(status=status)
        for w in qs[:500]:
            rows.append(
                [
                    w.student.full_name,
                    w.internship.title,
                    w.week_start.isoformat(),
                    w.week_end.isoformat(),
                    w.progress_percentage,
                    w.get_status_display(),
                ]
            )
        return columns, rows

    if report_type == "completion":
        columns = ["Student", "Company", "Internship", "End Date", "Status"]
        rows = []
        qs = Internship.objects.filter(status="COMPLETED").select_related(
            "company"
        ).order_by("-updated_at")
        if "company" in scope:
            qs = qs.filter(company=scope["company"])
        if company_id:
            qs = qs.filter(company_id=company_id)
        if status:
            qs = qs.filter(status=status)
        for i in qs:
            rows.append(
                [
                    ", ".join(i.allocations.values_list("student__full_name", flat=True)[:3]),
                    i.company.company_name,
                    i.title,
                    i.end_date.isoformat() if i.end_date else "-",
                    i.get_status_display(),
                ]
            )
        return columns, rows

    if report_type == "certificates":
        columns = ["Certificate No", "Student", "Company", "Status", "Issue Date"]
        rows = []
        qs = Certificate.objects.select_related("student", "company").order_by("-created_at")
        if "company" in scope:
            qs = qs.filter(company=scope["company"])
        if student_id:
            qs = qs.filter(student_id=student_id)
        if status:
            qs = qs.filter(verification_status=status)
        for c in qs[:500]:
            rows.append(
                [
                    c.certificate_number,
                    c.student.full_name,
                    c.company.company_name,
                    c.get_verification_status_display(),
                    c.issue_date.isoformat() if c.issue_date else "-",
                ]
            )
        return columns, rows

    if report_type == "irregular":
        columns = ["Student", "Attendance %", "Progress %", "Overdue Tasks", "Reasons"]
        rows = []
        if "company" in scope:
            students = [
                a.student
                for a in InternshipAllocation.objects.filter(
                    internship__company=scope["company"], status="ACTIVE"
                ).select_related("student")
            ]
        else:
            students = list(
                StudentProfile.objects.filter(
                    id__in=InternshipAllocation.objects.filter(status="ACTIVE").values_list("student_id", flat=True)
                )
            )
        for s in students:
            if student_id and s.id != int(student_id):
                continue
            alloc = s.allocations.filter(status="ACTIVE").first()
            if not alloc:
                continue
            details = irregular_student_details(s, alloc.internship)
            if details["reasons"]:
                rows.append(
                    [
                        f"{s.full_name} ({s.student_id})",
                        details["attendance_percentage"],
                        details["progress_percentage"],
                        details["overdue_tasks"],
                        "; ".join(details["reasons"]),
                    ]
                )
        return columns, rows

    return [], []


# ---------------------------------------------------------------------------
# Report pages
# ---------------------------------------------------------------------------
def _reports_allowed(request):
    return request.user.role in ("COLLEGE", "FACULTY", "COMPANY")


@login_required
def reports_home(request):
    if not _reports_allowed(request):
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied
    return render(request, "reports/home.html", {"report_types": REPORT_TYPES})


@login_required
def report_view(request, report_type):
    if not _reports_allowed(request):
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied
    if report_type not in REPORT_TYPES:
        from django.http import Http404

        raise Http404
    columns, rows = get_report_rows(report_type, request)
    page = Paginator(rows, 20).get_page(request.GET.get("page", 1))
    filters = {
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),
        "status": request.GET.get("status", ""),
    }
    return render(
        request,
        "reports/report_detail.html",
        {
            "report_type": report_type,
            "report_title": REPORT_TYPES[report_type],
            "columns": columns,
            "page": page,
            "filters": filters,
        },
    )


def _export_name(report_type, ext):
    return f"{report_type}_{timezone.localdate().isoformat()}.{ext}"


@login_required
def report_export(request, report_type, fmt):
    if not _reports_allowed(request):
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied
    if report_type not in REPORT_TYPES or fmt not in ("csv", "xlsx", "pdf"):
        from django.http import Http404

        raise Http404
    columns, rows = get_report_rows(report_type, request)

    if fmt == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{_export_name(report_type, "csv")}"'
        writer = csv.writer(response)
        writer.writerow(columns)
        writer.writerows(rows)
        return response

    if fmt == "xlsx":
        from openpyxl import Workbook
        from openpyxl.styles import Font

        wb = Workbook()
        ws = wb.active
        ws.title = REPORT_TYPES[report_type][:30]
        ws.append(columns)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for row in rows:
            ws.append(row)
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{_export_name(report_type, "xlsx")}"'
        wb.save(response)
        return response

    # PDF
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{_export_name(report_type, "pdf")}"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = [Paragraph(REPORT_TYPES[report_type], styles["Title"]), Spacer(1, 12)]
    data = [columns] + rows
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return response
