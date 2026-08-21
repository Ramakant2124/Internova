"""Faculty / Mentor portal views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import faculty_required
from accounts.models import StudentProfile
from accounts.utils import paginate
from attendance.services import attendance_summary
from certificates.models import Certificate, CertificateStatus
from certificates.services import verify_certificate
from internships.models import FacultyAssignment, InternshipAllocation
from notifications.services import create_notification
from progress.forms import ReviewForm
from progress.models import (
    DailyWorkLog,
    Feedback,
    PerformanceEvaluation,
    ReviewStatus,
    WeeklyProgress,
)
from progress.services import review_submission
from reports.services import irregular_student_details
from tasks.models import Task, TaskStatus

from .forms import EvaluationCreateForm, FacultyFeedbackForm


def _faculty(request):
    return request.user.faculty_profile


def _assignments(faculty):
    return (
        FacultyAssignment.objects.filter(faculty=faculty, active=True)
        .select_related("student", "student__user", "internship")
    )


def _assigned_student_ids(faculty):
    return FacultyAssignment.objects.filter(
        faculty=faculty, active=True
    ).values_list("student_id", flat=True)


@login_required
@faculty_required
def dashboard(request):
    faculty = _faculty(request)
    assignments = list(_assignments(faculty))
    students = [a.student for a in assignments]

    total_assigned = len(students)
    active_internships = sum(
        1 for a in assignments if a.internship.status in ("ALLOCATED", "ACTIVE")
    )
    completed_internships = sum(
        1 for a in assignments if a.internship.status == "COMPLETED"
    )

    low_attendance = []
    low_progress = []
    pending_reviews = 0
    for a in assignments:
        details = irregular_student_details(a.student, a.internship)
        if details["attendance_percentage"] and details["attendance_percentage"] < 75:
            low_attendance.append(a.student)
        if details["progress_percentage"] < 50:
            low_progress.append(a.student)
        pending_reviews += (
            DailyWorkLog.objects.filter(student=a.student, internship=a.internship, status="PENDING").count()
            + WeeklyProgress.objects.filter(student=a.student, internship=a.internship, status="PENDING").count()
        )

    context = {
        "faculty": faculty,
        "assignments": assignments,
        "total_assigned": total_assigned,
        "active_internships": active_internships,
        "completed_internships": completed_internships,
        "low_attendance": len(low_attendance),
        "low_progress": len(low_progress),
        "pending_reviews": pending_reviews,
        "recent_notifications": request.user.notifications.all()[:6],
    }
    return render(request, "faculty/dashboard.html", context)


@login_required
@faculty_required
def students_list(request):
    faculty = _faculty(request)
    ids = _assigned_student_ids(faculty)
    qs = StudentProfile.objects.filter(id__in=ids).select_related("user", "college")
    q = request.GET.get("q", "")
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(student_id__icontains=q))
    page = paginate(request, qs, per_page=15)
    return render(request, "faculty/students.html", {"students": page, "q": q})


def _get_assigned_student(faculty, pk):
    student = get_object_or_404(StudentProfile, pk=pk)
    if not FacultyAssignment.objects.filter(
        faculty=faculty, student=student, active=True
    ).exists():
        raise PermissionDenied
    return student


@login_required
@faculty_required
def student_detail(request, pk):
    faculty = _faculty(request)
    student = _get_assigned_student(faculty, pk)
    assignment = (
        FacultyAssignment.objects.filter(faculty=faculty, student=student, active=True)
        .select_related("internship", "internship__company")
        .first()
    )
    internship = assignment.internship if assignment else None
    attendance = attendance_summary(student, internship)
    tasks = Task.objects.filter(student=student)
    if internship:
        tasks = tasks.filter(internship=internship)
    pending_tasks = tasks.filter(status__in=["PENDING", "IN_PROGRESS"]).count()
    overdue_tasks = tasks.filter(due_date__lt=timezone.localdate()).exclude(
        status__in=["APPROVED", "COMPLETED"]
    ).count()
    weekly = WeeklyProgress.objects.filter(student=student)
    if internship:
        weekly = weekly.filter(internship=internship)
    weekly_avg = round(weekly.aggregate(avg=Avg("progress_percentage"))["avg"] or 0, 1)
    evaluations = student.evaluations.all()[:5]
    feedback = student.feedback.all()[:5]
    certificate = (
        Certificate.objects.filter(student=student, internship=internship).first()
        if internship
        else None
    )
    return render(
        request,
        "faculty/student_detail.html",
        {
            "student": student,
            "assignment": assignment,
            "internship": internship,
            "attendance": attendance,
            "pending_tasks": pending_tasks,
            "overdue_tasks": overdue_tasks,
            "weekly_avg": weekly_avg,
            "evaluations": evaluations,
            "feedback": feedback,
            "certificate": certificate,
        },
    )


@login_required
@faculty_required
def attendance_view(request):
    faculty = _faculty(request)
    ids = _assigned_student_ids(faculty)
    qs = (
        __import__("attendance.models", fromlist=["Attendance"]).Attendance.objects.filter(
            student_id__in=ids
        )
        .select_related("student", "internship")
    )
    q = request.GET.get("q", "")
    status = request.GET.get("status", "")
    if q:
        qs = qs.filter(student__full_name__icontains=q)
    if status:
        qs = qs.filter(status=status)
    page = paginate(request, qs, per_page=15)
    return render(request, "faculty/attendance.html",
                  {"records": page, "q": q, "status": status,
                   "attendance_statuses": __import__("attendance.models", fromlist=["AttendanceStatus"]).AttendanceStatus.choices})


@login_required
@faculty_required
def work_logs(request):
    faculty = _faculty(request)
    ids = _assigned_student_ids(faculty)
    qs = DailyWorkLog.objects.filter(student_id__in=ids).select_related(
        "student", "internship"
    )
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)
    page = paginate(request, qs, per_page=15)
    return render(request, "faculty/work_logs.html",
                  {"logs": page, "status": status, "review_statuses": ReviewStatus.choices})


@login_required
@faculty_required
def weekly_progress(request):
    faculty = _faculty(request)
    ids = _assigned_student_ids(faculty)
    qs = WeeklyProgress.objects.filter(student_id__in=ids).select_related(
        "student", "internship"
    )
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)
    page = paginate(request, qs, per_page=15)
    return render(request, "faculty/progress.html",
                  {"reports": page, "status": status, "review_statuses": ReviewStatus.choices})


def _can_review(faculty, obj):
    return FacultyAssignment.objects.filter(
        faculty=faculty, student=obj.student, internship=obj.internship, active=True
    ).exists()


@require_POST
@login_required
@faculty_required
def review_action(request, kind, pk):
    faculty = _faculty(request)
    if kind == "work":
        obj = get_object_or_404(DailyWorkLog, pk=pk)
    elif kind == "weekly":
        obj = get_object_or_404(WeeklyProgress, pk=pk)
    else:
        messages.error(request, "Invalid target.")
        return redirect("faculty:dashboard")
    if not _can_review(faculty, obj):
        raise PermissionDenied
    decision = request.POST.get("decision", "")
    comments = request.POST.get("comments", "")
    if decision not in ReviewStatus.values:
        messages.error(request, "Invalid decision.")
        return redirect("faculty:" + ("work_logs" if kind == "work" else "weekly_progress"))
    review_submission(obj, decision, request.user, comments)
    messages.success(request, "Submission reviewed.")
    return redirect("faculty:" + ("work_logs" if kind == "work" else "weekly_progress"))


@login_required
@faculty_required
def tasks_view(request):
    """View-only task monitoring: faculty may not assign or review tasks."""
    faculty = _faculty(request)
    ids = _assigned_student_ids(faculty)
    qs = Task.objects.filter(student_id__in=ids).select_related(
        "student", "internship", "assigned_by", "supervisor"
    )
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)
    page = paginate(request, qs, per_page=15)
    return render(request, "faculty/tasks.html",
                  {"tasks": page, "status": status, "task_statuses": TaskStatus.choices})


@login_required
@faculty_required
def evaluations(request):
    faculty = _faculty(request)
    ids = _assigned_student_ids(faculty)
    qs = PerformanceEvaluation.objects.filter(student_id__in=ids).select_related(
        "student", "internship", "faculty"
    )
    page = paginate(request, qs, per_page=15)
    return render(request, "faculty/evaluations.html", {"evaluations": page})


@login_required
@faculty_required
def evaluation_create(request, pk):
    faculty = _faculty(request)
    student = _get_assigned_student(faculty, pk)
    allocation = student.allocations.filter(status="ACTIVE").first()
    if not allocation:
        messages.error(request, "Student has no active allocation.")
        return redirect("faculty:student_detail", pk=student.pk)
    if PerformanceEvaluation.objects.filter(
        student=student, internship=allocation.internship, faculty=faculty
    ).exists():
        messages.error(request, "You have already evaluated this student for this internship.")
        return redirect("faculty:student_detail", pk=student.pk)
    form = EvaluationCreateForm()
    if request.method == "POST":
        form = EvaluationCreateForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.student = student
            evaluation.internship = allocation.internship
            evaluation.faculty = faculty
            evaluation.save()
            create_notification(
                recipient=student.user,
                title="New Performance Evaluation",
                message=f"You received a performance evaluation from {faculty.full_name}.",
                notification_type="FEEDBACK",
                related_url="/student/feedback/",
            )
            messages.success(request, "Evaluation submitted.")
            return redirect("faculty:evaluations")
    return render(request, "faculty/evaluation_form.html", {"form": form, "student": student})


@login_required
@faculty_required
def feedback_view(request):
    faculty = _faculty(request)
    ids = _assigned_student_ids(faculty)
    qs = Feedback.objects.filter(student_id__in=ids).select_related("student", "internship")
    page = paginate(request, qs, per_page=15)
    return render(request, "faculty/feedback.html", {"feedback": page})


@login_required
@faculty_required
def feedback_create(request, pk):
    faculty = _faculty(request)
    student = _get_assigned_student(faculty, pk)
    allocation = student.allocations.filter(status="ACTIVE").first()
    form = FacultyFeedbackForm()
    if request.method == "POST":
        form = FacultyFeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.student = student
            feedback.internship = allocation.internship if allocation else None
            feedback.given_by = request.user
            feedback.feedback_type = Feedback.FeedbackType.FACULTY
            feedback.save()
            create_notification(
                recipient=student.user,
                title="New Feedback",
                message=f"You received feedback from {faculty.full_name}.",
                notification_type="FEEDBACK",
                related_url="/student/feedback/",
            )
            messages.success(request, "Feedback submitted.")
            return redirect("faculty:feedback")
    return render(request, "faculty/feedback_form.html", {"form": form, "student": student})


@login_required
@faculty_required
def certificates_view(request):
    faculty = _faculty(request)
    ids = _assigned_student_ids(faculty)
    qs = Certificate.objects.filter(student_id__in=ids).select_related(
        "student", "company", "internship"
    )
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(verification_status=status)
    page = paginate(request, qs, per_page=15)
    return render(request, "faculty/certificates.html",
                  {"certificates": page, "status": status,
                   "certificate_statuses": CertificateStatus.choices})


@require_POST
@login_required
@faculty_required
def certificate_verify(request, pk):
    faculty = _faculty(request)
    certificate = get_object_or_404(Certificate, pk=pk)
    if not _can_review(faculty, certificate):
        raise PermissionDenied
    decision = request.POST.get("decision", "")
    comments = request.POST.get("comments", "")
    if decision not in ("verify", "reject"):
        messages.error(request, "Invalid decision.")
        return redirect("faculty:certificates")
    verify_certificate(certificate, request.user, decision == "verify", comments)
    messages.success(request, "Certificate processed.")
    return redirect("faculty:certificates")
