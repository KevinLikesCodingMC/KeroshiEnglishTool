from django.db import models

from .voices import DEFAULT_VOICE


class ListeningJob(models.Model):
	class Status:
		GENERATING = "generating"
		ASSEMBLING = "assembling"
		COMPLETED = "completed"
		FAILED = "failed"
		CHOICES = (
			(GENERATING, "生成片段中"),
			(ASSEMBLING, "拼接中"),
			(COMPLETED, "已完成"),
			(FAILED, "失败"),
		)

	material = models.JSONField("材料快照")
	playlist = models.JSONField("播放顺序")
	status = models.CharField("状态", max_length = 20, choices = Status.CHOICES, default = Status.GENERATING, db_index = True)
	audio_file = models.FileField("音频文件", upload_to = "listening/", blank = True)
	error_message = models.TextField("错误信息", blank = True)
	created_at = models.DateTimeField("创建时间", auto_now_add = True)
	completed_at = models.DateTimeField("完成时间", null = True, blank = True)

	class Meta:
		ordering = ["created_at", "id"]
		verbose_name = "听力生成任务"
		verbose_name_plural = "听力生成任务"

	def __str__(self):
		return f"听力任务 #{self.pk} - {self.get_status_display()}"


class TTSJob(models.Model):
	class Status:
		QUEUED = "queued"
		PROCESSING = "processing"
		COMPLETED = "completed"
		FAILED = "failed"
		CHOICES = (
			(QUEUED, "等待中"),
			(PROCESSING, "生成中"),
			(COMPLETED, "已完成"),
			(FAILED, "失败"),
		)

	listening_job = models.ForeignKey(ListeningJob, null = True, blank = True, on_delete = models.CASCADE, related_name = "tts_jobs")
	position = models.PositiveIntegerField(default = 0)
	text = models.TextField("文本")
	voice = models.CharField("音色", max_length = 50, default = DEFAULT_VOICE)
	speed = models.FloatField("语速", default = 1.0)
	status = models.CharField(
		"状态",
		max_length = 20,
		choices = Status.CHOICES,
		default = Status.QUEUED,
		db_index = True,
	)
	audio_file = models.FileField("音频文件", upload_to = "tts/", blank = True)
	error_message = models.TextField("错误信息", blank = True)
	created_at = models.DateTimeField("创建时间", auto_now_add = True)
	started_at = models.DateTimeField("开始时间", null = True, blank = True)
	completed_at = models.DateTimeField("完成时间", null = True, blank = True)

	class Meta:
		constraints = [models.UniqueConstraint(fields = ["listening_job", "position"], name = "unique_listening_tts_position")]
		ordering = ["created_at", "id"]
		verbose_name = "语音生成任务"
		verbose_name_plural = "语音生成任务"

	def __str__(self):
		return f"TTS #{self.pk} - {self.get_status_display()}"
