"""Update internship and allocation statuses based on dates.

- Internships in ALLOCATED status become ACTIVE once their start date arrives.
- Internships in ACTIVE status become COMPLETED once their end date has passed.
- Active allocations are aligned with their internship status.
- Sends attendance warnings to students below the threshold.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from attendance.services import send_attendance_warnings
from internships.models import Internship, InternshipAllocation, InternshipStatus
from notifications.services import create_notification


class Command(BaseCommand):
    help = "Advance internship statuses based on dates and send attendance warnings."

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.localdate()

        started = Internship.objects.filter(
            status=InternshipStatus.ALLOCATED, start_date__lte=today
        )
        for internship in started:
            internship.status = InternshipStatus.ACTIVE
            internship.save(update_fields=["status", "updated_at"])
            _notify_internship_change(
                internship, "Internship Started",
                f"Your internship '{internship.title}' has started.",
            )
        self.stdout.write(f"Started {started.count()} internship(s).")

        finished = Internship.objects.filter(
            status=InternshipStatus.ACTIVE, end_date__lt=today
        )
        for internship in finished:
            internship.status = InternshipStatus.COMPLETED
            internship.save(update_fields=["status", "updated_at"])
            _notify_internship_change(
                internship, "Internship Completed",
                f"Your internship '{internship.title}' has been marked completed.",
            )
        self.stdout.write(f"Completed {finished.count()} internship(s).")

        aligned_allocations = 0
        for internship in started:
            aligned_allocations += InternshipAllocation.objects.filter(
                internship=internship, status="ALLOCATED"
            ).update(status="ACTIVE")
        for internship in finished:
            aligned_allocations += InternshipAllocation.objects.filter(
                internship=internship, status="ACTIVE"
            ).update(status="COMPLETED")
        self.stdout.write(f"Aligned {aligned_allocations} allocation(s).")

        warnings = send_attendance_warnings()
        self.stdout.write(self.style.SUCCESS(f"Sent {warnings} attendance warning(s)."))


def _notify_internship_change(internship, title, message):
    for allocation in internship.allocations.select_related("student", "student__user"):
        create_notification(
            recipient=allocation.student.user,
            title=title,
            message=message,
            notification_type="ALLOCATION",
            related_url="/student/internship/",
        )
