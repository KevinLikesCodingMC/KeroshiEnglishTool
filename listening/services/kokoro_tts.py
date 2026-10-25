from pathlib import Path

import onnxruntime as ort
import soundfile
from django.conf import settings
from kokoro_onnx import Kokoro

from listening.voices import get_voice_language

_engine = None

def get_engine():
	global _engine

	if _engine is None:
		session_options = ort.SessionOptions()
		session_options.intra_op_num_threads = settings.KOKORO_CPU_THREADS
		session_options.inter_op_num_threads = 1
		session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
		session_options.add_session_config_entry(
			"session.intra_op.allow_spinning",
			"0",
		)

		session = ort.InferenceSession(
			str(settings.KOKORO_MODEL_PATH),
			sess_options = session_options,
			providers = ["CPUExecutionProvider"],
		)
		_engine = Kokoro.from_session(
			session,
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
		lang = get_voice_language(voice),
	)

	soundfile.write(output_path, audio, sample_rate)
	return output_path
