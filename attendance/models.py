from django.conf import settings
from django.db import models


class AttendanceRecord(models.Model):
    class ConfirmedVia(models.TextChoices):
        TELEGRAM = "telegram", "Telegram button"
        WEB = "web", "Platform"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendance_records",
        limit_choices_to={"role": "student"},
    )
    date = models.DateField()
    confirmed_at = models.DateTimeField(auto_now_add=True)
    confirmed_via = models.CharField(
        max_length=20, choices=ConfirmedVia.choices, default=ConfirmedVia.TELEGRAM
    )

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["student", "date"], name="one_confirmation_per_day")
        ]

    def __str__(self):
        return f"{self.student} present on {self.date}"


class NotificationLog(models.Model):
    """Demo-visible record of who would have been pinged, without needing a live
    Telegram bot to prove the notification fan-out works."""

    recipient_label = models.CharField(max_length=255)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    related_attendance = models.ForeignKey(
        AttendanceRecord,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"-> {self.recipient_label}: {self.message[:40]}"
