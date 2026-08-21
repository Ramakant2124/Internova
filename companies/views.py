"""Company portal views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import company_required
from accounts.models import StudentProfile
from accounts.utils import paginate
from attendance.services import attendance_summary
from certificates.models import Certificate, CertificateStatus
from certificates.services import upload_certificate
from internships.forms import SupervisorForm
from internships.models import (
    Internship,
    InternshipAllocation,
    InternshipStatus,
    SupervisorAssignment,
)
from internships.services import assign_supervisor, request_completion
from notifications.services import create_notification
from progress.models import (
    DailyWorkLog,
    Feedback,
    ReviewStatus,
    WeeklyProgress,
)
from progress.services import review_submission
from supervisors.access import SESSION_KEY
from tasks.models import Task, TaskStatus
from tasks.services import create_task, review_task

from .forms import (
    CertificateUploadForm,
    CompanyFeedbackForm,
    CompanyInternshipForm,
    CompanyProfileForm,
    CompanyTaskForm,
    CompletionRequestForm,
    SupervisorAssignForm,
    SupervisorVerifyForm,
)


def _company(request):
    return request.user.company_profile


def _allocated_student_ids(company):
    return InternshipAllocation.objects.filter(
        internship__company=company, status="ACTIVE"
    ).values_list("student_id", flat=True)


def _allocated_students(company):
    return StudentProfile.objects.filter(id__in=_allocated_student_ids(company))


@login_required
@company_required
def dashboard(request):
    company = _company(request)
    internships = company.internships.all()
    allocated_ids = _allocated_student_ids(company)
    allocations = InternshipAllocation.objects.filter(
        internship__company=company
    ).select_related("student", "internship")

    opportunities = internships.count()
    allocated_students = allocated_ids.count()
    active_interns = allocations.filter(status="ACTIVE").count()
    pending_reviews = (
        DailyWorkLog.objects.filter(
            internship__company=company, status="PENDING"
        ).count()
        + WeeklyProgress.objects.filter(
            internship__company=company, status="PENDING"
        ).count()
    )
    pending_tasks = Task.objects.filter(
        internship__company=company, status=TaskStatus.SUBMITTED
    ).count()
    completion_requests = allocations.filter(
        status="ACTIVE",
        internship__status=InternshipStatus.ACTIVE,
    ).count()
    certificates = Certificate.objects.filter(company=company).count()

    context = {
        "company": company,
        "opportunities": opportunities,
        "allocated_students": allocated_students,
        "active_interns": active_interns,
        "pending_reviews": pending_reviews,
        "pending_tasks": pending_tasks,
        "completion_requests": completion_requests,
        "certificates": certificates,
        "recent_notifications": request.user.notifications.all()[:6],
    }
    return render(request, "company/dashboard.html", context)


@login_required
@company_required
def profile(request):
    company = _company(request)
    form = CompanyProfileForm(instance=company)
    if request.method == "POST":
        form = CompanyProfileForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Company profile updated.")
            return redirect("companies:profile")
    return render(request, "company/profile.html", {"company": company, "form": form})


@login_required
@company_required
def attendance_select(request):
    """Step 1-3 of the Intern Attendance flow: select + verify supervisor."""
    company = _company(request)
    form = SupervisorVerifyForm(company=company)
    if request.method == "POST":
        form = SupervisorVerifyForm(request.POST, company=company)
        if form.is_valid():
            supervisor = form.cleaned_data["supervisor"]
            request.session[SESSION_KEY] = supervisor.pk
            messages.success(
                request,
                f"Verified as {supervisor.name}. You can now view their assigned "
                "interns and mark attendance.",
            )
            return redirect("supervisors:students", pk=supervisor.pk)
    return render(request, "company/attendance.html", {"form": form, "company": company})


@require_POST
@login_required
@company_required
def attendance_exit(request):
    """Exit the supervisor template and clear the verified supervisor."""
    request.session.pop(SESSION_KEY, None)
    messages.info(request, "Exited supervisor view.")
    return redirect("companies:dashboard")


@login_required
@company_required
def internships_list(request):
    company = _company(request)
    qs = company.internships.all()
    status = request.GET.get("status", "")
    q = request.GET.get("q", "")
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(title__icontains=q)
    page = paginate(request, qs, per_page=12)
    return render(
        request, "company/internships.html",
        {"internships": page, "status": status, "q": q,
         "internship_statuses": InternshipStatus.choices},
    )


@login_required
@company_required
def internship_add(request):
    company = _company(request)
    form = CompanyInternshipForm()
    if request.method == "POST":
        form = CompanyInternshipForm(request.POST)
        if form.is_valid():
            form.save(company=company, user=request.user)
            messages.success(request, "Internship opportunity created.")
            return redirect("companies:internships")
    return render(request, "company/internship_form.html", {"form": form})


@login_required
@company_required
def internship_edit(request, pk):
    company = _company(request)
    internship = get_object_or_404(company.internships, pk=pk)
    form = CompanyInternshipForm(instance=internship)
    if request.method == "POST":
        form = CompanyInternshipForm(request.POST, instance=internship)
        if form.is_valid():
            form.save(company=company, user=request.user)
            messages.success(request, "Internship updated.")
            return redirect("companies:internships")
    return render(
        request,
        "company/internship_form.html",
        {"form": form, "internship": internship, "editing": True},
    )


@login_required
@company_required
def internship_detail(request, pk):
    company = _company(request)
    internship = get_object_or_404(
        company.internships.prefetch_related("allocations__student", "applications__student"),
        pk=pk,
    )
    return render(
        request,
        "company/internship_detail.html",
        {"internship": internship},
    )


@login_required
@company_required
def students_list(request):
    company = _company(request)
    ids = _allocated_student_ids(company)
    qs = StudentProfile.objects.filter(id__in=ids).select_related("user")
    q = request.GET.get("q", "")
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(student_id__icontains=q))
    page = paginate(request, qs, per_page=15)
    return render(request, "company/students.html", {"students": page, "q": q})


def _get_allocated_student(company, pk):
    student = get_object_or_404(StudentProfile, pk=pk)
    if not InternshipAllocation.objects.filter(
        internship__company=company, student=student, status="ACTIVE"
    ).exists():
        raise PermissionDenied
    return student


@login_required
@company_required
def student_detail(request, pk):
    company = _company(request)
    student = _get_allocated_student(company, pk)
    allocation = (
        student.allocations.filter(internship__company=company, status="ACTIVE")
        .select_related("internship")
        .first()
    )
    internship = allocation.internship if allocation else None
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
    supervisor_assignment = (
        SupervisorAssignment.objects.filter(
            student=student, internship=internship, active=True
        ).select_related("supervisor").first()
        if internship
        else None
    )
    certificate = (
        Certificate.objects.filter(student=student, internship=internship).first()
        if internship
        else None
    )
    feedback = Feedback.objects.filter(student=student, internship=internship)[:5]
    return render(
        request,
        "company/student_detail.html",
        {
            "student": student,
            "allocation": allocation,
            "internship": internship,
            "attendance": attendance,
            "pending_tasks": pending_tasks,
            "weekly_avg": weekly_avg,
            "supervisor_assignment": supervisor_assignment,
            "supervisor_form": SupervisorAssignForm(company=company),
            "certificate": certificate,
            "feedback": feedback,
        },
    )


@login_required
@company_required
def tasks_view(request):
    company = _company(request)
    qs = Task.objects.filter(internship__company=company).select_related(
        "student", "internship"
    )
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)
    page = paginate(request, qs, per_page=15)
    return render(request, "company/tasks.html",
                  {"tasks": page, "status": status, "task_statuses": TaskStatus.choices})


@login_required
@company_required
def task_assign(request):
    """Assign a task to an allocated intern with a mandatory supervisor."""
    company = _company(request)
    initial = {}
    student_pk = request.GET.get("student")
    if student_pk:
        try:
            candidate = StudentProfile.objects.get(pk=student_pk)
            if InternshipAllocation.objects.filter(
                internship__company=company, student=candidate, status="ACTIVE"
            ).exists():
                initial["student"] = candidate.pk
        except StudentProfile.DoesNotExist:
            pass
    form = CompanyTaskForm(company=company, initial=initial)
    if request.method == "POST":
        form = CompanyTaskForm(request.POST, request.FILES, company=company)
        if form.is_valid():
            student = form.cleaned_data["student"]
            supervisor = form.cleaned_data["supervisor"]
            allocation = form.cleaned_data["_allocation"]
            create_task(
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
                student=student,
                internship=allocation.internship,
                assigned_by=request.user,
                supervisor=supervisor,
                start_date=timezone.localdate(),
                due_date=form.cleaned_data["due_date"],
                priority=form.cleaned_data["priority"],
                attachment=form.cleaned_data.get("attachment"),
            )
            assign_supervisor(
                supervisor, student, allocation.internship, request.user
            )
            messages.success(
                request,
                f"Task assigned to {student.full_name} under supervisor {supervisor.name}.",
            )
            return redirect("companies:tasks")
    return render(request, "company/task_form.html", {"form": form, "company": company})


@require_POST
@login_required
@company_required
def student_assign_supervisor(request, pk):
    """Link a company supervisor to an allocated intern."""
    company = _company(request)
    student = _get_allocated_student(company, pk)
    allocation = (
        student.allocations.filter(internship__company=company, status="ACTIVE")
        .select_related("internship")
        .first()
    )
    if not allocation:
        messages.error(request, "Student has no active allocation with your company.")
        return redirect("companies:student_detail", pk=student.pk)
    form = SupervisorAssignForm(request.POST, company=company)
    if form.is_valid():
        supervisor = form.cleaned_data["supervisor"]
        assign_supervisor(supervisor, student, allocation.internship, request.user)
        messages.success(
            request,
            f"{supervisor.name} assigned as supervisor for {student.full_name}.",
        )
    else:
        messages.error(request, "Please select a valid supervisor.")
    return redirect("companies:student_detail", pk=student.pk)


@require_POST
@login_required
@company_required
def task_review(request, pk):
    company = _company(request)
    task = get_object_or_404(Task.objects.select_related("internship"), pk=pk)
    if task.internship.company_id != company.pk:
        raise PermissionDenied
    decision = request.POST.get("decision", "")
    comments = request.POST.get("comments", "")
    if decision not in ("approve", "reject"):
        messages.error(request, "Invalid decision.")
        return redirect("companies:tasks")
    review_task(task, decision=decision == "approve", reviewer=request.user, comments=comments)
    messages.success(request, "Task reviewed.")
    return redirect("companies:tasks")


@login_required
@company_required
def progress_view(request):
    company = _company(request)
    kind = request.GET.get("kind", "work")
    status = request.GET.get("status", "")
    if kind == "weekly":
        qs = WeeklyProgress.objects.filter(internship__company=company)
    else:
        qs = DailyWorkLog.objects.filter(internship__company=company)
    qs = qs.select_related("student", "internship")
    if status:
        qs = qs.filter(status=status)
    page = paginate(request, qs, per_page=15)
    return render(
        request, "company/progress.html",
        {"kind": kind, "status": status, "page": page,
         "review_statuses": ReviewStatus.choices},
    )


@require_POST
@login_required
@company_required
def progress_review_action(request, kind, pk):
    company = _company(request)
    if kind == "weekly":
        obj = get_object_or_404(
            WeeklyProgress.objects.select_related("internship"), pk=pk
        )
    else:
        obj = get_object_or_404(
            DailyWorkLog.objects.select_related("internship"), pk=pk
        )
    if obj.internship.company_id != company.pk:
        raise PermissionDenied
    decision = request.POST.get("decision", "")
    comments = request.POST.get("comments", "")
    if decision not in ReviewStatus.values:
        messages.error(request, "Invalid decision.")
        return redirect("companies:progress")
    review_submission(obj, decision, request.user, comments)
    messages.success(request, "Submission reviewed.")
    return redirect("companies:progress")


@login_required
@company_required
def supervisors_view(request):
    company = _company(request)
    qs = company.supervisors.all()
    page = paginate(request, qs, per_page=15)
    return render(request, "company/supervisors.html", {"supervisors": page})


@login_required
@company_required
def supervisor_add(request):
    company = _company(request)
    form = SupervisorForm()
    if request.method == "POST":
        form = SupervisorForm(request.POST)
        if form.is_valid():
            supervisor = form.save(commit=False)
            supervisor.company = company
            supervisor.save()
            messages.success(request, "Supervisor added.")
            return redirect("companies:supervisors")
    return render(request, "company/supervisor_form.html", {"form": form})


@login_required
@company_required
def supervisor_edit(request, pk):
    company = _company(request)
    supervisor = get_object_or_404(company.supervisors, pk=pk)
    form = SupervisorForm(instance=supervisor)
    if request.method == "POST":
        form = SupervisorForm(request.POST, instance=supervisor)
        if form.is_valid():
            form.save()
            messages.success(request, "Supervisor updated.")
            return redirect("companies:supervisors")
    return render(
        request,
        "company/supervisor_form.html",
        {"form": form, "supervisor": supervisor, "editing": True},
    )


@login_required
@company_required
def feedback_view(request):
    company = _company(request)
    qs = Feedback.objects.filter(internship__company=company).select_related(
        "student", "internship"
    )
    page = paginate(request, qs, per_page=15)
    return render(request, "company/feedback.html", {"feedback": page})


@login_required
@company_required
def feedback_create(request, pk):
    company = _company(request)
    student = _get_allocated_student(company, pk)
    allocation = student.allocations.filter(
        internship__company=company, status="ACTIVE"
    ).first()
    form = CompanyFeedbackForm()
    if request.method == "POST":
        form = CompanyFeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.student = student
            feedback.internship = allocation.internship if allocation else None
            feedback.given_by = request.user
            feedback.feedback_type = Feedback.FeedbackType.COMPANY
            feedback.save()
            create_notification(
                recipient=student.user,
                title="Company Feedback",
                message=f"You received feedback from {company.company_name}.",
                notification_type="FEEDBACK",
                related_url="/student/feedback/",
            )
            messages.success(request, "Feedback submitted.")
            return redirect("companies:feedback")
    return render(request, "company/feedback_form.html", {"form": form, "student": student})


@login_required
@company_required
def completion_view(request):
    company = _company(request)
    qs = InternshipAllocation.objects.filter(
        internship__company=company, status="ACTIVE"
    ).select_related("student", "internship")
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(internship__status=status)
    page = paginate(request, qs, per_page=15)
    return render(request, "company/completion.html",
                  {"allocations": page, "status": status,
                   "internship_statuses": InternshipStatus.choices})


@require_POST
@login_required
@company_required
def completion_request(request, pk):
    company = _company(request)
    allocation = get_object_or_404(
        InternshipAllocation.objects.select_related("internship"), pk=pk
    )
    if allocation.internship.company_id != company.pk:
        raise PermissionDenied
    form = CompletionRequestForm(request.POST)
    if form.is_valid():
        try:
            request_completion(
                allocation, request.user, form.cleaned_data.get("reason", "")
            )
            messages.success(request, "Completion request submitted for approval.")
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
    else:
        messages.error(request, "Invalid request.")
    return redirect("companies:completion")


@login_required
@company_required
def certificates_view(request):
    company = _company(request)
    qs = Certificate.objects.filter(company=company).select_related(
        "student", "internship"
    )
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(verification_status=status)
    page = paginate(request, qs, per_page=15)
    return render(request, "company/certificates.html",
                  {"certificates": page, "status": status,
                   "certificate_statuses": CertificateStatus.choices})


@login_required
@company_required
def certificate_upload(request, pk):
    company = _company(request)
    student = _get_allocated_student(company, pk)
    allocation = student.allocations.filter(
        internship__company=company, status="ACTIVE"
    ).first()
    if not allocation:
        messages.error(request, "Student has no active allocation with your company.")
        return redirect("companies:student_detail", pk=student.pk)
    form = CertificateUploadForm()
    if request.method == "POST":
        form = CertificateUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                cert = upload_certificate(
                    student,
                    allocation.internship,
                    form.cleaned_data["certificate_file"],
                    form.cleaned_data["issue_date"],
                )
                messages.success(
                    request, f"Certificate uploaded as {cert.certificate_number}."
                )
            except ValidationError as exc:
                messages.error(request, exc.messages[0])
            return redirect("companies:certificates")
    return render(
        request, "company/certificate_form.html", {"form": form, "student": student}
    )

