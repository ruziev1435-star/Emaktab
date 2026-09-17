from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from accounts.models import User
from bot.notify import notify

from .models import Meeting, StaffAvailability


def _open_slots_for(staff, days_ahead=14):
    """Expand StaffAvailability windows into concrete free slots for the next
    `days_ahead` days, excluding ones already booked."""
    now = timezone.now()
    booked_starts = set(
        Meeting.objects.filter(staff=staff, status__in=["pending", "confirmed"]).values_list(
            "start_time", flat=True
        )
    )
    windows = StaffAvailability.objects.filter(staff=staff)
    slots = []
    for offset in range(days_ahead):
        day = (now + timedelta(days=offset)).date()
        for window in windows.filter(weekday=day.weekday()):
            slot_start = datetime.combine(day, window.start_time, tzinfo=now.tzinfo)
            slot_end_bound = datetime.combine(day, window.end_time, tzinfo=now.tzinfo)
            step = timedelta(minutes=window.slot_minutes)
            current = slot_start
            while current + step <= slot_end_bound:
                if current > now and current not in booked_starts:
                    slots.append({"start": current, "end": current + step, "day": current.date()})
                current += step
    slots.sort(key=lambda s: s["start"])
    return slots


@login_required
def staff_list(request):
    staff_members = User.objects.filter(role__in=[User.Role.PRINCIPAL, User.Role.COUNSELLOR])
    return render(request, "meetings/staff_list.html", {"staff_members": staff_members})


@login_required
def calendar(request, staff_id):
    staff = get_object_or_404(
        User, id=staff_id, role__in=[User.Role.PRINCIPAL, User.Role.COUNSELLOR]
    )
    slots = _open_slots_for(staff)

    if request.method == "POST" and request.user.role == User.Role.STUDENT:
        start_iso = request.POST.get("start")
        end_iso = request.POST.get("end")
        topic = request.POST.get("topic", "")
        try:
            start_time = datetime.fromisoformat(start_iso)
            end_time = datetime.fromisoformat(end_iso)
        except (TypeError, ValueError):
            messages.error(request, "Please pick a valid time slot.")
            return redirect("meetings:calendar", staff_id=staff.id)

        meeting, created = Meeting.objects.get_or_create(
            staff=staff,
            start_time=start_time,
            defaults={
                "student": request.user,
                "end_time": end_time,
                "topic": topic,
                "status": Meeting.Status.PENDING,
                "source": Meeting.Source.WEB,
            },
        )
        if not created:
            messages.error(request, "That slot was just taken. Please pick another.")
        else:
            messages.success(request, f"Meeting request sent to {staff}.")
            notify(
                staff,
                f"New meeting request from {request.user.get_full_name() or request.user.username} "
                f"on {start_time:%a %d %b, %H:%M}"
                + (f' — "{topic}"' if topic else ""),
            )
        return redirect("meetings:calendar", staff_id=staff.id)

    return render(
        request, "meetings/calendar.html", {"staff": staff, "slots": slots}
    )


@login_required
def my_meetings(request):
    if request.user.role == User.Role.STUDENT:
        meetings = Meeting.objects.filter(student=request.user).select_related("staff")
    else:
        meetings = Meeting.objects.filter(staff=request.user).select_related("student")
    return render(request, "meetings/my_meetings.html", {"meetings": meetings, "now": timezone.now()})


@login_required
def update_status(request, meeting_id, new_status):
    meeting = get_object_or_404(Meeting, id=meeting_id, staff=request.user)
    if new_status in dict(Meeting.Status.choices):
        meeting.status = new_status
        meeting.save(update_fields=["status"])
        notify(
            meeting.student,
            f"Your meeting with {meeting.staff} on {meeting.start_time:%a %d %b, %H:%M} "
            f"is now {meeting.get_status_display().lower()}.",
        )
        messages.success(request, "Meeting updated.")

    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect("meetings:my_meetings")
