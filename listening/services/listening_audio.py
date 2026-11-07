import math
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

import numpy as np
import soundfile
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from listening.models import ListeningJob, TTSJob
from listening.voices import VOICE_IDS
from .shanghai_materials import validate_material


DEFAULT_VOICES = {"woman": "af_heart", "man": "bm_lewis", "narrator": "af_heart"}
QUESTION_LABEL_PAUSE_MS = 500


@dataclass(frozen = True)
class Pacing:
	turn_pause_ms: int = 500
	before_questions_ms: int = 1500
	repeat_pause_ms: int = 3000
	answer_pause_ms: int = 5000

	def validate(self):
		for value in asdict(self).values():
			if type(value) is not int or not 0 <= value <= 30000:
				raise ValueError("Pauses must be integer milliseconds between 0 and 30000.")


def create_listening_job(material, *, voices = None, speed = 1.0, pacing = None):

	material = validate_material(material)
	pacing = pacing if pacing is not None else Pacing()
	pacing.validate()
	if isinstance(speed, bool) or not isinstance(speed, (int, float)) or not math.isfinite(speed) or not 0.5 <= speed <= 2:
		raise ValueError("Speed must be between 0.5 and 2.0.")
	voice_map = dict(DEFAULT_VOICES)
	if voices is not None:
		if not isinstance(voices, dict) or set(voices) - set(voice_map):
			raise ValueError("Unknown speaker in voice mapping.")
		voice_map.update(voices)
	if any(not isinstance(voice, str) or voice not in VOICE_IDS for voice in voice_map.values()):
		raise ValueError("Unknown voice.")
	segments = material["segments"]
	questions = material["questions"]
	playlist = []
	repeats = 1 if material["section"] == "A" else 2
	replay_cue_position = len(segments) + 2 * len(questions)
	before_replay_cue_ms = pacing.repeat_pause_ms // 2
	for repeat in range(repeats):
		for position in range(len(segments)):
			pause = pacing.turn_pause_ms
			if position == len(segments) - 1:
				pause = before_replay_cue_ms if repeat < repeats - 1 else pacing.before_questions_ms
			playlist.append({"position": position, "pause_after_ms": pause})
		if repeat < repeats - 1:
			playlist.append({"position": replay_cue_position,
				"pause_after_ms": pacing.repeat_pause_ms - before_replay_cue_ms})
	for index in range(len(questions)):
		label_position = len(segments) + 2 * index
		playlist.append({"position": label_position, "pause_after_ms": QUESTION_LABEL_PAUSE_MS})
		playlist.append({"position": label_position + 1, "pause_after_ms": pacing.answer_pause_ms})
	with transaction.atomic():
		job = ListeningJob.objects.create(material = material, playlist = playlist)
		clips = [(segment["text"], voice_map[segment["speaker"]]) for segment in segments]
		for number, question in enumerate(questions, start = 1):
			label = "Question" if material["section"] == "A" else f"Question {number}"
			clips.append((f"{label}.", voice_map["narrator"]))
			clips.append((question["text"].strip(), voice_map["narrator"]))
		if repeats == 2:
			clips.append(("Now listen again.", voice_map["narrator"]))
		TTSJob.objects.bulk_create([
			TTSJob(listening_job = job, position = position, text = text, voice = voice, speed = speed)
			for position, (text, voice) in enumerate(clips)
		])
	return job


def assemble_audio(playlist, clips, output_path):

	output_path = Path(output_path)
	output_path.parent.mkdir(parents = True, exist_ok = True)
	temporary_path = output_path.with_name(f".{output_path.stem}-{uuid4().hex}.wav")
	try:
		with soundfile.SoundFile(clips[playlist[0]["position"]]) as first:
			sample_rate = first.samplerate
		with soundfile.SoundFile(temporary_path, mode = "w", samplerate = sample_rate, channels = 1, subtype = "PCM_16") as output:
			for entry in playlist:
				pause = entry["pause_after_ms"]
				if type(pause) is not int or not 0 <= pause <= 30000:
					raise ValueError("Invalid pause in playlist.")
				with soundfile.SoundFile(clips[entry["position"]]) as clip:
					if clip.samplerate != sample_rate or clip.channels != 1:
						raise ValueError("All clips must have the same sample rate and be mono.")
					for block in clip.blocks(blocksize = 65536, dtype = "float32"):
						output.write(block)
				output.write(np.zeros(round(sample_rate * pause / 1000), dtype = "float32"))
		temporary_path.replace(output_path)
	finally:
		temporary_path.unlink(missing_ok = True)
	return output_path


def finalize_ready_jobs():

	finalized = False
	for job in ListeningJob.objects.filter(status = ListeningJob.Status.GENERATING).iterator():
		children = list(job.tts_jobs.all())
		failed = next((child for child in children if child.status == TTSJob.Status.FAILED), None)
		if failed is not None:
			ListeningJob.objects.filter(pk = job.pk, status = ListeningJob.Status.GENERATING).update(
				status = ListeningJob.Status.FAILED,
				error_message = f"TTS #{failed.pk}: {failed.error_message}", completed_at = timezone.now(),
			)
			finalized = True
			continue
		if not children or any(child.status != TTSJob.Status.COMPLETED for child in children):
			continue
		claimed = ListeningJob.objects.filter(pk = job.pk, status = ListeningJob.Status.GENERATING).update(status = ListeningJob.Status.ASSEMBLING)
		if not claimed:
			continue
		try:
			audio_name = f"listening/{job.pk}.wav"
			assemble_audio(job.playlist, {child.position: child.audio_file.path for child in children}, Path(settings.MEDIA_ROOT) / audio_name)
		except Exception as error:
			ListeningJob.objects.filter(pk = job.pk).update(
				status = ListeningJob.Status.FAILED, error_message = str(error), completed_at = timezone.now(),
			)
		else:
			ListeningJob.objects.filter(pk = job.pk).update(
				status = ListeningJob.Status.COMPLETED, audio_file = audio_name, error_message = "", completed_at = timezone.now(),
			)
		finalized = True
	return finalized


def retry_listening_job(job_id):

	with transaction.atomic():
		claimed = ListeningJob.objects.filter(pk = job_id, status = ListeningJob.Status.FAILED).update(
			status = ListeningJob.Status.GENERATING, error_message = "", completed_at = None,
		)
		if not claimed:
			raise ValueError("Only failed listening jobs can be retried.")
		TTSJob.objects.filter(listening_job_id = job_id, status = TTSJob.Status.FAILED).update(
			status = TTSJob.Status.QUEUED, error_message = "", started_at = None, completed_at = None, audio_file = "",
		)
