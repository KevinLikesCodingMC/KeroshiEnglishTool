from dataclasses import dataclass


@dataclass
class ImportedDocument:
	source_id: str
	words: list[str]
