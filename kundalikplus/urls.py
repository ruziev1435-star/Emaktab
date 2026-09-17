from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

from accounts.views import dashboard, telegram_link

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="dashboard", permanent=False)),
    path("dashboard/", dashboard, name="dashboard"),
    path("telegram/", telegram_link, name="telegram_link"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # No password-change UI yet — accounts.models.User.can_change_password is
    # the underlying support for it, wired up in a later task.
    path("meetings/", include("meetings.urls")),
    path("attendance/", include("attendance.urls")),
    path("quizzes/", include("quizzes.urls")),
    path("library/", include("library.urls")),
]
