from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

from accounts.views import KundalikPasswordChangeView, dashboard

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="dashboard", permanent=False)),
    path("dashboard/", dashboard, name="dashboard"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("password-change/", KundalikPasswordChangeView.as_view(), name="password_change"),
    path(
        "password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="accounts/password_change_done.html"
        ),
        name="password_change_done",
    ),
    path("meetings/", include("meetings.urls")),
    path("attendance/", include("attendance.urls")),
    path("quizzes/", include("quizzes.urls")),
    path("library/", include("library.urls")),
]
