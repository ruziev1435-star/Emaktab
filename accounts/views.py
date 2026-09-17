from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from core.models import ClassSubjectTeacher, SchoolClass
from meetings.models import Meeting

from .models import StudentProfile, User


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
    today = timezone.localdate()

    homeroom_class_ids = set(user.homeroom_classes.values_list("id", flat=True))
    assignments = list(
        ClassSubjectTeacher.objects.filter(teacher=user).select_related("school_class", "subject")
    )
    taught_class_ids = {a.school_class_id for a in assignments}

    classes = SchoolClass.objects.filter(
        Q(id__in=homeroom_class_ids) | Q(id__in=taught_class_ids)
    ).order_by("name")

    my_classes = []
    for school_class in classes:
        my_classes.append(
            {
                "school_class": school_class,
                "is_homeroom": school_class.id in homeroom_class_ids,
                "subjects": [a.subject for a in assignments if a.school_class_id == school_class.id],
                "students": StudentProfile.objects.filter(school_class=school_class)
                .select_related("user")
                .order_by("user__first_name"),
            }
        )

    return _render_dashboard(
        request,
        "accounts/dashboard_teacher.html",
        {
            "today": today,
            "my_classes": my_classes,
        },
    )


def staff_dashboard(request):
    user = request.user
    today = timezone.localdate()

    meeting_requests = (
        Meeting.objects.filter(
            staff=user, start_time__gte=timezone.now(), status__in=["pending", "confirmed"]
        )
        .select_related("student")
        .order_by("start_time")[:10]
    )

    students = (
        StudentProfile.objects.select_related("user", "school_class")
        .order_by("user__first_name")[:25]
    )
    student_count = StudentProfile.objects.count()

    return _render_dashboard(
        request,
        "accounts/dashboard_staff.html",
        {
            "today": today,
            "meeting_requests": meeting_requests,
            "students": students,
            "student_count": student_count,
        },
    )


def _render_dashboard(request, template_name, extra_context):
    return render(request, template_name, extra_context)


@login_required
def telegram_link(request):
    user = request.user
    deep_link = f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={user.telegram_link_code}"
    return render(
        request,
        "accounts/telegram_link.html",
        {"deep_link": deep_link},
    )
