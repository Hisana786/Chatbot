from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="dashboard"),
    path("chat/", views.chat_page, name="chat"),
    path("reports/", views.reports_page, name="reports"),
    path("api/chat/", views.chat_api, name="chat_api"),
]
