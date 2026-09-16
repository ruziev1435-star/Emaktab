from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Parent, StudentProfile, TeacherProfile, User


class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Kundalik+", {"fields": ("role", "telegram_chat_id", "telegram_link_code")}),
    )
    list_display = ("username", "first_name", "last_name", "role", "is_linked_to_telegram")
    list_filter = ("role",) + BaseUserAdmin.list_filter
    readonly_fields = ("telegram_link_code",)


admin.site.register(User, UserAdmin)
admin.site.register(TeacherProfile)
admin.site.register(StudentProfile)
admin.site.register(Parent)
