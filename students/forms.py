"""Forms used in the student portal."""
from django import forms

from accounts.forms import StudentProfileForm
from internships.models import InternshipApplication
from tasks.models import Task, TaskStatus


class StudentProfileEditForm(StudentProfileForm):
    class Meta(StudentProfileForm.Meta):
        fields = (
            "full_name",
            "email",
            "phone",
            "date_of_birth",
            "gender",
            "department",
            "course",
            "year",
            "semester",
            "address",
            "city",
            "state",
            "profile_photo",
            "resume",
            "skills",
            "cgpa",
        )


class TaskUpdateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("progress_percentage", "student_comments", "status", "attachment")
        widgets = {
            "progress_percentage": forms.NumberInput(attrs={"min": 0, "max": 100}),
            "student_comments": forms.Textarea(attrs={"rows": 3}),
            "status": forms.Select(
                choices=[
                    (TaskStatus.PENDING, "Pending"),
                    (TaskStatus.IN_PROGRESS, "In Progress"),
                    (TaskStatus.SUBMITTED, "Submitted"),
                ]
            ),
        }


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = InternshipApplication
        fields = ("cover_letter",)
        widgets = {"cover_letter": forms.Textarea(attrs={"rows": 4})}
