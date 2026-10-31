import json
import re
import time
from collections import Counter
from collections.abc import Iterator
from typing import Any
from urllib.parse import quote

import requests

from .base import ImportedDocument


BASE_URL = "https://papers.over-achiever.org"
MANIFEST_URL = f"{BASE_URL}/api/manifest"
USER_AGENT = "KeroshiEnglishTool/0.1"

WORD_PATTERN = re.compile(r"[A-Za-z]+(?:[’'-][A-Za-z]+)*")
PREVIEW_PAPER_ID = "2026-huangpu-first"


def fetch_json(session: requests.Session, url: str) -> dict[str, Any]:
	response = session.get(url, timeout = 30)
	response.raise_for_status()
	payload = response.json()

	if not isinstance(payload, dict):
		raise ValueError(f"Expected a JSON object from {url}.")

	return payload


def extract_words(payload: dict[str, Any]) -> list[str]:
	words = []
	blocks = payload.get("blocks", [])

	if not isinstance(blocks, list):
		raise ValueError("Paper payload must contain a list of blocks.")

	for block in blocks:
		if not isinstance(block, dict):
			continue

		if block.get("role") == "heading":
			continue
		if block.get("questionType") == "all":
			continue

		text = block.get("text")
		if not isinstance(text, str):
			continue

		words.extend(
			match.group().replace("’", "'")
			for match in WORD_PATTERN.finditer(text)
		)

	return words


def iter_documents(
	*,
	paper_id: str | None = None,
	limit: int | None = None,
	delay: float = 0.2,
	**_options,
) -> Iterator[ImportedDocument]:
	if limit is not None and limit < 0:
		raise ValueError("limit must be at least 0.")
	if delay < 0:
		raise ValueError("delay must be at least 0.")

	with requests.Session() as session:
		session.headers.update(
			{
				"Accept": "application/json",
				"User-Agent": USER_AGENT,
			}
		)

		manifest = fetch_json(session, MANIFEST_URL)
		papers = manifest.get("papers", [])

		if not isinstance(papers, list):
			raise ValueError("Manifest must contain a list of papers.")

		if paper_id is not None:
			papers = [paper for paper in papers if paper.get("id") == paper_id]
			if not papers:
				raise ValueError(f"Paper {paper_id!r} was not found in the manifest.")

		if limit is not None:
			papers = papers[:limit]

		for index, paper in enumerate(papers):
			if not isinstance(paper, dict) or not isinstance(paper.get("id"), str):
				raise ValueError("Each manifest paper must have a string id.")

			source_paper_id = paper["id"]
			encoded_id = quote(source_paper_id, safe = "")
			payload = fetch_json(
				session,
				f"{BASE_URL}/api/papers/{encoded_id}",
			)

			yield ImportedDocument(
				source_id = f"shanghai-exam-bank:{source_paper_id}",
				words = extract_words(payload),
			)

			if index < len(papers) - 1 and delay:
				time.sleep(delay)


def main():
	document = next(
		iter_documents(
			paper_id = PREVIEW_PAPER_ID,
			delay = 0,
		)
	)
	word_counts = Counter(word.casefold() for word in document.words)
	print(json.dumps(word_counts.most_common(), ensure_ascii = False))


if __name__ == "__main__":
	main()
