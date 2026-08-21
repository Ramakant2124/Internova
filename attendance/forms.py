"""Forms for recording attendance."""
from django import forms

from accounts.models import StudentProfile

from .models import AttendanceStatus


class AttendanceMarkForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    status = forms.ChoiceField(choices=AttendanceStatus.choices)
    check_in = forms.TimeField(
        required=False, widget=forms.TimeInput(attrs={"type": "time"})
    )
    check_out = forms.TimeField(
        required=False, widget=forms.TimeInput(attrs={"type": "time"})
    )
    remarks = forms.CharField(max_length=255, required=False)
    student = forms.ModelChoiceField(
        queryset=StudentProfile.objects.none(), empty_label="Select a student"
    )

    def __init__(self, *args, students=None, **kwargs):
        super().__init__(*args, **kwargs)
        if students is not None:
            self.fields["student"].queryset = students
