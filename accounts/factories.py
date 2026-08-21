"""Test data factories for building role users and related objects quickly."""
import uuid

from django.contrib.auth import get_user_model

from accounts.models import (
    CollegeProfile,
    CompanyProfile,
    FacultyProfile,
    StudentProfile,
)
from internships.models import CompanySupervisor, Internship, InternshipStatus

User = get_user_model()
PASSWORD = "pass12345"


def create_user(username, role, **extra):
    user = User(username=username, email=f"{username}@example.test", role=role, **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


def _suffix():
    return uuid.uuid4().hex[:8]


def create_college(username="college"):
    user = create_user(username, User.Role.COLLEGE)
    return CollegeProfile.objects.create(
        user=user,
        college_name=f"{username} University",
        college_code=f"UC{_suffix().upper()}",
    )


def create_faculty(college, username="faculty"):
    user = create_user(username, User.Role.FACULTY)
    return FacultyProfile.objects.create(
        user=user,
        employee_id=f"EMP-{_suffix()}",
        full_name=f"Prof {username}",
        email=user.email,
        college=college,
    )


def create_company(username="company"):
    user = create_user(username, User.Role.COMPANY)
    return CompanyProfile.objects.create(
        user=user,
        company_name=f"{username} Corp",
        company_code=f"C{_suffix().upper()}",
        email=user.email,
    )


def create_student(college, username="student"):
    user = create_user(username, User.Role.STUDENT)
    return StudentProfile.objects.create(
        user=user,
        student_id=f"STU-{_suffix()}",
        full_name=username.title(),
        email=user.email,
        college=college,
    )


def create_supervisor(company, username="supervisor", pin="1234"):
    user = create_user(username, User.Role.SUPERVISOR)
    supervisor = CompanySupervisor.objects.create(
        user=user,
        company=company,
        name=f"{username.title()} Supervisor",
        email=user.email,
        is_active=True,
    )
    supervisor.set_pin(pin)
    supervisor.save(update_fields=["pin"])
    return supervisor


def create_internship(
    company,
    title="Software Intern",
    status=InternshipStatus.APPROVED,
    start=None,
    end=None,
):
    internship = Internship.objects.create(
        title=f"{title} {_suffix()}",
        company=company,
        status=status,
        available_positions=3,
    )
    if start and end:
        internship.start_date = start
        internship.end_date = end
        internship.save(update_fields=["start_date", "end_date"])
    return internship
