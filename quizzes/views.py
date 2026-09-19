from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render

from .models import Quiz, QuizAttempt


@login_required
def quiz_list(request):
    school_class = getattr(getattr(request.user, "student_profile", None), "school_class", None)
    quizzes = Quiz.objects.filter(school_class=school_class) if school_class else Quiz.objects.none()
    taken_ids = set(
        QuizAttempt.objects.filter(student=request.user).values_list("quiz_id", flat=True)
    )
    return render(
        request, "quizzes/quiz_list.html", {"quizzes": quizzes, "taken_ids": taken_ids}
    )


@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    already = QuizAttempt.objects.filter(quiz=quiz, student=request.user).first()

    if request.method == "POST":
        if already:
            messages.info(request, f"You already took {quiz.topic}.")
            return redirect("quizzes:list")

        score = 0
        questions = list(quiz.questions.all())
        for question in questions:
            selected_id = request.POST.get(f"question_{question.id}")
            # selected_id is untrusted POST data — a non-numeric value would
            # otherwise crash the id__exact lookup with ValueError instead
            # of just counting as an unanswered/wrong question.
            if selected_id and str(selected_id).isdigit():
                if question.choices.filter(id=selected_id, is_correct=True).exists():
                    score += 1

        try:
            with transaction.atomic():
                QuizAttempt.objects.create(
                    quiz=quiz, student=request.user, score=score, total=len(questions)
                )
        except IntegrityError:
            messages.info(request, f"You already took {quiz.topic}.")
            return redirect("quizzes:list")

        messages.success(request, f"You scored {score}/{len(questions)} on {quiz.topic}.")
        return redirect("quizzes:list")

    return render(
        request, "quizzes/take_quiz.html", {"quiz": quiz, "already": already}
    )


@login_required
def my_results(request):
    attempts = QuizAttempt.objects.filter(student=request.user)
    return render(request, "quizzes/my_results.html", {"attempts": attempts})
