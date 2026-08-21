"""Forms for internships, applications, allocations and supervisors."""
from django import forms

from .models import (
    CompanySupervisor,
    Internship,
    InternshipAllocation,
    InternshipApplication,
)


class InternshipForm(forms.ModelForm):
    class Meta:
        model = Internship
        fields = (
            "title",
            "description",
            "company",
            "location",
            "internship_type",
            "skills_required",
            "stipend",
            "duration",
            "start_date",
            "end_date",
            "available_positions",
            "status",
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


class InternshipApplicationForm(forms.ModelForm):
    class Meta:
        model = InternshipApplication
        fields = ("cover_letter",)
        widgets = {"cover_letter": forms.Textarea(attrs={"rows": 4})}


class AllocationForm(forms.ModelForm):
    class Meta:
        model = InternshipAllocation
        fields = ("student", "internship", "start_date", "end_date")
        widgets = {
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


class FacultyAssignmentForm(forms.Form):
    faculty = forms.ModelChoiceField(
        queryset=None, label="Faculty Mentor", empty_label="Select a faculty member"
    )

    def __init__(self, *args, faculty_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if faculty_queryset is not None:
            self.fields["faculty"].queryset = faculty_queryset


class SupervisorForm(forms.ModelForm):
    pin = forms.CharField(
        label="Password/PIN",
        required=False,
        max_length=128,
        widget=forms.PasswordInput(attrs={"placeholder": "Set a verification PIN"}),
        help_text="Optional hashed PIN. The company uses it to verify this "
        "supervisor before opening their intern attendance view.",
    )

    class Meta:
        model = CompanySupervisor
        fields = ("name", "designation", "email", "phone", "is_active")

    def save(self, commit=True):
        supervisor = super().save(commit=False)
        raw_pin = self.cleaned_data.get("pin")
        if raw_pin:
            supervisor.set_pin(raw_pin)
        if commit:
            supervisor.save()
        return supervisor
