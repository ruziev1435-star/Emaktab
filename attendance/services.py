from django.db import transaction
from django.utils import timezone

from bot.notify import notify

from .models import AttendanceRecord


def confirm_student_attendance(student, via="telegram"):
    """Core attendance flow: record the confirmation, then notify the
    homeroom (head) teacher, that day's subject teachers, and parents.
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
    message = f"{student_name} confirmed arrival at school today ({record.date:%d %b})."

    if school_class:
        if school_class.homeroom_teacher:
            notify(school_class.homeroom_teacher, message, related_attendance=record)
        for assignment in school_class.subject_teachers.select_related("teacher"):
            if assignment.teacher != school_class.homeroom_teacher:
                notify(assignment.teacher, message, related_attendance=record)

    if profile:
        for parent in profile.parents.all():
            notify(parent, message, related_attendance=record)

    return record
