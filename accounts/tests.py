from django.contrib.auth.password_validation import validate_password
from django.test import TestCase
from django.urls import reverse

from .models import User


class RoleAuthTests(TestCase):
    """Covers: each of the 4 roles has its own login, simple passwords work
    with no complexity requirements, and the student-only
    can_change_password flag behaves as underlying support for the
    (not-yet-built) self-service password-change UI."""

    def _make_user(self, username, role, password="abc"):
        return User.objects.create_user(username=username, password=password, role=role)

    def test_all_four_roles_can_be_created_and_log_in_with_simple_passwords(self):
        roster = [
            ("head_principal", User.Role.PRINCIPAL, "simple1"),
            ("head_counsellor", User.Role.COUNSELLOR, "12345"),
            ("math_teacher", User.Role.TEACHER, "password"),
            ("student_a", User.Role.STUDENT, "1234"),
        ]
        for username, role, password in roster:
            with self.subTest(role=role):
                self._make_user(username, role, password)
                logged_in = self.client.login(username=username, password=password)
                self.assertTrue(logged_in, f"{role} could not log in with a simple password")
                self.client.logout()

    def test_login_view_authenticates_each_role(self):
        for role in [
            User.Role.PRINCIPAL,
            User.Role.COUNSELLOR,
            User.Role.TEACHER,
            User.Role.STUDENT,
        ]:
            with self.subTest(role=role):
                username = f"user_{role}"
                self._make_user(username, role, "simplepass")
                response = self.client.post(
                    reverse("login"), {"username": username, "password": "simplepass"}
                )
                self.assertRedirects(response, reverse("dashboard"))
                self.client.logout()

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_no_password_complexity_requirements(self):
        user = self._make_user("weak_pw_student", User.Role.STUDENT, "1234")
        # Should not raise ValidationError even though "1234" is short/numeric/common.
        validate_password("1234", user=user)

    def test_can_change_password_defaults_false(self):
        user = self._make_user("new_student", User.Role.STUDENT)
        self.assertFalse(user.can_change_password)

    def test_can_change_password_can_be_enabled_for_students(self):
        user = self._make_user("opted_in_student", User.Role.STUDENT)
        user.can_change_password = True
        user.save()
        user.refresh_from_db()
        self.assertTrue(user.can_change_password)

    def test_can_change_password_is_clamped_off_for_non_students(self):
        user = self._make_user("a_teacher", User.Role.TEACHER)
        user.can_change_password = True
        user.save()
        user.refresh_from_db()
        self.assertFalse(
            user.can_change_password,
            "can_change_password is a student-only capability and must not persist for staff",
        )

    def test_each_role_gets_its_own_dashboard_view(self):
        expected_templates = {
            User.Role.STUDENT: "accounts/dashboard_student.html",
            User.Role.TEACHER: "accounts/dashboard_teacher.html",
            User.Role.COUNSELLOR: "accounts/dashboard_staff.html",
            User.Role.PRINCIPAL: "accounts/dashboard_staff.html",
        }
        for role, template in expected_templates.items():
            with self.subTest(role=role):
                username = f"dash_{role}"
                self._make_user(username, role, "simplepass")
                self.client.login(username=username, password="simplepass")
                response = self.client.get(reverse("dashboard"))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)
                self.client.logout()
