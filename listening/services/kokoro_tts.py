from pathlib import Path

import soundfile
from django.conf import settings
from kokoro_onnx import Kokoro

_engine = None

def get_engine():
	global _engine

	if _engine is None:
		_engine = Kokoro(
			str(settings.KOKORO_MODEL_PATH),
			str(settings.KOKORO_VOICES_PATH),
		)

	return _engine


def generate_audio(text, output_path, voice = "af_heart", speed = 1.0):
	output_path = Path(output_path)
	output_path.parent.mkdir(parents = True, exist_ok = True)

	engine = get_engine()
	audio, sample_rate = engine.create(
		text,
		voice = voice,
		speed = speed,
		lang = "en-us",
	)

	soundfile.write(output_path, audio, sample_rate)
	return output_path
