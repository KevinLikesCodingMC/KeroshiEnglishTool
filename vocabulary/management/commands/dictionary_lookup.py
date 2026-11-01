import json

from django.core.management.base import BaseCommand, CommandError

from vocabulary.dictionary import DictionaryError, lookup_word


class Command(BaseCommand):
	help = "Look up a word in the read-only ECDICT dictionary."

	def add_arguments(self, parser):
		parser.add_argument("word", help = "Word or phrase to look up.")

	def handle(self, *args, **options):
		try:
			entry = lookup_word(options["word"])
		except DictionaryError as exc:
			raise CommandError(str(exc)) from exc

		if entry is None:
			self.stdout.write("Word not found.")
			return

		self.stdout.write(json.dumps(entry, ensure_ascii = False, indent = 2))
