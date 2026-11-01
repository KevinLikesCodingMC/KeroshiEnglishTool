import sqlite3
from contextlib import closing
from pathlib import Path

from django.conf import settings

from .models import normalize_word


class DictionaryError(Exception):
	"""The configured dictionary could not be read."""


def lookup_word(text: str) -> dict | None:

	word = normalize_word(text)
	if not word:
		return None

	path = Path(settings.ECDICT_PATH).resolve()
	try:
		# mode=ro also prevents sqlite from creating an empty DB for a wrong path.
		with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri = True)) as connection:
			connection.row_factory = sqlite3.Row
			row = connection.execute(
				"SELECT * FROM stardict WHERE word = ? COLLATE NOCASE",
				(word,),
			).fetchone()
	except sqlite3.Error as exc:
		raise DictionaryError(
			f"Cannot read ECDICT at {path}. Check ECDICT_PATH and the stardict table."
		) from exc

	return dict(row) if row is not None else None
