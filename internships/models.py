"""Internship, application, allocation and status tracking models."""
from django.db import models
from django.utils import timezone

from accounts.models import CompanyProfile, StudentProfile, User


class InternshipStatus(models.TextChoices):
    APPLIED = "APPLIED", "Applied"
    APPROVED = "APPROVED", "Approved"
    ALLOCATED = "ALLOCATED", "Allocated"
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class InternshipType(models.TextChoices):
    ONSITE = "ONSITE", "On-site"
    REMOTE = "REMOTE", "Remote"
    HYBRID = "HYBRID", "Hybrid"


class ApplicationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class AllocationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"
    TERMINATED = "TERMINATED", "Terminated"


class Internship(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    company = models.ForeignKey(
        CompanyProfile, on_delete=models.CASCADE, related_name="internships"
    )
    location = models.CharField(max_length=200, blank=True)
    internship_type = models.CharField(
        max_length=20, choices=InternshipType.choices, default=InternshipType.ONSITE
    )
    skills_required = models.TextField(blank=True)
    stipend = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    duration = models.CharField(max_length=100, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    available_positions = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=InternshipStatus.choices,
        default=InternshipStatus.APPLIED,
        db_index=True,
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_internships"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["start_date", "end_date"]),
        ]

    def __str__(self):
        return f"{self.title} @ {self.company.company_name}"

    def transition_to(self, new_status, changed_by=None, reason=""):
        """Persist a status transition in the history log."""
        if self.status == new_status:
            return False
        InternshipStatusHistory.objects.create(
            internship=self,
            old_status=self.status,
            new_status=new_status,
            changed_by=changed_by,
            reason=reason,
        )
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])
        return True


class InternshipApplication(models.Model):
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="applications"
    )
    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="applications"
    )
    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
        db_index=True,
    )
    cover_letter = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-applied_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "internship"], name="unique_application"
            )
        ]

    def __str__(self):
        return f"{self.student.full_name} -> {self.internship.title}"


class InternshipAllocation(models.Model):
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="allocations"
    )
    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="allocations"
    )
    allocated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="made_allocations"
    )
    allocation_date = models.DateField(default=timezone.localdate)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=AllocationStatus.choices,
        default=AllocationStatus.ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-allocation_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["student"],
                condition=models.Q(status=AllocationStatus.ACTIVE),
                name="unique_active_allocation_per_student",
            )
        ]

    def __str__(self):
        return f"{self.student.full_name} / {self.internship.title}"


class InternshipStatusHistory(models.Model):
    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="status_history"
    )
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.internship.title}: {self.old_status} -> {self.new_status}"


class FacultyAssignment(models.Model):
    """Links a faculty mentor to a student for a specific internship."""

    faculty = models.ForeignKey(
        "accounts.FacultyProfile", on_delete=models.CASCADE, related_name="assignments"
    )
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="faculty_assignments"
    )
    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="faculty_assignments"
    )
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="made_assignments"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "internship"],
                condition=models.Q(active=True),
                name="unique_active_assignment_per_internship",
            )
        ]

    def __str__(self):
        return f"{self.faculty.full_name} -> {self.student.full_name}"


class SupervisorAssignment(models.Model):
    """Links a company supervisor to a student for a specific internship."""

    supervisor = models.ForeignKey(
        "CompanySupervisor", on_delete=models.CASCADE, related_name="assignments"
    )
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="supervisor_assignments"
    )
    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="supervisor_assignments"
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="made_supervisor_assignments",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "internship"],
                condition=models.Q(active=True),
                name="unique_active_supervisor_assignment_per_internship",
            )
        ]

    def __str__(self):
        return f"{self.supervisor.name} -> {self.student.full_name}"


class CompanySupervisor(models.Model):
    company = models.ForeignKey(
        CompanyProfile, on_delete=models.CASCADE, related_name="supervisors"
    )
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervisor_profile",
    )
    name = models.CharField(max_length=150)
    designation = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    pin = models.CharField(
        "Password/PIN",
        max_length=128,
        blank=True,
        help_text="Hashed verification PIN used by the company to verify "
        "this supervisor before accessing their intern view.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.company.company_name})"

    def set_pin(self, raw_pin):
        """Hash and store the supervisor verification PIN."""
        from django.contrib.auth.hashers import make_password

        self.pin = make_password(raw_pin)

    def verify_pin(self, raw_pin):
        """Return True if the raw PIN matches the stored hashed PIN."""
        if not self.pin:
            return False
        from django.contrib.auth.hashers import check_password

        return check_password(raw_pin, self.pin)
