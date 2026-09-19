from django.contrib import admin

from .models import AttendanceRecord, NotificationLog, SubjectAttendanceRecord

admin.site.register(AttendanceRecord)
admin.site.register(SubjectAttendanceRecord)
admin.site.register(NotificationLog)
