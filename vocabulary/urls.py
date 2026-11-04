from django.urls import path

from . import views

app_name = "vocabulary"

urlpatterns = [
	path("", views.index, name = "index"),
	path("meaning/", views.meaning, name = "meaning"),
	path("questions/", views.questions, name = "questions"),
]
