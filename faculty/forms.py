"""Forms for the faculty portal."""
from django import forms

from progress.models import Feedback, PerformanceEvaluation


class EvaluationCreateForm(forms.ModelForm):
    class Meta:
        model = PerformanceEvaluation
        fields = (
            "technical_skills",
            "communication",
            "professionalism",
            "task_completion",
            "punctuality",
            "teamwork",
            "comments",
        )
        widgets = {
            "technical_skills": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "communication": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "professionalism": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "task_completion": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "punctuality": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "teamwork": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "comments": forms.Textarea(attrs={"rows": 4}),
        }


class FacultyFeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ("rating", "comments")
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "comments": forms.Textarea(attrs={"rows": 4}),
        }
