from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from attendance.models import AttendanceRecord
from meetings.models import Meeting
from quizzes.models import Quiz

from .models import User


@login_required
def dashboard(request):
    user = request.user
    if user.role == User.Role.STUDENT:
        return student_dashboard(request)
    if user.role == User.Role.TEACHER:
        return teacher_dashboard(request)
    if user.role in (User.Role.COUNSELLOR, User.Role.PRINCIPAL):
        return staff_dashboard(request)
    return staff_dashboard(request)


def student_dashboard(request):
    user = request.user
    today = timezone.localdate()
    school_class = getattr(getattr(user, "student_profile", None), "school_class", None)

    next_meeting = (
        Meeting.objects.filter(
            student=user, start_time__gte=timezone.now(), status__in=["pending", "confirmed"]
        )
        .select_related("staff")
        .first()
    )

    return _render_dashboard(
        request,
        "accounts/dashboard_student.html",
        {
            "today": today,
            "school_class": school_class,
            "next_meeting": next_meeting,
        },
    )


def teacher_dashboard(request):
    user = request.user
    my_quizzes = Quiz.objects.filter(created_by=user)[:10]
    homeroom_classes = user.homeroom_classes.all()
    today = timezone.localdate()
    todays_attendance = AttendanceRecord.objects.filter(
        date=today, student__student_profile__school_class__in=homeroom_classes
    ) if homeroom_classes else AttendanceRecord.objects.none()

    return _render_dashboard(
        request,
        "accounts/dashboard_teacher.html",
        {
            "my_quizzes": my_quizzes,
            "homeroom_classes": homeroom_classes,
            "todays_attendance": todays_attendance,
        },
    )


def staff_dashboard(request):
    user = request.user
    upcoming_meetings = Meeting.objects.filter(
        staff=user, start_time__gte=timezone.now(), status__in=["pending", "confirmed"]
    )[:10]
    today = timezone.localdate()
    todays_attendance = AttendanceRecord.objects.filter(date=today).select_related("student")

    return _render_dashboard(
        request,
        "accounts/dashboard_staff.html",
        {
            "upcoming_meetings": upcoming_meetings,
            "todays_attendance": todays_attendance,
        },
    )


def _render_dashboard(request, template_name, extra_context):
    return render(request, template_name, extra_context)
