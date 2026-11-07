from django.core.management.base import BaseCommand, CommandError
from openai import APIError

from listening.services.listening_audio import create_listening_job
from listening.services.materials import MaterialGenerationError
from listening.services.shanghai_materials import KINDS, generate_shanghai_material


class Command(BaseCommand):
	help = "Generate a Shanghai-style listening exercise and queue its audio clips."

	def add_arguments(self, parser):
		parser.add_argument("topic")
		parser.add_argument("--section", choices = ("A", "B"), default = "A")
		parser.add_argument("--kind", choices = tuple(KINDS))
		parser.add_argument("--speed", type = float, default = 1.0)

	def handle(self, *args, **options):
		if not 0.5 <= options["speed"] <= 2.0:
			raise CommandError("Speed must be between 0.5 and 2.0.")
		try:
			material = generate_shanghai_material(
				topic = options["topic"], section = options["section"], kind = options["kind"],
			)
			job = create_listening_job(material, speed = options["speed"])
		except (ValueError, MaterialGenerationError) as error:
			raise CommandError(str(error)) from error
		except APIError as error:
			raise CommandError("DeepSeek request failed. Check API configuration or try again later.") from error
		self.stdout.write(self.style.SUCCESS(f"Listening job #{job.pk} queued with {job.tts_jobs.count()} TTS clips."))
		self.stdout.write("Run: python manage.py tts_worker --watch")
