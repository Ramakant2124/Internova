"""Student portal views."""
import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Avg, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import student_required
from accounts.models import FacultyProfile
from accounts.utils import paginate
from attendance.models import Attendance, AttendanceStatus
from attendance.services import (
    attendance_summary,
    monthly_counts,
    student_check_in,
    student_check_out,
)
from certificates.models import Certificate, CertificateStatus
from certificates.services import (
    request_verification,
    upload_certificate,
)
from documents.forms import DocumentUploadForm
from documents.models import Document
from internships.models import Internship, InternshipStatus
from internships.services import apply_to_internship, assign_faculty
from progress.forms import DailyWorkLogForm, WeeklyProgressForm
from progress.models import DailyWorkLog, Feedback, ReviewStatus, WeeklyProgress
from tasks.models import Task, TaskStatus

from .forms import ApplicationForm, StudentProfileEditForm, TaskUpdateForm

STUDENT_DASHBOARD = "students:dashboard"


def _student(request):
    return request.user.student_profile


def _allocation(student):
    return (
        student.allocations.filter(status="ACTIVE")
        .select_related("internship", "internship__company")
        .first()
    )


def _faculty_assignment(student, internship):
    from internships.models import FacultyAssignment

    return (
        FacultyAssignment.objects.filter(
            student=student, internship=internship, active=True
        ).select_related("faculty").first()
    )


@login_required
@student_required
def dashboard(request):
    student = _student(request)
    allocation = _allocation(student)
    internship = allocation.internship if allocation else None

    attendance = attendance_summary(student, internship)
    tasks_qs = Task.objects.filter(student=student)
    if internship:
        tasks_qs = tasks_qs.filter(internship=internship)
    pending_tasks = tasks_qs.filter(status__in=["PENDING", "IN_PROGRESS"]).count()
    completed_tasks = tasks_qs.filter(status__in=["COMPLETED", "APPROVED"]).count()

    weekly = WeeklyProgress.objects.filter(student=student)
    if internship:
        weekly = weekly.filter(internship=internship)
    overall_progress = round(weekly.aggregate(avg=Avg("progress_percentage"))["avg"] or 0, 1)

    certificate = None
    certificate_status = CertificateStatus.NOT_UPLOADED
    if internship:
        certificate = (
            Certificate.objects.filter(student=student, internship=internship).first()
        )
        certificate_status = certificate.verification_status if certificate else "NOT_UPLOADED"

    recent_tasks = tasks_qs.order_by("-created_at")[:5]
    context = {
        "student": student,
        "allocation": allocation,
        "internship": internship,
        "attendance": attendance,
        "pending_tasks": pending_tasks,
        "completed_tasks": completed_tasks,
        "overall_progress": overall_progress,
        "certificate": certificate,
        "certificate_status": certificate_status,
        "recent_tasks": recent_tasks,
        "recent_notifications": request.user.notifications.all()[:6],
    }
    return render(request, "student/dashboard.html", context)


@login_required
@student_required
def profile(request):
    student = _student(request)
    form = StudentProfileEditForm(instance=student)
    if request.method == "POST":
        form = StudentProfileEditForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("students:profile")
    return render(request, "student/profile.html", {"student": student, "form": form})


@login_required
@student_required
def internship_detail(request):
    student = _student(request)
    allocation = _allocation(student)
    internship = allocation.internship if allocation else None
    if internship:
        history = internship.status_history.all()[:10]
        application = (
            student.applications.filter(internship=internship).first()
        )
    else:
        history = []
        application = None
    return render(
        request,
        "student/internship.html",
        {
            "student": student,
            "allocation": allocation,
            "internship": internship,
            "history": history,
            "application": application,
        },
    )


@login_required
@student_required
def company_detail(request):
    student = _student(request)
    allocation = _allocation(student)
    company = allocation.internship.company if allocation else None
    supervisors = company.supervisors.all() if company else []
    return render(
        request,
        "student/company.html",
        {"student": student, "company": company, "supervisors": supervisors},
    )


