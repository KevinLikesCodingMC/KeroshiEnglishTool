import json
import shutil
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import TTSJob
from .services.kokoro_tts import generate_audio


TEST_MEDIA_ROOT = Path("test-media")


class StaffAuthenticatedTestCase(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.staff_user = get_user_model().objects.create_user(
			username = "staff",
			password = "test-password",
			is_staff = True,
		)

	def setUp(self):
		self.client.force_login(self.staff_user)


class ListeningAccessTests(TestCase):
	def test_anonymous_user_is_redirected_to_admin_login_for_every_endpoint(self):
		requests = (
			("get", reverse("listening:index"), {}),
			("post", reverse("listening:job-create"), {}),
			("get", reverse("listening:job-status", args = [1]), {}),
			("get", reverse("listening:job-audio", args = [1]), {}),
		)

		for method, url, kwargs in requests:
			with self.subTest(url = url):
				response = getattr(self.client, method)(url, **kwargs)

				self.assertEqual(response.status_code, 302)
				self.assertTrue(response.url.startswith("/admin/login/?next="))

	def test_logged_in_non_staff_user_is_redirected_to_admin_login(self):
		user = get_user_model().objects.create_user(
			username = "regular-user",
			password = "test-password",
		)
		self.client.force_login(user)

		response = self.client.get(reverse("listening:index"))

		self.assertEqual(response.status_code, 302)
		self.assertTrue(response.url.startswith("/admin/login/?next="))


class ListeningApiTests(StaffAuthenticatedTestCase):
	def test_index_renders_api_frontend(self):
		response = self.client.get(reverse("listening:index"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, reverse("listening:job-create"))
		self.assertContains(response, '<select id="voice"')
		self.assertContains(response, 'value="af_heart" selected')
		self.assertContains(response, 'value="bm_lewis"')
		self.assertNotContains(response, "bootstrap.bundle.min.js")
		self.assertNotContains(response, "window.location.reload()")

	def test_create_job_returns_accepted_response(self):
		response = self.client.post(
			reverse("listening:job-create"),
			data = json.dumps(
				{
					"text": "  Hello world  ",
					"voice": "bf_emma",
					"speed": 1.5,
				},
			),
			content_type = "application/json",
		)

		job = TTSJob.objects.get()
		self.assertEqual(response.status_code, 202)
		self.assertEqual(
			response.json(),
			{
				"id": job.pk,
				"status": TTSJob.Status.QUEUED,
				"status_url": reverse(
					"listening:job-status",
					args = [job.pk],
				),
			},
		)
		self.assertEqual(job.text, "Hello world")
		self.assertEqual(job.voice, "bf_emma")
		self.assertEqual(job.speed, 1.5)

	def test_create_job_uses_default_voice_when_omitted(self):
		response = self.client.post(
			reverse("listening:job-create"),
			data = json.dumps({"text": "Hello world", "speed": 1.0}),
			content_type = "application/json",
		)

		self.assertEqual(response.status_code, 202)
		self.assertEqual(TTSJob.objects.get().voice, "af_heart")

	def test_create_job_rejects_invalid_input(self):
		invalid_payloads = (
			{"text": "", "speed": 1.0},
			{"text": "Hello", "speed": 0.4},
			{"text": "Hello", "speed": 2.1},
			{"text": "Hello", "speed": "fast"},
			{"text": "Hello", "speed": 1.0, "voice": "unknown"},
			{"text": "Hello", "speed": 1.0, "voice": None},
		)

		for payload in invalid_payloads:
			with self.subTest(payload = payload):
				response = self.client.post(
					reverse("listening:job-create"),
					data = json.dumps(payload),
					content_type = "application/json",
				)

				self.assertEqual(response.status_code, 400)
				self.assertIn("error", response.json())

		self.assertFalse(TTSJob.objects.exists())

	def test_job_status_returns_completed_audio(self):
		job = TTSJob.objects.create(
			text = "Hello world",
			status = TTSJob.Status.COMPLETED,
			audio_file = "tts/example.wav",
		)

		response = self.client.get(
			reverse("listening:job-status", args = [job.pk]),
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(
			response.json(),
			{
				"id": job.pk,
				"status": TTSJob.Status.COMPLETED,
				"audio_url": reverse(
					"listening:job-audio",
					args = [job.pk],
				),
				"error_message": "",
			},
		)

	def test_job_status_returns_json_404(self):
		response = self.client.get(
			reverse("listening:job-status", args = [999]),
		)

		self.assertEqual(response.status_code, 404)
		self.assertEqual(response.json(), {"error": "Job not found."})


@override_settings(MEDIA_ROOT = TEST_MEDIA_ROOT)
class ListeningAudioTests(StaffAuthenticatedTestCase):
	def tearDown(self):
		shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors = True)

	def test_audio_endpoint_supports_byte_ranges(self):
		job = TTSJob.objects.create(
			text = "Hello world",
			status = TTSJob.Status.COMPLETED,
			audio_file = SimpleUploadedFile(
				"example.wav",
				b"0123456789",
				content_type = "audio/wav",
			),
		)

		response = self.client.get(
			reverse("listening:job-audio", args = [job.pk]),
			HTTP_RANGE = "bytes=2-5",
		)

		self.assertEqual(response.status_code, 206)
		self.assertEqual(response["Accept-Ranges"], "bytes")
		self.assertEqual(response["Content-Range"], "bytes 2-5/10")
		self.assertEqual(response["Content-Length"], "4")
		self.assertEqual(b"".join(response.streaming_content), b"2345")


class TTSWorkerTests(TestCase):
	@override_settings(MEDIA_ROOT = TEST_MEDIA_ROOT)
	@patch("listening.management.commands.tts_worker.generate_audio")
	def test_worker_completes_queued_job(
			self,
			generate_audio_mock
	):
		job = TTSJob.objects.create(
			text = "Hello world",
			voice = "af_heart",
			speed = 1.0,
		)

		call_command("tts_worker", stdout = StringIO())
		generate_audio_mock.assert_called_once_with(
			"Hello world",
			TEST_MEDIA_ROOT / "tts" / f"{job.pk}.wav",
			voice = "af_heart",
			speed = 1.0,
		)

		job.refresh_from_db()
		self.assertEqual(job.status, TTSJob.Status.COMPLETED)
		self.assertEqual(job.audio_file.name, f"tts/{job.pk}.wav")
		self.assertIsNotNone(job.started_at)
		self.assertIsNotNone(job.completed_at)
		self.assertEqual(job.error_message, "")

	@override_settings(MEDIA_ROOT = TEST_MEDIA_ROOT)
	@patch(
		"listening.management.commands.tts_worker.generate_audio",
		side_effect = RuntimeError("model unavailable"),
	)
	def test_worker_marks_job_failed_when_generation_fails(
			self,
			generate_audio_mock,
	):
		job = TTSJob.objects.create(text = "Hello world")

		call_command(
			"tts_worker",
			stdout = StringIO(),
			stderr = StringIO(),
		)

		generate_audio_mock.assert_called_once_with(
			"Hello world",
			TEST_MEDIA_ROOT / "tts" / f"{job.pk}.wav",
			voice = "af_heart",
			speed = 1.0,
		)

		job.refresh_from_db()
		self.assertEqual(job.status, TTSJob.Status.FAILED)
		self.assertEqual(job.error_message, "model unavailable")
		self.assertFalse(job.audio_file)
		self.assertIsNotNone(job.started_at)
		self.assertIsNotNone(job.completed_at)


class KokoroTTSTests(TestCase):
	@patch("listening.services.kokoro_tts.soundfile.write")
	@patch("listening.services.kokoro_tts.get_engine")
	def test_british_voice_uses_british_phonemes(self, get_engine_mock, write_mock):
		get_engine_mock.return_value.create.return_value = (b"audio", 24000)

		generate_audio("Hello world", "example.wav", voice = "bf_emma")

		get_engine_mock.return_value.create.assert_called_once_with(
			"Hello world",
			voice = "bf_emma",
			speed = 1.0,
			lang = "en-gb",
		)
		write_mock.assert_called_once_with(Path("example.wav"), b"audio", 24000)
