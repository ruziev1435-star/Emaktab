from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("confirm/", views.confirm_web, name="confirm"),
    path("status/", views.status, name="status"),
]
