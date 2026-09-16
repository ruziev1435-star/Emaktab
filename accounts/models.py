import secrets

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        PRINCIPAL = "principal", "Principal"
        COUNSELLOR = "counsellor", "Counsellor"
        TEACHER = "teacher", "Teacher"
        STUDENT = "student", "Student"

    role = models.CharField(max_length=20, choices=Role.choices)
    telegram_chat_id = models.CharField(max_length=64, blank=True, null=True, unique=True)
    telegram_link_code = models.CharField(max_length=16, blank=True)

    def save(self, *args, **kwargs):
        if not self.telegram_link_code:
            self.telegram_link_code = secrets.token_hex(4)
        super().save(*args, **kwargs)

    @property
    def is_linked_to_telegram(self):
        return bool(self.telegram_chat_id)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    subjects = models.ManyToManyField("core.Subject", related_name="teachers", blank=True)

    def __str__(self):
        return str(self.user)


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    school_class = models.ForeignKey(
        "core.SchoolClass", on_delete=models.SET_NULL, null=True, related_name="students"
    )

    def __str__(self):
        return str(self.user)


class Parent(models.Model):
    """Parents don't get a platform login (only 4 staff/student roles do) but are
    kept in the loop via Telegram notifications about their children."""

    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=32, blank=True)
    telegram_chat_id = models.CharField(max_length=64, blank=True, null=True, unique=True)
    telegram_link_code = models.CharField(max_length=16, blank=True)
    students = models.ManyToManyField(StudentProfile, related_name="parents", blank=True)

    def save(self, *args, **kwargs):
        if not self.telegram_link_code:
            self.telegram_link_code = secrets.token_hex(4)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name
