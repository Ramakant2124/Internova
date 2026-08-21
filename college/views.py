"""College Training & Placement portal views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import college_required
from accounts.models import CompanyProfile, StudentProfile
from accounts.utils import paginate
from attendance.models import Attendance, AttendanceStatus
from attendance.services import attendance_summary, mark_attendance
from certificates.models import Certificate, CertificateStatus
from certificates.services import verify_certificate
from documents.models import Document
from internships.forms import FacultyAssignmentForm
from internships.models import (
    AllocationStatus,
    ApplicationStatus,
    FacultyAssignment,
    Internship,
    InternshipAllocation,
    InternshipApplication,
    InternshipStatus,
)
from internships.services import (
    allocate_internship,
    approve_completion,
    assign_faculty,
    review_application,
)
from notifications.services import create_notification
from progress.models import (
    Approval,
    DailyWorkLog,
    ReviewStatus,
    WeeklyProgress,
)
from progress.services import review_document, review_submission
from reports.services import irregular_students
from tasks.models import Task, TaskStatus

from .forms import (
    ApplicationReviewForm,
    AttendanceMarkForm,
    CompanyCreateForm,
    CompanyProfileEditForm,
    FacultyCreateForm,
    FacultyEditForm,
    InternshipForm,
    StudentCreateForm,
    StudentEditForm,
    StudentPasswordForm,
)

DASHBOARD = "college:dashboard"


def _college(request):
    return request.user.college_profile


def _students_of(college):
    return StudentProfile.objects.filter(college=college)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@login_required
@college_required
def dashboard(request):
    college = _college(request)
    students = _students_of(college)
    allocations = InternshipAllocation.objects.filter(
        student__college=college
    ).select_related("student", "internship")

    total_students = students.count()
    active_internships = Internship.objects.filter(
        status__in=[InternshipStatus.ALLOCATED, InternshipStatus.ACTIVE]
    ).count()
    total_companies = CompanyProfile.objects.count()
    currently_interning = allocations.filter(status="ACTIVE").count()
    pending_approvals = Approval.objects.filter(status="PENDING").count()
    pending_certificates = Certificate.objects.filter(
        verification_status=CertificateStatus.PENDING_VERIFICATION
    ).count()
    completed_internships = Internship.objects.filter(
        status=InternshipStatus.COMPLETED
    ).count()

    irregular = irregular_students(college=college)

    recent_applications = InternshipApplication.objects.select_related(
        "student", "internship"
    ).order_by("-applied_at")[:8]

    context = {
        "college": college,
        "total_students": total_students,
        "active_internships": active_internships,
        "total_companies": total_companies,
        "currently_interning": currently_interning,
        "pending_approvals": pending_approvals,
        "pending_certificates": pending_certificates,
        "completed_internships": completed_internships,
        "irregular": irregular,
        "recent_applications": recent_applications,
        "recent_notifications": request.user.notifications.all()[:6],
    }
    return render(request, "college/dashboard.html", context)


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------
@login_required
@college_required
def students_list(request):
    college = _college(request)
    qs = _students_of(college).select_related("user")
    q = request.GET.get("q", "")
    dept = request.GET.get("department", "")
    year = request.GET.get("year", "")
    if q:
        qs = qs.filter(
            Q(full_name__icontains=q)
            | Q(student_id__icontains=q)
            | Q(email__icontains=q)
        )
    if dept:
        qs = qs.filter(department=dept)
    if year:
        qs = qs.filter(year=year)
    page = paginate(request, qs, per_page=15)
    departments = StudentProfile.objects.filter(college=college).values_list(
        "department", flat=True
    ).distinct()
    return render(
        request,
        "college/students.html",
        {"students": page, "q": q, "department": dept, "year": year, "departments": departments},
    )


@login_required
@college_required
def student_add(request):
    college = _college(request)
    form = StudentCreateForm()
    if request.method == "POST":
        form = StudentCreateForm(request.POST)
        if form.is_valid():
            user = form.save(college=college)
            messages.success(
                request,
                f"Student '{user.username}' created. "
                f"Email: {user.email}. Temporary password set by you.",
            )
            return redirect("college:students")
    return render(request, "college/student_form.html", {"form": form})


@login_required
@college_required
def student_edit(request, pk):
    college = _college(request)
    student = get_object_or_404(StudentProfile, pk=pk, college=college)
    form = StudentEditForm(instance=student)
    if request.method == "POST":
        form = StudentEditForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "Student updated.")
            return redirect("college:student_detail", pk=student.pk)
    return render(
        request, "college/student_form.html", {"form": form, "student": student, "editing": True}
    )


@login_required
@college_required
def student_detail(request, pk):
    college = _college(request)
    student = get_object_or_404(
        StudentProfile.objects.select_related("user", "college"), pk=pk, college=college
    )
    allocation = (
        student.allocations.filter(status="ACTIVE")
        .select_related("internship", "internship__company")
        .first()
    )
    attendance = attendance_summary(student, allocation.internship if allocation else None)
    tasks = Task.objects.filter(student=student)
    pending_tasks = tasks.filter(status__in=["PENDING", "IN_PROGRESS"]).count()
    overdue_tasks = tasks.filter(
        due_date__lt=timezone.localdate()
    ).exclude(status__in=["APPROVED", "COMPLETED"]).count()
    weekly_avg = (
        WeeklyProgress.objects.filter(student=student)
        .aggregate(avg=Avg("progress_percentage"))["avg"]
        or 0
    )
    assignments = student.faculty_assignments.filter(active=True).select_related("faculty", "internship")
    certificate = None
    if allocation:
        certificate = (
            Certificate.objects.filter(student=student, internship=allocation.internship).first()
        )
    password_form = StudentPasswordForm()
    return render(
        request,
        "college/student_detail.html",
        {
            "student": student,
            "allocation": allocation,
            "attendance": attendance,
            "pending_tasks": pending_tasks,
            "overdue_tasks": overdue_tasks,
            "weekly_avg": round(weekly_avg, 1),
            "assignments": assignments,
            "certificate": certificate,
            "password_form": password_form,
        },
    )


@require_POST
@login_required
@college_required
def student_toggle_active(request, pk):
    college = _college(request)
    student = get_object_or_404(StudentProfile, pk=pk, college=college)
    student.user.is_active = not student.user.is_active
    student.user.save(update_fields=["is_active"])
    state = "activated" if student.user.is_active else "deactivated"
    messages.success(request, f"Student '{student.full_name}' {state}.")
    return redirect("college:students")


@require_POST
@login_required
@college_required
def student_set_password(request, pk):
    college = _college(request)
    student = get_object_or_404(StudentProfile, pk=pk, college=college)
    form = StudentPasswordForm(request.POST)
    if form.is_valid():
        student.user.set_password(form.cleaned_data["new_password"])
        student.user.save()
        messages.success(request, f"Password updated for {student.full_name}.")
    else:
        messages.error(request, "Password must be at least 8 characters.")
    return redirect("college:student_detail", pk=student.pk)


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------
@login_required
@college_required
def companies_list(request):
    qs = CompanyProfile.objects.all().select_related("user")
    q = request.GET.get("q", "")
    if q:
        qs = qs.filter(
            Q(company_name__icontains=q) | Q(company_code__icontains=q) | Q(industry__icontains=q)
        )
    page = paginate(request, qs, per_page=15)
    return render(request, "college/companies.html", {"companies": page, "q": q})


@login_required
@college_required
def company_add(request):
    form = CompanyCreateForm()
    if request.method == "POST":
        form = CompanyCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Company '{user.username}' created.")
            return redirect("college:companies")
    return render(request, "college/company_form.html", {"form": form})


@login_required
@college_required
def company_edit(request, pk):
    company = get_object_or_404(CompanyProfile, pk=pk)
    form = CompanyProfileEditForm(instance=company)
    if request.method == "POST":
        form = CompanyProfileEditForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Company updated.")
            return redirect("college:companies")
    return render(
        request, "college/company_form.html", {"form": form, "company": company, "editing": True}
    )


@require_POST
@login_required
@college_required
def company_toggle_active(request, pk):
    company = get_object_or_404(CompanyProfile, pk=pk)
    company.user.is_active = not company.user.is_active
    company.user.save(update_fields=["is_active"])
    state = "activated" if company.user.is_active else "deactivated"
    messages.success(request, f"Company '{company.company_name}' {state}.")
    return redirect("college:companies")


# ---------------------------------------------------------------------------
# Internships
# ---------------------------------------------------------------------------
@login_required
@college_required
def internships_list(request):
    qs = Internship.objects.select_related("company")
    q = request.GET.get("q", "")
    status = request.GET.get("status", "")
    company_id = request.GET.get("company", "")
    if q:
        qs = qs.filter(title__icontains=q)
    if status:
        qs = qs.filter(status=status)
    if company_id:
        qs = qs.filter(company_id=company_id)
    page = paginate(request, qs, per_page=12)
    companies = CompanyProfile.objects.all()
    return render(
        request,
        "college/internships.html",
        {"internships": page, "q": q, "status": status, "companies": companies,
         "internship_statuses": InternshipStatus.choices},
    )


@login_required
@college_required
def internship_add(request):
    form = InternshipForm()
    if request.method == "POST":
        form = InternshipForm(request.POST)
        if form.is_valid():
            internship = form.save(commit=False)
            internship.created_by = request.user
            internship.save()
            messages.success(request, "Internship created.")
            return redirect("college:internships")
    return render(request, "college/internship_form.html", {"form": form})


@login_required
@college_required
def internship_edit(request, pk):
    internship = get_object_or_404(Internship, pk=pk)
    form = InternshipForm(instance=internship)
    if request.method == "POST":
        form = InternshipForm(request.POST, instance=internship)
        if form.is_valid():
            form.save()
            messages.success(request, "Internship updated.")
            return redirect("college:internship_detail", pk=internship.pk)
    return render(
        request,
        "college/internship_form.html",
        {"form": form, "internship": internship, "editing": True},
    )


@login_required
@college_required
def internship_detail(request, pk):
    internship = get_object_or_404(
        Internship.objects.select_related("company"), pk=pk
    )
    applications = internship.applications.select_related("student").order_by("-applied_at")
    allocations = internship.allocations.select_related("student")
    history = internship.status_history.all()[:12]
    return render(
        request,
        "college/internship_detail.html",
        {
            "internship": internship,
            "applications": applications,
            "allocations": allocations,
            "history": history,
        },
    )


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
@login_required
@college_required
def applications_list(request):
    qs = InternshipApplication.objects.select_related(
        "student", "internship", "internship__company"
    )
    status = request.GET.get("status", "")
    company_id = request.GET.get("company", "")
    if status:
        qs = qs.filter(status=status)
    if company_id:
        qs = qs.filter(internship__company_id=company_id)
    page = paginate(request, qs, per_page=15)
    form = ApplicationReviewForm()
    companies = CompanyProfile.objects.all()
    return render(
        request,
        "college/applications.html",
        {"applications": page, "status": status, "companies": companies, "form": form,
         "application_statuses": ApplicationStatus.choices},
    )


@require_POST
@login_required
@college_required
def application_review(request, pk):
    application = get_object_or_404(InternshipApplication, pk=pk)
    decision = request.POST.get("decision")
    comments = request.POST.get("comments", "")
    if decision not in ("approve", "reject"):
        messages.error(request, "Invalid decision.")
        return redirect("college:applications")
    review_application(application, approved=decision == "approve", reviewer=request.user, comments=comments)
    messages.success(request, f"Application {decision}d.")
    return redirect("college:applications")


# ---------------------------------------------------------------------------
# Allocations
# ---------------------------------------------------------------------------
@login_required
@college_required
def allocations_list(request):
    qs = InternshipAllocation.objects.select_related("student", "internship", "internship__company")
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)
    page = paginate(request, qs, per_page=15)
    return render(
        request,
        "college/allocations.html",
        {"allocations": page, "status": status,
         "allocation_statuses": AllocationStatus.choices},
    )


@login_required
@college_required
def allocation_create(request):
    college = _college(request)
    from .forms import AllocationForm

    form = AllocationForm()
    form.fields["student"].queryset = _students_of(college).order_by("full_name")
    if request.method == "POST":
        form = AllocationForm(request.POST)
        form.fields["student"].queryset = _students_of(college).order_by("full_name")
        if form.is_valid():
            try:
                allocation = allocate_internship(
                    student=form.cleaned_data["student"],
                    internship=form.cleaned_data["internship"],
                    allocated_by=request.user,
                    start_date=form.cleaned_data["start_date"],
                    end_date=form.cleaned_data["end_date"],
                )
                messages.success(request, "Internship allocated to student.")
                return redirect("college:allocations")
            except ValidationError as exc:
                form.add_error(None, exc.messages[0])
    return render(request, "college/allocation_form.html", {"form": form})


@login_required
@college_required
def allocation_assign_faculty(request, pk):
    college = _college(request)
    allocation = get_object_or_404(
        InternshipAllocation.objects.select_related("student", "internship"), pk=pk
    )
    if allocation.status != "ACTIVE":
        messages.error(request, "Only active allocations can have a faculty mentor.")
        return redirect("college:allocations")
    faculty_qs = college.faculty_members.all()
    form = FacultyAssignmentForm(faculty_queryset=faculty_qs)
    if request.method == "POST":
        form = FacultyAssignmentForm(request.POST, faculty_queryset=faculty_qs)
        if form.is_valid():
            assign_faculty(
                faculty=form.cleaned_data["faculty"],
                student=allocation.student,
                internship=allocation.internship,
                assigned_by=request.user,
            )
            messages.success(request, "Faculty mentor assigned.")
            return redirect("college:allocations")
    return render(
        request,
        "college/assign_faculty.html",
        {"form": form, "allocation": allocation},
    )


@require_POST
@login_required
@college_required
def allocation_terminate(request, pk):
    allocation = get_object_or_404(InternshipAllocation, pk=pk)
    if allocation.status != "ACTIVE":
        messages.error(request, "Only active allocations can be terminated.")
        return redirect("college:allocations")
    allocation.status = "TERMINATED"
    allocation.save(update_fields=["status", "updated_at"])
    create_notification(
        recipient=allocation.student.user,
        title="Allocation Terminated",
        message=f"Your allocation to '{allocation.internship.title}' was terminated.",
        notification_type="ALLOCATION",
        related_url="/student/internship/",
    )
    messages.success(request, "Allocation terminated.")
    return redirect("college:allocations")


# ---------------------------------------------------------------------------
# Faculty
# ---------------------------------------------------------------------------
@login_required
@college_required
def faculty_list(request):
    college = _college(request)
    qs = college.faculty_members.select_related("user")
    q = request.GET.get("q", "")
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(employee_id__icontains=q))
    page = paginate(request, qs, per_page=15)
    return render(request, "college/faculty.html", {"faculty": page, "q": q})


@login_required
@college_required
def faculty_add(request):
    college = _college(request)
    form = FacultyCreateForm()
    if request.method == "POST":
        form = FacultyCreateForm(request.POST)
        if form.is_valid():
            user = form.save(college=college)
            messages.success(request, f"Faculty member '{user.username}' created.")
            return redirect("college:faculty")
    return render(request, "college/faculty_form.html", {"form": form})


@login_required
@college_required
def faculty_edit(request, pk):
    college = _college(request)
    faculty = get_object_or_404(college.faculty_members, pk=pk)
    form = FacultyEditForm(instance=faculty)
    if request.method == "POST":
        form = FacultyEditForm(request.POST, instance=faculty)
        if form.is_valid():
            form.save()
            messages.success(request, "Faculty member updated.")
            return redirect("college:faculty")
    return render(
        request, "college/faculty_form.html", {"form": form, "faculty": faculty, "editing": True}
    )


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------
@login_required
@college_required
def attendance_view(request):
    college = _college(request)
    qs = Attendance.objects.filter(student__college=college).select_related(
        "student", "internship"
    )
    q = request.GET.get("q", "")
    status = request.GET.get("status", "")
    month = request.GET.get("month", "")
    if q:
        qs = qs.filter(student__full_name__icontains=q)
    if status:
        qs = qs.filter(status=status)
    if month:
        qs = qs.filter(date__year=month[:4], date__month=int(month[5:7]))
    page = paginate(request, qs, per_page=15)

    mark_form = AttendanceMarkForm(students=_students_of(college).order_by("full_name"))
    if request.method == "POST":
        mark_form = AttendanceMarkForm(
            request.POST, students=_students_of(college).order_by("full_name")
        )
        if mark_form.is_valid():
            student = mark_form.cleaned_data["student"]
            allocation = student.allocations.filter(status="ACTIVE").first()
            if not allocation:
                messages.error(request, "Selected student has no active allocation.")
            else:
                try:
                    mark_attendance(
                        student=student,
                        internship=allocation.internship,
                        date=mark_form.cleaned_data["date"],
                        status=mark_form.cleaned_data["status"],
                        remarks=mark_form.cleaned_data["remarks"],
                    )
                    messages.success(request, "Attendance recorded.")
                    return redirect("college:attendance")
                except ValidationError as exc:
                    messages.error(request, exc.messages[0])
    return render(
        request,
        "college/attendance.html",
        {"records": page, "q": q, "status": status, "mark_form": mark_form,
         "attendance_statuses": AttendanceStatus.choices},
    )


# ---------------------------------------------------------------------------
# Progress reviews (work logs + weekly)
# ---------------------------------------------------------------------------
@login_required
@college_required
def progress_reviews(request):
    kind = request.GET.get("kind", "work")
    status = request.GET.get("status", "")
    if kind == "weekly":
        qs = WeeklyProgress.objects.select_related("student", "internship")
    else:
        qs = DailyWorkLog.objects.select_related("student", "internship")
    if status:
        qs = qs.filter(status=status)
    page = paginate(request, qs, per_page=15)
    return render(
        request,
        "college/progress.html",
        {"kind": kind, "status": status, "page": page,
         "review_statuses": ReviewStatus.choices},
    )


@require_POST
@login_required
@college_required
def progress_review_action(request, kind, pk):
    if kind == "weekly":
        obj = get_object_or_404(WeeklyProgress, pk=pk)
    elif kind == "work":
        obj = get_object_or_404(DailyWorkLog, pk=pk)
    else:
        messages.error(request, "Invalid review target.")
        return redirect("college:progress")
    decision = request.POST.get("decision", "")
    comments = request.POST.get("comments", "")
    if decision not in ReviewStatus.values:
        messages.error(request, "Invalid decision.")
        return redirect("college:progress")
    review_submission(obj, decision, request.user, comments)
    messages.success(request, "Submission reviewed.")
    return redirect("college:progress")


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------
@login_required
@college_required
def approvals_list(request):
    qs = Approval.objects.filter(status="PENDING").select_related(
        "content_type", "requested_by"
    ).order_by("created_at")
    page = paginate(request, qs, per_page=15)
    return render(request, "college/approvals.html", {"approvals": page})


@require_POST
@login_required
@college_required
def approval_action(request, pk):
    approval = get_object_or_404(Approval, pk=pk)
    decision = request.POST.get("decision", "")
    comments = request.POST.get("comments", "")
    if decision not in ("approve", "reject"):
        messages.error(request, "Invalid decision.")
        return redirect("college:approvals")

    approved = decision == "approve"
    obj = approval.content_object

    if obj is None:
        approval.status = Approval.Status.APPROVED if approved else Approval.Status.REJECTED
        approval.reviewed_by = request.user
        approval.comments = comments
        approval.save()
        messages.success(request, "Approval updated.")
        return redirect("college:approvals")

    try:
        if approval.approval_type == Approval.ApprovalType.INTERNSHIP_APPLICATION:
            review_application(obj, approved, request.user, comments)
        elif approval.approval_type == Approval.ApprovalType.COMPLETION:
            if approved:
                approve_completion(obj, request.user, comments)
            else:
                approval.status = Approval.Status.REJECTED
                approval.reviewed_by = request.user
                approval.comments = comments
                approval.save()
        elif approval.approval_type == Approval.ApprovalType.DOCUMENT:
            review_document(
                obj,
                ReviewStatus.APPROVED if approved else ReviewStatus.REJECTED,
                request.user,
                comments,
            )
        elif approval.approval_type == Approval.ApprovalType.CERTIFICATE:
            verify_certificate(obj, request.user, approved, comments)
        elif approval.approval_type == Approval.ApprovalType.DAILY_WORK_LOG:
            review_submission(
                obj,
                ReviewStatus.APPROVED if approved else ReviewStatus.REJECTED,
                request.user,
                comments,
            )
        elif approval.approval_type == Approval.ApprovalType.WEEKLY_PROGRESS:
            review_submission(
                obj,
                ReviewStatus.APPROVED if approved else ReviewStatus.REJECTED,
                request.user,
                comments,
            )
        else:
            approval.status = Approval.Status.APPROVED if approved else Approval.Status.REJECTED
            approval.reviewed_by = request.user
            approval.comments = comments
            approval.save()
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
        return redirect("college:approvals")

    messages.success(request, "Approval processed.")
    return redirect("college:approvals")


# ---------------------------------------------------------------------------
# Certificates
# ---------------------------------------------------------------------------
@login_required
@college_required
def certificates_list(request):
    qs = Certificate.objects.select_related("student", "company", "internship")
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(verification_status=status)
    q = request.GET.get("q", "")
    if q:
        qs = qs.filter(
            Q(certificate_number__icontains=q)
            | Q(student__full_name__icontains=q)
            | Q(company__company_name__icontains=q)
        )
    page = paginate(request, qs, per_page=15)
    return render(
        request,
        "college/certificates.html",
        {"certificates": page, "status": status, "q": q,
         "certificate_statuses": CertificateStatus.choices},
    )


@require_POST
@login_required
@college_required
def certificate_verify_action(request, pk):
    certificate = get_object_or_404(Certificate, pk=pk)
    decision = request.POST.get("decision", "")
    comments = request.POST.get("comments", "")
    if decision not in ("verify", "reject"):
        messages.error(request, "Invalid decision.")
        return redirect("college:certificates")
    verify_certificate(
        certificate, request.user, decision == "verify", comments
    )
    messages.success(request, "Certificate processed.")
    return redirect("college:certificates")
