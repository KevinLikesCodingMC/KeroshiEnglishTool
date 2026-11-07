import re
from pathlib import Path

from .materials import (
	MaterialGenerationError,
	is_material_text,
	request_material_json,
	validate_multiple_choice_question,
	validate_script_segments,
)


KINDS = {"short_conversation": ("A", 1), "passage": ("B", 3), "long_conversation": ("B", 4)}
HAN = r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U000323af]"
ENGLISH_LETTER = r"[A-Za-z]"
MIXED_LANGUAGE_BOUNDARY = re.compile(
	rf"(?<={HAN})(?=[“\u0022]?{ENGLISH_LETTER})"
	rf"|(?<={ENGLISH_LETTER})(?={HAN})"
	rf"|(?<={ENGLISH_LETTER}[”\u0022])(?={HAN})"
	rf"|(?<={ENGLISH_LETTER}[.!?][”\u0022])(?={HAN})"
)


def space_explanations(material):
	return {**material, "questions": [
		{**question, "explanation": MIXED_LANGUAGE_BOUNDARY.sub(" ", question["explanation"])}
		for question in material["questions"]
	]}


def validate_material(material):

	if not isinstance(material, dict) or not isinstance(material.get("kind"), str):
		raise MaterialGenerationError("Invalid listening material.")
	kind = material["kind"]
	if kind not in KINDS or material.get("section") != KINDS[kind][0]:
		raise MaterialGenerationError("Invalid section or exercise kind.")
	if not is_material_text(material.get("title"), 200):
		raise MaterialGenerationError("Missing or invalid title.")
	segments, questions = material.get("segments"), material.get("questions")
	validate_script_segments(segments, speakers = ("woman", "man", "narrator"))
	speakers = [segment["speaker"] for segment in segments]
	if kind == "passage":
		if set(speakers) != {"narrator"}:
			raise MaterialGenerationError("Passages must use the narrator.")
	else:
		valid_length = len(segments) == 2 if kind == "short_conversation" else 6 <= len(segments) <= 14
		if (not valid_length or set(speakers) != {"woman", "man"}
			or any(a == b for a, b in zip(speakers, speakers[1:]))):
			raise MaterialGenerationError("Conversations must have alternating woman/man turns.")
	if not isinstance(questions, list) or len(questions) != KINDS[kind][1]:
		raise MaterialGenerationError("Incorrect question count.")
	for question in questions:
		validate_multiple_choice_question(question)
	material = space_explanations(material)
	if any(len(question["explanation"]) > 2000 for question in material["questions"]):
		raise MaterialGenerationError("Explanation is too long after formatting.")
	return material


def generate_shanghai_material(*, topic, section = "A", kind = None):

	if not is_material_text(topic, 500):
		raise ValueError("Topic must contain 1-500 characters.")
	if section not in ("A", "B"):
		raise ValueError("Section must be A or B.")
	kind = kind or ("short_conversation" if section == "A" else "passage")
	if not isinstance(kind, str) or kind not in KINDS or KINDS[kind][0] != section:
		raise ValueError("Exercise kind does not match section.")
	prompt = (Path(__file__).resolve().parent.parent / "prompts" / "shanghai.txt").read_text(encoding = "utf-8")
	material = request_material_json(
		prompt = prompt,
		fields = {"section": section, "kind": kind, "topic": topic.strip()},
		max_tokens = 6000,
	)
	material = validate_material(material)
	if material["section"] != section or material["kind"] != kind:
		raise MaterialGenerationError("Model returned the wrong exercise kind.")
	return material
