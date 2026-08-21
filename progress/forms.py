"""Forms for work logs, weekly progress, evaluation and feedback."""
from django import forms

from .models import (
    DailyWorkLog,
    Feedback,
    PerformanceEvaluation,
    ReviewStatus,
    WeeklyProgress,
)


class DailyWorkLogForm(forms.ModelForm):
    class Meta:
        model = DailyWorkLog
        fields = (
            "date",
            "work_description",
            "hours_worked",
            "tasks_completed",
            "challenges",
            "learning_skills",
            "attachment",
        )
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "work_description": forms.Textarea(attrs={"rows": 4}),
            "tasks_completed": forms.Textarea(attrs={"rows": 3}),
            "challenges": forms.Textarea(attrs={"rows": 3}),
            "learning_skills": forms.Textarea(attrs={"rows": 3}),
        }


class WeeklyProgressForm(forms.ModelForm):
    class Meta:
        model = WeeklyProgress
        fields = (
            "week_start",
            "week_end",
            "summary",
            "completed_tasks",
            "challenges",
            "learnings",
            "next_week_plan",
            "progress_percentage",
            "attachment",
        )
        widgets = {
            "week_start": forms.DateInput(attrs={"type": "date"}),
            "week_end": forms.DateInput(attrs={"type": "date"}),
            "summary": forms.Textarea(attrs={"rows": 4}),
            "completed_tasks": forms.Textarea(attrs={"rows": 3}),
            "challenges": forms.Textarea(attrs={"rows": 3}),
            "learnings": forms.Textarea(attrs={"rows": 3}),
            "next_week_plan": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("week_start")
        end = cleaned.get("week_end")
        if start and end and end < start:
            raise forms.ValidationError("Week end cannot be before week start.")
        return cleaned


class ReviewForm(forms.Form):
    action = forms.ChoiceField(
        choices=[
            (ReviewStatus.APPROVED, "Approve"),
            (ReviewStatus.REJECTED, "Reject"),
            (ReviewStatus.CHANGES_REQUESTED, "Request Changes"),
        ]
    )
    comments = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Review comments"})
    )


class EvaluationForm(forms.ModelForm):
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


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ("rating", "comments")
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "comments": forms.Textarea(attrs={"rows": 4}),
        }
