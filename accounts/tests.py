# accounts module

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .factories import (
    create_college,
    create_company,
    create_faculty,
    create_student,
    create_supervisor,
)


class ProfileCreationTest(TestCase):
    def test_student_display_name_uses_profile(self):
        college = create_college()
        student = create_student(college)
        self.assertEqual(student.user.get_profile(), student)
        self.assertEqual(student.user.display_name, student.full_name)

    def test_company_display_name_uses_company_name(self):
        company = create_company()
        self.assertEqual(company.user.display_name, company.company_name)

    def test_college_display_name_uses_college_name(self):
        college = create_college()
        self.assertEqual(college.user.display_name, college.college_name)

    def test_roles_are_set_on_user(self):
        User = get_user_model()
        college = create_college()
        faculty = create_faculty(college)
        company = create_company()
        student = create_student(college)
        self.assertEqual(college.user.role, User.Role.COLLEGE)
        self.assertEqual(faculty.user.role, User.Role.FACULTY)
        self.assertEqual(company.user.role, User.Role.COMPANY)
        self.assertEqual(student.user.role, User.Role.STUDENT)

    def test_supervisor_display_name_uses_supervisor_name(self):
        company = create_company()
        supervisor = create_supervisor(company)
        self.assertEqual(supervisor.user.role, "SUPERVISOR")
        self.assertEqual(supervisor.user.get_profile(), supervisor)
        self.assertEqual(supervisor.user.display_name, supervisor.name)


class AuthAndRoleGuardTest(TestCase):
    def test_unauthenticated_user_redirected_to_login(self):
        response = self.client.get("/student/dashboard/")
        self.assertRedirects(response, "/home/?next=/student/dashboard/")

    def test_student_blocked_from_college_portal(self):
        college = create_college()
        student = create_student(college)
        self.client.force_login(student.user)
        response = self.client.get("/college/dashboard/")
        self.assertEqual(response.status_code, 403)

    def test_student_blocked_from_company_portal(self):
        college = create_college()
        student = create_student(college)
        self.client.force_login(student.user)
        self.assertEqual(self.client.get("/company/dashboard/").status_code, 403)

    def test_faculty_blocked_from_college_portal(self):
        college = create_college()
        faculty = create_faculty(college)
        self.client.force_login(faculty.user)
        self.assertEqual(self.client.get("/college/dashboard/").status_code, 403)

    def test_company_blocked_from_faculty_portal(self):
        college = create_college()
        company = create_company()
        self.client.force_login(company.user)
        self.assertEqual(self.client.get("/faculty/dashboard/").status_code, 403)

    def test_supervisor_blocked_from_company_portal(self):
        company = create_company()
        supervisor = create_supervisor(company)
        self.client.force_login(supervisor.user)
        self.assertEqual(self.client.get("/company/dashboard/").status_code, 403)

    def test_supervisor_login_redirects_to_dashboard(self):
        company = create_company()
        supervisor = create_supervisor(company)
        response = self.client.post(
            reverse("accounts:supervisor_login"),
            {"username": supervisor.user.username, "password": "pass12345"},
        )
        self.assertRedirects(
            response,
            reverse("supervisors:dashboard", args=[supervisor.pk]),
            fetch_redirect_response=False,
        )

    def test_login_with_password(self):
        college = create_college()
        logged_in = self.client.login(
            username=college.user.username, password="pass12345"
        )
        self.assertTrue(logged_in)

    def test_wrong_password_fails(self):
        college = create_college()
        logged_in = self.client.login(
            username=college.user.username, password="wrong-pass"
        )
        self.assertFalse(logged_in)
