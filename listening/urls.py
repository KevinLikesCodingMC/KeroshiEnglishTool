from django.urls import path

from . import views
from . import practice_views


app_name = "listening"

urlpatterns = [
	path("", views.index, name = "index"),
	path("audio", views.audio, name = "audio"),
	path("material", views.materials, name = "materials"),
	path("practice", practice_views.index, name = "practice"),
	path("api/practice/material/", practice_views.material, name = "practice-material"),
	path("api/practice/jobs/", practice_views.create, name = "practice-create"),
	path("api/practice/jobs/<int:job_id>/", practice_views.status, name = "practice-status"),
	path("api/practice/jobs/<int:job_id>/retry/", practice_views.retry, name = "practice-retry"),
	path("api/practice/jobs/<int:job_id>/audio/", practice_views.audio, name = "practice-audio"),
	path("api/materials/", views.create_material, name = "material-create"),
	path("api/jobs/", views.create_job, name = "job-create"),
	path("api/jobs/<int:job_id>/", views.job_status, name = "job-status"),
	path("api/jobs/<int:job_id>/audio/", views.job_audio, name = "job-audio"),
]
