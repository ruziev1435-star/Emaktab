from django.db import transaction
from django.utils import timezone

from bot.notify import notify
from core.models import ClassSubjectTeacher

from .models import AttendanceRecord, SubjectAttendanceRecord


def confirm_student_attendance(student, via="telegram"):
    """Step 1 of attendance: the student confirms they've entered the school
    building. Notifies the homeroom (head) teacher and parents only — NOT
    subject teachers, since the student hasn't said which class they're
    attending yet; that's step 2, confirm_subject_attendance() below.
    Raises django.db.IntegrityError if already confirmed today — the
    duplicate .create() is wrapped in its own atomic() so that error only
    rolls back this savepoint, not any wider transaction a caller (a test,
    an admin action, ATOMIC_REQUESTS) might already be running inside."""
    with transaction.atomic():
        record = AttendanceRecord.objects.create(
            student=student, date=timezone.localdate(), confirmed_via=via
        )

    profile = getattr(student, "student_profile", None)
    school_class = getattr(profile, "school_class", None)
    student_name = student.get_full_name() or student.username
    message = f"{student_name} entered the school today ({record.date:%d %b})."

    if school_class and school_class.homeroom_teacher:
        notify(school_class.homeroom_teacher, message, related_attendance=record)

    if profile:
        for parent in profile.parents.all():
            notify(parent, message, related_attendance=record)

    return record


def subjects_for_student(student):
    """ClassSubjectTeacher assignments for the student's class — the list of
    subjects they can check into via confirm_subject_attendance(), and who
    teaches each. Empty queryset if the student has no class assigned."""
    profile = getattr(student, "student_profile", None)
    school_class = getattr(profile, "school_class", None)
    if school_class is None:
        return ClassSubjectTeacher.objects.none()
    return ClassSubjectTeacher.objects.filter(school_class=school_class).select_related(
        "subject", "teacher"
    )


def confirm_subject_attendance(student, subject, via="telegram"):
    """Step 2 of attendance: the student confirms they're in a specific
    subject's class. Notifies that subject's teacher, the homeroom teacher,
    and parents (deduplicated if the homeroom teacher also teaches this
    subject to this class).

    Raises django.db.IntegrityError if already confirmed for this subject
    today. Raises ValueError if the student has no class assigned, or the
    subject isn't taught to their class — both caller-facing edge cases the
    Telegram/web handlers must catch and report, not let crash."""
    profile = getattr(student, "student_profile", None)
    school_class = getattr(profile, "school_class", None)
    if school_class is None:
        raise ValueError(f"{student} has no class assigned; cannot confirm subject attendance.")

    assignment = (
        ClassSubjectTeacher.objects.filter(school_class=school_class, subject=subject)
        .select_related("teacher")
        .first()
    )
    if assignment is None:
        raise ValueError(f"{subject} is not taught to {school_class}.")

    with transaction.atomic():
        record = SubjectAttendanceRecord.objects.create(
            student=student, subject=subject, date=timezone.localdate(), confirmed_via=via
        )

    student_name = student.get_full_name() or student.username
    message = f"{student_name} checked into {subject} class today ({record.date:%d %b})."

    notified_teacher_ids = set()
    notify(assignment.teacher, message, related_subject_attendance=record)
    notified_teacher_ids.add(assignment.teacher_id)

    if school_class.homeroom_teacher and school_class.homeroom_teacher_id not in notified_teacher_ids:
        notify(school_class.homeroom_teacher, message, related_subject_attendance=record)

    if profile:
        for parent in profile.parents.all():
            notify(parent, message, related_subject_attendance=record)

    return record
