import json
import sqlite3
from contextlib import closing
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from vocabulary.dictionary import DictionaryError, lookup_word
from vocabulary.models import Word


class DictionaryTests(TestCase):
	def setUp(self):
		self.directory = TemporaryDirectory()
		self.addCleanup(self.directory.cleanup)
		self.path = Path(self.directory.name) / "dictionary with spaces.db"
		with closing(sqlite3.connect(self.path)) as connection:
			connection.execute(
				"CREATE TABLE stardict (word TEXT UNIQUE COLLATE NOCASE, "
				"phonetic TEXT, translation TEXT, tag TEXT, exchange TEXT)"
			)
			connection.execute(
				"INSERT INTO stardict VALUES (?, ?, ?, ?, ?)",
				("study", "ˈstʌdi", "学习", "zk gk", "p:studied"),
			)
			connection.execute(
				"INSERT INTO stardict (word) VALUES (?)", ("teacher's",),
			)
			connection.commit()
		self.settings_context = override_settings(ECDICT_PATH = self.path)
		self.settings_context.enable()
		self.addCleanup(self.settings_context.disable)

	def test_lookup_normalizes_input_and_leaves_dictionary_unchanged(self):
		original = self.path.read_bytes()
		entry = lookup_word("  STUDY  ")
		self.assertEqual(entry["translation"], "学习")
		self.assertEqual(entry["exchange"], "p:studied")
		self.assertEqual(lookup_word("teacher’s")["word"], "teacher's")
		self.assertEqual(self.path.read_bytes(), original)

	def test_unknown_empty_and_sql_input_return_none(self):
		for text in ("missing", " ", "' OR 1=1 --"):
			with self.subTest(text = text):
				self.assertIsNone(lookup_word(text))

	def test_missing_file_is_not_created(self):
		missing = self.path.parent / "missing.db"
		with override_settings(ECDICT_PATH = missing):
			with self.assertRaises(DictionaryError):
				lookup_word("study")
		self.assertFalse(missing.exists())

	def test_invalid_database_has_clear_command_error(self):
		invalid = self.path.parent / "invalid.db"
		invalid.write_text("not a database", encoding = "utf-8")
		with override_settings(ECDICT_PATH = invalid):
			with self.assertRaises(CommandError):
				call_command("dictionary_lookup", "study")

	def test_word_can_fetch_details_without_changing_learning_data(self):
		word = Word.objects.create(text = "Study", count = 3)
		self.assertEqual(word.get_dictionary_entry()["translation"], "学习")
		word.refresh_from_db()
		self.assertEqual(word.count, 3)
		self.assertEqual(Word.objects.count(), 1)

	def test_lookup_command_returns_json_or_not_found(self):
		stdout = StringIO()
		call_command("dictionary_lookup", "study", stdout = stdout)
		self.assertEqual(json.loads(stdout.getvalue())["word"], "study")
		stdout = StringIO()
		call_command("dictionary_lookup", "missing", stdout = stdout)
		self.assertIn("Word not found", stdout.getvalue())
