"""Business logic for the internship lifecycle.

All critical workflows (application, approval, allocation, faculty
assignment, completion) live here so views stay thin and logic is reused.
"""
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction

from notifications.services import create_notification
from progress.models import Approval

from .models import (
    AllocationStatus,
    ApplicationStatus,
    CompanySupervisor,
    FacultyAssignment,
    Internship,
    InternshipAllocation,
    InternshipApplication,
    InternshipStatus,
    SupervisorAssignment,
)


def _internship_url(internship_id):
    return f"/college/internships/{internship_id}/"


def apply_to_internship(student, internship, cover_letter=""):
    """Student applies for an internship."""
    existing = InternshipApplication.objects.filter(
        student=student, internship=internship
    ).first()
    if existing and existing.status in (
        ApplicationStatus.PENDING,
        ApplicationStatus.APPROVED,
    ):
        raise ValidationError("You have already applied to this internship.")
    if internship.status in (InternshipStatus.REJECTED, InternshipStatus.CANCELLED):
        raise ValidationError("This internship is not accepting applications.")
    application = InternshipApplication.objects.create(
        student=student,
        internship=internship,
        cover_letter=cover_letter,
        status=ApplicationStatus.PENDING,
    )
    Approval.objects.create(
        content_object=application,
        approval_type=Approval.ApprovalType.INTERNSHIP_APPLICATION,
        requested_by=student.user,
    )
    return application


@transaction.atomic
def review_application(application, approved, reviewer, comments=""):
    """College approves/rejects an internship application."""
    old_status = application.status
    application.status = (
        ApplicationStatus.APPROVED if approved else ApplicationStatus.REJECTED
    )
    application.save(update_fields=["status"])

    approval = Approval.objects.filter(
        content_type=ContentType.objects.get_for_model(application),
        object_id=application.pk,
        approval_type=Approval.ApprovalType.INTERNSHIP_APPLICATION,
    ).order_by("-created_at").first()
    if approval:
        approval.status = Approval.Status.APPROVED if approved else Approval.Status.REJECTED
        approval.reviewed_by = reviewer
        approval.comments = comments
        approval.save()

    if approved:
        internship = application.internship
        if internship.status == InternshipStatus.APPLIED:
            internship.transition_to(
                InternshipStatus.APPROVED, changed_by=reviewer, reason="Application approved"
            )
        create_notification(
            recipient=application.student.user,
            title="Application Approved",
            message=f"Your application for '{internship.title}' was approved.",
            notification_type="APPLICATION",
            related_url=f"/student/internship/",
        )
        create_notification(
            recipient=internship.company.user,
            title="New Approved Applicant",
            message=f"{application.student.full_name} was approved for '{internship.title}'.",
            notification_type="APPLICATION",
            related_url="/company/internships/",
        )
    else:
        create_notification(
            recipient=application.student.user,
            title="Application Rejected",
            message=f"Your application for '{application.internship.title}' was rejected."
            + (f" Reason: {comments}" if comments else ""),
            notification_type="APPLICATION",
            related_url="/student/internship/",
        )
    return application


@transaction.atomic
def allocate_internship(student, internship, allocated_by, start_date, end_date):
    """Allocate a student to an internship (college action)."""
    if InternshipAllocation.objects.filter(
        student=student, status=AllocationStatus.ACTIVE
    ).exists():
        raise ValidationError("This student already has an active allocation.")

    allocation = InternshipAllocation.objects.create(
        student=student,
        internship=internship,
        allocated_by=allocated_by,
        start_date=start_date,
        end_date=end_date,
    )
    if internship.status in (
        InternshipStatus.APPLIED,
        InternshipStatus.APPROVED,
    ):
        internship.transition_to(
            InternshipStatus.ALLOCATED, changed_by=allocated_by, reason="Student allocated"
        )
    create_notification(
        recipient=student.user,
        title="Internship Allocated",
        message=f"You have been allocated to '{internship.title}' at {internship.company.company_name}.",
        notification_type="ALLOCATION",
        related_url="/student/internship/",
    )
    create_notification(
        recipient=internship.company.user,
        title="Student Allocated",
        message=f"{student.full_name} has been allocated to '{internship.title}'.",
        notification_type="ALLOCATION",
        related_url="/company/students/",
    )
    return allocation


