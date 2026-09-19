from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import User

from .models import AttendanceRecord
from .services import confirm_student_attendance


@login_required
def confirm_web(request):
    """Web fallback for confirming attendance (the real flow is the Telegram
    button, this exists so the platform is demoable without a live bot).
    Student-only: AttendanceRecord.student's limit_choices_to is admin/form
    UI only, not enforced at the ORM level, so without this check any
    logged-in staff account could create a bogus record for itself."""
    if request.user.role != User.Role.STUDENT:
        messages.error(request, "Only students confirm attendance.")
        return redirect("dashboard")

    if request.method == "POST":
        try:
            confirm_student_attendance(request.user, via="web")
            messages.success(request, "Attendance confirmed — parents and teachers notified.")
        except IntegrityError:
            messages.info(request, "You already confirmed attendance today.")
        return redirect("attendance:status")

    already = AttendanceRecord.objects.filter(
        student=request.user, date=timezone.localdate()
    ).exists()
    return render(request, "attendance/confirm.html", {"already_confirmed": already})


@login_required
def status(request):
    records = AttendanceRecord.objects.filter(student=request.user)[:14]
    return render(request, "attendance/status.html", {"records": records})
