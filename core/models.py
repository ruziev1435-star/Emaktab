from django.db import models


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ClassSubjectTeacher(models.Model):
    """Which teacher teaches a given subject to a given class. Used to fan out
    attendance notifications to "that day's subject teachers" — the MVP keeps
    this as a class-wide assignment rather than a full daily timetable."""

    school_class = models.ForeignKey(
        "SchoolClass", on_delete=models.CASCADE, related_name="subject_teachers"
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        limit_choices_to={"role": "teacher"},
    )

    class Meta:
        unique_together = ("school_class", "subject")

    def __str__(self):
        return f"{self.school_class} {self.subject} - {self.teacher}"


class SchoolClass(models.Model):
    """A school class/cohort, e.g. "9-A"."""

    name = models.CharField(max_length=20, unique=True)
    homeroom_teacher = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="homeroom_classes",
        limit_choices_to={"role": "teacher"},
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "School classes"

    def __str__(self):
        return self.name
