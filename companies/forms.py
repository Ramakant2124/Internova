"""Forms for the company portal."""
from django import forms

from accounts.forms import CompanyProfileForm
from accounts.models import StudentProfile
from documents.validators import validate_file_extension, validate_file_size
from internships.models import (
    CompanySupervisor,
    Internship,
    InternshipAllocation,
    InternshipStatus,
)
from progress.models import Feedback
from tasks.models import Task, TaskPriority


class CompanyInternshipForm(forms.ModelForm):
    class Meta:
        model = Internship
        fields = (
            "title",
            "description",
            "location",
            "internship_type",
            "skills_required",
            "stipend",
            "duration",
            "start_date",
            "end_date",
            "available_positions",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "skills_required": forms.Textarea(attrs={"rows": 3}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            raise forms.ValidationError("End date cannot be before start date.")
        return cleaned

    def save(self, company, user, commit=True):
        internship = super().save(commit=False)
        internship.company = company
        if not internship.pk:
            internship.status = InternshipStatus.APPLIED
            internship.created_by = user
        if commit:
            internship.save()
        return internship


class CompanyTaskForm(forms.ModelForm):
    """Task assignment form: Intern + Supervisor selection is mandatory."""

    student = forms.ModelChoiceField(
        queryset=StudentProfile.objects.none(),
        label="Intern / Student",
        empty_label="Select an intern",
    )
    supervisor = forms.ModelChoiceField(
        queryset=CompanySupervisor.objects.none(),
        label="Supervisor",
        empty_label="Select a supervisor",
    )

    class Meta:
        model = Task
        fields = (
            "student",
            "supervisor",
            "title",
            "description",
            "due_date",
            "priority",
            "attachment",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        if company is not None:
            allocated_ids = InternshipAllocation.objects.filter(
                internship__company=company, status="ACTIVE"
            ).values_list("student_id", flat=True)
            self.fields["student"].queryset = StudentProfile.objects.filter(
                id__in=allocated_ids
            ).order_by("full_name")
            self.fields["supervisor"].queryset = CompanySupervisor.objects.filter(
                company=company, is_active=True
            ).order_by("name")
        self.fields["priority"].initial = TaskPriority.MEDIUM

    def clean(self):
        cleaned = super().clean()
        student = cleaned.get("student")
        supervisor = cleaned.get("supervisor")
        company = self.company
        if student and company is not None:
            allocation = (
                student.allocations.filter(
                    internship__company=company, status="ACTIVE"
                )
                .select_related("internship")
                .first()
            )
            if not allocation:
                self.add_error(
                    "student",
                    "This intern has no active internship with your company.",
                )
            else:
                cleaned["_allocation"] = allocation
        if supervisor and company is not None and supervisor.company_id != company.pk:
            self.add_error("supervisor", "This supervisor does not belong to your company.")
        return cleaned


class SupervisorAssignForm(forms.Form):
    """Assign a company supervisor to an allocated intern."""

    supervisor = forms.ModelChoiceField(
        queryset=CompanySupervisor.objects.none(),
        label="Supervisor",
        empty_label="Select a supervisor",
    )

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields["supervisor"].queryset = CompanySupervisor.objects.filter(
                company=company, is_active=True
            ).order_by("name")


class SupervisorVerifyForm(forms.Form):
    """Verify a supervisor before entering the Intern Attendance flow."""

    supervisor = forms.ModelChoiceField(
        queryset=CompanySupervisor.objects.none(),
        label="Select Supervisor",
        empty_label="Select a supervisor",
    )
    pin = forms.CharField(
        label="Supervisor Password / PIN",
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}),
        strip=False,
    )

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields["supervisor"].queryset = CompanySupervisor.objects.filter(
                company=company, is_active=True
            ).order_by("name")

    def clean(self):
        cleaned = super().clean()
        supervisor = cleaned.get("supervisor")
        pin = cleaned.get("pin", "")
        if supervisor and not supervisor.verify_pin(pin):
            self.add_error("pin", "Invalid supervisor PIN / password.")
        return cleaned


class CompanyFeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ("rating", "comments")
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "comments": forms.Textarea(attrs={"rows": 4}),
        }


class CertificateUploadForm(forms.Form):
    certificate_file = forms.FileField(
        validators=[validate_file_extension, validate_file_size]
    )
    issue_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))


class CompletionRequestForm(forms.Form):
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Reason / summary"}),
    )