@transaction.atomic
def assign_faculty(faculty, student, internship, assigned_by):
    """Assign a faculty mentor to a student's internship."""
    FacultyAssignment.objects.filter(
        student=student, internship=internship, active=True
    ).update(active=False)
    assignment = FacultyAssignment.objects.create(
        faculty=faculty,
        student=student,
        internship=internship,
        assigned_by=assigned_by,
    )
    create_notification(
        recipient=student.user,
        title="Mentor Assigned",
        message=f"{faculty.full_name} is now your faculty mentor for '{internship.title}'.",
        notification_type="FACULTY_ASSIGNMENT",
        related_url="/student/mentor/",
    )
    create_notification(
        recipient=faculty.user,
        title="Student Assigned",
        message=f"You have been assigned to mentor {student.full_name} for '{internship.title}'.",
        notification_type="FACULTY_ASSIGNMENT",
        related_url="/faculty/students/",
    )
    return assignment


@transaction.atomic
def assign_supervisor(supervisor, student, internship, assigned_by):
    """Assign a company supervisor to a student's internship.

    The previous active assignment for the same student/internship is
    deactivated so each intern has exactly one active supervisor.
    """
    if not isinstance(supervisor, CompanySupervisor):
        raise ValidationError("A valid supervisor must be selected.")
    SupervisorAssignment.objects.filter(
        student=student, internship=internship, active=True
    ).update(active=False)
    assignment = SupervisorAssignment.objects.create(
        supervisor=supervisor,
        student=student,
        internship=internship,
        assigned_by=assigned_by,
    )
    create_notification(
        recipient=student.user,
        title="Supervisor Assigned",
        message=f"{supervisor.name} is now your company supervisor for '{internship.title}'.",
        notification_type="SUPERVISOR_ASSIGNMENT",
        related_url="/student/internship/",
    )
    if supervisor.user_id:
        create_notification(
            recipient=supervisor.user,
            title="Intern Assigned",
            message=f"You have been assigned to supervise {student.full_name} for '{internship.title}'.",
            notification_type="SUPERVISOR_ASSIGNMENT",
            related_url=f"/company/supervisor/{supervisor.pk}/students/",
        )
    return assignment


@transaction.atomic
def request_completion(allocation, requested_by, reason=""):
    """Company/faculty request completion; requires approval."""
    if allocation.internship.status != InternshipStatus.ACTIVE:
        raise ValidationError("Only active internships can be marked complete.")
    approval = Approval.objects.create(
        content_object=allocation,
        approval_type=Approval.ApprovalType.COMPLETION,
        requested_by=requested_by,
        comments=reason,
    )
    create_notification(
        recipient=allocation.student.user,
        title="Completion Requested",
        message=f"Completion was requested for '{allocation.internship.title}'.",
        notification_type="COMPLETION_APPROVAL",
        related_url="/student/internship/",
    )
    college_users = []
    if allocation.student.college:
        college_users.append(allocation.student.college.user)
    for user in college_users:
        create_notification(
            recipient=user,
            title="Completion Approval Pending",
            message=f"Approve completion of '{allocation.internship.title}' for {allocation.student.full_name}.",
            notification_type="COMPLETION_APPROVAL",
            related_url="/college/approvals/",
        )
    return approval


@transaction.atomic
def approve_completion(allocation, reviewer, comments=""):
    """College approves internship completion."""
    if allocation.internship.status != InternshipStatus.ACTIVE:
        raise ValidationError("Only active internships can be completed.")
    allocation.internship.transition_to(
        InternshipStatus.COMPLETED, changed_by=reviewer, reason="Completion approved"
    )
    allocation.status = AllocationStatus.COMPLETED
    allocation.save(update_fields=["status", "updated_at"])
    approval = (
        Approval.objects.filter(
            content_type=ContentType.objects.get_for_model(allocation),
            object_id=allocation.pk,
            approval_type=Approval.ApprovalType.COMPLETION,
        )
        .order_by("-created_at")
        .first()
    )
    if approval:
        approval.status = Approval.Status.APPROVED
        approval.reviewed_by = reviewer
        approval.comments = comments
        approval.save()
    create_notification(
        recipient=allocation.student.user,
        title="Internship Completed",
        message=f"Congratulations! Your internship '{allocation.internship.title}' has been completed.",
        notification_type="INTERNSHIP_COMPLETION",
        related_url="/student/internship/",
    )
    return allocation.internship