@login_required
@student_required
def mentor_detail(request):
    student = _student(request)
    allocation = _allocation(student)
    assignment = (
        _faculty_assignment(student, allocation.internship) if allocation else None
    )
    faculty_list = (
        FacultyProfile.objects.filter(college=student.college)
        .select_related("user")
        .order_by("full_name")
        if student.college
        else []
    )
    return render(
        request,
        "student/mentor.html",
        {
            "student": student,
            "allocation": allocation,
            "assignment": assignment,
            "faculty_list": faculty_list,
        },
    )


@require_POST
@login_required
@student_required
def mentor_select(request):
    student = _student(request)
    allocation = _allocation(student)
    if not allocation:
        messages.error(request, "You are not allocated to an internship yet.")
        return redirect("students:mentor")
    faculty = get_object_or_404(
        FacultyProfile.objects.select_related("user"), pk=request.POST.get("faculty", "")
    )
    if student.college_id != faculty.college_id:
        raise PermissionDenied
    assign_faculty(faculty, student, allocation.internship, request.user)
    messages.success(request, f"{faculty.full_name} is now your faculty mentor.")
    return redirect("students:mentor")


@login_required
@student_required
def attendance_view(request):
    student = _student(request)
    allocation = _allocation(student)
    internship = allocation.internship if allocation else None

    year = request.GET.get("year")
    month = request.GET.get("month")
    today = timezone.localdate()
    if not year or not month:
        year, month = today.year, today.month

    records = Attendance.objects.filter(student=student)
    if internship:
        records = records.filter(internship=internship)
    records = records.filter(date__year=year, date__month=month).select_related("internship")
    attendance_page = paginate(request, records, per_page=15)
    monthly = monthly_counts(student, internship, year, month) if internship else {}

    summary = attendance_summary(student, internship)
    today_record = None
    if internship:
        today_record = Attendance.objects.filter(
            student=student, internship=internship, date=today
        ).first()

    return render(
        request,
        "student/attendance.html",
        {
            "student": student,
            "internship": internship,
            "summary": summary,
            "records": attendance_page,
            "monthly": monthly,
            "year": year,
            "month": month,
            "today_record": today_record,
            "today": today,
        },
    )


@require_POST
@login_required
@student_required
def check_in(request):
    student = _student(request)
    allocation = _allocation(student)
    if not allocation:
        messages.error(request, "You are not allocated to an internship.")
        return redirect("students:attendance")
    try:
        student_check_in(student, allocation.internship)
        messages.success(request, "Checked in successfully.")
    except ValidationError as exc:
        messages.error(request, exc.message)
    return redirect("students:attendance")


@require_POST
@login_required
@student_required
def check_out(request):
    student = _student(request)
    allocation = _allocation(student)
    if not allocation:
        messages.error(request, "You are not allocated to an internship.")
        return redirect("students:attendance")
    try:
        student_check_out(student, allocation.internship)
        messages.success(request, "Checked out successfully.")
    except ValidationError as exc:
        messages.error(request, exc.message)
    return redirect("students:attendance")


@login_required
@student_required
def work_logs(request):
    student = _student(request)
    allocation = _allocation(student)
    internship = allocation.internship if allocation else None
    qs = DailyWorkLog.objects.filter(student=student).select_related("internship")
    page = paginate(request, qs, per_page=12)

    form = None
    if internship:
        form = DailyWorkLogForm(
            initial={"date": timezone.localdate()}
            if not DailyWorkLog.objects.filter(
                student=student, internship=internship, date=timezone.localdate()
            ).exists()
            else None
        )
        if request.method == "POST":
            form = DailyWorkLogForm(request.POST, request.FILES)
            if form.is_valid():
                if DailyWorkLog.objects.filter(
                    student=student, internship=internship, date=form.cleaned_data["date"]
                ).exists():
                    form.add_error(None, "A work log for this date already exists.")
                else:
                    log = form.save(commit=False)
                    log.student = student
                    log.internship = internship
                    log.save()
                    messages.success(request, "Daily work log submitted.")
                    return redirect("students:work_logs")
    return render(
        request,
        "student/work_logs.html",
        {"student": student, "internship": internship, "logs": page, "form": form},
    )


