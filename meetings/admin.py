from django.contrib import admin

from .models import Meeting, StaffAvailability

admin.site.register(StaffAvailability)
admin.site.register(Meeting)
