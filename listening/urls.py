from django.urls import path

from . import views


app_name = "listening"

urlpatterns = [
	path("", views.index, name = "index"),
	path("api/jobs/", views.create_job, name = "job-create"),
	path("api/jobs/<int:job_id>/", views.job_status, name = "job-status"),
	path("api/jobs/<int:job_id>/audio/", views.job_audio, name = "job-audio"),
]
