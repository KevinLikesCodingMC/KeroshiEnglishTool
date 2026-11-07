import json

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST, require_safe
from openai import APIError, APITimeoutError

from .models import ListeningJob, TTSJob
from .services.listening_audio import DEFAULT_VOICES, Pacing, create_listening_job, retry_listening_job
from .services.materials import MaterialGenerationError
from .services.shanghai_materials import generate_shanghai_material, space_explanations
from .views import audio_response
from .voices import VOICES


def _payload(request):
	try:
		data = json.loads(request.body)
	except (json.JSONDecodeError, UnicodeDecodeError) as error:
		raise ValueError("请求必须是有效 JSON。") from error
	if not isinstance(data, dict):
		raise ValueError("请求必须是 JSON 对象。")
	return data


def _job_urls(job):
	return {
		"id": job.pk,
		"status_url": reverse("listening:practice-status", args = [job.pk]),
		"retry_url": reverse("listening:practice-retry", args = [job.pk]),
	}


@staff_member_required(login_url = "admin:login")
@require_GET
def index(request):
	job_id = request.GET.get("job", "")
	initial_url = reverse("listening:practice-status", args = [int(job_id)]) if job_id.isascii() and job_id.isdigit() and len(job_id) <= 18 else ""
	return render(request, "listening/practice.html", {
		"voices": VOICES,
		"speakers": [{"id": role, "label": label, "voice": DEFAULT_VOICES[role]}
			for role, label in (("woman", "女声角色"), ("man", "男声角色"), ("narrator", "旁白／提问"))],
		"recent_jobs": ListeningJob.objects.order_by("-created_at")[:10],
		"initial_status_url": initial_url,
	})


@staff_member_required(login_url = "admin:login")
@require_POST
def material(request):
	try:
		data = _payload(request)
		result = generate_shanghai_material(topic = data.get("topic"), section = data.get("section", "A"), kind = data.get("kind"))
	except ValueError as error:
		return JsonResponse({"error": str(error)}, status = 400)
	except MaterialGenerationError as error:
		return JsonResponse({"error": str(error)}, status = 503)
	except APITimeoutError:
		return JsonResponse({"error": "材料生成超时，请重试。"}, status = 504)
	except APIError:
		return JsonResponse({"error": "材料服务暂时不可用，请检查服务配置或稍后重试。"}, status = 502)
	return JsonResponse({"material": result})


@staff_member_required(login_url = "admin:login")
@require_POST
def create(request):
	try:
		data = _payload(request)
		pauses = data.get("pacing", {})
		if not isinstance(pauses, dict) or set(pauses) - set(Pacing.__dataclass_fields__):
			raise ValueError("停顿设置无效。")
		job = create_listening_job(data.get("material"), voices = data.get("voices"),
			speed = data.get("speed", 1.0), pacing = Pacing(**pauses))
	except (ValueError, MaterialGenerationError) as error:
		return JsonResponse({"error": str(error)}, status = 400)
	return JsonResponse(_job_urls(job), status = 202)


@staff_member_required(login_url = "admin:login")
@require_GET
def status(request, job_id):
	job = ListeningJob.objects.filter(pk = job_id).first()
	if job is None:
		return JsonResponse({"error": "听力任务不存在。"}, status = 404)
	children = list(job.tts_jobs.values_list("status", flat = True))
	return JsonResponse({
		**_job_urls(job), "status": job.status, "material": space_explanations(job.material),
		"completed": children.count(TTSJob.Status.COMPLETED), "total": len(children),
		"error": "生成失败，可以重试；若持续失败，请检查后台任务错误信息。" if job.status == ListeningJob.Status.FAILED else "",
		"audio_url": reverse("listening:practice-audio", args = [job.pk]) if job.status == ListeningJob.Status.COMPLETED and job.audio_file else None,
	})


@staff_member_required(login_url = "admin:login")
@require_POST
def retry(request, job_id):
	job = ListeningJob.objects.filter(pk = job_id).first()
	if job is None:
		return JsonResponse({"error": "听力任务不存在。"}, status = 404)
	try:
		retry_listening_job(job_id)
	except ValueError as error:
		return JsonResponse({"error": str(error)}, status = 409)
	return JsonResponse(_job_urls(job), status = 202)


@staff_member_required(login_url = "admin:login")
@require_safe
def audio(request, job_id):
	job = ListeningJob.objects.filter(pk = job_id, status = ListeningJob.Status.COMPLETED).first()
	if job is None or not job.audio_file:
		return JsonResponse({"error": "音频尚未就绪。"}, status = 404)
	try:
		return audio_response(request, job.audio_file)
	except FileNotFoundError:
		return JsonResponse({"error": "音频文件不存在。"}, status = 404)
