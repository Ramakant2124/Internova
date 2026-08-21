"""Forms for the college portal."""
from django import forms
from django.contrib.auth.forms import UserCreationForm

from accounts.models import (
    CollegeProfile,
    CompanyProfile,
    FacultyProfile,
    StudentProfile,
    User,
)
from attendance.models import AttendanceStatus
from internships.models import Internship, InternshipAllocation, InternshipApplication
from progress.models import WeeklyProgress


class StudentCreateForm(UserCreationForm):
    email = forms.EmailField(required=True)
    full_name = forms.CharField(max_length=150)
    student_id = forms.CharField(max_length=30)
    phone = forms.CharField(max_length=20, required=False)
    department = forms.CharField(max_length=150, required=False)
    course = forms.CharField(max_length=150, required=False)
    year = forms.IntegerField(required=False, min_value=1, max_value=6)
    semester = forms.IntegerField(required=False, min_value=1, max_value=12)
    city = forms.CharField(max_length=100, required=False)
    state = forms.CharField(max_length=100, required=False)
    cgpa = forms.DecimalField(max_digits=4, decimal_places=2, required=False)
    skills = forms.CharField(widget=forms.Textarea, required=False)
    username = forms.CharField(help_text="Required. Login username for the student.")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_student_id(self):
        student_id = self.cleaned_data["student_id"]
        if StudentProfile.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError("A student with this ID already exists.")
        return student_id

    def save(self, college=None, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                student_id=self.cleaned_data["student_id"],
                full_name=self.cleaned_data["full_name"],
                email=user.email,
                phone=self.cleaned_data.get("phone", ""),
                department=self.cleaned_data.get("department", ""),
                course=self.cleaned_data.get("course", ""),
                year=self.cleaned_data.get("year"),
                semester=self.cleaned_data.get("semester"),
                city=self.cleaned_data.get("city", ""),
                state=self.cleaned_data.get("state", ""),
                cgpa=self.cleaned_data.get("cgpa"),
                skills=self.cleaned_data.get("skills", ""),
                college=college,
            )
        return user


class StudentEditForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = (
            "student_id", "full_name", "email", "phone", "date_of_birth", "gender",
            "department", "course", "year", "semester", "college", "address",
            "city", "state", "profile_photo", "resume", "skills", "cgpa",
        )
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3}),
            "skills": forms.Textarea(attrs={"rows": 3}),
        }


class StudentPasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput, min_length=8, label="New Password"
    )


class CompanyCreateForm(UserCreationForm):
    email = forms.EmailField(required=True)
    company_name = forms.CharField(max_length=200)
    company_code = forms.CharField(max_length=30)
    industry = forms.CharField(max_length=100, required=False)
    city = forms.CharField(max_length=100, required=False)
    state = forms.CharField(max_length=100, required=False)
    phone = forms.CharField(max_length=20, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_company_code(self):
        code = self.cleaned_data["company_code"]
        if self.instance.pk is None:
            from accounts.models import CompanyProfile

            if CompanyProfile.objects.filter(company_code=code).exists():
                raise forms.ValidationError("A company with this code already exists.")
        return code

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.COMPANY
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            from accounts.models import CompanyProfile

            CompanyProfile.objects.create(
                user=user,
                company_name=self.cleaned_data["company_name"],
                company_code=self.cleaned_data["company_code"],
                industry=self.cleaned_data.get("industry", ""),
                email=user.email,
                phone=self.cleaned_data.get("phone", ""),
                city=self.cleaned_data.get("city", ""),
                state=self.cleaned_data.get("state", ""),
            )
        return user


class FacultyCreateForm(UserCreationForm):
    email = forms.EmailField(required=True)
    full_name = forms.CharField(max_length=150)
    employee_id = forms.CharField(max_length=30)
    department = forms.CharField(max_length=150, required=False)
    designation = forms.CharField(max_length=150, required=False)
    phone = forms.CharField(max_length=20, required=False)
    specialization = forms.CharField(max_length=200, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_employee_id(self):
        employee_id = self.cleaned_data["employee_id"]
        if FacultyProfile.objects.filter(employee_id=employee_id).exists():
            raise forms.ValidationError("A faculty member with this ID already exists.")
        return employee_id

    def save(self, college=None, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.FACULTY
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            FacultyProfile.objects.create(
                user=user,
                employee_id=self.cleaned_data["employee_id"],
                full_name=self.cleaned_data["full_name"],
                department=self.cleaned_data.get("department", ""),
                designation=self.cleaned_data.get("designation", ""),
                phone=self.cleaned_data.get("phone", ""),
                email=user.email,
                college=college,
                specialization=self.cleaned_data.get("specialization", ""),
            )
        return user


class FacultyEditForm(forms.ModelForm):
    class Meta:
        model = FacultyProfile
        fields = (
            "employee_id", "full_name", "department", "designation",
            "phone", "email", "college", "specialization",
        )


class CompanyProfileEditForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = (
            "company_name", "company_code", "industry", "description",
            "website", "email", "phone", "address", "city", "state", "logo",
        )


class AllocationForm(forms.ModelForm):
    class Meta:
        model = InternshipAllocation
        fields = ("student", "internship", "start_date", "end_date")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class AttendanceMarkForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    status = forms.ChoiceField(choices=AttendanceStatus.choices)
    remarks = forms.CharField(max_length=255, required=False)
    student = forms.ModelChoiceField(queryset=StudentProfile.objects.none(), empty_label="Select a student")

    def __init__(self, *args, students=None, **kwargs):
        super().__init__(*args, **kwargs)
        if students is not None:
            self.fields["student"].queryset = students


class InternshipForm(forms.ModelForm):
    class Meta:
        model = Internship
        fields = (
            "title", "description", "company", "location", "internship_type",
            "skills_required", "stipend", "duration", "start_date", "end_date",
            "available_positions", "status",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "skills_required": forms.Textarea(attrs={"rows": 3}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class ApplicationReviewForm(forms.Form):
    comments = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
