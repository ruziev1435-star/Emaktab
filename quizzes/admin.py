from django.contrib import admin

from .models import Choice, Exam, Question, Quiz, QuizAttempt


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    inlines = [QuestionInline]
    list_display = ("topic", "subject", "school_class", "created_by")


admin.site.register(QuizAttempt)
admin.site.register(Exam)
