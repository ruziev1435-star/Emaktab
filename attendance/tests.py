from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Parent, StudentProfile, User
from core.models import ClassSubjectTeacher, SchoolClass, Subject

from .models import AttendanceRecord, NotificationLog
from .services import confirm_student_attendance


class ConfirmStudentAttendanceTests(TestCase):
    def setUp(self):
        self.homeroom_teacher = User.objects.create_user(
            username="homeroom", password="x", role=User.Role.TEACHER, first_name="Homeroom"
        )
        self.subject_teacher = User.objects.create_user(
            username="subject", password="x", role=User.Role.TEACHER, first_name="Subject"
        )
        self.school_class = SchoolClass.objects.create(
            name="9-A", homeroom_teacher=self.homeroom_teacher
        )
        subject = Subject.objects.create(name="Math")
        ClassSubjectTeacher.objects.create(
            school_class=self.school_class, subject=subject, teacher=self.subject_teacher
        )
        self.student = User.objects.create_user(
            username="dilnoza", password="x", role=User.Role.STUDENT, first_name="Dilnoza"
        )
        self.profile = StudentProfile.objects.create(
            user=self.student, school_class=self.school_class
        )
        self.parent = Parent.objects.create(full_name="Parent of Dilnoza")
        self.parent.students.add(self.profile)

    def test_creates_record_and_notifies_homeroom_subject_teacher_and_parent(self):
        record = confirm_student_attendance(self.student, via="telegram")
        self.assertEqual(record.student, self.student)
        self.assertEqual(record.date, timezone.localdate())
        self.assertEqual(record.confirmed_via, "telegram")

        labels = list(NotificationLog.objects.values_list("recipient_label", flat=True))
        self.assertEqual(len(labels), 3)
        self.assertTrue(any("Homeroom" in label for label in labels))
        self.assertTrue(any("Subject" in label for label in labels))
        self.assertTrue(any("Parent of Dilnoza" in label for label in labels))

    def test_homeroom_teacher_not_double_notified_when_also_a_subject_teacher(self):
        ClassSubjectTeacher.objects.create(
            school_class=self.school_class,
            subject=Subject.objects.create(name="Homeroom period"),
            teacher=self.homeroom_teacher,
        )
        confirm_student_attendance(self.student, via="web")
        homeroom_notifications = NotificationLog.objects.filter(recipient_label__icontains="Homeroom")
        self.assertEqual(homeroom_notifications.count(), 1)

    def test_second_confirmation_same_day_raises_integrity_error(self):
        confirm_student_attendance(self.student, via="web")
        with self.assertRaises(IntegrityError):
            confirm_student_attendance(self.student, via="web")

    def test_student_without_profile_does_not_crash_and_notifies_no_one(self):
        lonely_student = User.objects.create_user(
            username="lonely", password="x", role=User.Role.STUDENT
        )
        record = confirm_student_attendance(lonely_student, via="web")
        self.assertIsNotNone(record)
        self.assertEqual(NotificationLog.objects.count(), 0)

    def test_student_with_class_but_no_homeroom_teacher_does_not_crash(self):
        self.school_class.homeroom_teacher = None
        self.school_class.save()
        confirm_student_attendance(self.student, via="web")
        homeroom_notifications = NotificationLog.objects.filter(recipient_label__icontains="Homeroom")
        self.assertEqual(homeroom_notifications.count(), 0)
        subject_notifications = NotificationLog.objects.filter(recipient_label__icontains="Subject")
        self.assertEqual(subject_notifications.count(), 1)


class ConfirmWebViewTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="dilnoza", password="x", role=User.Role.STUDENT, first_name="Dilnoza"
        )
        self.client.force_login(self.student)

    def test_get_renders_confirm_form_when_not_yet_confirmed(self):
        response = self.client.get(reverse("attendance:confirm"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["already_confirmed"])
        self.assertContains(response, "I'm at school today")

    def test_post_confirms_and_redirects(self):
        response = self.client.post(reverse("attendance:confirm"))
        self.assertRedirects(response, reverse("attendance:status"))
        self.assertEqual(AttendanceRecord.objects.filter(student=self.student).count(), 1)

    def test_get_after_confirming_shows_already_confirmed_state(self):
        self.client.post(reverse("attendance:confirm"))
        response = self.client.get(reverse("attendance:confirm"))
        self.assertTrue(response.context["already_confirmed"])
        self.assertContains(response, "already confirmed")

    def test_posting_twice_does_not_crash_and_shows_info_message(self):
        self.client.post(reverse("attendance:confirm"))
        response = self.client.post(reverse("attendance:confirm"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AttendanceRecord.objects.filter(student=self.student).count(), 1)
        messages = list(response.context["messages"])
        self.assertTrue(any("already confirmed" in str(m) for m in messages))

    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("attendance:confirm"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_non_student_cannot_confirm_attendance(self):
        teacher = User.objects.create_user(username="cara", password="x", role=User.Role.TEACHER)
        self.client.force_login(teacher)
        response = self.client.post(reverse("attendance:confirm"), follow=True)
        self.assertEqual(AttendanceRecord.objects.filter(student=teacher).count(), 0)
        messages = list(response.context["messages"])
        self.assertTrue(any("Only students" in str(m) for m in messages))


class StatusViewTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="dilnoza", password="x", role=User.Role.STUDENT, first_name="Dilnoza"
        )
        self.client.force_login(self.student)

    def test_empty_state_does_not_crash(self):
        response = self.client.get(reverse("attendance:status"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No attendance confirmed yet")

    def test_lists_own_records_only(self):
        other_student = User.objects.create_user(
            username="other", password="x", role=User.Role.STUDENT
        )
        confirm_student_attendance(self.student, via="web")
        confirm_student_attendance(other_student, via="web")
        response = self.client.get(reverse("attendance:status"))
        self.assertEqual(len(response.context["records"]), 1)
        self.assertEqual(response.context["records"][0].student, self.student)
