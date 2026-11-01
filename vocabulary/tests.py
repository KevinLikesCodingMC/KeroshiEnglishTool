from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import SourceDocument, Word


class SourceDocumentModelTests(TestCase):
	def test_source_id_is_unique(self):
		SourceDocument.objects.create(source_id = "shanghai-exam-bank:paper-1")

		with self.assertRaises(IntegrityError), transaction.atomic():
			SourceDocument.objects.create(source_id = "shanghai-exam-bank:paper-1")


class WordModelTests(TestCase):
	def test_normalized_is_generated_from_text(self):
		word = Word.objects.create(text = "  Teacher’s  ")

		self.assertEqual(word.normalized, "teacher's")

	def test_normalized_is_unique(self):
		Word.objects.create(text = "English")

		with self.assertRaises(IntegrityError), transaction.atomic():
			Word.objects.create(text = "ENGLISH")
