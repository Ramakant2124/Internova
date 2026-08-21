"""Forms for the accounts application."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import (
    CollegeProfile,
    CompanyProfile,
    FacultyProfile,
    StudentProfile,
    User,
)


class RoleAuthenticationForm(AuthenticationForm):
    """AuthenticationForm that only authenticates users of a given role."""

    role = None

    def confirm_login_allowed(self, user):
        if user.role != self.role:
            raise forms.ValidationError(
                "This account does not have access to this portal. Please use the correct login page.",
                code="invalid_role",
            )
        super().confirm_login_allowed(user)


class StudentAuthenticationForm(RoleAuthenticationForm):
    role = User.Role.STUDENT


class CollegeAuthenticationForm(RoleAuthenticationForm):
    role = User.Role.COLLEGE


class FacultyAuthenticationForm(RoleAuthenticationForm):
    role = User.Role.FACULTY


class CompanyAuthenticationForm(RoleAuthenticationForm):
    role = User.Role.COMPANY


class SupervisorAuthenticationForm(RoleAuthenticationForm):
    role = User.Role.SUPERVISOR


class StudentSignupForm(UserCreationForm):
    """Used by the college to create student accounts."""

    email = forms.EmailField(required=True)
    full_name = forms.CharField(max_length=150, label="Full Name")
    student_id = forms.CharField(max_length=30, label="Student ID")

    class Meta:
        model = User
        fields = ("username", "email")

    def save(self, commit=True):
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
            )
        return user


class FacultyUserForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email")


class CompanyUserForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email")


class CollegeProfileForm(forms.ModelForm):
    class Meta:
        model = CollegeProfile
        fields = (
            "college_name",
            "college_code",
            "address",
            "city",
            "state",
            "contact_email",
            "contact_phone",
            "website",
        )
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "contact_email": forms.EmailInput(),
        }


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = (
            "student_id",
            "full_name",
            "email",
            "phone",
            "date_of_birth",
            "gender",
            "department",
            "course",
            "year",
            "semester",
            "college",
            "address",
            "city",
            "state",
            "profile_photo",
            "resume",
            "skills",
            "cgpa",
        )
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3}),
            "skills": forms.Textarea(attrs={"rows": 3}),
        }


class FacultyProfileForm(forms.ModelForm):
    class Meta:
        model = FacultyProfile
        fields = (
            "employee_id",
            "full_name",
            "department",
            "designation",
            "phone",
            "email",
            "college",
            "specialization",
        )


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = (
            "company_name",
            "company_code",
            "industry",
            "description",
            "website",
            "email",
            "phone",
            "address",
            "city",
            "state",
            "logo",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }


class RoleChangeForm(forms.Form):
    """Used by college to change a user's password / role status."""

    new_password = forms.CharField(
        label="New Password",
        required=False,
        widget=forms.PasswordInput,
        min_length=8,
    )


class BasicInfoForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")
