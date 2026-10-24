from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.core.management import call_command

from .models import TTSJob


TEST_MEDIA_ROOT = Path("test-media")


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