@login_required
@student_required
def work_log_edit(request, pk):
    student = _student(request)
    log = get_object_or_404(DailyWorkLog, pk=pk, student=student)
    if log.status != ReviewStatus.PENDING:
        messages.error(request, "This work log has already been reviewed.")
        return redirect("students:work_logs")
    form = DailyWorkLogForm(instance=log)
    if request.method == "POST":
        form = DailyWorkLogForm(request.POST, request.FILES, instance=log)
        if form.is_valid():
            form.save()
            messages.success(request, "Work log updated.")
            return redirect("students:work_logs")
    return render(
        request, "student/work_log_form.html", {"form": form, "log": log}
    )


@login_required
@student_required
def weekly_progress_view(request):
    student = _student(request)
    allocation = _allocation(student)
    internship = allocation.internship if allocation else None
    qs = WeeklyProgress.objects.filter(student=student).select_related("internship")
    page = paginate(request, qs, per_page=12)

    form = None
    if internship:
        form = WeeklyProgressForm()
        if request.method == "POST":
            form = WeeklyProgressForm(request.POST, request.FILES)
            if form.is_valid():
                ws = form.cleaned_data["week_start"]
                if WeeklyProgress.objects.filter(
                    student=student, internship=internship, week_start=ws
                ).exists():
                    form.add_error(None, "A weekly report for this week already exists.")
                else:
                    report = form.save(commit=False)
                    report.student = student
                    report.internship = internship
                    report.save()
                    messages.success(request, "Weekly progress report submitted.")
                    return redirect("students:weekly_progress")
    return render(
        request,
        "student/progress.html",
        {"student": student, "internship": internship, "reports": page, "form": form},
    )


@login_required
@student_required
def weekly_progress_edit(request, pk):
    student = _student(request)
    report = get_object_or_404(WeeklyProgress, pk=pk, student=student)
    if report.status != ReviewStatus.PENDING:
        messages.error(request, "This report has already been reviewed.")
        return redirect("students:weekly_progress")
    form = WeeklyProgressForm(instance=report)
    if request.method == "POST":
        form = WeeklyProgressForm(request.POST, request.FILES, instance=report)
        if form.is_valid():
            form.save()
            messages.success(request, "Weekly report updated.")
            return redirect("students:weekly_progress")
    return render(
        request, "student/progress_form.html", {"form": form, "report": report}
    )


@login_required
@student_required
def tasks_view(request):
    student = _student(request)
    qs = Task.objects.filter(student=student).select_related("internship", "assigned_by")
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)
    page = paginate(request, qs, per_page=12)
    return render(
        request,
        "student/tasks.html",
        {"student": student, "tasks": page, "status": status, "statuses": TaskStatus.choices},
    )


@login_required
@student_required
def task_detail(request, pk):
    student = _student(request)
    task = get_object_or_404(
        Task.objects.select_related("internship", "assigned_by"), pk=pk, student=student
    )
    form = TaskUpdateForm(instance=task)
    if request.method == "POST":
        form = TaskUpdateForm(request.POST, request.FILES, instance=task)
        if form.is_valid():
            task = form.save()
            if task.status == TaskStatus.SUBMITTED:
                messages.success(request, "Task submitted for review.")
            else:
                messages.success(request, "Task progress updated.")
            return redirect("students:task_detail", pk=task.pk)
    return render(
        request, "student/task_detail.html", {"student": student, "task": task, "form": form}
    )


