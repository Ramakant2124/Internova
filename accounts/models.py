"""Custom user model and role-specific profiles."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Application user. Roles are fixed to the four primary portals."""

    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        COLLEGE = "COLLEGE", "College"
        FACULTY = "FACULTY", "Faculty"
        COMPANY = "COMPANY", "Company"
        SUPERVISOR = "SUPERVISOR", "Supervisor"

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.STUDENT, db_index=True
    )
    email = models.EmailField("email address", unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    REQUIRED_FIELDS = ["email", "role"]

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def get_profile(self):
        """Return the role-specific profile instance or None."""
        mapping = {
            self.Role.STUDENT: getattr(self, "student_profile", None),
            self.Role.COLLEGE: getattr(self, "college_profile", None),
            self.Role.FACULTY: getattr(self, "faculty_profile", None),
            self.Role.COMPANY: getattr(self, "company_profile", None),
            self.Role.SUPERVISOR: getattr(self, "supervisor_profile", None),
        }
        return mapping.get(self.role)

    @property
    def display_name(self):
        profile = self.get_profile()
        if profile and getattr(profile, "full_name", None):
            return profile.full_name
        if profile and getattr(profile, "company_name", None):
            return profile.company_name
        if profile and getattr(profile, "college_name", None):
            return profile.college_name
        if profile and getattr(profile, "name", None):
            return profile.name
        return self.username


class StudentProfile(models.Model):
    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile"
    )
    student_id = models.CharField(max_length=30, unique=True, db_index=True)
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    department = models.CharField(max_length=150, blank=True)
    course = models.CharField(max_length=150, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    semester = models.PositiveSmallIntegerField(null=True, blank=True)
    college = models.ForeignKey(
        "CollegeProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    profile_photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)
    resume = models.FileField(upload_to="resumes/", blank=True)
    skills = models.TextField(blank=True)
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]
        indexes = [models.Index(fields=["department", "year"])]

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"


class CollegeProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="college_profile"
    )
    college_name = models.CharField(max_length=200)
    college_code = models.CharField(max_length=30, unique=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["college_name"]

    def __str__(self):
        return self.college_name


class FacultyProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="faculty_profile"
    )
    employee_id = models.CharField(max_length=30, unique=True)
    full_name = models.CharField(max_length=150)
    department = models.CharField(max_length=150, blank=True)
    designation = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    college = models.ForeignKey(
        CollegeProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faculty_members",
    )
    specialization = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"


class CompanyProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="company_profile"
    )
    company_name = models.CharField(max_length=200)
    company_code = models.CharField(max_length=30, unique=True)
    industry = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    logo = models.ImageField(upload_to="company_logos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company_name"]

    def __str__(self):
        return self.company_name
