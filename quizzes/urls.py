from django.urls import path

from . import views

app_name = "quizzes"

urlpatterns = [
    path("", views.quiz_list, name="list"),
    path("results/", views.my_results, name="results"),
    path("<int:quiz_id>/take/", views.take_quiz, name="take"),
]
