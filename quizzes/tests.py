from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from accounts.models import StudentProfile, User
from core.models import SchoolClass, Subject

from .models import Choice, Question, Quiz, QuizAttempt


class QuizListViewTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="x", role=User.Role.TEACHER)
        self.school_class = SchoolClass.objects.create(name="9-A")
        self.subject = Subject.objects.create(name="Math")
        self.quiz = Quiz.objects.create(
            subject=self.subject, school_class=self.school_class, topic="Fractions", created_by=self.teacher
        )
        self.student = User.objects.create_user(username="dilnoza", password="x", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=self.student, school_class=self.school_class)
        self.client.force_login(self.student)

    def test_lists_quizzes_for_students_class(self):
        response = self.client.get(reverse("quizzes:list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.quiz, response.context["quizzes"])

    def test_excludes_quizzes_for_other_classes(self):
        other_class = SchoolClass.objects.create(name="10-B")
        Quiz.objects.create(
            subject=self.subject, school_class=other_class, topic="Other", created_by=self.teacher
        )
        response = self.client.get(reverse("quizzes:list"))
        self.assertEqual(list(response.context["quizzes"]), [self.quiz])

    def test_student_without_class_sees_empty_list_not_crash(self):
        lonely = User.objects.create_user(username="lonely", password="x", role=User.Role.STUDENT)
        self.client.force_login(lonely)
        response = self.client.get(reverse("quizzes:list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["quizzes"]), [])

    def test_taken_quiz_shows_taken_badge_not_start_button(self):
        QuizAttempt.objects.create(quiz=self.quiz, student=self.student, score=1, total=1)
        response = self.client.get(reverse("quizzes:list"))
        self.assertIn(self.quiz.id, response.context["taken_ids"])
        self.assertContains(response, "Taken")
        self.assertNotContains(response, "Start")


class TakeQuizViewTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="x", role=User.Role.TEACHER)
        self.school_class = SchoolClass.objects.create(name="9-A")
        self.subject = Subject.objects.create(name="Math")
        self.quiz = Quiz.objects.create(
            subject=self.subject, school_class=self.school_class, topic="Fractions", created_by=self.teacher
        )
        self.q1 = Question.objects.create(quiz=self.quiz, text="2+2?", order=1)
        self.correct = Choice.objects.create(question=self.q1, text="4", is_correct=True)
        self.wrong = Choice.objects.create(question=self.q1, text="5", is_correct=False)
        self.q2 = Question.objects.create(quiz=self.quiz, text="3+3?", order=2)
        Choice.objects.create(question=self.q2, text="6", is_correct=True)
        Choice.objects.create(question=self.q2, text="7", is_correct=False)

        self.student = User.objects.create_user(username="dilnoza", password="x", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=self.student, school_class=self.school_class)
        self.client.force_login(self.student)

    def test_get_renders_form_when_not_yet_taken(self):
        response = self.client.get(reverse("quizzes:take", args=[self.quiz.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["already"])
        self.assertContains(response, "2+2?")

    def test_post_correct_answers_scores_full_marks(self):
        response = self.client.post(
            reverse("quizzes:take", args=[self.quiz.id]),
            {f"question_{self.q1.id}": self.correct.id, f"question_{self.q2.id}": ""},
            follow=True,
        )
        attempt = QuizAttempt.objects.get(quiz=self.quiz, student=self.student)
        self.assertEqual(attempt.score, 1)
        self.assertEqual(attempt.total, 2)
        messages = list(response.context["messages"])
        self.assertTrue(any("1/2" in str(m) for m in messages))

    def test_post_wrong_answer_scores_zero_for_that_question(self):
        self.client.post(
            reverse("quizzes:take", args=[self.quiz.id]),
            {f"question_{self.q1.id}": self.wrong.id},
        )
        attempt = QuizAttempt.objects.get(quiz=self.quiz, student=self.student)
        self.assertEqual(attempt.score, 0)

    def test_post_with_no_answers_does_not_crash(self):
        response = self.client.post(reverse("quizzes:take", args=[self.quiz.id]), {})
        self.assertEqual(response.status_code, 302)
        attempt = QuizAttempt.objects.get(quiz=self.quiz, student=self.student)
        self.assertEqual(attempt.score, 0)
        self.assertEqual(attempt.total, 2)

    def test_post_with_tampered_non_numeric_choice_id_does_not_crash(self):
        response = self.client.post(
            reverse("quizzes:take", args=[self.quiz.id]),
            {f"question_{self.q1.id}": "not-a-real-id; DROP TABLE quizzes_quiz;"},
        )
        self.assertEqual(response.status_code, 302)
        attempt = QuizAttempt.objects.get(quiz=self.quiz, student=self.student)
        self.assertEqual(attempt.score, 0)
        self.assertTrue(Quiz.objects.filter(pk=self.quiz.pk).exists())

    def test_post_with_choice_id_for_a_different_question_does_not_count(self):
        """Answering question 1 with a choice that belongs to question 2 should
        never score a point — the lookup is scoped to the question's own choices."""
        other_quiz_choice = Choice.objects.create(question=self.q2, text="unrelated", is_correct=True)
        response = self.client.post(
            reverse("quizzes:take", args=[self.quiz.id]),
            {f"question_{self.q1.id}": other_quiz_choice.id},
        )
        self.assertEqual(response.status_code, 302)
        attempt = QuizAttempt.objects.get(quiz=self.quiz, student=self.student)
        self.assertEqual(attempt.score, 0)

    def test_get_after_taking_shows_already_taken_state(self):
        QuizAttempt.objects.create(quiz=self.quiz, student=self.student, score=1, total=2)
        response = self.client.get(reverse("quizzes:take", args=[self.quiz.id]))
        self.assertIsNotNone(response.context["already"])
        self.assertContains(response, "already took")

    def test_resubmitting_after_taking_does_not_create_duplicate_or_crash(self):
        self.client.post(reverse("quizzes:take", args=[self.quiz.id]), {f"question_{self.q1.id}": self.correct.id})
        response = self.client.post(
            reverse("quizzes:take", args=[self.quiz.id]),
            {f"question_{self.q1.id}": self.wrong.id},
            follow=True,
        )
        self.assertEqual(QuizAttempt.objects.filter(quiz=self.quiz, student=self.student).count(), 1)
        # score from the first (real) submission must be preserved, not overwritten
        attempt = QuizAttempt.objects.get(quiz=self.quiz, student=self.student)
        self.assertEqual(attempt.score, 1)
        messages = list(response.context["messages"])
        self.assertTrue(any("already took" in str(m) for m in messages))

    def test_model_level_duplicate_attempt_raises_integrity_error(self):
        QuizAttempt.objects.create(quiz=self.quiz, student=self.student, score=1, total=2)
        with self.assertRaises(IntegrityError):
            QuizAttempt.objects.create(quiz=self.quiz, student=self.student, score=2, total=2)

    def test_nonexistent_quiz_returns_404_not_crash(self):
        response = self.client.get(reverse("quizzes:take", args=[999999]))
        self.assertEqual(response.status_code, 404)


class MyResultsViewTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="x", role=User.Role.TEACHER)
        self.school_class = SchoolClass.objects.create(name="9-A")
        self.subject = Subject.objects.create(name="Math")
        self.quiz = Quiz.objects.create(
            subject=self.subject, school_class=self.school_class, topic="Fractions", created_by=self.teacher
        )
        self.student = User.objects.create_user(username="dilnoza", password="x", role=User.Role.STUDENT)
        self.client.force_login(self.student)

    def test_empty_state_does_not_crash(self):
        response = self.client.get(reverse("quizzes:results"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "haven't taken")

    def test_lists_own_attempts_only(self):
        other_student = User.objects.create_user(username="other", password="x", role=User.Role.STUDENT)
        QuizAttempt.objects.create(quiz=self.quiz, student=self.student, score=1, total=1)
        QuizAttempt.objects.create(quiz=self.quiz, student=other_student, score=0, total=1)
        response = self.client.get(reverse("quizzes:results"))
        self.assertEqual(len(response.context["attempts"]), 1)
        self.assertEqual(response.context["attempts"][0].student, self.student)

    def test_perfect_score_shown_with_zero_total_does_not_crash(self):
        """A quiz with zero questions gives total=0 — score==total (0==0) is
        still True, so this must render without a ZeroDivisionError-style
        issue even though nothing here divides."""
        empty_quiz = Quiz.objects.create(
            subject=self.subject, school_class=self.school_class, topic="Empty", created_by=self.teacher
        )
        QuizAttempt.objects.create(quiz=empty_quiz, student=self.student, score=0, total=0)
        response = self.client.get(reverse("quizzes:results"))
        self.assertEqual(response.status_code, 200)
