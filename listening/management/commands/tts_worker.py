from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from listening.models import TTSJob
from listening.services.kokoro_tts import generate_audio


class Command(BaseCommand):
	help = "Process one queued TTS job"

	def handle(self, * args, ** options):
		job = self._claim_job()

		if job is None:
			self.stdout.write("No queued TTS jobs.")
			return

		audio_name = f"tts/{job.pk}.wav"
		output_path = Path(settings.MEDIA_ROOT) / audio_name

		try:
			generate_audio(
				job.text,
				output_path,
				voice = job.voice,
				speed = job.speed,
			)
		except Exception as error:
			job.status = TTSJob.Status.FAILED
			job.error_message = str(error)
			job.completed_at = timezone.now()
			job.save(
				update_fields = ["status", "error_message", "completed_at"],
			)
			self.stderr.write(self.style.ERROR(f"TTS job #{job.pk} failed: {error}"))
			return

		job.status = TTSJob.Status.COMPLETED
		job.audio_file.name = audio_name
		job.error_message = ""
		job.completed_at = timezone.now()
		job.save(
			update_fields = [
				"status",
				"audio_file",
				"error_message",
				"completed_at",
			],
		)
		self.stdout.write(self.style.SUCCESS(f"TTS job #{job.pk} completed."))

	def _claim_job(self):
		with transaction.atomic():
			job = (
				TTSJob.objects.select_for_update()
				.filter(status = TTSJob.Status.QUEUED)
				.first()
			)

			if job is None:
				return None

			job.status = TTSJob.Status.PROCESSING
			job.started_at = timezone.now()
			job.save(update_fields = ["status", "started_at"])
			return job
