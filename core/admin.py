from django.contrib import admin

from .models import ClassSubjectTeacher, SchoolClass, Subject

admin.site.register(Subject)
admin.site.register(SchoolClass)
admin.site.register(ClassSubjectTeacher)
