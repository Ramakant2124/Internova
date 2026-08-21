"""Daily work logs, weekly progress, evaluation, feedback and approvals."""
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from accounts.models import FacultyProfile, StudentProfile, User
from internships.models import Internship


class ReviewStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CHANGES_REQUESTED = "CHANGES_REQUESTED", "Changes Requested"


class DailyWorkLog(models.Model):
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="work_logs"
    )
    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="work_logs"
    )
    date = models.DateField(db_index=True)
    work_description = models.TextField()
    hours_worked = models.DecimalField(
        max_digits=4, decimal_places=1, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
    )
    tasks_completed = models.TextField(blank=True)
    challenges = models.TextField(blank=True)
    learning_skills = models.TextField(blank=True)
    attachment = models.FileField(upload_to="work_log_attachments/", blank=True)
    status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING, db_index=True
    )
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_work_logs"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "internship", "date"],
                name="unique_work_log_per_day",
            )
        ]

    def __str__(self):
        return f"{self.student.full_name} - {self.date}"


class WeeklyProgress(models.Model):
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="weekly_progress"
    )
    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="weekly_progress"
    )
    week_start = models.DateField(db_index=True)
    week_end = models.DateField(db_index=True)
    summary = models.TextField(blank=True)
    completed_tasks = models.TextField(blank=True)
    challenges = models.TextField(blank=True)
    learnings = models.TextField(blank=True)
    next_week_plan = models.TextField(blank=True)
    progress_percentage = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(100), MinValueValidator(0)]
    )
    attachment = models.FileField(upload_to="weekly_progress_attachments/", blank=True)
    status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING, db_index=True
    )
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_progress"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-week_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "internship", "week_start"],
                name="unique_weekly_report",
            )
        ]

    def __str__(self):
        return f"{self.student.full_name} - week of {self.week_start}"


class PerformanceEvaluation(models.Model):
    RATINGS = [(i, str(i)) for i in range(1, 6)]

    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="evaluations"
    )
    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="evaluations"
    )
    faculty = models.ForeignKey(
        FacultyProfile, on_delete=models.CASCADE, related_name="evaluations"
    )
    technical_skills = models.PositiveSmallIntegerField(choices=RATINGS)
    communication = models.PositiveSmallIntegerField(choices=RATINGS)
    professionalism = models.PositiveSmallIntegerField(choices=RATINGS)
    task_completion = models.PositiveSmallIntegerField(choices=RATINGS)
    punctuality = models.PositiveSmallIntegerField(choices=RATINGS)
    teamwork = models.PositiveSmallIntegerField(choices=RATINGS)
    overall_performance = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True
    )
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "internship", "faculty"],
                name="unique_evaluation",
            )
        ]

    def __str__(self):
        return f"Evaluation of {self.student.full_name} by {self.faculty.full_name}"

    def save(self, *args, **kwargs):
        ratings = [
            self.technical_skills, self.communication, self.professionalism,
            self.task_completion, self.punctuality, self.teamwork,
        ]
        self.overall_performance = round(sum(ratings) / len(ratings), 2)
        super().save(*args, **kwargs)


class Feedback(models.Model):
    class FeedbackType(models.TextChoices):
        FACULTY = "FACULTY", "Faculty"
        COMPANY = "COMPANY", "Company"
        COLLEGE = "COLLEGE", "College"

    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="feedback"
    )
    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="feedback"
    )
    given_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="given_feedback"
    )
    feedback_type = models.CharField(max_length=20, choices=FeedbackType.choices)
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)], null=True, blank=True
    )
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Feedback for {self.student.full_name} ({self.feedback_type})"


class Approval(models.Model):
    class ApprovalType(models.TextChoices):
        INTERNSHIP_APPLICATION = "INTERNSHIP_APPLICATION", "Internship Application"
        DAILY_WORK_LOG = "DAILY_WORK_LOG", "Daily Work Log"
        WEEKLY_PROGRESS = "WEEKLY_PROGRESS", "Weekly Progress"
        DOCUMENT = "DOCUMENT", "Document"
        CERTIFICATE = "CERTIFICATE", "Certificate"
        COMPLETION = "COMPLETION", "Completion"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    approval_type = models.CharField(max_length=40, choices=ApprovalType.choices)
    requested_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="requested_approvals"
    )
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_approvals"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["content_type", "object_id", "approval_type"])]

    def __str__(self):
        return f"{self.approval_type} ({self.status})"
