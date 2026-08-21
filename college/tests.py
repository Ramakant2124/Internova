# college module

from django.test import TestCase
from django.urls import reverse

from accounts.factories import (
    create_college,
    create_company,
    create_faculty,
    create_internship,
    create_student,
)
from accounts.models import User
from internships.models import ApplicationStatus
from internships.services import apply_to_internship


class CollegePortalTest(TestCase):
    def setUp(self):
        self.college = create_college()
        self.company = create_company()
        self.client.force_login(self.college.user)

    def test_dashboard_renders(self):
        self.assertEqual(
            self.client.get(reverse("college:dashboard")).status_code, 200
        )

    def test_student_add_creates_profile(self):
        response = self.client.post(
            reverse("college:student_add"),
            {
                "username": "new_student",
                "email": "new_student@example.test",
                "full_name": "New Student",
                "student_id": "STU-NEW-1",
                "password1": "Str0ng!Pass",
                "password2": "Str0ng!Pass",
            },
        )
        self.assertRedirects(response, reverse("college:students"))
        new_user = User.objects.get(username="new_student")
        self.assertEqual(new_user.role, User.Role.STUDENT)
        self.assertEqual(new_user.student_profile.full_name, "New Student")

    def test_faculty_add_creates_profile(self):
        response = self.client.post(
            reverse("college:faculty_add"),
            {
                "username": "new_faculty",
                "email": "new_faculty@example.test",
                "full_name": "New Faculty",
                "employee_id": "EMP-NEW-1",
                "password1": "Str0ng!Pass",
                "password2": "Str0ng!Pass",
            },
        )
        self.assertRedirects(response, reverse("college:faculty"))
        new_user = User.objects.get(username="new_faculty")
        self.assertEqual(new_user.role, User.Role.FACULTY)
        self.assertEqual(new_user.faculty_profile.college, self.college)

    def test_application_review_approve(self):
        student = create_student(self.college)
        internship = create_internship(self.company)
        application = apply_to_internship(student, internship, "Please accept me")
        response = self.client.post(
            reverse("college:application_review", args=[application.pk]),
            {"decision": "approve", "comments": "Welcome."},
        )
        self.assertRedirects(response, reverse("college:applications"))
        application.refresh_from_db()
        self.assertEqual(application.status, ApplicationStatus.APPROVED)

    def test_invalid_decision_redirects(self):
        student = create_student(self.college)
        internship = create_internship(self.company)
        application = apply_to_internship(student, internship)
        response = self.client.post(
            reverse("college:application_review", args=[application.pk]),
            {"decision": "maybe"},
        )
        self.assertRedirects(response, reverse("college:applications"))
        application.refresh_from_db()
        self.assertEqual(application.status, ApplicationStatus.PENDING)

    def test_faculty_cannot_access_college_portal(self):
        faculty = create_faculty(self.college)
        self.client.force_login(faculty.user)
        self.assertEqual(
            self.client.get(reverse("college:dashboard")).status_code, 403
        )
