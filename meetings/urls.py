from django.urls import path

from . import views

app_name = "meetings"

urlpatterns = [
    path("", views.staff_list, name="staff_list"),
    path("mine/", views.my_meetings, name="my_meetings"),
    path("with/<int:staff_id>/", views.calendar, name="calendar"),
    path("<int:meeting_id>/status/<str:new_status>/", views.update_status, name="update_status"),
]