@login_required
@student_required
def documents_view(request):
    student = _student(request)
    allocation = _allocation(student)
    qs = Document.objects.filter(student=student).select_related("internship")
    page = paginate(request, qs, per_page=12)
    form = None
    if allocation:
        form = DocumentUploadForm()
        if request.method == "POST":
            form = DocumentUploadForm(request.POST, request.FILES)
            if form.is_valid():
                doc = form.save(commit=False)
                doc.student = student
                doc.internship = allocation.internship
                doc.save()
                messages.success(request, "Document uploaded for verification.")
                return redirect("students:documents")
    return render(
        request,
        "student/documents.html",
        {"student": student, "internship": allocation.internship if allocation else None, "documents": page, "form": form},
    )


@require_POST
@login_required
@student_required
def document_delete(request, pk):
    student = _student(request)
    doc = get_object_or_404(Document, pk=pk, student=student)
    if doc.status == "PENDING":
        doc.file.delete(save=False)
        doc.delete()
        messages.success(request, "Document deleted.")
    else:
        messages.error(request, "Only pending documents can be deleted.")
    return redirect("students:documents")


@login_required
@student_required
def certificate_view(request):
    student = _student(request)
    allocation = _allocation(student)
    certificate = None
    internship = allocation.internship if allocation else None
    if internship:
        certificate = Certificate.objects.filter(student=student, internship=internship).first()
    return render(
        request,
        "student/certificate.html",
        {"student": student, "certificate": certificate, "internship": internship},
    )


@login_required
@student_required
def certificate_upload(request):
    student = _student(request)
    allocation = _allocation(student)
    if not allocation:
        messages.error(request, "You are not allocated to an internship.")
        return redirect("students:certificate")
    internship = allocation.internship
    if request.method == "POST" and request.FILES.get("certificate_file"):
        try:
            cert = upload_certificate(
                student, internship, request.FILES["certificate_file"]
            )
            messages.success(request, f"Certificate uploaded as {cert.certificate_number}.")
        except ValidationError as exc:
            messages.error(request, exc.message)
    else:
        messages.error(request, "Please choose a certificate file to upload.")
    return redirect("students:certificate")


@require_POST
@login_required
@student_required
def certificate_request_verification(request):
    student = _student(request)
    certificate = get_object_or_404(Certificate, student=student)
    if certificate.verification_status not in (
        CertificateStatus.UPLOADED,
        CertificateStatus.REJECTED,
    ):
        messages.error(request, "Certificate is not eligible for verification.")
        return redirect("students:certificate")
    request_verification(certificate, request.user)
    messages.success(request, "Certificate submitted for verification.")
    return redirect("students:certificate")


@login_required
@student_required
def feedback_view(request):
    student = _student(request)
    qs = Feedback.objects.filter(student=student).select_related("internship")
    page = paginate(request, qs, per_page=12)
    return render(
        request,
        "student/feedback.html",
        {"student": student, "feedback": page},
    )


@login_required
@student_required
def internships_available(request):
    student = _student(request)
    applied_ids = student.applications.values_list("internship_id", flat=True)
    qs = Internship.objects.filter(
        status__in=[InternshipStatus.APPLIED, InternshipStatus.APPROVED]
    ).exclude(id__in=applied_ids)
    qs = qs.select_related("company")
    keyword = request.GET.get("q", "")
    if keyword:
        qs = qs.filter(title__icontains=keyword)
    page = paginate(request, qs, per_page=10)

    form = ApplicationForm()
    if request.method == "POST":
        form = ApplicationForm(request.POST)
        internship_id = request.POST.get("internship_id")
        internship = get_object_or_404(Internship, pk=internship_id)
        if form.is_valid():
            try:
                apply_to_internship(student, internship, form.cleaned_data["cover_letter"])
                messages.success(request, f"Applied to '{internship.title}'.")
            except ValidationError as exc:
                messages.error(request, exc.messages[0])
            return redirect("students:internships_available")
    return render(
        request,
        "student/internships_available.html",
        {"student": student, "internships": page, "form": form, "keyword": keyword},
    )


@login_required
@student_required
def notifications_view(request):
    page = paginate(request, request.user.notifications.all(), per_page=15)
    return render(request, "notifications/list.html", {"notifications": page})
