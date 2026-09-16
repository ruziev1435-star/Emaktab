from django.conf import settings
from django.db import models


class StaffAvailability(models.Model):
    """A recurring weekly window during which a counsellor/principal can be booked."""

    WEEKDAYS = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
    ]

    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availability_windows",
        limit_choices_to={"role__in": ["principal", "counsellor"]},
    )
    weekday = models.IntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_minutes = models.PositiveIntegerField(default=20)

    class Meta:
        ordering = ["weekday", "start_time"]
        verbose_name_plural = "Staff availability windows"

    def __str__(self):
        return f"{self.staff} - {self.get_weekday_display()} {self.start_time}-{self.end_time}"


class Meeting(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    class Source(models.TextChoices):
        WEB = "web", "Platform"
        TELEGRAM = "telegram", "Telegram"

    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meetings_as_staff",
        limit_choices_to={"role__in": ["principal", "counsellor"]},
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meetings_as_student",
        limit_choices_to={"role": "student"},
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    topic = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.WEB)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["staff", "start_time"],
                condition=~models.Q(status="cancelled"),
                name="unique_active_staff_slot",
            )
        ]

    def __str__(self):
        return f"{self.student} with {self.staff} @ {self.start_time:%Y-%m-%d %H:%M}"
