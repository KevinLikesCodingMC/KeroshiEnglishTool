import re
import sqlite3
from contextlib import closing
from functools import lru_cache
from pathlib import Path

from django.conf import settings

from .models import normalize_word


class DictionaryError(Exception):
	"""The configured dictionary could not be read."""


def meaning_entries():
	path = Path(settings.ECDICT_PATH).resolve()
	try:
		stat = path.stat()
		return _meaning_entries(str(path), stat.st_mtime_ns, stat.st_size)
	except (OSError, sqlite3.Error) as exc:
		raise DictionaryError(f"Cannot read ECDICT at {path}.") from exc


@lru_cache(maxsize = 1)
def _meaning_entries(path, modified, size):
	with closing(sqlite3.connect(Path(path).as_uri() + "?mode=ro", uri = True)) as connection:
		rows = connection.execute(
			"SELECT word, phonetic, translation FROM stardict "
			"WHERE (instr(' ' || coalesce(tag, '') || ' ', ' cet4 ') > 0 "
			"OR instr(' ' || coalesce(tag, '') || ' ', ' cet6 ') > 0) "
			"AND instr(' ' || coalesce(tag, '') || ' ', ' zk ') = 0"
		)
		entries = []
		for word, phonetic, translation in rows:
			if not re.fullmatch(r"[a-z]{2,30}", word):
				continue
			lines = [line.strip() for line in (translation or "").replace("\\n", "\n").splitlines()
				if re.search(r"[\u3400-\u9fff]", line)]
			definition = "\n".join(lines[:3])
			if not definition or len(definition) > 240:
				continue
			entries.append({"word": word, "phonetic": phonetic or "", "definition": definition})
		return tuple(entries)


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
