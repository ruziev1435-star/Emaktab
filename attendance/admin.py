from django.contrib import admin

from .models import AttendanceRecord, NotificationLog

admin.site.register(AttendanceRecord)
admin.site.register(NotificationLog)
