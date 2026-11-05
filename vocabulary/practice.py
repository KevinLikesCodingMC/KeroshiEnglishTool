import re
from random import sample, shuffle
from uuid import uuid4

from .dictionary import lookup_word, meaning_entries
from .models import Word


def _meaning_parts(definition):
	"""Exclude obvious shared meanings, even when POS labels differ."""
	return set(re.findall(r"[\u3400-\u9fff]+", definition))


def choose_meaning_questions(batch_size = 10, words = None):
	entries = meaning_entries()
	if len(entries) < 4:
		return []
	questions = []
	targets = entries if words is None else [entry for entry in entries if entry["word"] in words]
	for entry in sample(targets, min(batch_size, len(targets))):
		choices = [entry]
		parts = _meaning_parts(entry["definition"])
		for candidate in sample(entries, len(entries)):
			candidate_parts = _meaning_parts(candidate["definition"])
			if candidate["word"] == entry["word"] or parts & candidate_parts:
				continue
			choices.append(candidate)
			parts.update(candidate_parts)
			if len(choices) == 4:
				break
		if len(choices) < 4:
			continue
		shuffle(choices)
		questions.append({
			"id": uuid4().hex,
			"word": entry["word"],
			"phonetic": entry["phonetic"],
			"choices": [{"id": index, "definition": choice["definition"]}
				for index, choice in enumerate(choices)],
			"answer_id": choices.index(entry),
		})
	return questions


def choose_spelling_question(previous_word = None):
	"""Choose only exam words with a Chinese dictionary definition."""
	words = Word.objects.order_by("?").values_list("normalized", flat = True)
	fallback = None
	for word in words.iterator():
		if not re.fullmatch(r"[a-z]{2,30}", word):
			continue
		entry = lookup_word(word)
		if not entry:
			continue
		meanings = []
		for line in (entry.get("translation") or "").replace("\\n", "\n").splitlines():
			if not re.search(r"[\u3400-\u9fff]", line):
				continue
			match = re.match(r"^\s*([a-z]+\.)\s*", line)
			pos = match.group(1) if match else ""
			meaning = line[match.end():] if match else line
			# English glosses can contain the answer or a closely related word.
			meaning = re.sub(r"[A-Za-z][A-Za-z'-]*", "…", meaning).strip()
			meanings.append({"pos": pos, "text": meaning})
		if not meanings:
			continue
		question = {
			"id": uuid4().hex,
			"answer": word,
			"meanings": meanings,
			"phonetic": entry.get("phonetic") or "",
		}
		if word != previous_word:
			return question
		fallback = question
	return fallback
