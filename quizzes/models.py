from django.conf import settings
from django.db import models


class Quiz(models.Model):
    """A short unit test delivered after a topic has been studied."""

    subject = models.ForeignKey("core.Subject", on_delete=models.CASCADE, related_name="quizzes")
    school_class = models.ForeignKey(
        "core.SchoolClass", on_delete=models.CASCADE, related_name="quizzes"
    )
    topic = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quizzes_created",
        limit_choices_to={"role": "teacher"},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} - {self.topic}"


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.CharField(max_length=500)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class QuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
        limit_choices_to={"role": "student"},
    )
    score = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.student} - {self.quiz} ({self.score}/{self.total})"


class Exam(models.Model):
    """Control work / exam schedule, surfaced prominently on the student dashboard."""

    subject = models.ForeignKey("core.Subject", on_delete=models.CASCADE, related_name="exams")
    school_class = models.ForeignKey(
        "core.SchoolClass", on_delete=models.CASCADE, related_name="exams"
    )
    title = models.CharField(max_length=255)
    date = models.DateField()

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.title} ({self.subject}) - {self.date}"
