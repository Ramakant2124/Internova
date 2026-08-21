"""Attendance tracking model."""
from django.db import models

from accounts.models import StudentProfile, User
from internships.models import CompanySupervisor, Internship


class AttendanceStatus(models.TextChoices):
    PRESENT = "PRESENT", "Present"
    ABSENT = "ABSENT", "Absent"
    HALF_DAY = "HALF_DAY", "Half Day"
    LEAVE = "LEAVE", "Leave"


class Attendance(models.Model):
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="attendance"
    )
    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="attendance"
    )
    supervisor = models.ForeignKey(
        CompanySupervisor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
    )
    marked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_marked",
    )
    date = models.DateField(db_index=True)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
        db_index=True,
    )
    remarks = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "internship", "date"],
                name="unique_attendance_per_day",
            )
        ]

    def __str__(self):
        return f"{self.student.full_name} - {self.date} ({self.get_status_display()})"

    @property
    def present_equivalent(self):
        if self.status == AttendanceStatus.PRESENT:
            return 1.0
        if self.status == AttendanceStatus.HALF_DAY:
            return 0.5
        return 0.0
