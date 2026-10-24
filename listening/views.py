import json

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .models import TTSJob


def index(request):
	return render(request, "listening/index.html")


@require_POST
def create_job(request):
	try:
		data = json.loads(request.body)
	except (json.JSONDecodeError, UnicodeDecodeError):
		return JsonResponse({"error": "Invalid JSON."}, status = 400)

	if not isinstance(data, dict):
		return JsonResponse({"error": "Invalid JSON."}, status = 400)

	text = data.get("text", "")
	if not isinstance(text, str) or not text.strip():
		return JsonResponse({"error": "Please enter some text."}, status = 400)

	raw_speed = data.get("speed", 1.0)
	try:
		if isinstance(raw_speed, bool):
			raise ValueError
		speed = float(raw_speed)
	except (TypeError, ValueError):
		return JsonResponse(
			{"error": "Please choose a speed between 0.5 and 2.0."},
			status = 400,
		)

	if not 0.5 <= speed <= 2.0:
		return JsonResponse(
			{"error": "Please choose a speed between 0.5 and 2.0."},
			status = 400,
		)

	job = TTSJob.objects.create(text = text.strip(), speed = speed)
	return JsonResponse(
		{
			"id": job.pk,
			"status": job.status,
			"status_url": reverse("listening:job-status", args = [job.pk]),
		},
		status = 202,
	)


@require_GET
def job_status(request, job_id):
	try:
		job = TTSJob.objects.get(pk = job_id)
	except TTSJob.DoesNotExist:
		return JsonResponse({"error": "Job not found."}, status = 404)

	return JsonResponse(
		{
			"id": job.pk,
			"status": job.status,
			"audio_url": job.audio_file.url if job.audio_file else None,
			"error_message": job.error_message,
		},
	)
