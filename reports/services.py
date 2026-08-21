"""Reporting helpers shared by dashboards and the reports module."""
from django.db.models import Avg
from django.utils import timezone

from attendance.services import attendance_summary
from internships.models import InternshipAllocation, InternshipStatus
from progress.models import WeeklyProgress
from tasks.models import Task


def irregular_student_details(student, internship):
    """Return irregularity flags for one student's internship."""
    attendance = attendance_summary(student, internship)
    weekly = WeeklyProgress.objects.filter(
        student=student, internship=internship
    ).aggregate(avg=Avg("progress_percentage"))
    progress = round(weekly["avg"] or 0, 1)

    overdue = Task.objects.filter(
        student=student,
        internship=internship,
        due_date__lt=timezone.localdate(),
    ).exclude(status__in=["APPROVED", "COMPLETED"]).count()

    reasons = []
    if attendance["irregular"]:
        reasons.append(f"Attendance below {attendance['percentage']}%")
    if progress < 50:
        reasons.append(f"Progress below 50% ({progress}%)")
    if overdue > 1:
        reasons.append(f"{overdue} overdue tasks")

    return {
        "attendance_percentage": attendance["percentage"],
        "progress_percentage": progress,
        "overdue_tasks": overdue,
        "reasons": reasons,
    }


def irregular_students(college=None, faculty=None):
    """Return allocated students flagged irregular.

    Returns a list of dicts with student, allocation, and reason details.
    """
    allocations = InternshipAllocation.objects.filter(
        status="ACTIVE", internship__status=InternshipStatus.ACTIVE
    ).select_related("student", "student__user", "internship")
    if college is not None:
        allocations = allocations.filter(student__college=college)
    if faculty is not None:
        allocations = allocations.filter(
            internship__faculty_assignments__faculty=faculty,
            internship__faculty_assignments__active=True,
        )

    result = []
    for allocation in allocations:
        details = irregular_student_details(allocation.student, allocation.internship)
        if details["reasons"]:
            result.append(
                {
                    "student": allocation.student,
                    "allocation": allocation,
                    **details,
                }
            )
    return result
