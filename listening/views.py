import json
import mimetypes
import re

from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST, require_safe

from .models import TTSJob
from .voices import DEFAULT_VOICE, VOICE_IDS, VOICES


BYTE_RANGE_PATTERN = re.compile(r"^bytes=(\d*)-(\d*)$")


@staff_member_required(login_url = "/admin/login/")
def index(request):
	return render(
		request,
		"listening/index.html",
		{
			"default_voice": DEFAULT_VOICE,
			"voices": VOICES,
		},
	)


@staff_member_required(login_url = "/admin/login/")
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

	voice = data.get("voice", DEFAULT_VOICE)
	if not isinstance(voice, str) or voice not in VOICE_IDS:
		return JsonResponse({"error": "Please choose a valid voice."}, status = 400)

	job = TTSJob.objects.create(
		text = text.strip(),
		voice = voice,
		speed = speed,
	)
	return JsonResponse(
		{
			"id": job.pk,
			"status": job.status,
			"status_url": reverse("listening:job-status", args = [job.pk]),
		},
		status = 202,
	)


@staff_member_required(login_url = "/admin/login/")
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
			"audio_url": (
				reverse("listening:job-audio", args = [job.pk])
				if job.audio_file
				else None
			),
			"error_message": job.error_message,
		},
	)


def _parse_byte_range(range_header, file_size):
	match = BYTE_RANGE_PATTERN.fullmatch(range_header)
	if match is None:
		raise ValueError

	start_text, end_text = match.groups()
	if not start_text and not end_text:
		raise ValueError

	if start_text:
		start = int(start_text)
		end = int(end_text) if end_text else file_size - 1
	else:
		suffix_length = int(end_text)
		if suffix_length <= 0:
			raise ValueError
		start = max(file_size - suffix_length, 0)
		end = file_size - 1

	if start >= file_size or start > end:
		raise ValueError

	return start, min(end, file_size - 1)


def _file_chunks(file_handle, length, chunk_size = 8192):
	remaining = length
	try:
		while remaining > 0:
			chunk = file_handle.read(min(chunk_size, remaining))
			if not chunk:
				break
			remaining -= len(chunk)
			yield chunk
	finally:
		file_handle.close()


@staff_member_required(login_url = "/admin/login/")
@require_safe
def job_audio(request, job_id):
	try:
		job = TTSJob.objects.get(pk = job_id)
	except TTSJob.DoesNotExist:
		return JsonResponse({"error": "Job not found."}, status = 404)

	if not job.audio_file:
		return JsonResponse({"error": "Audio is not ready."}, status = 404)

	file_size = job.audio_file.size
	content_type = mimetypes.guess_type(job.audio_file.name)[0] or "application/octet-stream"
	range_header = request.headers.get("Range")

	if not range_header:
		if request.method == "HEAD":
			response = HttpResponse(content_type = content_type)
			response["Content-Length"] = file_size
		else:
			response = FileResponse(
				job.audio_file.open("rb"),
				content_type = content_type,
			)
		response["Accept-Ranges"] = "bytes"
		return response

	try:
		start, end = _parse_byte_range(range_header, file_size)
	except ValueError:
		response = HttpResponse(status = 416)
		response["Content-Range"] = f"bytes */{file_size}"
		return response

	length = end - start + 1
	if request.method == "HEAD":
		response = HttpResponse(status = 206, content_type = content_type)
	else:
		file_handle = job.audio_file.open("rb")
		file_handle.seek(start)
		response = StreamingHttpResponse(
			_file_chunks(file_handle, length),
			status = 206,
			content_type = content_type,
		)

	response["Accept-Ranges"] = "bytes"
	response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
	response["Content-Length"] = length
	return response
